"""SPEC-016 unit tests — Ephemeris web page and regen-on-download endpoint.

Covers all acceptance criteria (unit-testable subset):
  - GET /ephemeris returns 200 with form
  - Valid range + profile renders scribal/kinematic/both previews
  - Download link present in preview response
  - GET /ephemeris/download returns Content-Disposition: attachment with correct filename
  - Repeated download call → byte-identical JSON (determinism)
  - Step < 5 min → form error (not 500)
  - Range > 7 days → form error (not 500)
  - Download with bad throttle → 400
  - Download with invalid profile → 400
  - Page contains no <script> tags
  - Ephemeris nav link present on all pages

UAT follows unit testing: see docs/devlog.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sask.config_loader import load_config
from sask.web import create_app

REAL_CONFIG = Path(__file__).parent.parent / "config"

CONFIG = load_config(REAL_CONFIG)
STORY = CONFIG.timeline.story_now_pulse
STEP_MIN = CONFIG.ephemeris.step_floor_pulses  # 300 pulses = 5 min
ONE_HOUR = 3600  # pulses
THIRTY_DAYS = CONFIG.ephemeris.range_cap_pulses  # 2592000


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def app():
    return create_app(config_dir=REAL_CONFIG)


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


# ── HTTP smoke ─────────────────────────────────────────────────────────────────


def test_ephemeris_returns_200(client):
    assert client.get("/ephemeris").status_code == 200


def test_ephemeris_has_form(client):
    data = client.get("/ephemeris").data
    assert b'action="/ephemeris"' in data


def test_ephemeris_no_script_tags(client):
    data = client.get("/ephemeris").data
    assert b"<script" not in data


def test_ephemeris_reset_button_present(client):
    data = client.get("/ephemeris").data
    assert b"Reset" in data
    assert b'href="/ephemeris"' in data


def test_ephemeris_nav_link_present(client):
    data = client.get("/ephemeris").data
    assert b'href="/ephemeris"' in data


def test_ephemeris_nav_link_on_sky_page(client):
    data = client.get("/sky").data
    assert b'href="/ephemeris"' in data


# ── Preview rendering ─────────────────────────────────────────────────────────


def _valid_qs(profile="scribal", step_minutes=5):
    return (
        f"/ephemeris?start_pulse={STORY}&end_pulse={STORY + ONE_HOUR}"
        f"&step_minutes={step_minutes}&profile={profile}"
    )


def test_ephemeris_scribal_preview_200(client):
    assert client.get(_valid_qs("scribal")).status_code == 200


def test_ephemeris_scribal_preview_present(client):
    data = client.get(_valid_qs("scribal")).data
    assert b"scribal" in data
    assert b'"profile"' in data or b"Scribal preview" in data


def test_ephemeris_kinematic_preview_present(client):
    data = client.get(_valid_qs("kinematic")).data
    assert b"kinematic" in data
    assert b'"profile"' in data or b"Kinematic preview" in data


def test_ephemeris_both_previews_present(client):
    data = client.get(_valid_qs("both")).data
    assert b"Scribal preview" in data
    assert b"Kinematic preview" in data


def test_ephemeris_preview_has_download_link(client):
    data = client.get(_valid_qs("scribal")).data
    assert b"/ephemeris/download" in data


def test_ephemeris_params_in_query_string(client):
    resp = client.get(_valid_qs("scribal"))
    assert b"start_pulse" in resp.data or STORY in (resp.data or b"")
    assert resp.status_code == 200


# ── Duration (Days) mode ──────────────────────────────────────────────────────


def _duration_qs(duration_days=1, profile="scribal"):
    return (
        f"/ephemeris?start_astro_day=1&duration_days={duration_days}"
        f"&step_minutes=5&profile={profile}"
    )


def test_ephemeris_duration_mode_200(client):
    assert client.get(_duration_qs()).status_code == 200


def test_ephemeris_duration_mode_preview_present(client):
    data = client.get(_duration_qs()).data
    assert b"Scribal preview" in data or b'"profile"' in data


def test_ephemeris_duration_mode_computed_end_shown(client):
    data = client.get(_duration_qs(duration_days=2)).data
    assert b"End:" in data


def test_ephemeris_duration_mode_download_link_present(client):
    data = client.get(_duration_qs()).data
    assert b"/ephemeris/download" in data


def test_ephemeris_duration_missing_no_500(client):
    qs = "/ephemeris?start_astro_day=1&step_minutes=5&profile=scribal"
    resp = client.get(qs)
    assert resp.status_code == 200
    assert b"Duration" in resp.data or b"required" in resp.data.lower()


def test_ephemeris_duration_zero_no_500(client):
    qs = "/ephemeris?start_astro_day=1&duration_days=0&step_minutes=5&profile=scribal"
    resp = client.get(qs)
    assert resp.status_code == 200
    assert b"error" in resp.data.lower() or b"least" in resp.data.lower()


# ── Throttle validation ───────────────────────────────────────────────────────


def test_ephemeris_step_too_small_no_500(client):
    qs = (
        f"/ephemeris?start_pulse={STORY}&end_pulse={STORY + ONE_HOUR}"
        f"&step_minutes=1&profile=scribal"
    )
    resp = client.get(qs)
    assert resp.status_code == 200
    data = resp.data
    assert (
        b"error" in data.lower()
        or b"minimum" in data.lower()
        or b"below" in data.lower()
    )


def test_ephemeris_range_too_large_no_500(client):
    over_cap = THIRTY_DAYS + ONE_HOUR
    qs = (
        f"/ephemeris?start_pulse={STORY}&end_pulse={STORY + over_cap}"
        f"&step_minutes=5&profile=scribal"
    )
    resp = client.get(qs)
    assert resp.status_code == 200
    data = resp.data
    assert (
        b"error" in data.lower()
        or b"maximum" in data.lower()
        or b"exceeds" in data.lower()
    )


# ── Download endpoint ─────────────────────────────────────────────────────────


def _dl_url(profile="scribal"):
    return (
        f"/ephemeris/download?start={STORY}&end={STORY + ONE_HOUR}"
        f"&step={STEP_MIN}&profile={profile}"
    )


def test_download_returns_200(client):
    assert client.get(_dl_url()).status_code == 200


def test_download_content_disposition(client):
    resp = client.get(_dl_url())
    cd = resp.headers.get("Content-Disposition", "")
    assert "attachment" in cd


def test_download_correct_filename_scribal(client):
    resp = client.get(_dl_url("scribal"))
    cd = resp.headers.get("Content-Disposition", "")
    expected = f"ephemeris_scribal_p{STORY}-{STORY + ONE_HOUR}_s{STEP_MIN}.json"
    assert expected in cd


def test_download_correct_filename_kinematic(client):
    resp = client.get(_dl_url("kinematic"))
    cd = resp.headers.get("Content-Disposition", "")
    expected = f"ephemeris_kinematic_p{STORY}-{STORY + ONE_HOUR}_s{STEP_MIN}.json"
    assert expected in cd


def test_download_content_type_json(client):
    resp = client.get(_dl_url())
    assert "application/json" in resp.content_type


def test_download_determinism(client):
    body1 = client.get(_dl_url()).data
    body2 = client.get(_dl_url()).data
    assert body1 == body2


def test_download_kinematic_determinism(client):
    body1 = client.get(_dl_url("kinematic")).data
    body2 = client.get(_dl_url("kinematic")).data
    assert body1 == body2


def test_download_step_too_small_400(client):
    url = f"/ephemeris/download?start={STORY}&end={STORY + ONE_HOUR}&step=60&profile=scribal"
    assert client.get(url).status_code == 400


def test_download_range_too_large_400(client):
    over = THIRTY_DAYS + ONE_HOUR
    url = f"/ephemeris/download?start={STORY}&end={STORY + over}&step={STEP_MIN}&profile=scribal"
    assert client.get(url).status_code == 400


def test_download_invalid_profile_400(client):
    url = f"/ephemeris/download?start={STORY}&end={STORY + ONE_HOUR}&step={STEP_MIN}&profile=magic"
    assert client.get(url).status_code == 400


def test_download_missing_params_400(client):
    assert client.get("/ephemeris/download?start=0").status_code == 400


def test_download_scribal_valid_json(client):
    import json

    body = client.get(_dl_url("scribal")).data
    parsed = json.loads(body)
    assert parsed.get("profile") == "scribal"
    assert "steps" in parsed


def test_download_kinematic_valid_json(client):
    import json

    body = client.get(_dl_url("kinematic")).data
    parsed = json.loads(body)
    assert parsed.get("profile") == "kinematic"
    assert "steps" in parsed


# ── Step-vs-duration validation ───────────────────────────────────────────────


def test_ephemeris_step_exceeds_duration_no_500(client):
    # step=1440 min == duration=1 day (1440 min); step >= span → form error.
    qs = (
        "/ephemeris?start_astro_day=1&duration_days=1&step_minutes=1440&profile=scribal"
    )
    resp = client.get(qs)
    assert resp.status_code == 200
    data = resp.data.lower()
    assert b"error" in data or b"exceeds" in data or b"duration" in data


def test_download_step_exceeds_range_400(client):
    # step=600 pulses, range=300 pulses: step >= range → 400.
    url = (
        f"/ephemeris/download?start={STORY}&end={STORY + 300}&step=600&profile=scribal"
    )
    assert client.get(url).status_code == 400

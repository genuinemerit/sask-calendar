"""SPEC-014 unit tests — Unified Sky-for-a-date web view.

Covers all acceptance criteria (unit-testable subset):
  - GET /sky returns 200 with form; with valid pulse renders all panels
  - All date formats rendered: Fatunik, Terpin, all four lunar calendars
  - Season, sky bodies (moons/planets), stars & houses, co-fullness, night
    summary, and image prompt all present in the response
  - No JavaScript in the page
  - Fatunik and Terpin date input accepted as well as pulse
  - Invalid pulse → 200 with error (no 500)
  - Lunar calendars are display-only (no lunar input fields)
  - Pulse rides in the query string (input field cross-populated)
  - Drill-down links to /moons and /planets present when bodies are above horizon
  - Sky nav link present on all pages (base.html update)

UAT follows unit testing: see docs/devlog.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sask.config_loader import load_config
from sask.lunar import get_cofullness
from sask.web import create_app

REAL_CONFIG = Path(__file__).parent.parent / "config"
PROJECT_ROOT = Path(__file__).parent.parent

CONFIG = load_config(REAL_CONFIG)
PPD = CONFIG.time_constants.pulses_per_day
STORY_PULSE = CONFIG.timeline.story_now_pulse


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def app():
    return create_app(config_dir=REAL_CONFIG)


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


# ── HTTP smoke ─────────────────────────────────────────────────────────────────


def test_sky_returns_200(client):
    assert client.get("/sky").status_code == 200


def test_sky_with_pulse_returns_200(client):
    assert client.get(f"/sky?pulse={STORY_PULSE}").status_code == 200


def test_sky_invalid_pulse_returns_200_not_500(client):
    resp = client.get("/sky?pulse=notanumber")
    assert resp.status_code == 200
    assert b"Invalid" in resp.data or b"error" in resp.data.lower()


def test_sky_no_input_shows_form(client):
    data = client.get("/sky").data
    assert b'action="/sky"' in data
    assert b"pulse" in data


# ── Date panel ────────────────────────────────────────────────────────────────


def test_sky_shows_fatunik_date(client):
    resp = client.get(f"/sky?pulse={STORY_PULSE}")
    # Fatunik date uses T<year> M<month> D<day> notation
    assert b"Fatunik" in resp.data


def test_sky_shows_terpin_date(client):
    resp = client.get(f"/sky?pulse={STORY_PULSE}")
    assert b"Terpin" in resp.data


def test_sky_shows_astro_day(client):
    resp = client.get(f"/sky?pulse={STORY_PULSE}")
    astro_day = STORY_PULSE // PPD + 1
    assert str(astro_day).encode() in resp.data


# ── Lunar calendar panel ──────────────────────────────────────────────────────


def test_sky_shows_all_four_lunar_calendars(client):
    data = client.get(f"/sky?pulse={STORY_PULSE}").data
    assert b"Untamed" in data
    assert b"Warren" in data
    assert b"Hearth" in data
    assert b"Terpin" in data


def test_sky_lunar_calendars_display_only(client):
    """No lunar calendar input fields — output only."""
    data = client.get("/sky").data
    # Input fields should only be for pulse, astro_day, fatunik, terpin
    assert b"lunar_year" not in data
    assert b"untamed_year" not in data
    assert b"warren_year" not in data


# ── Season panel ──────────────────────────────────────────────────────────────


def test_sky_shows_season(client):
    data = client.get(f"/sky?pulse={STORY_PULSE}").data
    season_words = [b"Greening", b"Blazing", b"Withering", b"Stillness"]
    assert any(w in data for w in season_words)


# ── Sky body panels ───────────────────────────────────────────────────────────


def test_sky_shows_moons_section(client):
    data = client.get(f"/sky?pulse={STORY_PULSE}").data
    assert b"Moons" in data


def test_sky_shows_wanderers_section(client):
    data = client.get(f"/sky?pulse={STORY_PULSE}").data
    assert b"Wanderers" in data


def test_sky_body_links_point_to_moons_page(client):
    """Moons above the horizon link through to /moons."""
    data = client.get(f"/sky?pulse={STORY_PULSE}").data
    assert b"/moons?pulse=" in data


def test_sky_body_links_point_to_planets_page(client):
    """Planets above the horizon link through to /planets."""
    data = client.get(f"/sky?pulse={STORY_PULSE}").data
    assert b"/planets?pulse=" in data


# ── Stars & houses panel ──────────────────────────────────────────────────────


def test_sky_shows_active_house(client):
    data = client.get(f"/sky?pulse={STORY_PULSE}").data
    assert b"Active house" in data or b"active house" in data.lower()
    assert b"House" in data


# ── Co-fullness panel ─────────────────────────────────────────────────────────


def test_sky_shows_cofullness_section(client):
    data = client.get(f"/sky?pulse={STORY_PULSE}").data
    assert b"Co-fullness" in data or b"co-fullness" in data.lower()


def test_sky_shows_next_cofullness(client):
    data = client.get(f"/sky?pulse={STORY_PULSE}").data
    assert b"Next event" in data


def test_sky_shows_cofullness_this_day_at_known_event(client):
    """At a known co-fullness midnight, the 'This day' indicator appears."""
    events = get_cofullness(0, 365 * PPD, CONFIG)
    assert events, "Need at least one co-fullness event for this test"
    ev = events[0]
    data = client.get(f"/sky?pulse={ev.pulse}").data
    assert b"This day" in data


# ── Night summary & image prompt ──────────────────────────────────────────────


def test_sky_shows_night_summary(client):
    data = client.get(f"/sky?pulse={STORY_PULSE}").data
    assert b"Night Summary" in data


def test_sky_shows_image_prompt(client):
    data = client.get(f"/sky?pulse={STORY_PULSE}").data
    assert b"Image Prompt" in data


def test_sky_image_prompt_contains_style_text(client):
    """Image prompt section should contain style directive text."""
    data = client.get(f"/sky?pulse={STORY_PULSE}").data
    assert b"Image style" in data


# ── Input methods ─────────────────────────────────────────────────────────────


def test_sky_accepts_fatunik_date_input(client):
    from sask.pulse import astro_to_fatunik

    fd = astro_to_fatunik(STORY_PULSE, CONFIG)
    url = f"/sky?fatunik_year={fd.year}&fatunik_month={fd.month}&fatunik_day={fd.day}"
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"Fatunik" in resp.data
    assert b"Untamed" in resp.data


def test_sky_accepts_terpin_date_input(client):
    from sask.pulse import astro_to_terpin

    td = astro_to_terpin(STORY_PULSE, CONFIG)
    url = f"/sky?terpin_year={td.year}&terpin_month={td.month}&terpin_day={td.day}"
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"Terpin" in resp.data
    assert b"Warren" in resp.data


def test_sky_fatunik_date_input_returns_day_start_time(client):
    """Entering a Fatunik date should show 06:00:00 (Fatunik calendar day start)."""
    from sask.pulse import astro_to_fatunik

    fd = astro_to_fatunik(STORY_PULSE, CONFIG)
    url = f"/sky?fatunik_year={fd.year}&fatunik_month={fd.month}&fatunik_day={fd.day}"
    data = client.get(url).data
    assert b"06:00:00" in data


# ── Bookmarkability ───────────────────────────────────────────────────────────


def test_sky_pulse_rides_in_query_string(client):
    """The queried pulse appears in the form's pulse input so URLs are shareable."""
    data = client.get(f"/sky?pulse={STORY_PULSE}").data
    assert str(STORY_PULSE).encode() in data


def test_sky_reload_reproduces_view(client):
    """Same URL produces identical response (determinism)."""
    url = f"/sky?pulse={STORY_PULSE}"
    assert client.get(url).data == client.get(url).data


# ── No JavaScript ─────────────────────────────────────────────────────────────


def test_sky_has_no_javascript(client):
    data = client.get(f"/sky?pulse={STORY_PULSE}").data
    assert b"<script" not in data


def test_sky_no_input_has_no_javascript(client):
    assert b"<script" not in client.get("/sky").data


# ── Nav link ──────────────────────────────────────────────────────────────────


def test_sky_nav_link_on_moons_page(client):
    assert b'href="/sky"' in client.get("/moons").data


def test_sky_nav_link_on_planets_page(client):
    assert b'href="/sky"' in client.get("/planets").data


def test_sky_nav_link_on_sky_page(client):
    assert b'href="/sky"' in client.get("/sky").data

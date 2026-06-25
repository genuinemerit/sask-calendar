"""SPEC-015 tests — sky-scene ephemeris: generator and JSON renderers.

Covers all acceptance criteria:
  - Steps produced at exactly the requested cadence
  - step < 5 min or range > 30 days is refused with ValueError
  - Identical (start, end, step, config) yields byte-identical JSON
  - Per-day context appears once per Astro day; steps reference it
  - Kinematic includes below-horizon bodies (up=False, negative altitude)
  - No civil/lore term appears in scribal or kinematic output
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sask.config_loader import load_config
from sask.calendar.ephemeris import (
    get_sky_series,
    render_kinematic_json,
    render_scribal_json,
)

CONFIG = load_config(Path(__file__).parent.parent / "config")
PPD = CONFIG.time_constants.pulses_per_day

_STORY = CONFIG.timeline.story_now_pulse
_STEP = CONFIG.ephemeris.step_floor_pulses  # 300


# ── Config loading ────────────────────────────────────────────────────────────


def test_ephemeris_config_loaded():
    assert CONFIG.ephemeris.step_floor_pulses == 300
    assert CONFIG.ephemeris.range_cap_pulses == 2592000
    assert len(CONFIG.ephemeris.tracked_bodies) > 0


def test_tracked_bodies_exist_in_engine():
    body_ids = {b.name.lower() for b in CONFIG.bodies}
    for tid in CONFIG.ephemeris.tracked_bodies:
        assert tid in body_ids, f"tracked body {tid!r} not found in engine bodies"


# ── Throttle validation ───────────────────────────────────────────────────────


def test_step_below_floor_raises():
    with pytest.raises(ValueError, match="below the minimum"):
        get_sky_series(_STORY, _STORY + 3600, 299, CONFIG)


def test_step_at_floor_is_accepted():
    series = get_sky_series(_STORY, _STORY + _STEP, _STEP, CONFIG)
    assert len(series.steps) >= 1


def test_range_above_cap_raises():
    over = CONFIG.ephemeris.range_cap_pulses + 1
    with pytest.raises(ValueError, match="exceeds the maximum"):
        get_sky_series(_STORY, _STORY + over, _STEP, CONFIG)


def test_range_at_cap_is_accepted():
    cap = CONFIG.ephemeris.range_cap_pulses
    ppd = CONFIG.time_constants.pulses_per_day
    # Use a 1-day step to keep scene count to ~30 rather than 8640.
    series = get_sky_series(_STORY, _STORY + cap, ppd, CONFIG)
    assert len(series.steps) > 0


def test_end_before_start_raises():
    with pytest.raises(ValueError, match="before start_pulse"):
        get_sky_series(_STORY + 1000, _STORY, _STEP, CONFIG)


# ── Step cadence ──────────────────────────────────────────────────────────────


def test_correct_step_cadence():
    start = _STORY
    end = _STORY + 3600  # 1 hour
    step = _STEP
    series = get_sky_series(start, end, step, CONFIG)
    expected = list(range(start, end + 1, step))
    assert [s.pulse for s in series.steps] == expected


def test_single_step_when_step_exceeds_range():
    series = get_sky_series(_STORY, _STORY + 100, _STEP, CONFIG)
    assert len(series.steps) == 1
    assert series.steps[0].pulse == _STORY


def test_exact_endpoint_included():
    end = _STORY + 4 * _STEP
    series = get_sky_series(_STORY, end, _STEP, CONFIG)
    assert series.steps[-1].pulse == end


def test_start_equals_end_gives_one_step():
    series = get_sky_series(_STORY, _STORY, _STEP, CONFIG)
    assert len(series.steps) == 1


# ── Per-day context ───────────────────────────────────────────────────────────


def test_per_day_context_once_per_astro_day():
    # Span two Astro days by starting close to midnight
    day_start = (_STORY // PPD) * PPD
    start = day_start + PPD - 3 * _STEP  # last 15 min of day N
    end = start + 6 * _STEP  # crosses into day N+1
    series = get_sky_series(start, end, _STEP, CONFIG)
    days_from_steps = {s.astro_day for s in series.steps}
    assert set(series.day_contexts.keys()) == days_from_steps
    assert len(series.day_contexts) == len(days_from_steps)


def test_day_context_has_valid_season():
    series = get_sky_series(_STORY, _STORY + 1800, _STEP, CONFIG)
    valid = {"greening", "blazing", "withering", "stillness"}
    for ctx in series.day_contexts.values():
        assert ctx.season_id in valid


def test_day_context_body_rts_covers_all_bodies():
    series = get_sky_series(_STORY, _STORY + _STEP, _STEP, CONFIG)
    body_ids = {b.name.lower() for b in CONFIG.bodies}
    ctx = next(iter(series.day_contexts.values()))
    assert set(ctx.body_rts.keys()) == body_ids


# ── Determinism ───────────────────────────────────────────────────────────────


def test_scribal_json_deterministic():
    kwargs = (_STORY, _STORY + 1800, _STEP, CONFIG)
    s1 = render_scribal_json(get_sky_series(*kwargs), CONFIG)
    s2 = render_scribal_json(get_sky_series(*kwargs), CONFIG)
    assert s1 == s2


def test_kinematic_json_deterministic():
    kwargs = (_STORY, _STORY + 1800, _STEP, CONFIG)
    s1 = render_kinematic_json(get_sky_series(*kwargs), CONFIG)
    s2 = render_kinematic_json(get_sky_series(*kwargs), CONFIG)
    assert s1 == s2


# ── Scribal JSON structure ────────────────────────────────────────────────────


def test_scribal_json_parses():
    text = render_scribal_json(
        get_sky_series(_STORY, _STORY + 1800, _STEP, CONFIG), CONFIG
    )
    data = json.loads(text)
    assert data["profile"] == "scribal"


def test_scribal_step_count_matches():
    series = get_sky_series(_STORY, _STORY + 1800, _STEP, CONFIG)
    data = json.loads(render_scribal_json(series, CONFIG))
    assert data["step_count"] == len(series.steps)
    assert len(data["steps"]) == data["step_count"]


def test_scribal_step_has_required_fields():
    data = json.loads(
        render_scribal_json(
            get_sky_series(_STORY, _STORY + _STEP, _STEP, CONFIG), CONFIG
        )
    )
    step = data["steps"][0]
    for field in (
        "pulse",
        "astro_day",
        "time_of_day",
        "bodies_up",
        "stars_up",
        "active_house",
        "circumpolar_houses",
        "co_fullness_tonight",
        "summary",
    ):
        assert field in step, f"scribal step missing field {field!r}"


def test_scribal_time_of_day_format():
    data = json.loads(
        render_scribal_json(
            get_sky_series(_STORY, _STORY + _STEP, _STEP, CONFIG), CONFIG
        )
    )
    tod = data["steps"][0]["time_of_day"]
    parts = tod.split(":")
    assert len(parts) == 3
    assert all(len(p) == 2 and p.isdigit() for p in parts)


def test_scribal_days_block_matches_steps():
    series = get_sky_series(_STORY, _STORY + 1800, _STEP, CONFIG)
    data = json.loads(render_scribal_json(series, CONFIG))
    step_days = {str(s["astro_day"]) for s in data["steps"]}
    assert set(data["days"].keys()) == step_days


# ── Kinematic JSON structure ──────────────────────────────────────────────────


def test_kinematic_json_parses():
    text = render_kinematic_json(
        get_sky_series(_STORY, _STORY + 1800, _STEP, CONFIG), CONFIG
    )
    data = json.loads(text)
    assert data["profile"] == "kinematic"


def test_kinematic_step_count_matches():
    series = get_sky_series(_STORY, _STORY + 1800, _STEP, CONFIG)
    data = json.loads(render_kinematic_json(series, CONFIG))
    assert data["step_count"] == len(series.steps)
    assert len(data["steps"]) == data["step_count"]


def test_kinematic_all_tracked_bodies_in_every_step():
    series = get_sky_series(_STORY, _STORY + _STEP, _STEP, CONFIG)
    data = json.loads(render_kinematic_json(series, CONFIG))
    tracked = set(data["tracked_bodies"])
    for step in data["steps"]:
        assert set(step["bodies"].keys()) == tracked


def test_kinematic_body_has_required_fields():
    data = json.loads(
        render_kinematic_json(
            get_sky_series(_STORY, _STORY + _STEP, _STEP, CONFIG), CONFIG
        )
    )
    body = next(iter(data["steps"][0]["bodies"].values()))
    for field in ("alt", "az", "ill", "up"):
        assert field in body, f"kinematic body missing field {field!r}"


def test_kinematic_includes_below_horizon():
    series = get_sky_series(_STORY, _STORY + 1800, _STEP, CONFIG)
    data = json.loads(render_kinematic_json(series, CONFIG))
    found_below = any(
        not body["up"] for step in data["steps"] for body in step["bodies"].values()
    )
    assert found_below, "kinematic should include at least one below-horizon body"


def test_kinematic_below_horizon_has_negative_altitude():
    series = get_sky_series(_STORY, _STORY + 1800, _STEP, CONFIG)
    data = json.loads(render_kinematic_json(series, CONFIG))
    for step in data["steps"]:
        for body in step["bodies"].values():
            if not body["up"]:
                assert body["alt"] < 0.0, (
                    f"below-horizon body has non-negative altitude {body['alt']}"
                )


# ── No lore/civil terms ───────────────────────────────────────────────────────

# "fatunik" / "terpin" are calendar names; shur/keyt/kell/deshan are constructed
# lore words that cannot appear naturally in engine data.
# "watch" is excluded: "The Watchers of Stillness" is a legitimate house name.
_LORE_TERMS = {"fatunik", "terpin", "shur", "keyt", "kell", "deshan"}


def test_scribal_no_lore_terms():
    text = render_scribal_json(
        get_sky_series(_STORY, _STORY + 1800, _STEP, CONFIG), CONFIG
    ).lower()
    for term in _LORE_TERMS:
        assert term not in text, f"lore term {term!r} found in scribal JSON"


def test_kinematic_no_lore_terms():
    text = render_kinematic_json(
        get_sky_series(_STORY, _STORY + 1800, _STEP, CONFIG), CONFIG
    ).lower()
    for term in _LORE_TERMS:
        assert term not in text, f"lore term {term!r} found in kinematic JSON"

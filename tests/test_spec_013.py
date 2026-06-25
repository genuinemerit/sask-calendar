"""SPEC-013 tests — sky-scene composition and text rendering.

Covers all acceptance criteria:
  - Scene contains only bodies with altitude > 0; each body placed by direction
  - render_night_summary and render_image_prompt are deterministic
  - render_image_prompt = summary + selected style directives; style switch works
  - co_fullness_tonight and next_co_fullness match the SPEC-012 tracker
  - No renderer performs a network call
  - Styles and scene inputs are read from config; nothing hardcoded
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from sask.config_loader import load_config
from sask.calendar.lunar import get_cofullness
from sask.message import SkyScene, validate
from sask.calendar.scene import get_sky_scene, render_image_prompt, render_night_summary

CONFIG = load_config(Path(__file__).parent.parent / "config")
PROJECT_ROOT = Path(__file__).parent.parent

PPD = CONFIG.time_constants.pulses_per_day

# A stable pulse mid-day on a well-defined Astro day (Astro year 1, day 30)
_STORY_PULSE = CONFIG.timeline.story_now_pulse
_EARLY_PULSE = 30 * PPD + PPD // 2  # day 30, noon-ish


# ── Config loading ────────────────────────────────────────────────────────────


def test_sky_styles_loaded():
    assert len(CONFIG.sky_styles) >= 2


def test_sky_style_settings_loaded():
    assert CONFIG.sky_style_settings.default_style != ""


def test_default_style_exists_in_styles():
    ids = {s.id for s in CONFIG.sky_styles}
    assert CONFIG.sky_style_settings.default_style in ids


def test_sky_style_required_fields_present():
    for style in CONFIG.sky_styles:
        assert style.id
        assert style.name
        assert style.medium
        assert style.palette
        assert style.composition


# ── Scene composition ─────────────────────────────────────────────────────────


def test_all_bodies_up_above_horizon():
    scene = get_sky_scene(_EARLY_PULSE, CONFIG)
    for body in scene.bodies_up:
        assert body.altitude > 0.0, (
            f"{body.name} altitude {body.altitude:.2f} not positive"
        )


def test_bodies_up_have_valid_types():
    scene = get_sky_scene(_EARLY_PULSE, CONFIG)
    valid = {"moon", "planet", "comet", "spark"}
    for body in scene.bodies_up:
        assert body.body_type in valid, f"Unknown body_type {body.body_type!r}"


def test_scene_has_active_house():
    scene = get_sky_scene(_EARLY_PULSE, CONFIG)
    assert scene.active_house is not None
    assert scene.active_house.id
    assert scene.active_house.name


def test_scene_season_matches_spec004():
    from sask.calendar.season import season_info

    scene = get_sky_scene(_EARLY_PULSE, CONFIG)
    si = season_info(_EARLY_PULSE, CONFIG)
    assert scene.season == si.season_id


def test_scene_is_deterministic():
    a = get_sky_scene(_EARLY_PULSE, CONFIG)
    b = get_sky_scene(_EARLY_PULSE, CONFIG)
    assert a == b


def test_next_cofullness_after_today():
    scene = get_sky_scene(_EARLY_PULSE, CONFIG)
    today_midnight = (_EARLY_PULSE // PPD) * PPD
    assert scene.next_co_fullness.pulse > today_midnight


def test_cofullness_tonight_matches_spec012():
    """At a known co-fullness midnight, scene.co_fullness_tonight reports it."""
    events = get_cofullness(0, 365 * PPD, CONFIG)
    assert events, "Expected at least one co-fullness event in first year"
    ev = events[0]
    scene = get_sky_scene(ev.pulse, CONFIG)
    assert scene.co_fullness_tonight is not None
    assert scene.co_fullness_tonight.count == ev.count
    assert scene.co_fullness_tonight.moons == ev.moons


def test_cofullness_tonight_absent_on_ordinary_night():
    """At a midnight with no co-fullness event, co_fullness_tonight is None."""
    events = get_cofullness(0, 365 * PPD, CONFIG)
    event_pulses = {ev.pulse for ev in events}
    # Find first midnight in [0, 365 days] not in the event set
    candidate = 0
    for day in range(365):
        p = day * PPD
        if p not in event_pulses:
            candidate = p
            break
    scene = get_sky_scene(candidate + PPD // 4, CONFIG)  # mid-morning on that day
    today_midnight = (candidate + PPD // 4) // PPD * PPD
    assert today_midnight not in event_pulses
    assert scene.co_fullness_tonight is None


def test_scene_at_story_now():
    """Scene can be computed at story_now without error."""
    scene = get_sky_scene(_STORY_PULSE, CONFIG)
    assert isinstance(scene, SkyScene)


# ── Renderers ─────────────────────────────────────────────────────────────────


def test_night_summary_nonempty():
    scene = get_sky_scene(_EARLY_PULSE, CONFIG)
    text = render_night_summary(scene, CONFIG)
    assert len(text) > 20


def test_night_summary_contains_season_text():
    scene = get_sky_scene(_EARLY_PULSE, CONFIG)
    text = render_night_summary(scene, CONFIG)
    assert scene.season in text or any(
        word in text.lower()
        for word in ("greening", "blazing", "withering", "stillness")
    )


def test_night_summary_is_deterministic():
    scene = get_sky_scene(_EARLY_PULSE, CONFIG)
    assert render_night_summary(scene, CONFIG) == render_night_summary(scene, CONFIG)


def test_image_prompt_nonempty():
    scene = get_sky_scene(_EARLY_PULSE, CONFIG)
    text = render_image_prompt(scene, CONFIG)
    assert len(text) > 50


def test_image_prompt_is_deterministic():
    scene = get_sky_scene(_EARLY_PULSE, CONFIG)
    assert render_image_prompt(scene, CONFIG) == render_image_prompt(scene, CONFIG)


def test_image_prompt_contains_night_summary():
    """Image prompt starts with the night-summary text."""
    scene = get_sky_scene(_EARLY_PULSE, CONFIG)
    summary = render_night_summary(scene, CONFIG)
    prompt = render_image_prompt(scene, CONFIG)
    assert prompt.startswith(summary)


def test_image_prompt_contains_default_style_medium():
    scene = get_sky_scene(_EARLY_PULSE, CONFIG)
    default_id = CONFIG.sky_style_settings.default_style
    default_style = next(s for s in CONFIG.sky_styles if s.id == default_id)
    prompt = render_image_prompt(scene, CONFIG)
    assert default_style.medium in prompt


def test_image_prompt_style_switch_changes_output():
    """Selecting a different style produces different prompt text."""
    scene = get_sky_scene(_EARLY_PULSE, CONFIG)
    assert len(CONFIG.sky_styles) >= 2, "Need at least two styles to test switching"
    ids = [s.id for s in CONFIG.sky_styles]
    prompt_a = render_image_prompt(scene, CONFIG, style_id=ids[0])
    prompt_b = render_image_prompt(scene, CONFIG, style_id=ids[1])
    assert prompt_a != prompt_b


def test_image_prompt_explicit_style_id():
    """Passing an explicit style_id applies that style's directives."""
    scene = get_sky_scene(_EARLY_PULSE, CONFIG)
    for style in CONFIG.sky_styles:
        prompt = render_image_prompt(scene, CONFIG, style_id=style.id)
        assert style.medium in prompt
        assert style.palette in prompt


def test_no_network_calls_in_scene_module():
    source = (PROJECT_ROOT / "src/sask/calendar/scene.py").read_text(encoding="utf-8")
    for bad in ("urllib", "requests", "httpx", "aiohttp", "socket"):
        assert bad not in source, f"Found {bad!r} in scene.py"


def test_scene_module_has_no_flask_import():
    path = PROJECT_ROOT / "src/sask/calendar/scene.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    flask_imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        and any(
            "flask" in (alias.name or "").lower()
            for alias in getattr(node, "names", [])
        )
        or isinstance(node, ast.ImportFrom)
        and "flask" in (getattr(node, "module", "") or "").lower()
    ]
    assert flask_imports == []


# ── Message unit validity ─────────────────────────────────────────────────────


def test_sky_scene_is_frozen_dataclass():
    scene = get_sky_scene(_EARLY_PULSE, CONFIG)
    assert isinstance(scene, SkyScene)
    with pytest.raises((AttributeError, TypeError)):
        scene.season = "blazing"  # type: ignore[misc]


def test_sky_scene_validates():
    scene = get_sky_scene(_EARLY_PULSE, CONFIG)
    assert validate(scene) == []


def test_validate_skips_optional_none_field():
    """validate() must not flag co_fullness_tonight=None as an error."""
    # Force a scene with co_fullness_tonight=None via the ordinary no-event path
    events = get_cofullness(0, 365 * PPD, CONFIG)
    event_pulses = {ev.pulse for ev in events}
    for day in range(365):
        p = day * PPD
        if p not in event_pulses:
            scene_no_cf = get_sky_scene(p + PPD // 4, CONFIG)
            if scene_no_cf.co_fullness_tonight is None:
                assert validate(scene_no_cf) == []
                return
    pytest.skip("No ordinary night found in first year to test optional=None path")

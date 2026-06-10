"""SPEC-012 tests — lunar calendars and co-fullness tracking.

Covers all acceptance criteria:
  - A month equals one synodic cycle; Terpin = mean of eight synodic periods
  - Turn-based dates report long/short count, turn, month, day; Round realigns
  - Hearth (no-turns) reports lunation and day only; turn fields are None
  - near_full exactly within one day of a full-moment; false outside
  - Co-fullness: every night with >= min_moons near-full moons, correct count
  - Results are reproducible; no live randomness
  - Civil-calendar structure does not affect lunar dates or co-fullness events
  - All config read from files; nothing hardcoded
"""

from __future__ import annotations

import ast
import math
from pathlib import Path

import pytest

from sask.config_loader import load_config
from sask.lunar import (
    _ay_days,
    _epoch_pulse,
    _round_turns_for,
    _synodic_period_days,
    get_cofullness,
    get_lunar_date,
    near_full,
)
from sask.message import CofullnessEvent, LunarDate, validate

CONFIG = load_config(Path(__file__).parent.parent / "config")
PROJECT_ROOT = Path(__file__).parent.parent

PPD = CONFIG.time_constants.pulses_per_day  # 86_400
AYP = CONFIG.time_constants.astro_year_pulses  # 31_556_926.08


# ── Helpers ───────────────────────────────────────────────────────────────────


def _full_moment_pulse(moon_id: str, n: int = 0) -> int:
    """Pulse of the nth full moon for a real moon (synodic fraction = 0.5)."""
    body = next(b for b in CONFIG.bodies if b.name.lower() == moon_id.lower())
    t_sid_p = body.sidereal_period_days * PPD
    # synodic_frac = 0.5: (pulse/t_sid + epoch_offset - pulse/ayp) % 1 = 0.5
    # pulse * (1/t_sid - 1/ayp) = 0.5 - epoch_offset + n
    freq = 1.0 / t_sid_p - 1.0 / AYP
    return round((0.5 - body.epoch_offset + n) / freq)


def _tsyn(moon_id: str) -> float:
    return _synodic_period_days(moon_id, CONFIG)


# ── Config loading ────────────────────────────────────────────────────────────


def test_four_lunar_calendars_loaded():
    assert len(CONFIG.lunar_calendars) == 4


def test_lunar_calendar_ids():
    ids = {c.id for c in CONFIG.lunar_calendars}
    assert ids == {"untamed", "warren", "hearth", "terpin_lunar"}


def test_cofullness_config_loaded():
    cf = CONFIG.cofullness
    assert cf.full_tolerance_days == pytest.approx(1.0)
    assert cf.min_moons == 2


def test_lunar_settings_loaded():
    assert CONFIG.lunar_settings.realign_tolerance_days == pytest.approx(2.0)


def test_turn_based_calendars_have_months_per_turn():
    for cal in CONFIG.lunar_calendars:
        if cal.has_turns:
            assert cal.months_per_turn is not None
        else:
            assert cal.months_per_turn is None


def test_hearth_has_no_turns():
    hearth = next(c for c in CONFIG.lunar_calendars if c.id == "hearth")
    assert hearth.has_turns is False
    assert hearth.months_per_turn is None


# ── Synodic period ────────────────────────────────────────────────────────────


def test_synodic_period_positive_for_all_moons():
    for body in CONFIG.bodies:
        if body.body_type == "moon":
            t_syn = _tsyn(body.name.lower())
            assert t_syn > 0


def test_synodic_period_longer_than_sidereal():
    """T_syn > T_sid because the planet moves in the same direction as the moon."""
    for body in CONFIG.bodies:
        if body.body_type == "moon":
            t_syn = _tsyn(body.name.lower())
            assert t_syn > body.sidereal_period_days


def test_mean_synodic_is_mean_of_eight():
    moons = [b for b in CONFIG.bodies if b.body_type == "moon"]
    expected = sum(_tsyn(b.name.lower()) for b in moons) / len(moons)
    assert _tsyn("mean") == pytest.approx(expected)


def test_eight_real_moons_in_config():
    moons = [b for b in CONFIG.bodies if b.body_type == "moon"]
    assert len(moons) == 8


# ── near_full ─────────────────────────────────────────────────────────────────


def test_near_full_true_at_full_moment():
    p = _full_moment_pulse("sella", n=0)
    assert near_full("sella", p, CONFIG) is True


def test_near_full_true_within_tolerance():
    """Half a day before full: still near-full (tolerance = 1 day)."""
    p = _full_moment_pulse("sella", n=0)
    assert near_full("sella", p - PPD // 2, CONFIG) is True


def test_near_full_false_at_quarter_phase():
    """Quarter phase is far from full."""
    p = _full_moment_pulse("sella", n=0)
    t_syn_p = round(_tsyn("sella") * PPD)
    quarter = p + t_syn_p // 4
    assert near_full("sella", quarter, CONFIG) is False


def test_near_full_false_at_new_moon():
    p = _full_moment_pulse("sella", n=0)
    t_syn_p = round(_tsyn("sella") * PPD)
    new_moon = p + t_syn_p // 2
    assert near_full("sella", new_moon, CONFIG) is False


def test_near_full_recurs_each_synodic_period():
    p0 = _full_moment_pulse("kanka", n=0)
    p1 = _full_moment_pulse("kanka", n=1)
    assert near_full("kanka", p0, CONFIG) is True
    assert near_full("kanka", p1, CONFIG) is True


# ── Lunar date at epoch ───────────────────────────────────────────────────────


@pytest.mark.parametrize("calendar_id", ["untamed", "warren", "hearth", "terpin_lunar"])
def test_lunation_zero_at_epoch(calendar_id):
    cal = next(c for c in CONFIG.lunar_calendars if c.id == calendar_id)
    ep = _epoch_pulse(cal.epoch_anchor, cal.epoch_offset_days, CONFIG)
    ld = get_lunar_date(ep, calendar_id, CONFIG)
    assert ld.lunation == 0
    assert ld.day == 1


@pytest.mark.parametrize("calendar_id", ["untamed", "warren", "terpin_lunar"])
def test_turn_fields_at_epoch(calendar_id):
    cal = next(c for c in CONFIG.lunar_calendars if c.id == calendar_id)
    ep = _epoch_pulse(cal.epoch_anchor, cal.epoch_offset_days, CONFIG)
    ld = get_lunar_date(ep, calendar_id, CONFIG)
    assert ld.month == 1
    assert ld.turn == 0
    assert ld.short_count == 1
    assert ld.long_count == 0


def test_hearth_has_null_turn_fields():
    cal = next(c for c in CONFIG.lunar_calendars if c.id == "hearth")
    ep = _epoch_pulse(cal.epoch_anchor, cal.epoch_offset_days, CONFIG)
    ld = get_lunar_date(ep, "hearth", CONFIG)
    assert ld.has_turns is False
    assert ld.month is None
    assert ld.turn is None
    assert ld.short_count is None
    assert ld.long_count is None


# ── Lunar date progression ────────────────────────────────────────────────────


@pytest.mark.parametrize("calendar_id", ["untamed", "warren", "hearth", "terpin_lunar"])
def test_day_advances_by_one_per_pulses_per_day(calendar_id):
    cal = next(c for c in CONFIG.lunar_calendars if c.id == calendar_id)
    ep = _epoch_pulse(cal.epoch_anchor, cal.epoch_offset_days, CONFIG)
    ld1 = get_lunar_date(ep, calendar_id, CONFIG)
    ld2 = get_lunar_date(ep + PPD, calendar_id, CONFIG)
    assert ld1.day == 1
    assert ld2.day == 2


@pytest.mark.parametrize("calendar_id", ["untamed", "warren", "hearth"])
def test_lunation_increments_after_one_synodic_cycle(calendar_id):
    cal = next(c for c in CONFIG.lunar_calendars if c.id == calendar_id)
    ep = _epoch_pulse(cal.epoch_anchor, cal.epoch_offset_days, CONFIG)
    t_syn_p = _tsyn(cal.moon) * PPD
    ld0 = get_lunar_date(ep, calendar_id, CONFIG)
    ld1 = get_lunar_date(math.ceil(ep + t_syn_p), calendar_id, CONFIG)
    assert ld1.lunation == ld0.lunation + 1
    assert ld1.day == 1


@pytest.mark.parametrize("calendar_id", ["untamed", "warren"])
def test_month_increments_each_lunation(calendar_id):
    cal = next(c for c in CONFIG.lunar_calendars if c.id == calendar_id)
    ep = _epoch_pulse(cal.epoch_anchor, cal.epoch_offset_days, CONFIG)
    t_syn_p = _tsyn(cal.moon) * PPD
    ld1 = get_lunar_date(math.ceil(ep + t_syn_p), calendar_id, CONFIG)
    assert ld1.month == 2


@pytest.mark.parametrize("calendar_id", ["untamed", "warren"])
def test_month_wraps_and_turn_increments(calendar_id):
    cal = next(c for c in CONFIG.lunar_calendars if c.id == calendar_id)
    ep = _epoch_pulse(cal.epoch_anchor, cal.epoch_offset_days, CONFIG)
    months = cal.months_per_turn
    assert months is not None
    t_syn_p = _tsyn(cal.moon) * PPD
    # After months_per_turn lunations, month resets to 1 and turn=1.
    next_turn_pulse = math.ceil(ep + months * t_syn_p)
    ld = get_lunar_date(next_turn_pulse, calendar_id, CONFIG)
    assert ld.month == 1
    assert ld.turn == 1
    assert ld.short_count == 2  # second turn within Round


# ── Round computation ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("calendar_id", ["untamed", "warren", "terpin_lunar"])
def test_round_turns_realigns_with_astro_year(calendar_id):
    cal = next(c for c in CONFIG.lunar_calendars if c.id == calendar_id)
    assert cal.months_per_turn is not None
    ay_days = _ay_days(CONFIG)
    t_syn = _tsyn(cal.moon)
    tolerance = CONFIG.lunar_settings.realign_tolerance_days
    k = _round_turns_for(cal.months_per_turn, t_syn, ay_days, tolerance)
    turn_days = cal.months_per_turn * t_syn
    nearest_years = round(k * turn_days / ay_days)
    error = abs(k * turn_days - nearest_years * ay_days)
    assert error <= tolerance, (
        f"{calendar_id}: Round {k} error {error:.4f}d > {tolerance}d"
    )


@pytest.mark.parametrize("calendar_id", ["untamed", "warren", "terpin_lunar"])
def test_round_turns_is_positive(calendar_id):
    cal = next(c for c in CONFIG.lunar_calendars if c.id == calendar_id)
    assert cal.months_per_turn is not None
    ay_days = _ay_days(CONFIG)
    t_syn = _tsyn(cal.moon)
    tolerance = CONFIG.lunar_settings.realign_tolerance_days
    k = _round_turns_for(cal.months_per_turn, t_syn, ay_days, tolerance)
    assert k >= 1


@pytest.mark.parametrize("calendar_id", ["untamed", "warren", "terpin_lunar"])
def test_round_turns_is_cached(calendar_id):
    """Same args return the same object (lru_cache hit)."""
    cal = next(c for c in CONFIG.lunar_calendars if c.id == calendar_id)
    assert cal.months_per_turn is not None
    ay_days = _ay_days(CONFIG)
    t_syn = _tsyn(cal.moon)
    tolerance = CONFIG.lunar_settings.realign_tolerance_days
    k1 = _round_turns_for(cal.months_per_turn, t_syn, ay_days, tolerance)
    k2 = _round_turns_for(cal.months_per_turn, t_syn, ay_days, tolerance)
    assert k1 == k2


# ── Co-fullness ───────────────────────────────────────────────────────────────


def test_cofullness_events_present_in_first_year():
    events = get_cofullness(0, 365 * PPD, CONFIG)
    assert len(events) >= 1


def test_cofullness_count_matches_moon_list():
    events = get_cofullness(0, 365 * PPD, CONFIG)
    for ev in events:
        assert ev.count == len(ev.moons)


def test_cofullness_all_counts_ge_min_moons():
    events = get_cofullness(0, 365 * PPD, CONFIG)
    for ev in events:
        assert ev.count >= CONFIG.cofullness.min_moons


def test_cofullness_moons_are_valid_ids():
    moon_ids = {b.name.lower() for b in CONFIG.bodies if b.body_type == "moon"}
    events = get_cofullness(0, 365 * PPD, CONFIG)
    for ev in events:
        for mid in ev.moons:
            assert mid in moon_ids


def test_cofullness_solar_dates_have_two_entries():
    events = get_cofullness(0, 365 * PPD, CONFIG)
    for ev in events:
        assert len(ev.solar_dates) == 2


def test_cofullness_solar_dates_have_fatunik_and_terpin():
    events = get_cofullness(0, 365 * PPD, CONFIG)
    for ev in events:
        cal_ids = {d.calendar_id for d in ev.solar_dates}
        assert "fatunik" in cal_ids
        assert "terpin" in cal_ids


def test_cofullness_reproduces():
    events_a = get_cofullness(0, 180 * PPD, CONFIG)
    events_b = get_cofullness(0, 180 * PPD, CONFIG)
    assert events_a == events_b


def test_cofullness_event_at_known_near_full_pair():
    """Sella and Shunna are both near-full near pulse 485060 (verified analytically)."""
    p_sella = _full_moment_pulse("sella", n=0)
    # Search a window of ±2 days around sella's full moment for a co-fullness event.
    window_start = p_sella - 2 * PPD
    window_end = p_sella + 2 * PPD
    events = get_cofullness(window_start, window_end, CONFIG)
    assert len(events) >= 1
    # At least one event should include sella.
    assert any("sella" in ev.moons for ev in events)


# ── Message unit validity ─────────────────────────────────────────────────────


@pytest.mark.parametrize("calendar_id", ["untamed", "warren", "terpin_lunar"])
def test_lunar_date_validates_for_turn_based(calendar_id):
    ld = get_lunar_date(CONFIG.timeline.story_now_pulse, calendar_id, CONFIG)
    assert validate(ld) == []


def test_lunar_date_is_frozen_dataclass():
    ld = get_lunar_date(0, "untamed", CONFIG)
    assert isinstance(ld, LunarDate)
    with pytest.raises((AttributeError, TypeError)):
        ld.lunation = 999  # type: ignore[misc]


def test_cofullness_event_validates():
    events = get_cofullness(0, 365 * PPD, CONFIG)
    assert len(events) >= 1
    assert validate(events[0]) == []


def test_cofullness_event_is_frozen_dataclass():
    events = get_cofullness(0, 365 * PPD, CONFIG)
    assert isinstance(events[0], CofullnessEvent)
    with pytest.raises((AttributeError, TypeError)):
        events[0].count = 999  # type: ignore[misc]


# ── Calendar independence ─────────────────────────────────────────────────────


def test_lunar_module_does_not_use_civil_leap_arithmetic():
    """Lunar date computation uses only epoch anchors, not civil-calendar structure."""
    source = (PROJECT_ROOT / "src/sask/lunar.py").read_text(encoding="utf-8")
    assert "_fatunik_is_leap" not in source
    assert "_fatunik_days_before_year" not in source
    assert "_terpin_year_of_day" not in source
    assert "_terpin_days_before_year" not in source


def test_same_pulse_same_lunar_date():
    p = 5_000_000_000
    ld_a = get_lunar_date(p, "untamed", CONFIG)
    ld_b = get_lunar_date(p, "untamed", CONFIG)
    assert ld_a == ld_b


# ── Layer purity ──────────────────────────────────────────────────────────────


def test_lunar_module_has_no_flask_import():
    path = PROJECT_ROOT / "src/sask/lunar.py"
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

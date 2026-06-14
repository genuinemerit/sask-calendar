"""SPEC-017 unit tests — lore overlay: time-of-day and calendar date rendering.

Covers all acceptance criteria (unit-testable subset):
  - Config loader reads lore_time.toml and 6 calendar lore TOML files
  - render_lore_time: correct watch/shur/keyt for Fatunik and Terpin cultures
  - render_lore_time: day-boundary wrap and invalid culture raises ValueError
  - render_lore_date: fatunik_solar (ages + fixed week, festival month)
  - render_lore_date: terpin_solar (ages + fixed week, 10-day deshan)
  - render_lore_date: fatunik_solar age boundary (year at exact start of new age)
  - render_lore_date: untamed (round + phase quarters, day=1)
  - render_lore_date: warren (round + phase quarters, day=1)
  - render_lore_date: terpin_lunar (ages + phase quarters, day=1)
  - render_lore_date: hearth (none + phase_terms, day=1)
  - apply_lore_overlay: result contains lore_time and lore_date
  - apply_lore_overlay: does not mutate original dict
  - apply_lore_overlay: deterministic (same inputs → same outputs)
  - lore_time.enabled is True in loaded config

UAT follows unit testing: see docs/user_testing.md and devlog.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sask.config_loader import load_config
from sask.lore import apply_lore_overlay, render_lore_date, render_lore_time
from sask.message import CalendarDate, LunarDate

REAL_CONFIG = Path(__file__).parent.parent / "config"
CONFIG = load_config(REAL_CONFIG)


# ── Config loading ────────────────────────────────────────────────────────────


def test_config_lore_time_enabled():
    assert CONFIG.lore_time.enabled is True


def test_config_lore_time_watch_names():
    assert len(CONFIG.lore_time.watch_names) == 6
    assert CONFIG.lore_time.watch_names[0] == "First"
    assert CONFIG.lore_time.watch_names[5] == "Sixth"


def test_config_lore_calendars_count():
    assert len(CONFIG.lore_calendars) == 6


def test_config_lore_calendar_ids():
    ids = {c.id for c in CONFIG.lore_calendars}
    assert ids == {
        "fatunik_solar",
        "terpin_solar",
        "untamed",
        "warren",
        "terpin_lunar",
        "hearth",
    }


def test_config_fatunik_solar_ages():
    lore = next(c for c in CONFIG.lore_calendars if c.id == "fatunik_solar")
    assert lore.ages is not None
    assert len(lore.ages) == 3
    assert lore.ages[2].name == "the Bright Age"
    assert lore.ages[2].start_turn == 1531


# ── render_lore_time ──────────────────────────────────────────────────────────


def test_terpin_lore_time_pulse_300():
    # Terpin midnight = pulse 0; pulse 300 is 5 min into shur 1, keyt 1
    assert render_lore_time(300, "terpin", CONFIG) == "First Watch . shur 1 : keyt 1"


def test_fatunik_lore_time_pulse_300():
    # Fatunik day starts at pulse 21600 (6 AM); pulse 300 is in the fifth shur
    assert render_lore_time(300, "fatunik", CONFIG) == "Fifth Watch . shur 10 : keyt 1"


def test_fatunik_lore_time_at_day_start():
    # pulse=21600 is exactly the start of the Fatunik day → First Watch, shur 1, keyt 1
    result = render_lore_time(21600, "fatunik", CONFIG)
    assert result == "First Watch . shur 1 : keyt 1"


def test_lore_time_day_boundary_wrap():
    # pulse 86400 is one full day past pulse 0; same Terpin position as pulse 0
    assert render_lore_time(86400, "terpin", CONFIG) == render_lore_time(
        0, "terpin", CONFIG
    )


def test_lore_time_invalid_culture():
    with pytest.raises(ValueError, match="Unknown lore culture"):
        render_lore_time(0, "gnomish", CONFIG)


# ── render_lore_date: solar ───────────────────────────────────────────────────


def test_fatunik_solar_lore_date():
    date = CalendarDate(calendar_id="fatunik", year=1782, month=10, day=29)
    result = render_lore_date(date, "fatunik_solar", CONFIG)
    assert result == "Velden, the 6th kell of Tarnel, Year 1782 of the Bright Age"


def test_terpin_solar_lore_date():
    date = CalendarDate(calendar_id="terpin", year=2271, month=2, day=2)
    result = render_lore_date(date, "terpin_solar", CONFIG)
    assert result == "Bessen, the 1st deshan of Omarra, Year 2271 of the Deepening"


def test_fatunik_solar_festival_month():
    # Month 1 is the festival month "Gleaming"
    date = CalendarDate(calendar_id="fatunik", year=1000, month=1, day=3)
    result = render_lore_date(date, "fatunik_solar", CONFIG)
    assert "Gleaming" in result
    assert "the Age of the Open Hand" in result


def test_fatunik_solar_age_boundary():
    # year=1531 is the first year of "the Bright Age"; year=1530 is still "the Age of the Open Hand"
    at = render_lore_date(
        CalendarDate(calendar_id="fatunik", year=1531, month=5, day=1),
        "fatunik_solar",
        CONFIG,
    )
    before = render_lore_date(
        CalendarDate(calendar_id="fatunik", year=1530, month=5, day=1),
        "fatunik_solar",
        CONFIG,
    )
    assert "the Bright Age" in at
    assert "the Age of the Open Hand" in before


# ── render_lore_date: lunar (round) ──────────────────────────────────────────


def test_untamed_lore_date_first_phase():
    # day=1 always maps to quarter_names[0] regardless of cycle length
    ld = LunarDate(
        pulse=0,
        calendar_id="untamed",
        has_turns=True,
        lunation=500,
        day=1,
        month=5,
        turn=41,
        short_count=2,
        long_count=3,
    )
    result = render_lore_date(ld, "untamed", CONFIG)
    assert "the Dark" in result  # quarter_names[0]
    assert "Olvar" in result  # month_names[4] (month 5, no festival)
    assert "Range 2 of the Reave 4" in result  # short=2, long=long_count+1=4


def test_warren_lore_date_first_phase():
    ld = LunarDate(
        pulse=0,
        calendar_id="warren",
        has_turns=True,
        lunation=200,
        day=1,
        month=2,
        turn=9,
        short_count=3,
        long_count=1,
    )
    result = render_lore_date(ld, "warren", CONFIG)
    assert "the Dark" in result  # quarter_names[0]
    assert "Fenn" in result  # month_names[1] (month 2)
    assert "Litter 3 of the Wend 2" in result  # short=3, long=long_count+1=2


# ── render_lore_date: lunar (ages) ───────────────────────────────────────────


def test_terpin_lunar_lore_date():
    # turn=125 → still in "the First Watching" (start_turn=700 not reached)
    ld = LunarDate(
        pulse=0,
        calendar_id="terpin_lunar",
        has_turns=True,
        lunation=1500,
        day=1,
        month=3,
        turn=125,
        short_count=1,
        long_count=0,
    )
    result = render_lore_date(ld, "terpin_lunar", CONFIG)
    assert "First Quarter" in result  # day=1 → quarter_names[0]
    assert "Olreth" in result  # month_names[2] (month 3)
    assert "Year 125 of the First Watching" in result


# ── render_lore_date: hearth ──────────────────────────────────────────────────


def test_hearth_lore_date_first_phase():
    # has_turns=False; day=1 → phase_terms[0] = "the waxing"; moon_count = lunation+1 = 51
    # day and moon_count are rendered as ordinals (1st, 51st)
    ld = LunarDate(
        pulse=0,
        calendar_id="hearth",
        has_turns=False,
        lunation=50,
        day=1,
    )
    result = render_lore_date(ld, "hearth", CONFIG)
    assert result == "the waxing, the 1st day of Old Jem's 51st turning"


# ── apply_lore_overlay ────────────────────────────────────────────────────────


def test_apply_lore_overlay_adds_fields():
    record = {"pulse": 300, "scene_data": "test"}
    result = apply_lore_overlay(record, "terpin", "terpin_solar", CONFIG)
    assert "lore_time" in result
    assert "lore_date" in result
    assert result["scene_data"] == "test"


def test_apply_lore_overlay_does_not_mutate():
    record = {"pulse": 300}
    apply_lore_overlay(record, "terpin", "terpin_solar", CONFIG)
    assert "lore_time" not in record
    assert "lore_date" not in record


def test_apply_lore_overlay_is_deterministic():
    record = {"pulse": 86400}
    r1 = apply_lore_overlay(record, "fatunik", "fatunik_solar", CONFIG)
    r2 = apply_lore_overlay(record, "fatunik", "fatunik_solar", CONFIG)
    assert r1["lore_time"] == r2["lore_time"]
    assert r1["lore_date"] == r2["lore_date"]

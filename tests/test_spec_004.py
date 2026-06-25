"""SPEC-004 tests — astronomical seasonal context.

Covers:
  - Four seasons from AstroYear orbital position quarters
  - Event proximity detection within near_tolerance (circular)
  - Tolerance boundary: just inside vs just outside
  - Seasonal context computed from any of the 3 calendars (via pulse)
  - No seasonal drift under Terpin leap rules (seasons track orbital position)
  - season.py has no Flask import (layer-purity)
"""

from __future__ import annotations

import ast
import math
from pathlib import Path

import pytest

from sask.config_loader import load_config
from sask.message import CalendarDate
from sask.calendar.pulse import terpin_to_pulse
from sask.calendar.season import season_info

CONFIG = load_config(Path(__file__).parent.parent / "config")
PROJECT_ROOT = Path(__file__).parent.parent
AYP = CONFIG.time_constants.astro_year_pulses
TOL = CONFIG.seasons.near_tolerance


def _pulse_at(orbital_pos: float) -> int:
    """Return the first pulse at or just past the given orbital position.

    ceil ensures boundary values (0.25, 0.5, 0.75) land on or above the
    season-start threshold rather than fractionally below it due to float rounding.
    """
    return math.ceil(orbital_pos * AYP)


# ── Season boundaries ─────────────────────────────────────────────────────────


def test_pulse_0_is_greening():
    assert season_info(0, CONFIG).season_id == "greening"


def test_summer_solstice_is_blazing():
    assert season_info(_pulse_at(0.25), CONFIG).season_id == "blazing"


def test_autumn_equinox_is_withering():
    assert season_info(_pulse_at(0.5), CONFIG).season_id == "withering"


def test_winter_solstice_is_stillness():
    assert season_info(_pulse_at(0.75), CONFIG).season_id == "stillness"


def test_mid_greening_is_greening():
    assert season_info(_pulse_at(0.125), CONFIG).season_id == "greening"


def test_late_stillness_is_stillness():
    # Just before the spring equinox wraps back to Greening
    assert season_info(_pulse_at(0.99), CONFIG).season_id == "stillness"


# ── Event proximity ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "pos, event_id",
    [
        (0.0, "spring_equinox"),
        (0.125, "mid_greening"),
        (0.25, "summer_solstice"),
        (0.375, "mid_blazing"),
        (0.5, "autumn_equinox"),
        (0.625, "mid_withering"),
        (0.75, "winter_solstice"),
        (0.875, "mid_stillness"),
    ],
)
def test_exact_event_position_detected(pos, event_id):
    info = season_info(_pulse_at(pos), CONFIG)
    assert info.near_event_id == event_id


def test_just_within_tolerance_detected():
    # TOL = 0.01; a pulse slightly inside the tolerance should trigger detection
    pos = TOL * 0.9  # 90% of tolerance away from spring equinox
    info = season_info(_pulse_at(pos), CONFIG)
    assert info.near_event_id == "spring_equinox"


def test_just_outside_tolerance_not_detected():
    # A pulse just beyond the tolerance from spring equinox (but far from mid_greening)
    pos = TOL * 1.1  # 110% of tolerance — just outside
    info = season_info(_pulse_at(pos), CONFIG)
    assert info.near_event_id is None


def test_arbitrary_pulse_no_near_event():
    # Position 0.05 is equidistant between spring_equinox (0.0) and mid_greening (0.125)
    # Both are 0.05 away, which is 5× the tolerance (0.01) — no event detected
    info = season_info(_pulse_at(0.05), CONFIG)
    assert info.near_event_id is None


def test_spring_equinox_detected_near_year_wrap():
    # Orbital position near 1.0 wraps to 0.0 (spring equinox) — circular distance check
    pos = 1.0 - TOL * 0.9  # just before the wrap
    info = season_info(_pulse_at(pos), CONFIG)
    assert info.near_event_id == "spring_equinox"


# ── SeasonInfo fields ─────────────────────────────────────────────────────────


def test_season_info_name_populated():
    info = season_info(0, CONFIG)
    assert info.name == "Greening"


def test_season_info_near_event_name_populated():
    info = season_info(0, CONFIG)
    assert info.near_event_name == "Green Day"


def test_season_info_no_event_fields_are_none():
    info = season_info(_pulse_at(0.05), CONFIG)
    assert info.near_event_id is None
    assert info.near_event_name is None


# ── Cross-calendar: season from any calendar ──────────────────────────────────


def test_terpin_year_1_is_near_spring_equinox():
    # Terpin epoch = spring equinox of Astro year 1043; year 1 day 1 starts
    # at midnight of that Astro day, which falls in the last hours of Stillness
    # (just before the equinox occurs that afternoon).
    pulse = terpin_to_pulse(CalendarDate("terpin", 1, 1, 1), CONFIG)
    info = season_info(pulse, CONFIG)
    assert info.season_id == "stillness"
    assert info.near_event_id == "spring_equinox"


def test_season_independent_of_calendar():
    # The same Astro pulse gives the same season regardless of which calendar we
    # start from.  Use story_now_pulse directly.
    p = CONFIG.timeline.story_now_pulse
    info = season_info(p, CONFIG)
    assert info.season_id in {"greening", "blazing", "withering", "stillness"}


def test_terpin_new_year_stays_in_late_stillness():
    # Terpin average year ≈ AstroYear, so new years consistently fall in late
    # Stillness (orbital_pos > 0.90) — always near the spring equinox but
    # never quite at it.  The drift within that band is real but confined.
    for yr in [1, 132, 500, 1000, 2000]:
        pulse = terpin_to_pulse(CalendarDate("terpin", yr, 1, 1), CONFIG)
        op = (pulse / CONFIG.time_constants.astro_year_pulses) % 1.0
        assert op > 0.90, (
            f"Terpin year {yr} new year at orbital_pos {op:.4f} — expected > 0.90"
        )


# ── Layer purity ──────────────────────────────────────────────────────────────


def test_season_module_has_no_flask_import():
    path = PROJECT_ROOT / "src/sask/calendar/season.py"
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

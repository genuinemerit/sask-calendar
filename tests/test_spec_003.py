"""SPEC-003 tests — solar calendar conversions (Fatunik and Terpin).

Covers:
  - astro_to_fatunik / fatunik_to_pulse round-trips
  - Fatunik leap rule (4/100/400) and year lengths
  - Fatunik sunrise day-boundary (day_start_offset = 21600)
  - astro_to_terpin / terpin_to_pulse round-trips
  - Terpin long-year (132) and super-long-year (4620) lengths
  - Terpin Shells formatting helpers
  - Ages helper: fatunik_turns_to_pulse_range
  - story_now_pulse resolves to roughly Fatunik ~1782, Terpin ~2271
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sask.config_loader import load_config
from sask.message import CalendarDate
from sask.calendar.pulse import (
    _fatunik_is_leap,
    astro_to_fatunik,
    astro_to_terpin,
    fatunik_to_pulse,
    fatunik_turns_to_pulse_range,
    terpin_shell_of_turn,
    terpin_shell_to_turn,
    terpin_to_pulse,
    terpin_turn_within_shell,
)

CONFIG = load_config(Path(__file__).parent.parent / "config")
FC = CONFIG.fatunik
TC = CONFIG.terpin

# Epoch pulses
FATUNIK_EPOCH_PULSE = (
    FC.epoch_astro_day - 1
) * CONFIG.time_constants.pulses_per_day + FC.day_start_offset
TERPIN_EPOCH_PULSE = (
    TC.epoch_astro_day - 1
) * CONFIG.time_constants.pulses_per_day + TC.day_start_offset


# ── Fatunik: epoch and basic round-trips ─────────────────────────────────────


def test_fatunik_epoch_is_y1m1d1():
    assert astro_to_fatunik(FATUNIK_EPOCH_PULSE, CONFIG) == CalendarDate(
        calendar_id="fatunik", year=1, month=1, day=1
    )


@pytest.mark.parametrize(
    "date",
    [
        CalendarDate("fatunik", 1, 1, 1),  # epoch start
        CalendarDate("fatunik", 1, 1, 5),  # last day of standard festival
        CalendarDate("fatunik", 1, 2, 1),  # first regular month, day 1
        CalendarDate("fatunik", 1, 13, 30),  # last day of standard year
        CalendarDate("fatunik", 4, 1, 1),  # first leap year
        CalendarDate("fatunik", 4, 1, 6),  # last day of leap festival
        CalendarDate("fatunik", 4, 13, 30),  # last day of leap year
        CalendarDate("fatunik", 100, 1, 1),  # century year (not leap)
        CalendarDate("fatunik", 400, 1, 1),  # 400-year restore (leap)
        CalendarDate("fatunik", 1782, 1, 1),  # near story_now
    ],
)
def test_fatunik_round_trip(date):
    assert astro_to_fatunik(fatunik_to_pulse(date, CONFIG), CONFIG) == date


# ── Fatunik: leap rule ────────────────────────────────────────────────────────


def test_fatunik_year_4_is_leap():
    assert _fatunik_is_leap(4, FC.leap)


def test_fatunik_year_100_not_leap():
    assert not _fatunik_is_leap(100, FC.leap)


def test_fatunik_year_400_is_leap():
    assert _fatunik_is_leap(400, FC.leap)


def test_fatunik_year_4_has_366_days():
    p4 = fatunik_to_pulse(CalendarDate("fatunik", 4, 1, 1), CONFIG)
    p5 = fatunik_to_pulse(CalendarDate("fatunik", 5, 1, 1), CONFIG)
    assert (p5 - p4) // CONFIG.time_constants.pulses_per_day == 366


def test_fatunik_year_100_has_365_days():
    p100 = fatunik_to_pulse(CalendarDate("fatunik", 100, 1, 1), CONFIG)
    p101 = fatunik_to_pulse(CalendarDate("fatunik", 101, 1, 1), CONFIG)
    assert (p101 - p100) // CONFIG.time_constants.pulses_per_day == 365


def test_fatunik_year_400_has_366_days():
    p400 = fatunik_to_pulse(CalendarDate("fatunik", 400, 1, 1), CONFIG)
    p401 = fatunik_to_pulse(CalendarDate("fatunik", 401, 1, 1), CONFIG)
    assert (p401 - p400) // CONFIG.time_constants.pulses_per_day == 366


# ── Fatunik: sunrise day-boundary ────────────────────────────────────────────


def test_fatunik_days_are_86400_pulses_apart():
    p_d1 = fatunik_to_pulse(CalendarDate("fatunik", 1, 1, 1), CONFIG)
    p_d2 = fatunik_to_pulse(CalendarDate("fatunik", 1, 1, 2), CONFIG)
    assert p_d2 - p_d1 == CONFIG.time_constants.pulses_per_day


def test_fatunik_one_pulse_before_sunrise_is_prior_day():
    # The pulse immediately before a Fatunik day-start belongs to the previous day.
    p_d2 = fatunik_to_pulse(CalendarDate("fatunik", 1, 1, 2), CONFIG)
    assert astro_to_fatunik(p_d2 - 1, CONFIG) == CalendarDate("fatunik", 1, 1, 1)


def test_fatunik_astro_midnight_within_day_still_same_fatunik_day():
    # Astro midnight within a Fatunik day is before sunrise → still the same civil day.
    p_d1 = fatunik_to_pulse(CalendarDate("fatunik", 1, 1, 1), CONFIG)
    # 86400 - 21600 = 64800 pulses after day start is the next Astro midnight,
    # still within this Fatunik day (sunrise is 21600 pulses into each Astro day).
    next_astro_midnight = (
        p_d1 + CONFIG.time_constants.pulses_per_day - FC.day_start_offset
    )
    assert astro_to_fatunik(next_astro_midnight, CONFIG) == CalendarDate(
        "fatunik", 1, 1, 1
    )


# ── Terpin: epoch and basic round-trips ──────────────────────────────────────


def test_terpin_epoch_is_y1m1d1():
    assert astro_to_terpin(TERPIN_EPOCH_PULSE, CONFIG) == CalendarDate(
        calendar_id="terpin", year=1, month=1, day=1
    )


@pytest.mark.parametrize(
    "date",
    [
        CalendarDate("terpin", 1, 1, 1),  # epoch
        CalendarDate("terpin", 1, 1, 5),  # last day of standard festival
        CalendarDate("terpin", 1, 2, 1),  # first regular month
        CalendarDate("terpin", 1, 13, 30),  # last day of standard year
        CalendarDate("terpin", 132, 1, 1),  # first long year (Shell 1 last year)
        CalendarDate("terpin", 132, 1, 37),  # last day of long festival
        CalendarDate("terpin", 132, 13, 30),  # last day of Shell 1
        CalendarDate("terpin", 133, 1, 1),  # Shell 2, Turn 1
        CalendarDate("terpin", 4620, 1, 1),  # super-long year
        CalendarDate("terpin", 4620, 1, 36),  # last day of super-long festival
        CalendarDate("terpin", 2271, 1, 1),  # near story_now
    ],
)
def test_terpin_round_trip(date):
    assert astro_to_terpin(terpin_to_pulse(date, CONFIG), CONFIG) == date


# ── Terpin: leap rules ────────────────────────────────────────────────────────


def test_terpin_year_132_has_397_days():
    p132 = terpin_to_pulse(CalendarDate("terpin", 132, 1, 1), CONFIG)
    p133 = terpin_to_pulse(CalendarDate("terpin", 133, 1, 1), CONFIG)
    assert (p133 - p132) // CONFIG.time_constants.pulses_per_day == 397


def test_terpin_year_133_has_365_days():
    p133 = terpin_to_pulse(CalendarDate("terpin", 133, 1, 1), CONFIG)
    p134 = terpin_to_pulse(CalendarDate("terpin", 134, 1, 1), CONFIG)
    assert (p134 - p133) // CONFIG.time_constants.pulses_per_day == 365


def test_terpin_year_4620_has_396_days():
    p4620 = terpin_to_pulse(CalendarDate("terpin", 4620, 1, 1), CONFIG)
    p4621 = terpin_to_pulse(CalendarDate("terpin", 4621, 1, 1), CONFIG)
    assert (p4621 - p4620) // CONFIG.time_constants.pulses_per_day == 396


def test_terpin_year_4488_has_397_days():
    # 4488 = 132 * 34 — long year, not super-long
    p4488 = terpin_to_pulse(CalendarDate("terpin", 4488, 1, 1), CONFIG)
    p4489 = terpin_to_pulse(CalendarDate("terpin", 4489, 1, 1), CONFIG)
    assert (p4489 - p4488) // CONFIG.time_constants.pulses_per_day == 397


# ── Terpin: Shells helpers ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "turn, shell",
    [(1, 1), (132, 1), (133, 2), (264, 2), (265, 3), (4620, 35)],
)
def test_terpin_shell_of_turn(turn, shell):
    assert terpin_shell_of_turn(turn) == shell


@pytest.mark.parametrize(
    "turn, within",
    [(1, 1), (132, 132), (133, 1), (134, 2), (264, 132), (265, 1)],
)
def test_terpin_turn_within_shell(turn, within):
    assert terpin_turn_within_shell(turn) == within


@pytest.mark.parametrize(
    "shell, within, turn",
    [(1, 1, 1), (1, 132, 132), (2, 1, 133), (2, 132, 264), (35, 132, 4620)],
)
def test_terpin_shell_to_turn(shell, within, turn):
    assert terpin_shell_to_turn(shell, within) == turn


def test_terpin_shell_round_trip():
    for t in [1, 50, 132, 133, 500, 4619, 4620]:
        shell = terpin_shell_of_turn(t)
        within = terpin_turn_within_shell(t)
        assert terpin_shell_to_turn(shell, within) == t


# ── Ages helper ───────────────────────────────────────────────────────────────


def test_fatunik_turns_to_pulse_range_year1():
    start, end = fatunik_turns_to_pulse_range(1, 1, CONFIG)
    assert start == FATUNIK_EPOCH_PULSE
    assert end == fatunik_to_pulse(CalendarDate("fatunik", 2, 1, 1), CONFIG) - 1


def test_fatunik_turns_to_pulse_range_multi_year():
    start, end = fatunik_turns_to_pulse_range(1, 100, CONFIG)
    assert start == FATUNIK_EPOCH_PULSE
    assert end == fatunik_to_pulse(CalendarDate("fatunik", 101, 1, 1), CONFIG) - 1


def test_fatunik_turns_to_pulse_range_start_lte_end():
    start, end = fatunik_turns_to_pulse_range(2000, 2010, CONFIG)
    assert start <= end


# ── story_now sanity checks ───────────────────────────────────────────────────


def test_story_now_fatunik_year_roughly_1782():
    date = astro_to_fatunik(CONFIG.timeline.story_now_pulse, CONFIG)
    assert 1780 <= date.year <= 1785


def test_story_now_terpin_year_roughly_2271():
    date = astro_to_terpin(CONFIG.timeline.story_now_pulse, CONFIG)
    assert 2268 <= date.year <= 2274

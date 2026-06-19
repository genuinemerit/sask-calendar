"""Pulse/day arithmetic, calendar translators, Ages helper, and Shells helpers.

SPEC-002: astro_day, day_pulse_offset, orbital_position, civil_day, pulse_info.
SPEC-003: astro_to_fatunik, fatunik_to_pulse, astro_to_terpin, terpin_to_pulse,
          fatunik_turns_to_pulse_range, terpin_shell_of_turn,
          terpin_turn_within_shell, terpin_shell_to_turn.

All functions are pure and stateless.
"""

from __future__ import annotations

from .config_loader import (
    AppConfig,
    FatunikConfig,
    FatunikLeap,
    TerpinConfig,
    TerpinLeap,
)
from .message import CalendarDate, PulseInfo


class CalendarRangeError(ValueError):
    """Raised when a civil calendar date's month or day is out of range for its turn."""


# ── Core arithmetic (SPEC-002) ────────────────────────────────────────────────


def astro_day(pulse: int, pulses_per_day: int = 86_400) -> int:
    """Return the 1-indexed Astro day for a pulse.

    Day 1 starts at pulse 0.  Negative pulses yield day 0 and below.
    Uses floor division, which Python guarantees rounds toward -∞.
    """
    return pulse // pulses_per_day + 1


def day_pulse_offset(pulse: int, pulses_per_day: int = 86_400) -> int:
    """Return pulses elapsed since Astro midnight for this day [0, pulses_per_day).

    Python's % always returns a non-negative result when the divisor is
    positive, so this is correct for negative pulses too.
    """
    return pulse % pulses_per_day


def orbital_position(pulse: int | float, astro_year_pulses: float) -> float:
    """Return the AstroYear orbital position as a normalised value in [0.0, 1.0).

    0.0 = spring equinox, 0.25 = summer solstice, 0.5 = autumn equinox,
    0.75 = winter solstice.
    """
    return (pulse % astro_year_pulses) / astro_year_pulses


def civil_day(pulse: int, day_start_offset: int, pulses_per_day: int = 86_400) -> int:
    """Return the civil day for a calendar whose day begins at day_start_offset.

    Shifting the pulse back by day_start_offset before flooring means the
    civil day boundary falls at (midnight + day_start_offset) pulses.
    Fatunik sunrise offset is 21600 (6 hours); Astro/Terpin is 0.
    """
    return (pulse - day_start_offset) // pulses_per_day + 1


def pulse_info(pulse: int, cfg: AppConfig) -> PulseInfo:
    """Return a PulseInfo message unit for the given pulse."""
    tc = cfg.time_constants
    return PulseInfo(
        pulse=pulse,
        astro_day=astro_day(pulse, tc.pulses_per_day),
        day_pulse_offset=day_pulse_offset(pulse, tc.pulses_per_day),
        orbital_position=orbital_position(pulse, tc.astro_year_pulses),
    )


# ── Fatunik calendar helpers ──────────────────────────────────────────────────


def _fatunik_is_leap(year: int, fl: FatunikLeap) -> bool:
    """True if the Fatunik year is a leap year (festival = 6 days)."""
    c, skip, restore = fl.cycle_short, fl.cycle_skip, fl.cycle_restore
    return year % c == 0 and (year % skip != 0 or year % restore == 0)


def _fatunik_festival_length(year: int, fc: FatunikConfig) -> int:
    """Return this turn's Fatunik festival-month (month 1) day count."""
    fm = fc.months
    return (
        fm.festival_days_leap
        if _fatunik_is_leap(year, fc.leap)
        else fm.festival_days_standard
    )


def fatunik_month_length(year: int, month: int, cfg: AppConfig) -> int:
    """Return the day count for `month` on Fatunik turn `year`.

    Month 1 is the festival month, whose length depends on whether `year`
    is a Fatunik leap turn; months 2..N are fixed-length. Raises
    CalendarRangeError if `month` is outside the calendar's valid range.
    """
    fc: FatunikConfig = cfg.fatunik
    max_month = fc.months.regular_month_count + 1
    if not 1 <= month <= max_month:
        raise CalendarRangeError(
            f"Fatunik month {month} is out of range for turn {year} "
            f"(valid months: 1-{max_month})"
        )
    return (
        _fatunik_festival_length(year, fc)
        if month == 1
        else fc.months.regular_month_days
    )


def _fatunik_days_before_year(year: int, fl: FatunikLeap) -> int:
    """Days from the Fatunik epoch start up to (but not including) the start of year."""
    n = year - 1
    return 365 * n + n // fl.cycle_short - n // fl.cycle_skip + n // fl.cycle_restore


def _fatunik_year_of_day(day_0: int, fl: FatunikLeap) -> int:
    """Return the 1-indexed Fatunik year containing 0-indexed day_0."""
    # Initial estimate: divide by the 400-year cycle average (365.2425 d/yr)
    year = day_0 * 400 // 146097 + 1
    while _fatunik_days_before_year(year + 1, fl) <= day_0:
        year += 1
    while _fatunik_days_before_year(year, fl) > day_0:
        year -= 1
    return year


# ── Terpin calendar helpers ───────────────────────────────────────────────────


def _terpin_festival_length(year: int, tc_cal: TerpinConfig) -> int:
    """Return this turn's Terpin festival-month (month 1) day count."""
    tm, tl = tc_cal.months, tc_cal.leap
    if year % tl.super_long_year_cycle == 0:
        return tm.festival_days_super_long
    if year % tl.long_year_cycle == 0:
        return tm.festival_days_long
    return tm.festival_days_standard


def terpin_month_length(year: int, month: int, cfg: AppConfig) -> int:
    """Return the day count for `month` on Terpin turn `year`.

    Month 1 is the festival month, whose length depends on whether `year`
    is a Terpin long or super-long turn; months 2..N are fixed-length.
    Raises CalendarRangeError if `month` is outside the calendar's valid range.
    """
    tc_cal: TerpinConfig = cfg.terpin
    max_month = tc_cal.months.regular_month_count + 1
    if not 1 <= month <= max_month:
        raise CalendarRangeError(
            f"Terpin month {month} is out of range for turn {year} "
            f"(valid months: 1-{max_month})"
        )
    return (
        _terpin_festival_length(year, tc_cal)
        if month == 1
        else tc_cal.months.regular_month_days
    )


def _terpin_days_before_year(year: int, tl: TerpinLeap) -> int:
    """Days from the Terpin epoch start up to (but not including) the start of year.

    Long years (every long_year_cycle) add 32 extra days; super-long years
    (every super_long_year_cycle) add 31 extra days instead.
    Simplified: 365*n + 32*(n//132) - (n//4620).
    """
    n = year - 1
    return 365 * n + 32 * (n // tl.long_year_cycle) - (n // tl.super_long_year_cycle)


def _terpin_year_of_day(day_0: int, tl: TerpinLeap) -> int:
    """Return the 1-indexed Terpin year containing 0-indexed day_0."""
    # Estimate using 4620-year cycle: 1687419 days / 4620 years = 365.2422 d/yr
    year = day_0 * 4620 // 1687419 + 1
    while _terpin_days_before_year(year + 1, tl) <= day_0:
        year += 1
    while _terpin_days_before_year(year, tl) > day_0:
        year -= 1
    return year


# ── Calendar translators (SPEC-003) ──────────────────────────────────────────


def astro_to_fatunik(pulse: int, cfg: AppConfig) -> CalendarDate:
    """Convert an Astro pulse to a Fatunik calendar date."""
    fc: FatunikConfig = cfg.fatunik
    tc = cfg.time_constants

    # Fatunik civil day (1-indexed in Astro days) — day starts at sunrise
    fatunik_civil = civil_day(pulse, fc.day_start_offset, tc.pulses_per_day)
    # 0-indexed days since the Fatunik epoch
    day_0 = fatunik_civil - fc.epoch_astro_day

    year = _fatunik_year_of_day(day_0, fc.leap)
    day_in_year = day_0 - _fatunik_days_before_year(year, fc.leap) + 1

    fm = fc.months
    fest = _fatunik_festival_length(year, fc)
    if day_in_year <= fest:
        month, day = 1, day_in_year
    else:
        rem = day_in_year - fest
        month = 2 + (rem - 1) // fm.regular_month_days
        day = (rem - 1) % fm.regular_month_days + 1

    return CalendarDate(calendar_id="fatunik", year=year, month=month, day=day)


def fatunik_to_pulse(date: CalendarDate, cfg: AppConfig) -> int:
    """Convert a Fatunik calendar date to the Astro pulse at civil day start."""
    fc: FatunikConfig = cfg.fatunik
    tc = cfg.time_constants
    fm = fc.months

    max_day = fatunik_month_length(date.year, date.month, cfg)
    if not 1 <= date.day <= max_day:
        raise CalendarRangeError(
            f"Fatunik day {date.day} is out of range for month {date.month} "
            f"of turn {date.year} (valid days: 1-{max_day})"
        )

    fest = _fatunik_festival_length(date.year, fc)
    if date.month == 1:
        day_in_year = date.day
    else:
        day_in_year = fest + (date.month - 2) * fm.regular_month_days + date.day

    day_0 = _fatunik_days_before_year(date.year, fc.leap) + day_in_year - 1
    astro_civil = day_0 + fc.epoch_astro_day
    return (astro_civil - 1) * tc.pulses_per_day + fc.day_start_offset


def astro_to_terpin(pulse: int, cfg: AppConfig) -> CalendarDate:
    """Convert an Astro pulse to a Terpin calendar date."""
    tc_cal: TerpinConfig = cfg.terpin
    tc = cfg.time_constants

    # Terpin day starts at midnight (day_start_offset = 0) = same as Astro day
    terpin_civil = civil_day(pulse, tc_cal.day_start_offset, tc.pulses_per_day)
    day_0 = terpin_civil - tc_cal.epoch_astro_day

    year = _terpin_year_of_day(day_0, tc_cal.leap)
    day_in_year = day_0 - _terpin_days_before_year(year, tc_cal.leap) + 1

    tm = tc_cal.months
    fest = _terpin_festival_length(year, tc_cal)

    if day_in_year <= fest:
        month, day = 1, day_in_year
    else:
        rem = day_in_year - fest
        month = 2 + (rem - 1) // tm.regular_month_days
        day = (rem - 1) % tm.regular_month_days + 1

    return CalendarDate(calendar_id="terpin", year=year, month=month, day=day)


def terpin_to_pulse(date: CalendarDate, cfg: AppConfig) -> int:
    """Convert a Terpin calendar date to the Astro pulse at civil day start."""
    tc_cal: TerpinConfig = cfg.terpin
    tc = cfg.time_constants
    tm = tc_cal.months
    tl = tc_cal.leap

    max_day = terpin_month_length(date.year, date.month, cfg)
    if not 1 <= date.day <= max_day:
        raise CalendarRangeError(
            f"Terpin day {date.day} is out of range for month {date.month} "
            f"of turn {date.year} (valid days: 1-{max_day})"
        )

    fest = _terpin_festival_length(date.year, tc_cal)
    if date.month == 1:
        day_in_year = date.day
    else:
        day_in_year = fest + (date.month - 2) * tm.regular_month_days + date.day

    day_0 = _terpin_days_before_year(date.year, tl) + day_in_year - 1
    astro_civil = day_0 + tc_cal.epoch_astro_day
    return (astro_civil - 1) * tc.pulses_per_day + tc_cal.day_start_offset


# ── Ages helper (SPEC-003) ────────────────────────────────────────────────────


def fatunik_turns_to_pulse_range(
    from_turn: int, to_turn: int, cfg: AppConfig
) -> tuple[int, int]:
    """Return the Astro pulse range [start, end] for a Fatunik Turn range.

    start = pulse at the civil-day start of from_turn Year 1 Month 1 Day 1.
    end   = one pulse before the civil-day start of (to_turn + 1) Year 1 Month 1 Day 1,
            i.e., the last pulse of the last day of to_turn.
    """
    start = fatunik_to_pulse(
        CalendarDate(calendar_id="fatunik", year=from_turn, month=1, day=1), cfg
    )
    end = (
        fatunik_to_pulse(
            CalendarDate(calendar_id="fatunik", year=to_turn + 1, month=1, day=1), cfg
        )
        - 1
    )
    return start, end


# ── Shells helpers (SPEC-003) ─────────────────────────────────────────────────


def terpin_shell_of_turn(turn: int) -> int:
    """Return the Shell number (1-indexed) for a Terpin Turn."""
    return (turn - 1) // 132 + 1


def terpin_turn_within_shell(turn: int) -> int:
    """Return the 1-indexed turn number within its Shell."""
    return (turn - 1) % 132 + 1


def terpin_shell_to_turn(shell: int, turn_within_shell: int) -> int:
    """Return the absolute Terpin Turn for a Shell + turn-within-shell."""
    return (shell - 1) * 132 + turn_within_shell

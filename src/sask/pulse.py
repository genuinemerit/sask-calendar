"""Pulse/day arithmetic and orbital position (SPEC-002).

All functions are pure and stateless: given the same inputs they always
return the same output.  Config constants are passed as arguments, never
read from globals.

Translator stubs (astro_to_fatunik etc.) are scaffolded here and will be
implemented in SPEC-003.
"""

from __future__ import annotations

from .config_loader import AppConfig
from .message import CalendarDate, PulseInfo


# ── Core arithmetic ───────────────────────────────────────────────────────────


def astro_day(pulse: int, pulses_per_day: int = 86_400) -> int:
    """Return the 1-indexed Astro day for a pulse.

    Day 1 starts at pulse 0.  Negative pulses yield day 0 and below.
    Uses floor division, which Python guarantees rounds toward -∞.
    """
    return pulse // pulses_per_day + 1


def pulse_of_day(pulse: int, pulses_per_day: int = 86_400) -> int:
    """Return the pulse count within the current Astro day [0, pulses_per_day).

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


# ── Message-unit constructor ──────────────────────────────────────────────────


def pulse_info(pulse: int, cfg: AppConfig) -> PulseInfo:
    """Return a PulseInfo message unit for the given pulse."""
    tc = cfg.time_constants
    return PulseInfo(
        pulse=pulse,
        astro_day=astro_day(pulse, tc.pulses_per_day),
        pulse_of_day=pulse_of_day(pulse, tc.pulses_per_day),
        orbital_position=orbital_position(pulse, tc.astro_year_pulses),
    )


# ── Calendar translator stubs (implemented in SPEC-003) ──────────────────────


def astro_to_fatunik(pulse: int, cfg: AppConfig) -> CalendarDate:
    """Convert an Astro pulse to a Fatunik calendar date."""
    raise NotImplementedError("astro_to_fatunik — implemented in SPEC-003")


def fatunik_to_pulse(date: CalendarDate, cfg: AppConfig) -> int:
    """Convert a Fatunik calendar date to the Astro pulse at civil day start."""
    raise NotImplementedError("fatunik_to_pulse — implemented in SPEC-003")


def astro_to_terpin(pulse: int, cfg: AppConfig) -> CalendarDate:
    """Convert an Astro pulse to a Terpin calendar date."""
    raise NotImplementedError("astro_to_terpin — implemented in SPEC-003")


def terpin_to_pulse(date: CalendarDate, cfg: AppConfig) -> int:
    """Convert a Terpin calendar date to the Astro pulse at civil day start."""
    raise NotImplementedError("terpin_to_pulse — implemented in SPEC-003")

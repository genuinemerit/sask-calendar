"""Lunar calendars and co-fullness tracking (SPEC-012).

get_lunar_date(pulse, calendar_id, config):
  Synodic period = 1 / (1/T_sid - 1/AstroYear). For 'mean' (Terpin lunar),
  T_syn is the arithmetic mean of all eight moons' synodic periods.
  epoch_pulse = anchor_pulse + epoch_offset_days.
  lunation = floor(elapsed / T_syn_pulses); day = floor(cycle_pos / ppd) + 1.
  Turn-based: month = lunation%months+1 (1-based), turn = lunation//months
  (0-based), short_count = turn%Round+1 (1-based), long_count = turn//Round
  (0-based). Round K = smallest K>=1 turns realigning with AstroYear <=tolerance.

get_cofullness(start_pulse, end_pulse, config):
  Checks midnight of each Astro day in range. near_full uses a phase tolerance
  of full_tolerance_days / T_syn per moon. Reports nights with >=min_moons
  near-full moons, with solar_dates from the civil-calendar translators.
  The event list (pulses, counts, moons) depends only on orbital mechanics;
  solar_dates depend on civil calendar config.
"""

from __future__ import annotations

import functools
import math
from collections.abc import Iterator

from sask.calendar.pulse import astro_to_fatunik, astro_to_terpin
from sask.config_loader import AppConfig, BodyConfig
from sask.message import CalendarDate, CofullnessEvent, LunarDate

DEFAULT_COFULLNESS_HORIZON_DAYS = 5 * 365


def _ay_days(config: AppConfig) -> float:
    """AstroYear in days."""
    return (
        config.time_constants.astro_year_pulses / config.time_constants.pulses_per_day
    )


def _synodic_period_days(moon_id: str, config: AppConfig) -> float:
    """Synodic period in days. 'mean' returns the mean over all 8 real moons."""
    ay = _ay_days(config)
    moons = [b for b in config.bodies if b.body_type == "moon"]

    def _tsyn(body: BodyConfig) -> float:
        return 1.0 / (1.0 / body.sidereal_period_days - 1.0 / ay)

    if moon_id == "mean":
        return sum(_tsyn(b) for b in moons) / len(moons)
    body = next((b for b in config.bodies if b.name.lower() == moon_id.lower()), None)
    if body is None:
        raise ValueError(f"Moon {moon_id!r} not found in body config")
    return _tsyn(body)


def _synodic_frac_body(body: BodyConfig, pulse: int, config: AppConfig) -> float:
    """Synodic fraction in [0, 1) for a real moon at pulse.

    0 = new (conjunction); 0.5 = full (opposition). Consistent with SPEC-007.
    """
    ppd = config.time_constants.pulses_per_day
    ayp = config.time_constants.astro_year_pulses
    t_sid_pulses = body.sidereal_period_days * ppd
    sidereal_frac = (body.epoch_offset + pulse / t_sid_pulses) % 1.0
    planet_frac = (pulse / ayp) % 1.0
    return (sidereal_frac - planet_frac) % 1.0


def _epoch_pulse(anchor: str, offset_days: float, config: AppConfig) -> int:
    """Resolve epoch_anchor + offset_days to an Astro pulse."""
    ppd = config.time_constants.pulses_per_day
    if anchor == "fatunik_solar_epoch":
        base = (
            config.fatunik.epoch_astro_day - 1
        ) * ppd + config.fatunik.day_start_offset
    elif anchor == "terpin_solar_epoch":
        base = (
            config.terpin.epoch_astro_day - 1
        ) * ppd + config.terpin.day_start_offset
    else:
        raise ValueError(f"Unknown epoch_anchor: {anchor!r}")
    return round(base + offset_days * ppd)


@functools.lru_cache(maxsize=None)
def _round_turns_for(
    months_per_turn: int, t_syn_days: float, ay_days: float, tolerance: float
) -> int:
    """Smallest K >= 1 turns where K turns realigns with AstroYear within tolerance."""
    turn_days = months_per_turn * t_syn_days
    for k in range(1, 100_001):
        nearest = round(k * turn_days / ay_days)
        if abs(k * turn_days - nearest * ay_days) <= tolerance:
            return k
    raise ValueError(
        f"Round not found within 100,000 turns "
        f"(months_per_turn={months_per_turn}, t_syn={t_syn_days:.4f}d)"
    )


def near_full(moon_id: str, pulse: int, config: AppConfig) -> bool:
    """True when the moon's illuminated fraction meets the configured threshold.

    Uses observer-visible illumination rather than a time-window around the
    exact full-moment, so slow moons (long synodic period) are treated the
    same as fast ones when they look equally full to a naked-eye observer.
    """
    body = next(b for b in config.bodies if b.name.lower() == moon_id.lower())
    syn = _synodic_frac_body(body, pulse, config)
    illum = (1.0 - math.cos(2.0 * math.pi * syn)) / 2.0
    return illum >= config.cofullness.full_illumination_threshold


def get_lunar_date(pulse: int, calendar_id: str, config: AppConfig) -> LunarDate:
    """Return the lunar date for a pulse in the named calendar."""
    cal_cfg = next(c for c in config.lunar_calendars if c.id == calendar_id)
    ppd = config.time_constants.pulses_per_day
    ay_days = _ay_days(config)
    t_syn_days = _synodic_period_days(cal_cfg.moon, config)
    t_syn_pulses = t_syn_days * ppd
    epoch_p = _epoch_pulse(cal_cfg.epoch_anchor, cal_cfg.epoch_offset_days, config)

    elapsed = pulse - epoch_p
    lunation = math.floor(elapsed / t_syn_pulses)
    cycle_offset = elapsed % t_syn_pulses
    day = math.floor(cycle_offset / ppd) + 1

    if not cal_cfg.has_turns:
        return LunarDate(
            pulse=pulse,
            calendar_id=calendar_id,
            has_turns=False,
            lunation=lunation,
            day=day,
        )

    assert cal_cfg.months_per_turn is not None  # always set when has_turns=True
    months = cal_cfg.months_per_turn
    round_turns = _round_turns_for(
        months, t_syn_days, ay_days, config.lunar_settings.realign_tolerance_days
    )
    month = lunation % months + 1
    turn = lunation // months
    short_count = turn % round_turns + 1
    long_count = turn // round_turns

    return LunarDate(
        pulse=pulse,
        calendar_id=calendar_id,
        has_turns=True,
        lunation=lunation,
        day=day,
        month=month,
        turn=turn,
        short_count=short_count,
        long_count=long_count,
    )


def _cofullness_events(
    start_pulse: int, end_pulse: int, config: AppConfig
) -> Iterator[CofullnessEvent]:
    """Yield each night in [start_pulse, end_pulse] where >= min_moons are near-full.

    Checks at midnight (Astro day boundary) of each day in the range, lazily:
    a caller that only wants the first match (next_cofullness) stops the
    scan there instead of paying for the rest of the range.
    """
    ppd = config.time_constants.pulses_per_day
    min_moons = config.cofullness.min_moons
    moon_ids = [b.name.lower() for b in config.bodies if b.body_type == "moon"]

    p = math.ceil(start_pulse / ppd) * ppd  # first midnight at or after start_pulse
    while p <= end_pulse:
        nf_ids = [mid for mid in moon_ids if near_full(mid, p, config)]
        if len(nf_ids) >= min_moons:
            solar_dates: tuple[CalendarDate, ...] = (
                astro_to_fatunik(p, config),
                astro_to_terpin(p, config),
            )
            yield CofullnessEvent(
                pulse=p,
                count=len(nf_ids),
                moons=tuple(nf_ids),
                solar_dates=solar_dates,
            )
        p += ppd


def get_cofullness(
    start_pulse: int, end_pulse: int, config: AppConfig
) -> list[CofullnessEvent]:
    """Return all nights in [start_pulse, end_pulse] where >= min_moons are near-full.

    See _cofullness_events for the per-night rule. Use next_cofullness
    instead when only the first qualifying night is needed - it stops at
    the first match rather than scanning the whole range.
    """
    return list(_cofullness_events(start_pulse, end_pulse, config))


def next_cofullness(
    start_pulse: int,
    config: AppConfig,
    *,
    horizon_days: int = DEFAULT_COFULLNESS_HORIZON_DAYS,
) -> CofullnessEvent | None:
    """Return the first qualifying night at or after start_pulse, or None.

    Stops scanning at the first match - unlike get_cofullness, it never
    pays for nights beyond the answer. None means no qualifying night
    occurred within horizon_days.
    """
    ppd = config.time_constants.pulses_per_day
    end_pulse = start_pulse + horizon_days * ppd
    return next(_cofullness_events(start_pulse, end_pulse, config), None)

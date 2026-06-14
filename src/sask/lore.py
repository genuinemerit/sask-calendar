"""SPEC-017: lore overlay renderers for time-of-day and calendar dates."""

from __future__ import annotations

from .config_loader import AppConfig, CalendarLoreConfig, LoreAge
from .lunar import _synodic_period_days, get_lunar_date
from .message import CalendarDate, LunarDate
from .pulse import astro_to_fatunik, astro_to_terpin


def _ordinal(n: int) -> str:
    """Return English ordinal string (1 → '1st', 6 → '6th')."""
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    r = n % 10
    suffix = ("st", "nd", "rd")
    return f"{n}{suffix[r - 1] if 1 <= r <= 3 else 'th'}"


def _find_age(ages: tuple[LoreAge, ...], turn: int) -> LoreAge:
    result = ages[0]
    for age in ages[1:]:
        if age.start_turn <= turn:
            result = age
    return result


def _month_name(lore: CalendarLoreConfig, month_idx: int) -> str:
    if lore.festival_index is not None and month_idx == lore.festival_index:
        return lore.festival_name or ""
    if lore.month_names is None:
        return str(month_idx)
    if lore.festival_index is None:
        return lore.month_names[month_idx - 1]
    return lore.month_names[month_idx - lore.festival_index - 1]


def _phase_idx(day: int, cycle_days: float, n_phases: int) -> int:
    """Return 0-based phase index for a 1-based day within a lunation cycle."""
    return min(int((day - 1) * n_phases / cycle_days), n_phases - 1)


def render_lore_time(pulse: int, culture: str, config: AppConfig) -> str:
    """Render pulse as a lore watch/shur/keyt string for the given culture."""
    lore = config.lore_time
    cult = next((c for c in lore.cultures if c.name == culture), None)
    if cult is None:
        raise ValueError(f"Unknown lore culture: {culture!r}")

    day_start = cult.day_start_pulses
    t = ((pulse % 86400) - day_start) % 86400
    shur_idx = t // 7200
    keyt_idx = (t % 7200) // 720
    watch_idx = shur_idx // 2

    return (
        lore.format_str.replace("{watch}", lore.watch_names[watch_idx])
        .replace("{shur}", str(shur_idx + 1))
        .replace("{keyt}", str(keyt_idx + 1))
    )


def render_lore_date(
    technical_date: CalendarDate | LunarDate,
    calendar_id: str,
    config: AppConfig,
) -> str:
    """Render a CalendarDate or LunarDate as a full lore date string."""
    lore = next((c for c in config.lore_calendars if c.id == calendar_id), None)
    if lore is None:
        raise ValueError(f"Unknown lore calendar: {calendar_id!r}")

    if lore.kind == "solar":
        assert isinstance(technical_date, CalendarDate)
        return _render_solar(technical_date, lore)
    assert isinstance(technical_date, LunarDate)
    return _render_lunar(technical_date, lore, config)


def _render_solar(date: CalendarDate, lore: CalendarLoreConfig) -> str:
    assert lore.ages is not None
    assert lore.week_length is not None
    assert lore.day_names is not None

    age = _find_age(lore.ages, date.year)
    month_name = _month_name(lore, date.month)
    week_idx = (date.day - 1) // lore.week_length
    day_in_week = (date.day - 1) % lore.week_length

    return (
        lore.format_full.replace("{day_name}", lore.day_names[day_in_week])
        .replace("{week_ordinal}", _ordinal(week_idx + 1))
        .replace("{week_word}", lore.week_word or "")
        .replace("{month}", month_name)
        .replace("{turn_word}", lore.turn_word or "")
        .replace("{turn}", str(date.year))
        .replace("{age}", age.name)
    )


def _render_lunar(date: LunarDate, lore: CalendarLoreConfig, config: AppConfig) -> str:
    cal_cfg = next(c for c in config.lunar_calendars if c.id == lore.id)
    cycle_days = _synodic_period_days(cal_cfg.moon, config)

    if lore.era_mode == "none":
        assert lore.phase_terms is not None
        phase_idx = _phase_idx(date.day, cycle_days, len(lore.phase_terms))
        return (
            lore.format_full.replace("{phase_term}", lore.phase_terms[phase_idx])
            .replace("{day}", _ordinal(date.day))
            .replace("{moon_word}", lore.moon_word or "")
            .replace("{moon_count}", _ordinal(date.lunation + 1))
        )

    assert date.has_turns
    assert lore.quarter_names is not None
    month_name = _month_name(lore, date.month)  # type: ignore[arg-type]
    quarter_idx = _phase_idx(date.day, cycle_days, len(lore.quarter_names))

    if lore.era_mode == "round":
        return (
            lore.format_full.replace("{quarter}", lore.quarter_names[quarter_idx])
            .replace("{day}", str(date.day))
            .replace("{month}", month_name)
            .replace("{turn_word}", lore.turn_word or "")
            .replace("{short}", str(date.short_count))  # type: ignore[union-attr]
            .replace("{round_word}", lore.round_word or "")
            .replace("{long}", str(date.long_count + 1))  # type: ignore[operator]
        )

    # era_mode == "ages"
    assert lore.ages is not None
    age = _find_age(lore.ages, date.turn)  # type: ignore[arg-type]
    return (
        lore.format_full.replace("{quarter}", lore.quarter_names[quarter_idx])
        .replace("{day}", str(date.day))
        .replace("{month}", month_name)
        .replace("{turn_word}", lore.turn_word or "")
        .replace("{turn}", str(date.turn))  # type: ignore[union-attr]
        .replace("{age}", age.name)
    )


def apply_lore_overlay(
    scribal_record: dict,
    culture: str,
    calendar_id: str,
    config: AppConfig,
) -> dict:
    """Return a copy of scribal_record with lore_time and lore_date added.

    Does not mutate the original dict.
    """
    pulse = scribal_record["pulse"]
    lore_cfg = next((c for c in config.lore_calendars if c.id == calendar_id), None)
    if lore_cfg is None:
        raise ValueError(f"Unknown lore calendar: {calendar_id!r}")

    if lore_cfg.kind == "solar":
        tech_date: CalendarDate | LunarDate = (
            astro_to_fatunik(pulse, config)
            if calendar_id == "fatunik_solar"
            else astro_to_terpin(pulse, config)
        )
    else:
        tech_date = get_lunar_date(pulse, calendar_id, config)

    result = dict(scribal_record)
    result["lore_time"] = render_lore_time(pulse, culture, config)
    result["lore_date"] = render_lore_date(tech_date, calendar_id, config)
    return result

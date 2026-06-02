"""Load and validate engine config from TOML files (SPEC-002).

The config directory must contain:
  time_constants.toml, calendars.toml, seasons.toml, timeline.toml

All validation is done at load time; callers receive a typed AppConfig or
a ConfigError is raised.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


class ConfigError(ValueError):
    """Raised when a config file is missing, malformed, or invalid."""


# ── Config dataclasses (typed representations of the TOML files) ──────────────


@dataclass(frozen=True)
class TimeConstants:
    pulses_per_day: int
    astro_year_pulses: float


@dataclass(frozen=True)
class FatunikMonths:
    festival_name: str
    festival_days_standard: int
    festival_days_leap: int
    regular_month_days: int
    regular_month_count: int


@dataclass(frozen=True)
class FatunikLeap:
    cycle_short: int
    cycle_skip: int
    cycle_restore: int


@dataclass(frozen=True)
class TerpinMonths:
    festival_name: str
    festival_days_standard: int
    festival_days_long: int
    festival_days_super_long: int
    regular_month_days: int
    regular_month_count: int


@dataclass(frozen=True)
class TerpinLeap:
    long_year_cycle: int
    super_long_year_cycle: int


@dataclass(frozen=True)
class CalendarConfig:
    id: str
    epoch_astro_day: int
    day_start_offset: int


@dataclass(frozen=True)
class FatunikConfig(CalendarConfig):
    months: FatunikMonths
    leap: FatunikLeap


@dataclass(frozen=True)
class TerpinConfig(CalendarConfig):
    months: TerpinMonths
    leap: TerpinLeap


@dataclass(frozen=True)
class SeasonConfig:
    id: str
    name: str
    orbital_start: float


@dataclass(frozen=True)
class SeasonsConfig:
    near_tolerance: float
    seasons: tuple[SeasonConfig, ...]


@dataclass(frozen=True)
class TimelineConfig:
    story_now_pulse: int


@dataclass(frozen=True)
class AppConfig:
    time_constants: TimeConstants
    astro: CalendarConfig
    fatunik: FatunikConfig
    terpin: TerpinConfig
    seasons: SeasonsConfig
    timeline: TimelineConfig


# ── Helpers ───────────────────────────────────────────────────────────────────


def _require(mapping: dict, key: str, source: str) -> object:
    """Return mapping[key] or raise ConfigError naming the source file."""
    if key not in mapping:
        raise ConfigError(f"{source}: missing required key '{key}'")
    return mapping[key]


def _load_toml(path: Path) -> dict:
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {path}")
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path.name}: TOML parse error — {exc}") from exc


# ── Per-file loaders ──────────────────────────────────────────────────────────


def _load_time_constants(raw: dict, src: str) -> TimeConstants:
    ppd = _require(raw, "pulses_per_day", src)
    ayp = _require(raw, "astro_year_pulses", src)
    if not isinstance(ppd, int) or ppd <= 0:
        raise ConfigError(f"{src}: pulses_per_day must be a positive integer")
    if not isinstance(ayp, (int, float)) or ayp <= 0:
        raise ConfigError(f"{src}: astro_year_pulses must be a positive number")
    return TimeConstants(pulses_per_day=int(ppd), astro_year_pulses=float(ayp))


def _load_calendar_base(raw: dict, cal_id: str, src: str) -> dict:
    sec = _require(raw, cal_id, src)
    if not isinstance(sec, dict):
        raise ConfigError(f"{src}: [{cal_id}] must be a table")
    _require(sec, "epoch_astro_day", f"{src} [{cal_id}]")
    _require(sec, "day_start_offset", f"{src} [{cal_id}]")
    return sec


def _load_calendars(
    raw: dict,
    src: str,
) -> tuple[CalendarConfig, FatunikConfig, TerpinConfig]:
    # astro
    a = _load_calendar_base(raw, "astro", src)
    astro = CalendarConfig(
        id="astro",
        epoch_astro_day=int(a["epoch_astro_day"]),
        day_start_offset=int(a["day_start_offset"]),
    )

    # fatunik
    f = _load_calendar_base(raw, "fatunik", src)
    fm_raw = _require(f, "months", f"{src} [fatunik]")
    fl_raw = _require(f, "leap", f"{src} [fatunik]")
    if not isinstance(fm_raw, dict):
        raise ConfigError(f"{src} [fatunik.months] must be a table")
    if not isinstance(fl_raw, dict):
        raise ConfigError(f"{src} [fatunik.leap] must be a table")
    fms = f"{src} [fatunik.months]"
    fm = FatunikMonths(
        festival_name=str(_require(fm_raw, "festival_name", fms)),
        festival_days_standard=int(_require(fm_raw, "festival_days_standard", fms)),
        festival_days_leap=int(_require(fm_raw, "festival_days_leap", fms)),
        regular_month_days=int(_require(fm_raw, "regular_month_days", fms)),
        regular_month_count=int(_require(fm_raw, "regular_month_count", fms)),
    )
    fls = f"{src} [fatunik.leap]"
    fl = FatunikLeap(
        cycle_short=int(_require(fl_raw, "cycle_short", fls)),
        cycle_skip=int(_require(fl_raw, "cycle_skip", fls)),
        cycle_restore=int(_require(fl_raw, "cycle_restore", fls)),
    )
    fatunik = FatunikConfig(
        id="fatunik",
        epoch_astro_day=int(f["epoch_astro_day"]),
        day_start_offset=int(f["day_start_offset"]),
        months=fm,
        leap=fl,
    )

    # terpin
    t = _load_calendar_base(raw, "terpin", src)
    tm_raw = _require(t, "months", f"{src} [terpin]")
    tl_raw = _require(t, "leap", f"{src} [terpin]")
    if not isinstance(tm_raw, dict):
        raise ConfigError(f"{src} [terpin.months] must be a table")
    if not isinstance(tl_raw, dict):
        raise ConfigError(f"{src} [terpin.leap] must be a table")
    tms = f"{src} [terpin.months]"
    tm = TerpinMonths(
        festival_name=str(_require(tm_raw, "festival_name", tms)),
        festival_days_standard=int(_require(tm_raw, "festival_days_standard", tms)),
        festival_days_long=int(_require(tm_raw, "festival_days_long", tms)),
        festival_days_super_long=int(_require(tm_raw, "festival_days_super_long", tms)),
        regular_month_days=int(_require(tm_raw, "regular_month_days", tms)),
        regular_month_count=int(_require(tm_raw, "regular_month_count", tms)),
    )
    tls = f"{src} [terpin.leap]"
    tl = TerpinLeap(
        long_year_cycle=int(_require(tl_raw, "long_year_cycle", tls)),
        super_long_year_cycle=int(_require(tl_raw, "super_long_year_cycle", tls)),
    )
    terpin = TerpinConfig(
        id="terpin",
        epoch_astro_day=int(t["epoch_astro_day"]),
        day_start_offset=int(t["day_start_offset"]),
        months=tm,
        leap=tl,
    )

    return astro, fatunik, terpin


def _load_seasons(raw: dict, src: str) -> SeasonsConfig:
    tol = _require(raw, "near_tolerance", src)
    if not isinstance(tol, (int, float)) or not (0 < tol < 0.5):
        raise ConfigError(
            f"{src}: near_tolerance must be a positive float less than 0.5"
        )
    season_list = _require(raw, "seasons", src)
    if not isinstance(season_list, list) or len(season_list) != 4:
        raise ConfigError(f"{src}: seasons must be an array of exactly 4 entries")
    seasons = []
    for i, s in enumerate(season_list):
        if not isinstance(s, dict):
            raise ConfigError(f"{src}: seasons[{i}] must be a table")
        seasons.append(
            SeasonConfig(
                id=str(_require(s, "id", f"{src} seasons[{i}]")),
                name=str(_require(s, "name", f"{src} seasons[{i}]")),
                orbital_start=float(
                    _require(s, "orbital_start", f"{src} seasons[{i}]")
                ),
            )
        )
    return SeasonsConfig(near_tolerance=float(tol), seasons=tuple(seasons))


def _load_timeline(raw: dict, src: str) -> TimelineConfig:
    snp = _require(raw, "story_now_pulse", src)
    if not isinstance(snp, int):
        raise ConfigError(f"{src}: story_now_pulse must be an integer")
    return TimelineConfig(story_now_pulse=snp)


# ── Public entry point ────────────────────────────────────────────────────────


def load_config(config_dir: Path) -> AppConfig:
    """Load and validate all engine config from config_dir.

    Raises ConfigError on any missing file, missing key, or bad value.
    """
    tc = _load_time_constants(
        _load_toml(config_dir / "time_constants.toml"), "time_constants.toml"
    )
    astro, fatunik, terpin = _load_calendars(
        _load_toml(config_dir / "calendars.toml"), "calendars.toml"
    )
    seasons = _load_seasons(_load_toml(config_dir / "seasons.toml"), "seasons.toml")
    timeline = _load_timeline(_load_toml(config_dir / "timeline.toml"), "timeline.toml")
    return AppConfig(
        time_constants=tc,
        astro=astro,
        fatunik=fatunik,
        terpin=terpin,
        seasons=seasons,
        timeline=timeline,
    )

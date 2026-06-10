"""Load and validate engine config from TOML files (SPEC-002, SPEC-006/007/010).

The config directory must contain:
  time_constants.toml, calendars.toml, seasons.toml, timeline.toml,
  body_data.toml, observation_data.toml,
  star_data.toml, house_data.toml

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
class EventConfig:
    id: str
    name: str
    orbital_position: float


@dataclass(frozen=True)
class SeasonsConfig:
    near_tolerance: float
    seasons: tuple[SeasonConfig, ...]
    events: tuple[EventConfig, ...]


@dataclass(frozen=True)
class TimelineConfig:
    story_now_pulse: int


@dataclass(frozen=True)
class BodyConfig:
    """One celestial body record from body_data.toml (SPEC-006/007)."""

    name: str
    body_type: str  # "moon" | "planet"
    sidereal_period_days: float
    epoch_offset: float  # [0.0, 1.0) frozen by SPEC-006
    inclination_deg: float  # orbital tilt to ecliptic; frozen by SPEC-006
    node: float  # ascending node fraction [0.0, 1.0); frozen by SPEC-006
    diameter_km: float
    albedo: float
    apparent_color: str
    distance_km: float | None  # moons only: orbital radius (constant, circular orbit)
    rotation_type: str | None  # moons only
    rotation_period_days: float | None  # moons only
    semi_major_axis: float | None  # planets only: Gavor-orbit units (Gavor=1.0)
    rings: str | None  # planets only: descriptive text
    visible_moons: int | None  # planets only: count of moons visible through a glass
    notes: str | None


@dataclass(frozen=True)
class GavorConfig:
    """Gavor (the world) and observer reference from observation_data.toml."""

    epoch_offset: float  # = 0.0; heliocentric orbit starts at pulse 0
    semi_major_axis: float  # = 1.0; unit reference for planetary distances
    obliquity_deg: float  # axial tilt = 23.44 degrees
    observer_latitude_deg: float  # canonical observer = 35.47 N


@dataclass(frozen=True)
class FixedStarConfig:
    """One fixed-star record from star_data.toml (SPEC-010)."""

    id: str
    name: str
    season: str  # "perennial" | "greening" | "blazing" | "withering" | "stillness"
    perennial: bool
    brightness: str
    color: str
    variable: bool
    trait: str
    position: str
    epithet: str | None
    lore: str | None
    house: str | None  # house id if linked to a specific house


@dataclass(frozen=True)
class HouseConfig:
    """One House-of-the-Equinox record from house_data.toml (SPEC-010)."""

    id: str
    name: str
    house_type: str  # "seasonal" | "circumpolar"
    shape: str
    lore: str | None
    order: int | None  # seasonal: 1..12; circumpolar: None
    season_span: str | None
    personality: tuple[str, ...] | None
    stars: tuple[str, ...]  # member fixed-star ids; may be empty


@dataclass(frozen=True)
class HouseNamingConfig:
    """Naming metadata from the [houses] block of house_data.toml (SPEC-010)."""

    name_technical: str
    name_colloquial: str
    tradition: str
    heresy_note: str


@dataclass(frozen=True)
class CometConfig:
    """One recurring comet record from comet_data.toml (SPEC-011)."""

    id: str
    name: str
    period_days: float
    epoch_offset: float
    visible_duration_days: float
    brightness: str
    color: str
    tail: str
    lore: str | None


@dataclass(frozen=True)
class SparkConfig:
    """The singleton Spark apparition from spark_data.toml (SPEC-011)."""

    id: str
    host_moon: str
    normal_visibility: float
    visibility_source: str
    glimmer_probability: float
    exposure_min_days: float
    exposure_max_days: float
    brightness: str
    color: str
    lore: str | None


@dataclass(frozen=True)
class LunarCalendarConfig:
    """One lunar calendar record from lunar_calendar_data.toml (SPEC-012)."""

    id: str
    name: str
    culture: str
    moon: str  # moon id or "mean" (Terpin lunar)
    has_turns: bool
    months_per_turn: int | None  # None when has_turns=False
    epoch_anchor: str  # "fatunik_solar_epoch" | "terpin_solar_epoch"
    epoch_offset_days: float
    lore: str | None


@dataclass(frozen=True)
class LunarCalendarSettings:
    """Global settings from the [settings] block of lunar_calendar_data.toml."""

    realign_tolerance_days: float  # tolerance for Round realignment search


@dataclass(frozen=True)
class CofullnessConfig:
    """Co-fullness tracking settings from cofullness_data.toml (SPEC-012)."""

    full_tolerance_days: float  # near-full window: 1 day per moon's synodic period
    min_moons: int  # minimum count to report a co-fullness event
    coverage_anchor: str  # informational: trusted-coverage start anchor
    coverage_note: str | None


@dataclass(frozen=True)
class AppConfig:
    time_constants: TimeConstants
    astro: CalendarConfig
    fatunik: FatunikConfig
    terpin: TerpinConfig
    seasons: SeasonsConfig
    timeline: TimelineConfig
    bodies: tuple[BodyConfig, ...]  # all 15 celestial bodies
    gavor: GavorConfig
    stars: tuple[FixedStarConfig, ...]  # 16 fixed stars (SPEC-010)
    houses: tuple[HouseConfig, ...]  # 14 Houses (SPEC-010)
    house_naming: HouseNamingConfig  # naming metadata (SPEC-010)
    comets: tuple[CometConfig, ...]  # 3 recurring comets (SPEC-011)
    spark: SparkConfig  # singleton Spark (SPEC-011)
    lunar_calendars: tuple[LunarCalendarConfig, ...]  # 4 lunar calendars (SPEC-012)
    lunar_settings: LunarCalendarSettings  # Round realignment settings (SPEC-012)
    cofullness: CofullnessConfig  # co-fullness tracking config (SPEC-012)


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
    event_list = raw.get("events", [])
    if not isinstance(event_list, list):
        raise ConfigError(f"{src}: events must be an array")
    events = []
    for i, e in enumerate(event_list):
        if not isinstance(e, dict):
            raise ConfigError(f"{src}: events[{i}] must be a table")
        esrc = f"{src} events[{i}]"
        events.append(
            EventConfig(
                id=str(_require(e, "id", esrc)),
                name=str(_require(e, "name", esrc)),
                orbital_position=float(_require(e, "orbital_position", esrc)),
            )
        )
    return SeasonsConfig(
        near_tolerance=float(tol),
        seasons=tuple(seasons),
        events=tuple(events),
    )


def _load_timeline(raw: dict, src: str) -> TimelineConfig:
    snp = _require(raw, "story_now_pulse", src)
    if not isinstance(snp, int):
        raise ConfigError(f"{src}: story_now_pulse must be an integer")
    return TimelineConfig(story_now_pulse=snp)


# ── Body and observer loaders ─────────────────────────────────────────────────


def _load_body(raw: dict, src: str) -> BodyConfig:
    name = str(_require(raw, "name", src))
    btype = str(_require(raw, "type", src))
    if btype not in ("moon", "planet"):
        raise ConfigError(f"{src}: type must be 'moon' or 'planet', got {btype!r}")
    return BodyConfig(
        name=name,
        body_type=btype,
        sidereal_period_days=float(_require(raw, "sidereal_period_days", src)),
        epoch_offset=float(_require(raw, "epoch_offset", src)),
        inclination_deg=float(_require(raw, "inclination_deg", src)),
        node=float(_require(raw, "node", src)),
        diameter_km=float(_require(raw, "diameter_km", src)),
        albedo=float(_require(raw, "albedo", src)),
        apparent_color=str(_require(raw, "apparent_color", src)),
        distance_km=float(raw["distance_km"]) if "distance_km" in raw else None,
        rotation_type=str(raw["rotation_type"]) if "rotation_type" in raw else None,
        rotation_period_days=float(raw["rotation_period_days"])
        if "rotation_period_days" in raw
        else None,
        semi_major_axis=float(raw["semi_major_axis"])
        if "semi_major_axis" in raw
        else None,
        rings=str(raw["rings"]) if "rings" in raw else None,
        visible_moons=int(raw["visible_moons"]) if "visible_moons" in raw else None,
        notes=str(raw["notes"]) if "notes" in raw else None,
    )


def _load_bodies(raw: dict, src: str) -> tuple[BodyConfig, ...]:
    entries = raw.get("body", [])
    if not isinstance(entries, list) or len(entries) != 15:
        raise ConfigError(
            f"{src}: expected exactly 15 [[body]] entries, found {len(entries)}"
        )
    return tuple(_load_body(e, f"{src} body[{i}]") for i, e in enumerate(entries))


def _load_gavor(raw: dict, src: str) -> GavorConfig:
    obs = _require(raw, "observation", src)
    gav = _require(raw, "gavor", src)
    if not isinstance(obs, dict):
        raise ConfigError(f"{src}: [observation] must be a table")
    if not isinstance(gav, dict):
        raise ConfigError(f"{src}: [gavor] must be a table")
    return GavorConfig(
        epoch_offset=float(_require(gav, "epoch_offset", f"{src} [gavor]")),
        semi_major_axis=float(_require(gav, "semi_major_axis", f"{src} [gavor]")),
        obliquity_deg=float(_require(obs, "obliquity_deg", f"{src} [observation]")),
        observer_latitude_deg=float(
            _require(obs, "observer_latitude_deg", f"{src} [observation]")
        ),
    )


# ── Stars and houses loaders (SPEC-010) ──────────────────────────────────────

_VALID_STAR_SEASONS = {"perennial", "greening", "blazing", "withering", "stillness"}
_VALID_HOUSE_TYPES = {"seasonal", "circumpolar"}


def _load_fixed_star(raw: dict, src: str) -> FixedStarConfig:
    sid = str(_require(raw, "id", src))
    season = str(_require(raw, "season", src))
    if season not in _VALID_STAR_SEASONS:
        raise ConfigError(
            f"{src}: star '{sid}' season {season!r} not in {_VALID_STAR_SEASONS}"
        )
    return FixedStarConfig(
        id=sid,
        name=str(_require(raw, "name", src)),
        season=season,
        perennial=bool(_require(raw, "perennial", src)),
        brightness=str(_require(raw, "brightness", src)),
        color=str(_require(raw, "color", src)),
        variable=bool(_require(raw, "variable", src)),
        trait=str(_require(raw, "trait", src)),
        position=str(_require(raw, "position", src)),
        epithet=str(raw["epithet"]) if "epithet" in raw else None,
        lore=str(raw["lore"]) if "lore" in raw else None,
        house=str(raw["house"]) if "house" in raw else None,
    )


def _load_fixed_stars(raw: dict, src: str) -> tuple[FixedStarConfig, ...]:
    entries = raw.get("star", [])
    if not isinstance(entries, list) or len(entries) != 16:
        raise ConfigError(
            f"{src}: expected exactly 16 [[star]] entries, found {len(entries)}"
        )
    return tuple(_load_fixed_star(e, f"{src} star[{i}]") for i, e in enumerate(entries))


def _load_house(raw: dict, src: str) -> HouseConfig:
    hid = str(_require(raw, "id", src))
    htype = str(_require(raw, "type", src))
    if htype not in _VALID_HOUSE_TYPES:
        raise ConfigError(
            f"{src}: house '{hid}' type {htype!r} not in {_VALID_HOUSE_TYPES}"
        )
    personality_raw = raw.get("personality")
    personality: tuple[str, ...] | None = (
        tuple(str(p) for p in personality_raw)
        if isinstance(personality_raw, list)
        else None
    )
    stars_raw = raw.get("stars", [])
    return HouseConfig(
        id=hid,
        name=str(_require(raw, "name", src)),
        house_type=htype,
        shape=str(_require(raw, "shape", src)),
        lore=str(raw["lore"]) if "lore" in raw else None,
        order=int(raw["order"]) if "order" in raw else None,
        season_span=str(raw["season_span"]) if "season_span" in raw else None,
        personality=personality,
        stars=tuple(str(s) for s in stars_raw),
    )


def _load_houses(
    raw: dict, src: str
) -> tuple[tuple[HouseConfig, ...], HouseNamingConfig]:
    entries = raw.get("house", [])
    if not isinstance(entries, list) or len(entries) != 14:
        raise ConfigError(
            f"{src}: expected exactly 14 [[house]] entries, found {len(entries)}"
        )
    houses = tuple(_load_house(e, f"{src} house[{i}]") for i, e in enumerate(entries))

    naming_raw = _require(raw, "houses", src)
    if not isinstance(naming_raw, dict):
        raise ConfigError(f"{src}: [houses] must be a table")
    ns = f"{src} [houses]"
    naming = HouseNamingConfig(
        name_technical=str(_require(naming_raw, "name_technical", ns)),
        name_colloquial=str(_require(naming_raw, "name_colloquial", ns)),
        tradition=str(_require(naming_raw, "tradition", ns)),
        heresy_note=str(_require(naming_raw, "heresy_note", ns)),
    )
    return houses, naming


def _load_comet(raw: dict, src: str) -> CometConfig:
    return CometConfig(
        id=str(_require(raw, "id", src)),
        name=str(_require(raw, "name", src)),
        period_days=float(_require(raw, "period_days", src)),  # type: ignore[arg-type]
        epoch_offset=float(_require(raw, "epoch_offset", src)),  # type: ignore[arg-type]
        visible_duration_days=float(_require(raw, "visible_duration_days", src)),  # type: ignore[arg-type]
        brightness=str(_require(raw, "brightness", src)),
        color=str(_require(raw, "color", src)),
        tail=str(_require(raw, "tail", src)),
        lore=str(raw["lore"]) if "lore" in raw else None,
    )


def _load_comets(raw: dict, src: str) -> tuple[CometConfig, ...]:
    entries = raw.get("comet", [])
    if not isinstance(entries, list) or len(entries) != 3:
        raise ConfigError(
            f"{src}: expected exactly 3 [[comet]] entries, found {len(entries)}"
        )
    return tuple(_load_comet(e, f"{src} comet[{i}]") for i, e in enumerate(entries))


def _load_spark(raw: dict, src: str) -> SparkConfig:
    s = _require(raw, "spark", src)
    if not isinstance(s, dict):
        raise ConfigError(f"{src}: [spark] must be a table")
    ns = f"{src} [spark]"
    return SparkConfig(
        id=str(_require(s, "id", ns)),
        host_moon=str(_require(s, "host_moon", ns)),
        normal_visibility=float(_require(s, "normal_visibility", ns)),  # type: ignore[arg-type]
        visibility_source=str(_require(s, "visibility_source", ns)),
        glimmer_probability=float(_require(s, "glimmer_probability", ns)),  # type: ignore[arg-type]
        exposure_min_days=float(_require(s, "exposure_min_days", ns)),  # type: ignore[arg-type]
        exposure_max_days=float(_require(s, "exposure_max_days", ns)),  # type: ignore[arg-type]
        brightness=str(_require(s, "brightness", ns)),
        color=str(_require(s, "color", ns)),
        lore=str(s["lore"]) if "lore" in s else None,
    )


def _load_lunar_calendar_entry(raw: dict, src: str) -> LunarCalendarConfig:
    return LunarCalendarConfig(
        id=str(_require(raw, "id", src)),
        name=str(_require(raw, "name", src)),
        culture=str(_require(raw, "culture", src)),
        moon=str(_require(raw, "moon", src)),
        has_turns=bool(_require(raw, "has_turns", src)),
        months_per_turn=int(raw["months_per_turn"])
        if "months_per_turn" in raw
        else None,
        epoch_anchor=str(_require(raw, "epoch_anchor", src)),
        epoch_offset_days=float(_require(raw, "epoch_offset_days", src)),  # type: ignore[arg-type]
        lore=str(raw["lore"]) if "lore" in raw else None,
    )


def _load_lunar_calendars(
    raw: dict, src: str
) -> tuple[tuple[LunarCalendarConfig, ...], LunarCalendarSettings]:
    settings_raw = _require(raw, "settings", src)
    if not isinstance(settings_raw, dict):
        raise ConfigError(f"{src}: [settings] must be a table")
    tolerance = float(
        _require(settings_raw, "realign_tolerance_days", f"{src} [settings]")
    )  # type: ignore[arg-type]
    settings = LunarCalendarSettings(realign_tolerance_days=tolerance)
    entries = raw.get("calendar", [])
    if not isinstance(entries, list) or len(entries) != 4:
        raise ConfigError(
            f"{src}: expected exactly 4 [[calendar]] entries, found {len(entries)}"
        )
    calendars = tuple(
        _load_lunar_calendar_entry(e, f"{src} calendar[{i}]")
        for i, e in enumerate(entries)
    )
    return calendars, settings


def _load_cofullness(raw: dict, src: str) -> CofullnessConfig:
    c = _require(raw, "cofullness", src)
    if not isinstance(c, dict):
        raise ConfigError(f"{src}: [cofullness] must be a table")
    ns = f"{src} [cofullness]"
    return CofullnessConfig(
        full_tolerance_days=float(_require(c, "full_tolerance_days", ns)),  # type: ignore[arg-type]
        min_moons=int(_require(c, "min_moons", ns)),  # type: ignore[arg-type]
        coverage_anchor=str(_require(c, "coverage_anchor", ns)),
        coverage_note=str(c["coverage_note"]) if "coverage_note" in c else None,
    )


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
    bodies = _load_bodies(_load_toml(config_dir / "body_data.toml"), "body_data.toml")
    gavor = _load_gavor(
        _load_toml(config_dir / "observation_data.toml"), "observation_data.toml"
    )
    stars = _load_fixed_stars(
        _load_toml(config_dir / "star_data.toml"), "star_data.toml"
    )
    houses, house_naming = _load_houses(
        _load_toml(config_dir / "house_data.toml"), "house_data.toml"
    )
    comets = _load_comets(_load_toml(config_dir / "comet_data.toml"), "comet_data.toml")
    spark = _load_spark(_load_toml(config_dir / "spark_data.toml"), "spark_data.toml")
    lunar_calendars, lunar_settings = _load_lunar_calendars(
        _load_toml(config_dir / "lunar_calendar_data.toml"), "lunar_calendar_data.toml"
    )
    cofullness = _load_cofullness(
        _load_toml(config_dir / "cofullness_data.toml"), "cofullness_data.toml"
    )
    return AppConfig(
        time_constants=tc,
        astro=astro,
        fatunik=fatunik,
        terpin=terpin,
        seasons=seasons,
        timeline=timeline,
        bodies=bodies,
        gavor=gavor,
        stars=stars,
        houses=houses,
        house_naming=house_naming,
        comets=comets,
        spark=spark,
        lunar_calendars=lunar_calendars,
        lunar_settings=lunar_settings,
        cofullness=cofullness,
    )

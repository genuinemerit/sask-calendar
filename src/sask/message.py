"""Message-unit dataclasses for the sask engine (REQ-OPS-008).

All message units are frozen dataclasses with snake_case fields.
Downstream callers (UI, tests) import only from this module — never
from internal engine modules directly.
"""

from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(frozen=True)
class PulseInfo:
    """Core quantities derived from a raw pulse (SPEC-002)."""

    pulse: int
    astro_day: int
    day_pulse_offset: int  # pulses elapsed since Astro midnight [0, 86400)
    orbital_position: float  # AstroYear position [0.0, 1.0)


@dataclass(frozen=True)
class CalendarDate:
    """A date expressed in one specific calendar (scaffold for SPEC-003)."""

    calendar_id: str  # "astro" | "fatunik" | "terpin"
    year: int
    month: int
    day: int


@dataclass(frozen=True)
class SeasonInfo:
    """Astronomical season and event proximity for a pulse (SPEC-004)."""

    season_id: str  # "greening" | "blazing" | "withering" | "stillness"
    name: str
    orbital_position: float  # position within the AstroYear [0.0, 1.0)
    near_event_id: str | None = None  # event id if within near_tolerance
    near_event_name: str | None = None  # display name of the near event


@dataclass(frozen=True)
class BodyState:
    """State of a celestial body at a given pulse (SPEC-007).

    All angles in degrees; times in pulses; distances in body-type units
    (km for moons, AU for planets). Brightness and apparent_size are
    dimensionless relative scalars — meaningful for comparison within a
    category, not for cross-category comparison.
    """

    name: str
    body_type: str  # "moon" | "planet"
    sidereal_fraction: float  # [0.0, 1.0) — position in sidereal orbit
    ecliptic_lon_deg: float  # [0.0, 360.0) — geocentric ecliptic longitude
    ecliptic_lat_deg: float  # (-90.0, 90.0) — geocentric ecliptic latitude
    geocentric_dist: float  # km (moons) or AU (planets)
    synodic_fraction: float  # [0.0, 1.0); 0=conjunction/new, 0.5=opposition/full
    illuminated_fraction: float  # [0.0, 1.0] — fraction of visible face lit by Fatune
    visibility: float  # [0.0, 1.0]; 0 when lost in glare or Gavor's shadow
    is_visible: bool
    eclipse_type: str | None  # "solar" | "lunar" | None
    apparent_size: float  # diameter_km / geocentric_dist_km (dimensionless)
    brightness: float  # albedo × illuminated_fraction × apparent_size (relative)


@dataclass(frozen=True)
class SkyPosition:
    """Local-sky horizontal coordinates for a body at a given pulse (SPEC-008).

    Produced by the ecliptic → equatorial → horizontal transform.
    All angles in degrees; all times in pulses.
    Azimuth convention: N=0, E=90, S=180, W=270.
    """

    name: str
    body_type: str  # "moon" | "planet" | "star" (Fatune)
    declination_deg: float  # equatorial declination (-90, 90)
    right_ascension_deg: float  # equatorial RA [0, 360)
    altitude_deg: float  # horizontal altitude (-90, 90); + = above horizon
    azimuth_deg: float  # horizontal azimuth [0, 360); N=0, E=90
    above_horizon: bool
    is_circumpolar: bool  # True: never sets; rise_pulse/set_pulse are None
    is_never_rising: bool  # True: never rises; rise_pulse/set_pulse are None
    transit_pulse: int  # pulse of upper meridian crossing (always defined)
    rise_pulse: int | None  # None when circumpolar or never-rising
    set_pulse: int | None  # None when circumpolar or never-rising


@dataclass(frozen=True)
class HouseInfo:
    """A House of the Equinox in a star_context message unit (SPEC-010).

    season_span and personality are None for circumpolar houses.
    """

    id: str
    name: str
    shape: str
    stars: tuple[str, ...]  # member fixed-star ids; may be empty
    lore: str | None = None
    season_span: str | None = None  # seasonal houses only
    personality: tuple[str, ...] | None = None  # seasonal houses only


@dataclass(frozen=True)
class FixedStarInfo:
    """A visible fixed star in a star_context message unit (SPEC-010)."""

    id: str
    name: str
    season: str  # "perennial" | season id
    brightness: str
    color: str
    variable: bool
    trait: str
    position: str
    epithet: str | None = None
    lore: str | None = None


@dataclass(frozen=True)
class StarContext:
    """Star context for a given pulse: active house, circumpolar houses,
    and visible fixed stars (SPEC-010)."""

    pulse: int
    season: str
    house_of_the_equinox: HouseInfo
    circumpolar_houses: tuple[HouseInfo, ...]
    visible_fixed_stars: tuple[FixedStarInfo, ...]


@dataclass(frozen=True)
class LunarDate:
    """Lunar calendar date for a given pulse (SPEC-012).

    turn, month, short_count, and long_count are None when has_turns=False
    (Hearth/Jembor calendar). month and short_count are 1-based; turn and
    long_count are 0-based.
    """

    pulse: int
    calendar_id: str
    has_turns: bool
    lunation: int  # completed synodic cycles since epoch (can be negative)
    day: int  # 1-based day within current cycle
    month: int | None = None  # 1-based; None when has_turns=False
    turn: int | None = None  # 0-based; None when has_turns=False
    short_count: int | None = None  # 1-based within Round; None when has_turns=False
    long_count: int | None = None  # 0-based Round count; None when has_turns=False


@dataclass(frozen=True)
class CofullnessEvent:
    """A night where >= min_moons real moons are near-full (SPEC-012)."""

    pulse: int
    count: int  # number of near-full moons
    moons: tuple[str, ...]  # moon ids that are near-full
    solar_dates: tuple[CalendarDate, ...]  # Fatunik and Terpin dates


@dataclass(frozen=True)
class BodyInScene:
    """One body visible above the horizon in a SkyScene (SPEC-013).

    body_type: "moon" | "planet" | "comet" | "spark"
    direction: compass + altitude band, e.g. "NE mid"
    phase: named phase for moons/planets; "tail visible" for comets; "glimpsed" for Spark
    """

    id: str
    name: str
    body_type: str
    direction: str
    altitude: float
    color: str
    brightness: float
    phase: str


@dataclass(frozen=True)
class StarInScene:
    """One visible fixed star in a SkyScene (SPEC-013)."""

    id: str
    name: str
    direction: str  # descriptive position text from star config


@dataclass(frozen=True)
class HouseRef:
    """Minimal House reference in a SkyScene (SPEC-013)."""

    id: str
    name: str


@dataclass(frozen=True)
class CofullnessTonightRef:
    """Co-fullness event occurring this Astro day, if any (SPEC-013).

    observable: True if at least one near-full moon is or will be above the
    horizon at some point during the current Astro day (midnight-to-midnight).
    """

    count: int
    moons: tuple[str, ...]
    observable: bool


@dataclass(frozen=True)
class NextCofullnessRef:
    """Next upcoming co-fullness event (SPEC-013)."""

    pulse: int
    count: int
    moons: tuple[str, ...]


@dataclass(frozen=True)
class SkyScene:
    """Composed sky scene for a given pulse (SPEC-013).

    co_fullness_tonight is None when no co-fullness event falls on this Astro day.
    next_co_fullness is always set; it refers to the next event from tomorrow onward.
    """

    pulse: int
    season: str
    bodies_up: tuple[BodyInScene, ...]
    stars_up: tuple[StarInScene, ...]
    active_house: HouseRef
    circumpolar_houses: tuple[HouseRef, ...]
    co_fullness_tonight: CofullnessTonightRef | None
    next_co_fullness: NextCofullnessRef


@dataclass(frozen=True)
class CometInfo:
    """A visible comet in an apparition_context message unit (SPEC-011)."""

    id: str
    name: str
    visibility: float  # [0.0, 1.0]; linear ramp, 1.0 at perihelion
    color: str
    tail: str
    lore: str | None = None


@dataclass(frozen=True)
class SparkInfo:
    """Spark state in an apparition_context message unit (SPEC-011).

    visible=False when not currently glimpsed; visibility and exposure_days are 0.0.
    """

    visible: bool
    visibility: float  # 0.0 or 1.0
    exposure_days: float  # 0.0 when not visible
    lore: str | None = None


@dataclass(frozen=True)
class ApparitionContext:
    """Apparitions (comets and Spark) for a given pulse (SPEC-011)."""

    pulse: int
    comets_visible: tuple[CometInfo, ...]
    spark: SparkInfo


def validate(unit: object) -> list[str]:
    """Return a list of field-level errors for a message-unit dataclass.

    Checks that no required field (any field whose type is not Optional)
    holds None.  Returns an empty list when the unit is valid.
    Fields annotated as X | None are skipped — None is their valid sentinel.
    """
    errors: list[str] = []
    for f in fields(unit):  # type: ignore[arg-type]
        ann = f.type if isinstance(f.type, str) else repr(f.type)
        if "None" in ann:
            continue  # Optional field; None is permitted
        value = getattr(unit, f.name)
        if value is None:
            errors.append(f"{type(unit).__name__}.{f.name} must not be None")
    return errors

"""Presentation translators: message units → view models (SPEC-005, SPEC-009).

Converts raw engine output into display-ready strings. No web-layer dependency.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..message import BodyState, PulseInfo, SkyPosition


# ── SPEC-005 ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PulseViewModel:
    """Display-ready representation of a PulseInfo result."""

    pulse: int
    astro_day: int
    day_pulse_offset: int
    orbital_position: float
    time_of_day: str  # HH:MM:SS (1 pulse = 1 second, from Astro midnight)
    orbital_position_pct: str  # "25.0000%" of AstroYear elapsed


def to_pulse_view(info: PulseInfo) -> PulseViewModel:
    """Translate a PulseInfo message unit into a PulseViewModel for the template."""
    h = info.day_pulse_offset // 3600
    m = (info.day_pulse_offset % 3600) // 60
    s = info.day_pulse_offset % 60
    return PulseViewModel(
        pulse=info.pulse,
        astro_day=info.astro_day,
        day_pulse_offset=info.day_pulse_offset,
        orbital_position=info.orbital_position,
        time_of_day=f"{h:02d}:{m:02d}:{s:02d}",
        orbital_position_pct=f"{info.orbital_position * 100:.4f}%",
    )


# ── SPEC-009 helpers ───────────────────────────────────────────────────────────

_CARDINAL = [
    "N",
    "NNE",
    "NE",
    "ENE",
    "E",
    "ESE",
    "SE",
    "SSE",
    "S",
    "SSW",
    "SW",
    "WSW",
    "W",
    "WNW",
    "NW",
    "NNW",
]


def _cardinal(az_deg: float) -> str:
    return _CARDINAL[int((az_deg + 11.25) / 22.5) % 16]


def _az_str(az_deg: float) -> str:
    return f"{az_deg:.1f}° {_cardinal(az_deg)}"


def _alt_str(alt_deg: float) -> str:
    sign = "+" if alt_deg >= 0 else ""
    return f"{sign}{alt_deg:.1f}°"


def _pulse_str(p: int | None, circumpolar: bool, never_rising: bool) -> str:
    if circumpolar:
        return "circumpolar"
    if never_rising:
        return "never rises"
    return str(p) if p is not None else "—"


def _phase_name(syn: float) -> str:
    """Rough phase name from synodic fraction (0=new, 0.5=full)."""
    if syn < 0.03 or syn >= 0.97:
        return "New"
    if syn < 0.22:
        return "Waxing Crescent"
    if syn < 0.28:
        return "First Quarter"
    if syn < 0.47:
        return "Waxing Gibbous"
    if syn < 0.53:
        return "Full"
    if syn < 0.72:
        return "Waning Gibbous"
    if syn < 0.78:
        return "Last Quarter"
    return "Waning Crescent"


# ── SPEC-009 moon view model ───────────────────────────────────────────────────


@dataclass(frozen=True)
class MoonViewModel:
    """Display-ready state of one moon for the sky view."""

    name: str
    phase_name: str
    illuminated_pct: str  # "87.3%"
    is_visible: bool
    visibility_pct: str  # "0.0%" or "65.4%"
    eclipse: str  # "Solar", "Lunar", or "—"
    altitude: str  # "+42.1°" or "−18.6°"
    azimuth: str  # "135.7° SE"
    above_horizon: bool
    rise_pulse: str
    transit_pulse: str
    set_pulse: str
    notes: str


def to_moon_view(body: BodyState, sky: SkyPosition, notes: str) -> MoonViewModel:
    eclipse = body.eclipse_type.capitalize() if body.eclipse_type else "—"
    return MoonViewModel(
        name=body.name,
        phase_name=_phase_name(body.synodic_fraction),
        illuminated_pct=f"{body.illuminated_fraction * 100:.1f}%",
        is_visible=body.is_visible and sky.above_horizon,
        visibility_pct=f"{body.visibility * 100:.1f}%",
        eclipse=eclipse,
        altitude=_alt_str(sky.altitude_deg),
        azimuth=_az_str(sky.azimuth_deg),
        above_horizon=sky.above_horizon,
        rise_pulse=_pulse_str(sky.rise_pulse, sky.is_circumpolar, sky.is_never_rising),
        transit_pulse=str(sky.transit_pulse),
        set_pulse=_pulse_str(sky.set_pulse, sky.is_circumpolar, sky.is_never_rising),
        notes=notes,
    )


# ── SPEC-009 planet view model ─────────────────────────────────────────────────


@dataclass(frozen=True)
class PlanetViewModel:
    """Display-ready state of one planet for the sky view."""

    name: str
    apparent_color: str
    phase_name: str
    illuminated_pct: str
    is_visible: bool
    visibility_pct: str
    altitude: str
    azimuth: str
    above_horizon: bool
    rise_pulse: str
    transit_pulse: str
    set_pulse: str
    brightness_rel: str  # relative scalar rounded to 4 d.p.
    rings: str  # descriptive text or "None"
    visible_moons: str  # "4" or "0"
    notes: str


def to_planet_view(
    body: BodyState,
    sky: SkyPosition,
    apparent_color: str,
    rings: str | None,
    visible_moons: int | None,
    notes: str,
) -> PlanetViewModel:
    rings_str = rings if rings and rings.lower() != "none" else "None"
    moons_str = str(visible_moons) if visible_moons is not None else "0"
    return PlanetViewModel(
        name=body.name,
        apparent_color=apparent_color,
        phase_name=_phase_name(body.synodic_fraction),
        illuminated_pct=f"{body.illuminated_fraction * 100:.1f}%",
        is_visible=body.is_visible and sky.above_horizon,
        visibility_pct=f"{body.visibility * 100:.1f}%",
        altitude=_alt_str(sky.altitude_deg),
        azimuth=_az_str(sky.azimuth_deg),
        above_horizon=sky.above_horizon,
        rise_pulse=_pulse_str(sky.rise_pulse, sky.is_circumpolar, sky.is_never_rising),
        transit_pulse=str(sky.transit_pulse),
        set_pulse=_pulse_str(sky.set_pulse, sky.is_circumpolar, sky.is_never_rising),
        brightness_rel=f"{body.brightness:.4f}",
        rings=rings_str,
        visible_moons=moons_str,
        notes=notes,
    )

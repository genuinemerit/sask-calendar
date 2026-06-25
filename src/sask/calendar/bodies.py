"""Body kinematics: orbital position, phase, visibility, eclipse (SPEC-007).

All computation is a pure function of pulse + frozen config.  No lore, no
calendar terms, no web-layer imports.

Coordinate conventions:
  - Sidereal/synodic fractions: [0.0, 1.0), circular arithmetic.
  - Ecliptic longitude: degrees [0.0, 360.0), geocentric.
  - Ecliptic latitude: degrees (-90.0, 90.0), geocentric.
  - Synodic fraction: 0 = conjunction (new / lost in glare), 0.5 = opposition (full).
  - Illuminated fraction: 0 = dark, 1 = fully lit.

Phase model (storytelling-grade, not research precision):
  Moons use a synodic-angle formula; planets use the law-of-cosines phase
  angle at the planet in the Fatune–Planet–Gavor triangle.  Both give correct
  qualitative behaviour.  Visibility uses the same synodic-window cutoff for
  all bodies (inner planets are mostly near conjunction and therefore mostly
  invisible, which matches observed behaviour for inner-planet analogues).

Eclipse detection:
  Fires when a body is simultaneously near a node (|ecliptic latitude| <=
  ECLIPSE_LAT_TOL_DEG) and near a syzygy (synodic fraction within
  ECLIPSE_SYZYGY_TOL of 0 or 0.5).  Solar at conjunction; lunar at opposition.
"""

from __future__ import annotations

import math

from sask.config_loader import AppConfig, BodyConfig, GavorConfig, TimeConstants
from sask.message import BodyState

# ── Module constants ───────────────────────────────────────────────────────────

AU_KM = 149_597_870.7  # kilometres per astronomical unit

VISIBILITY_LOW = 0.1  # synodic fractions at or below this: in glare/shadow
VISIBILITY_HIGH = 0.9  # synodic fractions at or above this: in glare/shadow
VISIBILITY_THRESHOLD = 0.15  # minimum visibility scalar to count as "visible"

ECLIPSE_SYZYGY_TOL = 0.03  # synodic fraction tolerance for syzygy (≈ 10.8°)
ECLIPSE_LAT_TOL_DEG = 0.8  # ecliptic latitude tolerance for node proximity


# ── Internal helpers ───────────────────────────────────────────────────────────


def _sidereal_fraction(
    epoch_offset: float,
    sidereal_period_days: float,
    pulse: int,
    pulses_per_day: int,
) -> float:
    period_pulses = sidereal_period_days * pulses_per_day
    return (epoch_offset + pulse / period_pulses) % 1.0


def _gavor_fraction(pulse: int, astro_year_pulses: float) -> float:
    return (pulse / astro_year_pulses) % 1.0


def _ecliptic_lat_deg(
    sidereal_fraction: float, inclination_deg: float, node: float
) -> float:
    """Ecliptic latitude from orbital inclination and ascending node.

    Argument of latitude = angular distance from the ascending node along
    the orbit.  For circular orbits this equals sidereal_fraction - node
    (mod 1.0) scaled to radians.
    """
    arg_lat = 2.0 * math.pi * ((sidereal_fraction - node) % 1.0)
    incl_rad = math.radians(inclination_deg)
    return math.degrees(math.asin(math.sin(incl_rad) * math.sin(arg_lat)))


def _moon_coords(
    sidereal_fraction: float,
    inclination_deg: float,
    node: float,
    distance_km: float,
) -> tuple[float, float, float]:
    """Geocentric ecliptic (lon_deg, lat_deg, dist_km) for a moon."""
    lon_deg = (sidereal_fraction * 360.0) % 360.0
    lat_deg = _ecliptic_lat_deg(sidereal_fraction, inclination_deg, node)
    return lon_deg, lat_deg, distance_km


def _planet_coords(
    planet_frac: float,
    gavor_frac: float,
    semi_major_axis: float,
    inclination_deg: float,
    node: float,
) -> tuple[float, float, float]:
    """Geocentric ecliptic (lon_deg, lat_deg, dist_AU) for a planet.

    Uses heliocentric Cartesian positions for Gavor (semi_major_axis=1.0)
    and the planet, then subtracts to get the geocentric vector.  Circular
    orbits only; storytelling-grade approximation.

    Ecliptic frame convention: the vernal equinox (gavor_frac=0, start of
    Greening) is at ecliptic longitude 0°.  Gavor's heliocentric position
    is therefore at (gavor_frac + 0.5) * 2π — opposite the direction of
    Fatune from Gavor — so that Fatune's geocentric lon = gavor_frac * 360°
    and declination peaks at +obliquity at Blazing (gavor_frac=0.25).
    """
    theta_p = 2.0 * math.pi * planet_frac
    theta_g = 2.0 * math.pi * (gavor_frac + 0.5)
    px = semi_major_axis * math.cos(theta_p)
    py = semi_major_axis * math.sin(theta_p)
    gx = math.cos(theta_g)
    gy = math.sin(theta_g)
    dx = px - gx
    dy = py - gy
    geo_dist_au = math.sqrt(dx * dx + dy * dy)
    lon_deg = math.degrees(math.atan2(dy, dx)) % 360.0
    lat_deg = _ecliptic_lat_deg(planet_frac, inclination_deg, node)
    return lon_deg, lat_deg, geo_dist_au


def _moon_synodic(moon_sidereal: float, gavor_sidereal: float) -> float:
    """Synodic fraction for a moon: 0 = new (conjunction), 0.5 = full (opposition).

    In the ecliptic frame, Fatune appears at gavor_frac * 360°.  A moon at the
    same ecliptic longitude as Fatune is at new moon; a moon at the opposite
    longitude is at full moon.  Synodic fraction = (moon_sid - gavor_sid) % 1.0
    places new moon (moon aligned with Fatune) at 0 and full moon at 0.5.
    """
    return (moon_sidereal - gavor_sidereal) % 1.0


def _planet_synodic(geo_lon_deg: float, gavor_frac: float) -> float:
    """Synodic fraction for a planet: 0 = conjunction, 0.5 = opposition.

    Fatune's geocentric ecliptic longitude = gavor_frac * 360°.  Synodic
    fraction is the angular separation of the planet from Fatune, normalised
    to [0.0, 1.0): 0 = planet in Fatune's direction (conjunction), 0.5 =
    planet opposite Fatune (opposition).
    """
    fatune_dir_deg = (gavor_frac * 360.0) % 360.0
    return ((geo_lon_deg - fatune_dir_deg) / 360.0) % 1.0


def _moon_illuminated(syn_fraction: float) -> float:
    """Illuminated fraction from synodic angle: 0 at new, 1 at full."""
    return (1.0 - math.cos(2.0 * math.pi * syn_fraction)) / 2.0


def _planet_illuminated(semi_major_axis: float, geo_dist_au: float) -> float:
    """Illuminated fraction via law of cosines on the Fatune-Planet-Gavor triangle.

    Phase angle ψ is the Fatune–Planet–Gavor angle; illuminated = (1+cosψ)/2.
    Gavor's semi_major_axis = 1.0 AU by definition.
    """
    a_gavor = 1.0
    denom = 2.0 * semi_major_axis * geo_dist_au
    if denom == 0.0:
        return 0.5
    cos_psi = (semi_major_axis**2 + geo_dist_au**2 - a_gavor**2) / denom
    cos_psi = max(-1.0, min(1.0, cos_psi))
    return (1.0 + cos_psi) / 2.0


def _visibility(syn_fraction: float) -> float:
    """Approximate sky visibility from synodic position.

    Bodies in the [0, VISIBILITY_LOW] and [VISIBILITY_HIGH, 1] bands are
    treated as lost in Fatune's glare (inner planets and moons near
    conjunction) or Gavor's shadow (moons near opposition-side conjunction).
    The same window is used for all body types — an acceptable simplification
    for a storytelling-grade sky model.
    """
    if syn_fraction <= VISIBILITY_LOW or syn_fraction >= VISIBILITY_HIGH:
        return 0.0
    return (1.0 - math.cos(2.0 * math.pi * syn_fraction)) / 2.0


def _circ_near(x: float, target: float, tol: float) -> bool:
    """True if x is within tol of target on the [0, 1) circle."""
    d = abs((x - target + 0.5) % 1.0 - 0.5)
    return d <= tol


def _eclipse_type(syn_fraction: float, ecliptic_lat_deg: float) -> str | None:
    """Eclipse predicate: node-gated syzygy.

    Returns "solar" (body near conjunction, between Gavor and Fatune),
    "lunar" (Gavor between body and Fatune, body in Gavor's shadow),
    or None.  Both conditions must hold simultaneously.
    """
    if abs(ecliptic_lat_deg) > ECLIPSE_LAT_TOL_DEG:
        return None
    if _circ_near(syn_fraction, 0.0, ECLIPSE_SYZYGY_TOL):
        return "solar"
    if _circ_near(syn_fraction, 0.5, ECLIPSE_SYZYGY_TOL):
        return "lunar"
    return None


# ── Public API ─────────────────────────────────────────────────────────────────


def body_state(
    pulse: int,
    body: BodyConfig,
    gavor: GavorConfig,
    tc: TimeConstants,
) -> BodyState:
    """Compute the full kinematic state of one body at the given pulse."""
    gavor_frac = _gavor_fraction(pulse, tc.astro_year_pulses)
    sid_frac = _sidereal_fraction(
        body.epoch_offset, body.sidereal_period_days, pulse, tc.pulses_per_day
    )

    if body.body_type == "moon":
        assert body.distance_km is not None
        lon_deg, lat_deg, dist = _moon_coords(
            sid_frac, body.inclination_deg, body.node, body.distance_km
        )
        syn = _moon_synodic(sid_frac, gavor_frac)
        illum = _moon_illuminated(syn)
        geo_dist_km = dist
        apparent_sz = body.diameter_km / geo_dist_km
    else:
        assert body.semi_major_axis is not None
        lon_deg, lat_deg, dist = _planet_coords(
            sid_frac, gavor_frac, body.semi_major_axis, body.inclination_deg, body.node
        )
        syn = _planet_synodic(lon_deg, gavor_frac)
        illum = _planet_illuminated(body.semi_major_axis, dist)
        geo_dist_km = dist * AU_KM
        apparent_sz = body.diameter_km / geo_dist_km

    vis = _visibility(syn)
    eclipse = _eclipse_type(syn, lat_deg)
    brightness = body.albedo * illum * apparent_sz

    return BodyState(
        name=body.name,
        body_type=body.body_type,
        sidereal_fraction=sid_frac,
        ecliptic_lon_deg=lon_deg,
        ecliptic_lat_deg=lat_deg,
        geocentric_dist=dist,
        synodic_fraction=syn,
        illuminated_fraction=illum,
        visibility=vis,
        is_visible=vis > VISIBILITY_THRESHOLD,
        eclipse_type=eclipse,
        apparent_size=apparent_sz,
        brightness=brightness,
    )


def all_body_states(pulse: int, config: AppConfig) -> tuple[BodyState, ...]:
    """Compute BodyState for every body in config at the given pulse."""
    return tuple(
        body_state(pulse, b, config.gavor, config.time_constants) for b in config.bodies
    )

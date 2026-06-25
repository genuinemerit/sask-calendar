"""Local-sky position: altitude/azimuth and rise/transit/set (SPEC-008).

Pure coordinate transform sitting on SPEC-007's geocentric ecliptic outputs.
Standard spherical-astronomy transforms, simplified for circular orbits
with no refraction, higher-order parallax, or precession.

Transform chain: ecliptic (lon, lat) → equatorial (RA, dec) → horizontal (alt, az)

Ecliptic frame convention (consistent with bodies.py and season.py):
  - Vernal equinox = gavor_frac = 0 = ecliptic longitude 0°.
  - Fatune's geocentric ecliptic longitude = gavor_frac * 360°.
  - At gavor_frac=0.25 (Blazing/summer), Fatune reaches maximum positive
    declination (+obliquity), giving the longest days at the canonical
    northern observer latitude.

Azimuth convention: N=0, E=90, S=180, W=270 (standard).
Rise/transit/set: integer pulses; None for circumpolar or never-rising bodies.
One sidereal rotation = 86,400 pulses (pulses_per_day).
"""

from __future__ import annotations

import math

from sask.config_loader import AppConfig, GavorConfig, TimeConstants
from sask.message import BodyState, SkyPosition

# ── Internal helpers ───────────────────────────────────────────────────────────


def _ecliptic_to_equatorial(
    lon_deg: float, lat_deg: float, obliquity_deg: float
) -> tuple[float, float]:
    """Convert geocentric ecliptic (lon, lat) to equatorial (RA, dec).

    Returns (right_ascension_deg [0, 360), declination_deg (-90, 90)).
    Standard IAU transform using the planet's axial obliquity.
    """
    lon = math.radians(lon_deg)
    lat = math.radians(lat_deg)
    eps = math.radians(obliquity_deg)

    sin_dec = math.sin(lat) * math.cos(eps) + math.cos(lat) * math.sin(eps) * math.sin(
        lon
    )
    dec = math.asin(max(-1.0, min(1.0, sin_dec)))

    ra = math.atan2(
        math.sin(lon) * math.cos(eps) - math.tan(lat) * math.sin(eps),
        math.cos(lon),
    )
    ra_deg = math.degrees(ra) % 360.0
    dec_deg = math.degrees(dec)
    return ra_deg, dec_deg


def _hour_angle(pulse: int, ra_deg: float, pulses_per_day: int) -> float:
    """Hour angle in radians at the given pulse for a body with the given RA.

    Local Sidereal Time fraction = (pulse / pulses_per_day) % 1.0;
    one full rotation = pulses_per_day pulses (the sidereal day approximation).
    """
    lst_deg = (pulse / pulses_per_day * 360.0) % 360.0
    ha_deg = (lst_deg - ra_deg) % 360.0
    return math.radians(ha_deg)


def _horizontal(
    dec_deg: float, ha_rad: float, observer_lat_deg: float
) -> tuple[float, float]:
    """Convert equatorial (dec, hour angle) to horizontal (altitude, azimuth).

    Returns (altitude_deg (-90, 90), azimuth_deg [0, 360)).
    Azimuth convention: N=0, E=90, S=180, W=270.
    """
    dec = math.radians(dec_deg)
    lat = math.radians(observer_lat_deg)

    sin_alt = math.sin(dec) * math.sin(lat) + math.cos(dec) * math.cos(lat) * math.cos(
        ha_rad
    )
    alt = math.asin(max(-1.0, min(1.0, sin_alt)))

    az = math.atan2(
        -math.cos(dec) * math.sin(ha_rad),
        math.sin(dec) * math.cos(lat)
        - math.cos(dec) * math.sin(lat) * math.cos(ha_rad),
    )
    az_deg = math.degrees(az) % 360.0
    return math.degrees(alt), az_deg


def _rise_transit_set(
    dec_deg: float,
    ra_deg: float,
    observer_lat_deg: float,
    pulse: int,
    pulses_per_day: int,
) -> tuple[int, int | None, int | None, bool, bool]:
    """Compute transit, rise, and set pulses nearest to the given pulse.

    Returns (transit_pulse, rise_pulse, set_pulse, is_circumpolar, is_never_rising).
    rise_pulse and set_pulse are None for circumpolar or never-rising bodies.

    Transit: body crosses the upper meridian (hour angle = 0).
    Rise/set: altitude = 0 (ignoring atmospheric refraction).
    """
    dec = math.radians(dec_deg)
    lat = math.radians(observer_lat_deg)

    # Transit: LST == RA → pulse_transit = ra_fraction * pulses_per_day (+ n*ppd)
    ra_fraction = ra_deg / 360.0
    transit_offset = ra_fraction * pulses_per_day
    n = round((pulse - transit_offset) / pulses_per_day)
    transit_pulse = int(transit_offset + n * pulses_per_day)

    # Hour angle at horizon: cos(H) = -tan(dec)*tan(lat)
    tan_product = math.tan(dec) * math.tan(lat)
    if tan_product < -1.0:
        # cos(H) > 1: body never rises
        return transit_pulse, None, None, False, True
    if tan_product > 1.0:
        # cos(H) < -1: body is circumpolar
        return transit_pulse, None, None, True, False

    h_set = math.acos(-tan_product)  # hour angle at set [0, π]
    h_frac = h_set / (2.0 * math.pi)  # fraction of a day
    half_day = int(h_frac * pulses_per_day)

    rise_pulse = transit_pulse - half_day
    set_pulse = transit_pulse + half_day
    return transit_pulse, rise_pulse, set_pulse, False, False


# ── Public API ─────────────────────────────────────────────────────────────────


def sky_position(
    pulse: int,
    body_state: BodyState,
    gavor: GavorConfig,
    tc: TimeConstants,
) -> SkyPosition:
    """Transform a body's geocentric ecliptic coordinates to local-sky position."""
    ra_deg, dec_deg = _ecliptic_to_equatorial(
        body_state.ecliptic_lon_deg,
        body_state.ecliptic_lat_deg,
        gavor.obliquity_deg,
    )
    ha = _hour_angle(pulse, ra_deg, tc.pulses_per_day)
    alt_deg, az_deg = _horizontal(dec_deg, ha, gavor.observer_latitude_deg)
    transit_p, rise_p, set_p, circumpolar, never_rising = _rise_transit_set(
        dec_deg, ra_deg, gavor.observer_latitude_deg, pulse, tc.pulses_per_day
    )
    return SkyPosition(
        name=body_state.name,
        body_type=body_state.body_type,
        declination_deg=dec_deg,
        right_ascension_deg=ra_deg,
        altitude_deg=alt_deg,
        azimuth_deg=az_deg,
        above_horizon=alt_deg > 0.0,
        is_circumpolar=circumpolar,
        is_never_rising=never_rising,
        transit_pulse=transit_p,
        rise_pulse=rise_p,
        set_pulse=set_p,
    )


def fatune_sky_position(
    pulse: int,
    gavor: GavorConfig,
    tc: TimeConstants,
) -> SkyPosition:
    """Local-sky position of Fatune (the star) at the given pulse.

    Fatune's geocentric ecliptic longitude = gavor_frac * 360°;
    ecliptic latitude = 0° (Fatune defines the ecliptic plane).
    Use above_horizon to test whether it is currently day or night.
    """
    gavor_frac = (pulse / tc.astro_year_pulses) % 1.0
    fatune_lon_deg = (gavor_frac * 360.0) % 360.0

    ra_deg, dec_deg = _ecliptic_to_equatorial(fatune_lon_deg, 0.0, gavor.obliquity_deg)
    ha = _hour_angle(pulse, ra_deg, tc.pulses_per_day)
    alt_deg, az_deg = _horizontal(dec_deg, ha, gavor.observer_latitude_deg)
    transit_p, rise_p, set_p, circumpolar, never_rising = _rise_transit_set(
        dec_deg, ra_deg, gavor.observer_latitude_deg, pulse, tc.pulses_per_day
    )
    return SkyPosition(
        name="Fatune",
        body_type="star",
        declination_deg=dec_deg,
        right_ascension_deg=ra_deg,
        altitude_deg=alt_deg,
        azimuth_deg=az_deg,
        above_horizon=alt_deg > 0.0,
        is_circumpolar=circumpolar,
        is_never_rising=never_rising,
        transit_pulse=transit_p,
        rise_pulse=rise_p,
        set_pulse=set_p,
    )


def all_sky_positions(
    pulse: int,
    body_states: tuple[BodyState, ...],
    config: AppConfig,
) -> tuple[SkyPosition, ...]:
    """Compute SkyPosition for every body in body_states at the given pulse."""
    return tuple(
        sky_position(pulse, bs, config.gavor, config.time_constants)
        for bs in body_states
    )

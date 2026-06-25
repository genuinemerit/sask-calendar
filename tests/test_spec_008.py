"""SPEC-008 tests — local-sky position: altitude/azimuth and rise/transit/set.

Covers:
  - Ecliptic → equatorial: known lon/lat → RA/dec at obliquity 23.44°
  - Equatorial → horizontal: dec=0 body transits due south at 90-lat altitude
  - Transit azimuth is due south (180°) for bodies on the celestial equator
  - Rise/set altitude is ~0 at computed rise and set pulses
  - Above-horizon boolean agrees with altitude sign
  - Transit is the altitude maximum between rise and set
  - Circumpolar body (dec > 90 - observer_lat): no rise/set pulses
  - Never-rising body (dec < -(90 - observer_lat)): no rise/set pulses
  - Fatune's declination = 0 at equinoxes (gavor_frac = 0.0 and 0.5)
  - Fatune's declination = +obliquity at summer solstice (gavor_frac = 0.25)
  - Fatune's declination = -obliquity at winter solstice (gavor_frac = 0.75)
  - Day length > 12h (43200 pulses) at summer solstice
  - Day length < 12h at winter solstice
  - sky.py has no web-layer import (layer purity)
  - all_sky_positions returns 15 SkyPositions matching body order
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from sask.calendar.bodies import all_body_states
from sask.config_loader import load_config
from sask.calendar.sky import (
    _ecliptic_to_equatorial,
    _horizontal,
    _rise_transit_set,
    all_sky_positions,
    fatune_sky_position,
    sky_position,
)

CONFIG = load_config(Path(__file__).parent.parent / "config")
TC = CONFIG.time_constants
GAVOR = CONFIG.gavor
SKY_SRC = Path(__file__).parent.parent / "src" / "sask" / "calendar" / "sky.py"

PPD = TC.pulses_per_day
AYP = TC.astro_year_pulses
OBL = GAVOR.obliquity_deg  # 23.44
LAT = GAVOR.observer_latitude_deg  # 35.47


# ── Ecliptic → equatorial ──────────────────────────────────────────────────────


def test_equinox_ecliptic_gives_zero_declination():
    """Ecliptic lon=0, lat=0 → dec=0 (on celestial equator at vernal equinox)."""
    ra, dec = _ecliptic_to_equatorial(0.0, 0.0, OBL)
    assert dec == pytest.approx(0.0, abs=1e-9)


def test_summer_solstice_ecliptic_gives_max_declination():
    """Ecliptic lon=90, lat=0 → dec=+obliquity (Fatune at summer solstice)."""
    ra, dec = _ecliptic_to_equatorial(90.0, 0.0, OBL)
    assert dec == pytest.approx(OBL, abs=1e-6)


def test_autumn_equinox_ecliptic_gives_zero_declination():
    ra, dec = _ecliptic_to_equatorial(180.0, 0.0, OBL)
    assert dec == pytest.approx(0.0, abs=1e-9)


def test_winter_solstice_ecliptic_gives_min_declination():
    """Ecliptic lon=270, lat=0 → dec=-obliquity."""
    ra, dec = _ecliptic_to_equatorial(270.0, 0.0, OBL)
    assert dec == pytest.approx(-OBL, abs=1e-6)


def test_ecliptic_lat_propagates_to_dec():
    """Non-zero ecliptic latitude shifts declination."""
    _, dec_flat = _ecliptic_to_equatorial(45.0, 0.0, OBL)
    _, dec_tilted = _ecliptic_to_equatorial(45.0, 10.0, OBL)
    assert dec_tilted != pytest.approx(dec_flat, abs=0.5)


# ── Equatorial → horizontal ────────────────────────────────────────────────────


def test_dec0_transit_altitude():
    """Body at dec=0 transits due south at altitude 90 - observer_lat."""
    expected_alt = 90.0 - LAT  # 54.53°
    # At transit, hour angle = 0
    alt, az = _horizontal(0.0, 0.0, LAT)
    assert alt == pytest.approx(expected_alt, abs=1e-6)


def test_dec0_transit_azimuth_is_due_south():
    """Body at dec=0 transits at azimuth 180° (due south)."""
    _, az = _horizontal(0.0, 0.0, LAT)
    assert az == pytest.approx(180.0, abs=1e-6)


def test_altitude_positive_above_horizon():
    """At transit for a visible body, altitude should be positive."""
    alt, _ = _horizontal(0.0, 0.0, LAT)
    assert alt > 0.0


def test_altitude_at_rise_is_zero():
    """At the hour angle of rise, altitude should be ~0."""
    dec = 20.0  # some non-equatorial declination
    dec_r = math.radians(dec)
    lat_r = math.radians(LAT)
    cos_h = -(math.tan(dec_r) * math.tan(lat_r))
    h_rise = -math.acos(cos_h)  # negative HA at rise
    alt, _ = _horizontal(dec, h_rise, LAT)
    assert alt == pytest.approx(0.0, abs=1e-5)


# ── Rise / transit / set ───────────────────────────────────────────────────────


def test_rise_transit_set_order():
    """For a non-circumpolar body, rise < transit < set."""
    transit, rise, set_, _, _ = _rise_transit_set(0.0, 0.0, LAT, 0, PPD)
    assert rise is not None and set_ is not None
    assert rise < transit < set_


def test_transit_is_altitude_maximum():
    """Altitude at transit exceeds altitude at rise and set."""
    transit, rise, set_, _, _ = _rise_transit_set(0.0, 0.0, LAT, 0, PPD)
    ra_deg = 0.0
    dec_deg = 0.0

    def alt_at(p: int) -> float:
        import math as m

        lst_deg = (p / PPD * 360.0) % 360.0
        ha = m.radians((lst_deg - ra_deg) % 360.0)
        alt, _ = _horizontal(dec_deg, ha, LAT)
        return alt

    assert alt_at(transit) > alt_at(rise)
    assert alt_at(transit) > alt_at(set_)


def test_rise_set_altitude_near_zero():
    """Altitude at computed rise and set pulses is close to 0°."""
    transit, rise, set_, _, _ = _rise_transit_set(0.0, 0.0, LAT, 0, PPD)
    ra_deg = 0.0
    dec_deg = 0.0

    def alt_at(p: int) -> float:
        import math as m

        lst_deg = (p / PPD * 360.0) % 360.0
        ha = m.radians((lst_deg - ra_deg) % 360.0)
        alt, _ = _horizontal(dec_deg, ha, LAT)
        return alt

    assert abs(alt_at(rise)) < 1.0  # within 1° (integer rounding)
    assert abs(alt_at(set_)) < 1.0


def test_circumpolar_body_no_rise_set():
    """Body with dec > 90 - LAT (= 54.53°) is circumpolar."""
    dec = 60.0  # > 54.53, circumpolar at 35.47°N
    transit, rise, set_, circumpolar, never_rising = _rise_transit_set(
        dec, 0.0, LAT, 0, PPD
    )
    assert circumpolar is True
    assert never_rising is False
    assert rise is None
    assert set_ is None


def test_never_rising_body_no_rise_set():
    """Body with dec < -(90 - LAT) (= -54.53°) never rises."""
    dec = -60.0  # < -54.53, never visible at 35.47°N
    transit, rise, set_, circumpolar, never_rising = _rise_transit_set(
        dec, 0.0, LAT, 0, PPD
    )
    assert never_rising is True
    assert circumpolar is False
    assert rise is None
    assert set_ is None


def test_equatorial_body_half_day():
    """Body at dec=0 is above horizon for exactly half the day (12h = 43200 pulses)."""
    transit, rise, set_, _, _ = _rise_transit_set(0.0, 0.0, LAT, 0, PPD)
    day_length = set_ - rise
    assert day_length == pytest.approx(PPD / 2, abs=10)  # within 10 pulses of rounding


# ── Fatune (star) sky position ────────────────────────────────────────────────


def test_fatune_declination_zero_at_spring_equinox():
    """gavor_frac=0 → vernal equinox → Fatune dec=0°."""
    pos = fatune_sky_position(0, GAVOR, TC)
    assert pos.declination_deg == pytest.approx(0.0, abs=1e-9)


def test_fatune_declination_max_at_summer_solstice():
    """gavor_frac=0.25 → summer solstice → Fatune dec=+obliquity."""
    pulse = int(0.25 * AYP)
    pos = fatune_sky_position(pulse, GAVOR, TC)
    assert pos.declination_deg == pytest.approx(OBL, abs=1e-4)


def test_fatune_declination_zero_at_autumn_equinox():
    pulse = int(0.5 * AYP)
    pos = fatune_sky_position(pulse, GAVOR, TC)
    assert pos.declination_deg == pytest.approx(0.0, abs=1e-4)


def test_fatune_declination_min_at_winter_solstice():
    """gavor_frac=0.75 → winter solstice → Fatune dec=-obliquity."""
    pulse = int(0.75 * AYP)
    pos = fatune_sky_position(pulse, GAVOR, TC)
    assert pos.declination_deg == pytest.approx(-OBL, abs=1e-4)


def test_summer_day_length_longer_than_12h():
    """At summer solstice, day length > 43200 pulses for northern observer."""
    pulse_solstice = int(0.25 * AYP)
    pos = fatune_sky_position(pulse_solstice, GAVOR, TC)
    assert pos.rise_pulse is not None and pos.set_pulse is not None
    assert (pos.set_pulse - pos.rise_pulse) > PPD // 2


def test_winter_day_length_shorter_than_12h():
    """At winter solstice, day length < 43200 pulses for northern observer."""
    pulse_solstice = int(0.75 * AYP)
    pos = fatune_sky_position(pulse_solstice, GAVOR, TC)
    assert pos.rise_pulse is not None and pos.set_pulse is not None
    assert (pos.set_pulse - pos.rise_pulse) < PPD // 2


# ── sky_position on real body_states ──────────────────────────────────────────


def test_sky_position_fields_in_range():
    states = all_body_states(0, CONFIG)
    for state in states:
        pos = sky_position(0, state, GAVOR, TC)
        assert -90.0 <= pos.altitude_deg <= 90.0
        assert 0.0 <= pos.azimuth_deg < 360.0
        assert -90.0 <= pos.declination_deg <= 90.0
        assert 0.0 <= pos.right_ascension_deg < 360.0


def test_above_horizon_agrees_with_altitude():
    states = all_body_states(0, CONFIG)
    for state in states:
        pos = sky_position(0, state, GAVOR, TC)
        assert pos.above_horizon == (pos.altitude_deg > 0.0)


def test_rise_set_none_iff_circumpolar_or_never_rising():
    states = all_body_states(0, CONFIG)
    for state in states:
        pos = sky_position(0, state, GAVOR, TC)
        if pos.is_circumpolar or pos.is_never_rising:
            assert pos.rise_pulse is None
            assert pos.set_pulse is None
        else:
            assert pos.rise_pulse is not None
            assert pos.set_pulse is not None


def test_all_sky_positions_count_and_order():
    states = all_body_states(0, CONFIG)
    positions = all_sky_positions(0, states, CONFIG)
    assert len(positions) == 15
    assert [p.name for p in positions] == [s.name for s in states]


# ── Layer purity ───────────────────────────────────────────────────────────────


def test_sky_has_no_web_layer_import():
    src = SKY_SRC.read_text(encoding="utf-8")
    assert "flask" not in src.lower()

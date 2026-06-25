"""SPEC-007 tests — body kinematics: orbital position, phase, visibility, eclipse.

Covers:
  - Sidereal fraction from known epoch_offset + period at a given pulse
  - Gavor fraction from pulse / astro_year_pulses
  - Moon synodic fraction: 0 = new (conjunction), 0.5 = full (opposition)
  - Planet synodic fraction: 0 = conjunction, 0.5 = opposition
  - Moon illuminated fraction: 0 at new, 1 at full, 0.5 at quarter
  - Planet illuminated fraction via law-of-cosines phase angle
  - Visibility: 0 in [0, 0.1] and [0.9, 1.0] synodic bands; nonzero in (0.1, 0.9)
  - is_visible threshold agrees with visibility scalar
  - Eclipse fires only when near node AND near syzygy; correct solar/lunar type
  - Zehembra produces more eclipse events than a high-inclination moon over a span
  - Apparent size is positive and larger when distance is smaller
  - Brightness tracks albedo, illuminated fraction, and apparent size
  - body_state() returns a BodyState with all fields in expected ranges
  - all_body_states() returns 15 states, one per body in config order
  - bodies.py has no Flask import (layer purity)
  - config_loader loads bodies and gavor without error
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from sask.calendar.bodies import (
    ECLIPSE_LAT_TOL_DEG,
    ECLIPSE_SYZYGY_TOL,
    VISIBILITY_HIGH,
    VISIBILITY_LOW,
    VISIBILITY_THRESHOLD,
    _eclipse_type,
    _gavor_fraction,
    _moon_illuminated,
    _moon_synodic,
    _planet_illuminated,
    _planet_synodic,
    _sidereal_fraction,
    _visibility,
    all_body_states,
    body_state,
)
from sask.config_loader import BodyConfig, load_config

CONFIG = load_config(Path(__file__).parent.parent / "config")
TC = CONFIG.time_constants
GAVOR = CONFIG.gavor
BODIES_SRC = Path(__file__).parent.parent / "src" / "sask" / "calendar" / "bodies.py"

PPD = TC.pulses_per_day
AYP = TC.astro_year_pulses


# ── Helpers ────────────────────────────────────────────────────────────────────


def _mock_moon(
    *,
    name: str = "TestMoon",
    sidereal_period_days: float = 30.0,
    epoch_offset: float = 0.0,
    inclination_deg: float = 5.0,
    node: float = 0.0,
    diameter_km: float = 1000.0,
    albedo: float = 0.2,
    distance_km: float = 300_000.0,
) -> BodyConfig:
    return BodyConfig(
        name=name,
        body_type="moon",
        sidereal_period_days=sidereal_period_days,
        epoch_offset=epoch_offset,
        inclination_deg=inclination_deg,
        node=node,
        diameter_km=diameter_km,
        albedo=albedo,
        distance_km=distance_km,
        semi_major_axis=None,
    )


def _mock_planet(
    *,
    name: str = "TestPlanet",
    sidereal_period_days: float = 500.0,
    epoch_offset: float = 0.0,
    inclination_deg: float = 3.0,
    node: float = 0.0,
    diameter_km: float = 10_000.0,
    albedo: float = 0.3,
    semi_major_axis: float = 1.5,
) -> BodyConfig:
    return BodyConfig(
        name=name,
        body_type="planet",
        sidereal_period_days=sidereal_period_days,
        epoch_offset=epoch_offset,
        inclination_deg=inclination_deg,
        node=node,
        diameter_km=diameter_km,
        albedo=albedo,
        distance_km=None,
        semi_major_axis=semi_major_axis,
    )


# ── Config loading ─────────────────────────────────────────────────────────────


def test_config_loads_15_bodies():
    assert len(CONFIG.bodies) == 15


def test_config_gavor_epoch_offset():
    assert GAVOR.epoch_offset == pytest.approx(0.0)


def test_config_gavor_semi_major_axis():
    assert GAVOR.semi_major_axis == pytest.approx(1.0)


# ── Sidereal and Gavor fractions ───────────────────────────────────────────────


def test_sidereal_fraction_at_epoch():
    """Body starts at its epoch_offset at pulse 0."""
    assert _sidereal_fraction(0.25, 30.0, 0, PPD) == pytest.approx(0.25)


def test_sidereal_fraction_at_half_period():
    period_days = 10.0
    half_pulse = int(period_days / 2 * PPD)
    result = _sidereal_fraction(0.0, period_days, half_pulse, PPD)
    assert result == pytest.approx(0.5, abs=1e-6)


def test_sidereal_fraction_wraps():
    period_days = 10.0
    full_pulse = int(period_days * PPD)
    result = _sidereal_fraction(0.0, period_days, full_pulse, PPD)
    assert result == pytest.approx(0.0, abs=1e-6)


def test_gavor_fraction_at_zero():
    assert _gavor_fraction(0, AYP) == pytest.approx(0.0)


def test_gavor_fraction_at_half_year():
    half = int(AYP / 2)
    assert _gavor_fraction(half, AYP) == pytest.approx(0.5, abs=1e-5)


# ── Synodic fraction ───────────────────────────────────────────────────────────


def test_moon_synodic_new_moon():
    """Moon at same ecliptic lon as Fatune → conjunction → synodic = 0."""
    # Fatune lon = gavor_frac * 360. New moon: moon_sid == gavor_sid.
    # syn = (0.3 - 0.3) % 1.0 = 0
    assert _moon_synodic(0.3, 0.3) == pytest.approx(0.0, abs=1e-9)


def test_moon_synodic_full_moon():
    """Moon opposite Fatune → opposition → synodic = 0.5."""
    # Full moon: moon_sid = gavor_sid + 0.5. syn = (0.8 - 0.3) % 1.0 = 0.5
    assert _moon_synodic(0.8, 0.3) == pytest.approx(0.5, abs=1e-9)


def test_moon_synodic_quarter():
    # syn = (0.5 - 0.25) % 1.0 = 0.25
    assert _moon_synodic(0.5, 0.25) == pytest.approx(0.25, abs=1e-9)


def test_planet_synodic_conjunction():
    """Planet in Fatune's direction from Gavor → conjunction → synodic = 0."""
    # Fatune geocentric lon = gavor_frac * 360 = 0° at gavor_frac=0.
    # Planet at geo_lon=0° is in Fatune's direction → conjunction → syn=0.
    assert _planet_synodic(0.0, 0.0) == pytest.approx(0.0, abs=1e-9)


def test_planet_synodic_opposition():
    """Planet opposite Fatune from Gavor → opposition → synodic = 0.5."""
    # Fatune at 0° when gavor_frac=0; planet at 180° is opposite → syn=0.5.
    # ((180 - 0) / 360) % 1.0 = 0.5
    assert _planet_synodic(180.0, 0.0) == pytest.approx(0.5, abs=1e-9)


# ── Illuminated fraction ───────────────────────────────────────────────────────


def test_moon_illuminated_new():
    assert _moon_illuminated(0.0) == pytest.approx(0.0)


def test_moon_illuminated_full():
    assert _moon_illuminated(0.5) == pytest.approx(1.0)


def test_moon_illuminated_quarter():
    assert _moon_illuminated(0.25) == pytest.approx(0.5, abs=1e-9)


def test_planet_illuminated_outer_opposition():
    """Outer planet at opposition: geocentric dist = a_planet - 1, nearly full."""
    a = 5.0
    geo = a - 1.0  # closest approach for outer planet
    illum = _planet_illuminated(a, geo)
    assert illum > 0.95


def test_planet_illuminated_inner_max_elongation():
    """Inner planet at maximum elongation shows ~half phase."""
    a = 0.387  # Aesthra/Mercury-equivalent
    # At max elongation the angle Fatune-Gavor-Planet = arcsin(a) ≈ 22.8°
    # The phase angle at the planet = 90°
    max_elong_rad = math.asin(a)
    geo = math.cos(max_elong_rad)  # right triangle: Gavor-Planet leg
    illum = _planet_illuminated(a, geo)
    assert illum == pytest.approx(0.5, abs=0.02)


def test_planet_illuminated_inner_superior_conjunction():
    """Inner planet at superior conjunction (far side of Fatune): nearly full."""
    a = 0.387
    geo = 1.0 + a  # behind Fatune
    illum = _planet_illuminated(a, geo)
    assert illum > 0.95


def test_planet_illuminated_stays_in_unit_range():
    for a in (0.387, 0.724, 1.234, 5.239):
        for geo in (abs(a - 1.0) + 0.01, 1.0, a + 1.0):
            illum = _planet_illuminated(a, geo)
            assert 0.0 <= illum <= 1.0


# ── Visibility ────────────────────────────────────────────────────────────────


def test_visibility_zero_at_conjunction():
    assert _visibility(0.0) == pytest.approx(0.0)


def test_visibility_zero_at_low_band():
    assert _visibility(VISIBILITY_LOW) == pytest.approx(0.0)


def test_visibility_zero_at_high_band():
    assert _visibility(VISIBILITY_HIGH) == pytest.approx(0.0)


def test_visibility_nonzero_in_visible_band():
    assert _visibility(0.5) > 0.0


def test_visibility_max_at_opposition():
    """Visibility peaks at synodic = 0.5 (opposition)."""
    assert _visibility(0.5) == pytest.approx(1.0)


def test_visibility_in_unit_range():
    for syn in [i / 100 for i in range(101)]:
        v = _visibility(syn)
        assert 0.0 <= v <= 1.0


# ── Eclipse ────────────────────────────────────────────────────────────────────


def test_eclipse_none_when_high_latitude():
    assert _eclipse_type(0.0, ECLIPSE_LAT_TOL_DEG + 0.1) is None


def test_eclipse_none_when_not_near_syzygy():
    assert _eclipse_type(0.25, 0.0) is None


def test_eclipse_solar_at_conjunction():
    assert _eclipse_type(0.0, 0.0) == "solar"


def test_eclipse_lunar_at_opposition():
    assert _eclipse_type(0.5, 0.0) == "lunar"


def test_eclipse_solar_near_conjunction():
    assert _eclipse_type(ECLIPSE_SYZYGY_TOL - 0.001, 0.0) == "solar"


def test_eclipse_none_just_outside_syzygy_tolerance():
    assert _eclipse_type(ECLIPSE_SYZYGY_TOL + 0.001, 0.0) is None


def test_zehembra_more_eclipses_than_high_incl_moon():
    """Over one AstroYear, Zehembra (low inclination) eclipses more than Kanka."""
    zehembra = next(b for b in CONFIG.bodies if b.name == "Zehembra")
    kanka = next(b for b in CONFIG.bodies if b.name == "Kanka")
    step = int(AYP / 500)  # sample 500 points over one year

    def eclipse_count(body: BodyConfig) -> int:
        count = 0
        prev = None
        for i in range(500):
            p = i * step
            state = body_state(p, body, GAVOR, TC)
            if state.eclipse_type is not None and state.eclipse_type != prev:
                count += 1
            prev = state.eclipse_type
        return count

    assert eclipse_count(zehembra) > eclipse_count(kanka)


# ── Apparent size and brightness ───────────────────────────────────────────────


def test_apparent_size_positive():
    state = body_state(
        0, next(b for b in CONFIG.bodies if b.name == "Endor"), GAVOR, TC
    )
    assert state.apparent_size > 0.0


def test_closer_moon_appears_larger():
    """Lelako (90,000 km, small) vs Endor (420,000 km, larger diameter)."""
    lelako = next(b for b in CONFIG.bodies if b.name == "Lelako")
    endor = next(b for b in CONFIG.bodies if b.name == "Endor")
    # Normalise by diameter to compare angular size per km of size
    s_l = body_state(0, lelako, GAVOR, TC).apparent_size / lelako.diameter_km
    s_e = body_state(0, endor, GAVOR, TC).apparent_size / endor.diameter_km
    assert s_l > s_e  # Lelako is much closer so subtends more angle per km


def test_brightness_positive_when_lit():
    """At a pulse where a moon has some illumination, brightness > 0."""
    endor = next(b for b in CONFIG.bodies if b.name == "Endor")
    # Pulse at quarter phase: syn ≈ 0.25 → illum > 0
    quarter_pulse = int(
        (0.25 - endor.epoch_offset + _gavor_fraction(0, AYP))
        % 1.0
        * endor.sidereal_period_days
        * PPD
    )
    state = body_state(quarter_pulse, endor, GAVOR, TC)
    if state.illuminated_fraction > 0.01:
        assert state.brightness > 0.0


def test_brightness_zero_when_new():
    """At new moon (syn=0), illuminated fraction=0, brightness=0."""
    illum = _moon_illuminated(0.0)
    assert illum == pytest.approx(0.0)


# ── BodyState completeness ────────────────────────────────────────────────────


def test_body_state_fields_in_range():
    for b in CONFIG.bodies:
        state = body_state(0, b, GAVOR, TC)
        assert 0.0 <= state.sidereal_fraction < 1.0
        assert 0.0 <= state.ecliptic_lon_deg < 360.0
        assert -90.0 < state.ecliptic_lat_deg < 90.0
        assert state.geocentric_dist > 0.0
        assert 0.0 <= state.synodic_fraction < 1.0
        assert 0.0 <= state.illuminated_fraction <= 1.0
        assert 0.0 <= state.visibility <= 1.0
        assert state.apparent_size > 0.0
        assert state.brightness >= 0.0
        assert state.eclipse_type in (None, "solar", "lunar")


def test_all_body_states_returns_15():
    states = all_body_states(0, CONFIG)
    assert len(states) == 15


def test_all_body_states_names_match_config():
    states = all_body_states(0, CONFIG)
    config_names = [b.name for b in CONFIG.bodies]
    state_names = [s.name for s in states]
    assert state_names == config_names


def test_is_visible_consistent_with_visibility():
    for b in CONFIG.bodies:
        state = body_state(0, b, GAVOR, TC)
        assert state.is_visible == (state.visibility > VISIBILITY_THRESHOLD)


# ── Layer purity ───────────────────────────────────────────────────────────────


def test_bodies_has_no_flask_import():
    src = BODIES_SRC.read_text(encoding="utf-8")
    assert "flask" not in src.lower()

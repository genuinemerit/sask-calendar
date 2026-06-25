"""SPEC-009 tests — Web UX: lunar and planetary sky for a given pulse.

Covers:
  - GET /moons and GET /planets return 200
  - With a valid pulse, each of the 8 moons / 7 planets appears in the response
  - Phase name, illuminated %, visibility, altitude, eclipse appear for moons
  - Color, phase, visibility, altitude, brightness appear for planets
  - Rendered HTML contains no <script> tags
  - Fatunik date query resolves to the correct pulse and renders bodies
  - Astro day query resolves to the correct pulse and renders bodies
  - Invalid pulse returns 200 with an error message (no 500)
  - Engine modules have no Flask import (layer purity)
  - Translator has no Flask import
  - Views are additive to SPEC-005 (/ still works)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sask.web import create_app

REAL_CONFIG = Path(__file__).parent.parent / "config"
PROJECT_ROOT = Path(__file__).parent.parent

MOON_NAMES = [
    "Endor",
    "Sella",
    "Lelako",
    "Jembor",
    "Calumbra",
    "Zehembra",
    "Shunna",
    "Kanka",
]
PLANET_NAMES = [
    "Aesthra",
    "Lethra",
    "Beyarus",
    "Dramond",
    "Thurnak",
    "Zelven",
    "Kreetha",
]

ENGINE_MODULES = [
    "src/sask/calendar/pulse.py",
    "src/sask/message.py",
    "src/sask/config_loader.py",
    "src/sask/calendar/season.py",
    "src/sask/calendar/bodies.py",
    "src/sask/calendar/sky.py",
]


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def app():
    return create_app(config_dir=REAL_CONFIG)


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


# ── HTTP smoke ─────────────────────────────────────────────────────────────────


def test_moons_returns_200(client):
    assert client.get("/moons").status_code == 200


def test_planets_returns_200(client):
    assert client.get("/planets").status_code == 200


def test_moons_with_pulse_returns_200(client):
    assert client.get("/moons?pulse=0").status_code == 200


def test_planets_with_pulse_returns_200(client):
    assert client.get("/planets?pulse=0").status_code == 200


# ── Body presence ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize("name", MOON_NAMES)
def test_moons_page_contains_each_moon(client, name):
    resp = client.get("/moons?pulse=0")
    assert name.encode() in resp.data


@pytest.mark.parametrize("name", PLANET_NAMES)
def test_planets_page_contains_each_planet(client, name):
    resp = client.get("/planets?pulse=0")
    assert name.encode() in resp.data


# ── Field presence ────────────────────────────────────────────────────────────


def test_moons_shows_phase_names(client):
    data = client.get("/moons?pulse=0").data
    phase_words = [b"New", b"Crescent", b"Quarter", b"Gibbous", b"Full"]
    assert any(p in data for p in phase_words)


def test_moons_shows_illuminated_pct(client):
    assert b"%" in client.get("/moons?pulse=0").data


def test_moons_shows_eclipse_column(client):
    # Eclipse column header is always present
    assert b"Eclipse" in client.get("/moons?pulse=0").data


def test_moons_shows_altitude(client):
    # Altitude values contain a degree symbol (°)
    assert "°".encode() in client.get("/moons?pulse=0").data


def test_planets_shows_color(client):
    # Beyarus is "Brilliant silver-white"
    assert b"silver" in client.get("/planets?pulse=0").data


def test_planets_shows_brightness(client):
    assert b"Brightness" in client.get("/planets?pulse=0").data


def test_planets_shows_through_a_glass(client):
    assert b"Through a glass" in client.get("/planets?pulse=0").data


# ── Input methods ──────────────────────────────────────────────────────────────


def test_astro_day_query_renders_moons(client):
    resp = client.get("/moons?astro_day=1")
    assert resp.status_code == 200
    assert b"Endor" in resp.data


def test_astro_day_query_renders_planets(client):
    resp = client.get("/planets?astro_day=1")
    assert resp.status_code == 200
    assert b"Aesthra" in resp.data


def test_fatunik_date_query_renders_moons(client):
    # Fatunik Y1 M1 D1 → pulse 0 → same as pulse=0
    resp = client.get("/moons?fatunik_year=1&fatunik_month=1&fatunik_day=1")
    assert resp.status_code == 200
    assert b"Endor" in resp.data


def test_fatunik_date_query_renders_planets(client):
    resp = client.get("/planets?fatunik_year=1&fatunik_month=1&fatunik_day=1")
    assert resp.status_code == 200
    assert b"Aesthra" in resp.data


# ── Error handling ─────────────────────────────────────────────────────────────


def test_invalid_pulse_moons_returns_200_with_error(client):
    resp = client.get("/moons?pulse=abc")
    assert resp.status_code == 200
    assert b"Invalid" in resp.data


def test_invalid_pulse_planets_returns_200_with_error(client):
    resp = client.get("/planets?pulse=abc")
    assert resp.status_code == 200
    assert b"Invalid" in resp.data


# ── No JavaScript ──────────────────────────────────────────────────────────────


def test_moons_no_script_tags(client):
    assert b"<script" not in client.get("/moons?pulse=0").data.lower()


def test_planets_no_script_tags(client):
    assert b"<script" not in client.get("/planets?pulse=0").data.lower()


# ── Calendar date display ──────────────────────────────────────────────────────


def test_moons_shows_fatunik_date(client):
    resp = client.get("/moons?pulse=0")
    assert b"Fatunik" in resp.data


def test_planets_shows_fatunik_date(client):
    resp = client.get("/planets?pulse=0")
    assert b"Fatunik" in resp.data


def test_moons_shows_fatune_horizon_status(client):
    resp = client.get("/moons?pulse=0")
    assert b"Fatune" in resp.data


# ── SPEC-005 additive — root still works ──────────────────────────────────────


def test_root_still_returns_200(client):
    assert client.get("/").status_code == 200


def test_root_still_shows_pulse_form(client):
    assert b"Pulse" in client.get("/").data


# ── Navigation present on all pages ───────────────────────────────────────────


def test_moons_nav_contains_planets_link(client):
    assert b'href="/planets"' in client.get("/moons").data


def test_planets_nav_contains_moons_link(client):
    assert b'href="/moons"' in client.get("/planets").data


# ── Layer purity ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize("rel_path", ENGINE_MODULES)
def test_engine_module_has_no_flask_import(rel_path):
    src = (PROJECT_ROOT / rel_path).read_text(encoding="utf-8")
    assert "flask" not in src.lower()


def test_translator_has_no_flask_import():
    src = (PROJECT_ROOT / "src/sask/web/translator.py").read_text(encoding="utf-8")
    assert "flask" not in src.lower()

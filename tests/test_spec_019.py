"""SPEC-019 tests — festival-month date validation (REQ-FUN-012, DD-0011).

Covers:
  - CalendarRangeError raised for a festival-month day past that turn's
    length, accepted at the boundary, across all five year-type cases:
    Fatunik standard/leap, Terpin regular/long/super-long.
  - CalendarRangeError raised for a regular-month day beyond its fixed
    length; accepted at the boundary.
  - CalendarRangeError raised for an out-of-range month number.
  - fatunik_month_length / terpin_month_length supply the same maxima the
    converters enforce — expected values are read from the accessor, never
    hardcoded.
  - The error message names the month, the turn, and the valid maximum.
  - Pulse and Astro-day inputs are unaffected.
  - The /ephemeris start resolver and the /moons date form render the error
    in-page instead of resolving to a silently-wrong date.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sask.config_loader import load_config
from sask.message import CalendarDate
from sask.pulse import (
    CalendarRangeError,
    fatunik_month_length,
    fatunik_to_pulse,
    terpin_month_length,
    terpin_to_pulse,
)
from sask.web import create_app

REAL_CONFIG = Path(__file__).parent.parent / "config"
CONFIG = load_config(REAL_CONFIG)

_CONVERT = {"fatunik": fatunik_to_pulse, "terpin": terpin_to_pulse}
_MONTH_LENGTH = {"fatunik": fatunik_month_length, "terpin": terpin_month_length}

# (calendar_id, turn) for each year-type case the festival length depends on.
FESTIVAL_CASES = [
    pytest.param("fatunik", 1, id="fatunik-standard"),
    pytest.param("fatunik", 4, id="fatunik-leap"),
    pytest.param("terpin", 1, id="terpin-regular"),
    pytest.param("terpin", 132, id="terpin-long"),
    pytest.param("terpin", 4620, id="terpin-super-long"),
]


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def app():
    return create_app(config_dir=REAL_CONFIG)


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


# ── Festival-month boundary: accept at max, reject one past ────────────────────


@pytest.mark.parametrize("calendar_id, turn", FESTIVAL_CASES)
def test_festival_day_at_max_is_accepted(calendar_id, turn):
    max_day = _MONTH_LENGTH[calendar_id](turn, 1, CONFIG)
    date = CalendarDate(calendar_id, turn, 1, max_day)
    _CONVERT[calendar_id](date, CONFIG)  # must not raise


@pytest.mark.parametrize("calendar_id, turn", FESTIVAL_CASES)
def test_festival_day_past_max_is_rejected(calendar_id, turn):
    max_day = _MONTH_LENGTH[calendar_id](turn, 1, CONFIG)
    date = CalendarDate(calendar_id, turn, 1, max_day + 1)
    with pytest.raises(CalendarRangeError):
        _CONVERT[calendar_id](date, CONFIG)


# ── Regular-month overflow ──────────────────────────────────────────────────────


def test_regular_month_day_at_length_is_accepted():
    fatunik_to_pulse(CalendarDate("fatunik", 1, 2, 30), CONFIG)  # must not raise


def test_regular_month_day_past_length_is_rejected():
    with pytest.raises(CalendarRangeError):
        fatunik_to_pulse(CalendarDate("fatunik", 1, 2, 31), CONFIG)


# ── Month out of range ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("calendar_id", ["fatunik", "terpin"])
def test_month_out_of_range_is_rejected(calendar_id):
    with pytest.raises(CalendarRangeError):
        _CONVERT[calendar_id](CalendarDate(calendar_id, 1, 14, 1), CONFIG)


# ── Error message content ────────────────────────────────────────────────────────


def test_day_error_names_month_turn_and_max():
    with pytest.raises(CalendarRangeError) as exc_info:
        fatunik_to_pulse(CalendarDate("fatunik", 1, 1, 6), CONFIG)
    message = str(exc_info.value)
    assert "month 1" in message
    assert "turn 1" in message
    assert "1-5" in message


def test_month_error_names_turn_and_max():
    with pytest.raises(CalendarRangeError) as exc_info:
        fatunik_to_pulse(CalendarDate("fatunik", 1, 14, 1), CONFIG)
    message = str(exc_info.value)
    assert "turn 1" in message
    assert "1-13" in message


# ── Pulse / Astro-day inputs unaffected ─────────────────────────────────────────


def test_pulse_input_unaffected(client):
    resp = client.get(f"/moons?pulse={CONFIG.timeline.story_now_pulse}")
    assert resp.status_code == 200
    assert b"Invalid" not in resp.data


def test_astro_day_input_unaffected(client):
    resp = client.get("/moons?astro_day=1")
    assert resp.status_code == 200
    assert b"Invalid" not in resp.data


# ── Web-layer rendering: in-page error, not a wrong date ───────────────────────


def test_moons_form_rejects_out_of_range_festival_day(client):
    qs = "/moons?fatunik_year=1&fatunik_month=1&fatunik_day=10"
    resp = client.get(qs)
    assert resp.status_code == 200
    assert b"out of range" in resp.data


def test_ephemeris_start_resolver_rejects_out_of_range_festival_day(client):
    qs = (
        "/ephemeris?start_fatunik_year=1&start_fatunik_month=1"
        "&start_fatunik_day=10&duration_days=1&step_minutes=5&profile=scribal"
    )
    resp = client.get(qs)
    assert resp.status_code == 200
    assert b"out of range" in resp.data

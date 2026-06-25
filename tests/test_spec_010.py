"""SPEC-010 tests — fixed stars and the Houses of the Equinox.

Covers:
  - Active house is always one of the twelve seasonal houses (never circumpolar)
  - Season points (equinoxes/solstices) fall mid-group (houses 11, 2, 5, 8)
  - All twelve seasonal houses reachable across one sidereal year
  - Visible stars: exactly four perennial + three seasonal per season (seven total)
  - Circumpolar houses: always two, always present
  - Calendar independence: result depends only on orbital position, not civil calendars
  - All names and attributes come from config; nothing hardcoded
  - stars.py has no Flask import (layer purity)
"""

from __future__ import annotations

import ast
import math
from pathlib import Path

import pytest

from sask.config_loader import load_config
from sask.message import StarContext, validate
from sask.calendar.stars import (
    HOUSE_ARC_OFFSET,
    HOUSE_ARC_WIDTH,
    HOUSE_COUNT,
    _active_house_order,
    get_star_context,
)

CONFIG = load_config(Path(__file__).parent.parent / "config")
PROJECT_ROOT = Path(__file__).parent.parent
AYP = CONFIG.time_constants.astro_year_pulses

SEASONS = ["greening", "blazing", "withering", "stillness"]
# Season orbital start positions (from seasons.toml: 0, 0.25, 0.5, 0.75)
SEASON_STARTS = [0.0, 0.25, 0.5, 0.75]


def _pulse_at(orbital_pos: float) -> int:
    """Return a pulse near the given orbital position."""
    return math.ceil(orbital_pos * AYP)


# ── Arc placement: house order from orbital position ──────────────────────────


def test_spring_equinox_is_house_11():
    assert _active_house_order(0.0) == 11


def test_summer_solstice_is_house_2():
    assert _active_house_order(0.25) == 2


def test_autumn_equinox_is_house_5():
    assert _active_house_order(0.5) == 5


def test_winter_solstice_is_house_8():
    assert _active_house_order(0.75) == 8


@pytest.mark.parametrize(
    "gavor_frac, expected_order",
    [
        (0.0, 11),  # spring equinox → mid-group 4 (houses 10-11-12)
        (0.25, 2),  # summer solstice → mid-group 1 (houses 1-2-3)
        (0.5, 5),  # autumn equinox → mid-group 2 (houses 4-5-6)
        (0.75, 8),  # winter solstice → mid-group 3 (houses 7-8-9)
    ],
)
def test_season_points_fall_mid_group(gavor_frac, expected_order):
    assert _active_house_order(gavor_frac) == expected_order


def test_all_twelve_house_orders_reachable():
    seen = set()
    for i in range(HOUSE_COUNT):
        frac = (HOUSE_ARC_OFFSET + (i + 0.5) * HOUSE_ARC_WIDTH) % 1.0
        seen.add(_active_house_order(frac))
    assert seen == set(range(1, HOUSE_COUNT + 1))


def test_houses_advance_in_order_across_year():
    orders = []
    for i in range(HOUSE_COUNT):
        frac = (HOUSE_ARC_OFFSET + (i + 0.5) * HOUSE_ARC_WIDTH) % 1.0
        orders.append(_active_house_order(frac))
    assert orders == list(range(1, HOUSE_COUNT + 1))


# ── get_star_context: active house ────────────────────────────────────────────


def test_active_house_is_seasonal_at_pulse_0():
    ctx = get_star_context(0, CONFIG)
    cfg = next(h for h in CONFIG.houses if h.id == ctx.house_of_the_equinox.id)
    assert cfg.house_type == "seasonal"


@pytest.mark.parametrize("orbital_pos", [0.0, 0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9])
def test_active_house_never_circumpolar(orbital_pos):
    ctx = get_star_context(_pulse_at(orbital_pos), CONFIG)
    cfg = next(h for h in CONFIG.houses if h.id == ctx.house_of_the_equinox.id)
    assert cfg.house_type == "seasonal"


def test_all_twelve_seasonal_houses_seen_over_one_year():
    seen_ids = set()
    for i in range(HOUSE_COUNT):
        frac = (HOUSE_ARC_OFFSET + (i + 0.5) * HOUSE_ARC_WIDTH) % 1.0
        ctx = get_star_context(_pulse_at(frac), CONFIG)
        seen_ids.add(ctx.house_of_the_equinox.id)
    seasonal_ids = {h.id for h in CONFIG.houses if h.house_type == "seasonal"}
    assert seen_ids == seasonal_ids


# ── get_star_context: circumpolar houses ──────────────────────────────────────


def test_circumpolar_houses_always_two():
    for pos in [0.0, 0.125, 0.25, 0.5, 0.75]:
        ctx = get_star_context(_pulse_at(pos), CONFIG)
        assert len(ctx.circumpolar_houses) == 2


def test_circumpolar_house_ids_are_stable():
    ctx_a = get_star_context(0, CONFIG)
    ctx_b = get_star_context(_pulse_at(0.5), CONFIG)
    assert {h.id for h in ctx_a.circumpolar_houses} == {
        h.id for h in ctx_b.circumpolar_houses
    }


# ── get_star_context: visible fixed stars ─────────────────────────────────────


@pytest.mark.parametrize("season_id, orbital_pos", list(zip(SEASONS, SEASON_STARTS)))
def test_visible_stars_seven_per_season(season_id, orbital_pos):
    ctx = get_star_context(_pulse_at(orbital_pos + 0.01), CONFIG)
    assert ctx.season == season_id
    assert len(ctx.visible_fixed_stars) == 7


def test_perennial_stars_always_present():
    perennial_ids = {s.id for s in CONFIG.stars if s.perennial}
    assert len(perennial_ids) == 4
    for pos in SEASON_STARTS:
        ctx = get_star_context(_pulse_at(pos + 0.01), CONFIG)
        visible_ids = {s.id for s in ctx.visible_fixed_stars}
        assert perennial_ids <= visible_ids


def test_visible_stars_match_season():
    for season_id, orbital_pos in zip(SEASONS, SEASON_STARTS):
        ctx = get_star_context(_pulse_at(orbital_pos + 0.01), CONFIG)
        seasonal = [s for s in ctx.visible_fixed_stars if not s.season == "perennial"]
        assert all(s.season == season_id for s in seasonal)


# ── Calendar independence ─────────────────────────────────────────────────────


def test_same_orbital_position_gives_same_context():
    p = 5_000_000
    ctx_a = get_star_context(p, CONFIG)
    ctx_b = get_star_context(round(p + AYP), CONFIG)
    assert ctx_a.season == ctx_b.season
    assert ctx_a.house_of_the_equinox.id == ctx_b.house_of_the_equinox.id
    assert len(ctx_a.visible_fixed_stars) == len(ctx_b.visible_fixed_stars)


def test_stars_module_does_not_reference_civil_calendars():
    source = (PROJECT_ROOT / "src/sask/calendar/stars.py").read_text(encoding="utf-8")
    assert "fatunik" not in source.lower()
    assert "terpin" not in source.lower()


# ── Message unit validity ─────────────────────────────────────────────────────


def test_star_context_validates():
    ctx = get_star_context(CONFIG.timeline.story_now_pulse, CONFIG)
    assert validate(ctx) == []


def test_star_context_is_frozen_dataclass():
    ctx = get_star_context(0, CONFIG)
    assert isinstance(ctx, StarContext)
    with pytest.raises((AttributeError, TypeError)):
        ctx.pulse = 999  # type: ignore[misc]


def test_all_house_ids_come_from_config():
    config_ids = {h.id for h in CONFIG.houses if h.house_type == "seasonal"}
    for pos in [0.0, 0.25, 0.5, 0.75, 0.125, 0.375, 0.625, 0.875]:
        ctx = get_star_context(_pulse_at(pos), CONFIG)
        assert ctx.house_of_the_equinox.id in config_ids


def test_all_visible_star_ids_come_from_config():
    config_ids = {s.id for s in CONFIG.stars}
    ctx = get_star_context(CONFIG.timeline.story_now_pulse, CONFIG)
    for star in ctx.visible_fixed_stars:
        assert star.id in config_ids


# ── Layer purity ──────────────────────────────────────────────────────────────


def test_stars_module_has_no_flask_import():
    path = PROJECT_ROOT / "src/sask/calendar/stars.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    flask_imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        and any(
            "flask" in (alias.name or "").lower()
            for alias in getattr(node, "names", [])
        )
        or isinstance(node, ast.ImportFrom)
        and "flask" in (getattr(node, "module", "") or "").lower()
    ]
    assert flask_imports == []

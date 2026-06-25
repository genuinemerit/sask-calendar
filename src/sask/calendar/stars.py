"""Fixed stars and the Houses of the Equinox for a given pulse (SPEC-010).

get_star_context(pulse, config) is a pure function of pulse and config:
  1. season      — from season_info() (SPEC-004)
  2. active house — Gavor's sidereal-arc position mapped to one of the twelve
                    equal arcs (HOUSE_ARC_OFFSET and HOUSE_COUNT below)
  3. visible stars — all perennial stars plus the three stars of the current season
  4. circumpolar houses — always the two type='circumpolar' houses

House arc placement (DD-0005):
  The twelve seasonal arcs are of equal width (HOUSE_ARC_WIDTH = 1/12).
  The offset HOUSE_ARC_OFFSET = 1/8 places house order=1 at gavor_frac=0.125
  (late Greening), so the four season points land mid-group:
    spring equinox (gavor_frac=0.000) → house 11
    summer solstice (gavor_frac=0.250) → house 2
    autumn equinox  (gavor_frac=0.500) → house 5
    winter solstice (gavor_frac=0.750) → house 8
  The offset of 1/24 between each season boundary and the nearest house boundary
  is the 'about half a house' described in DD-0005.
"""

from __future__ import annotations

import math

from sask.calendar.pulse import orbital_position as _orbital_position
from sask.calendar.season import season_info
from sask.config_loader import AppConfig, FixedStarConfig, HouseConfig
from sask.message import FixedStarInfo, HouseInfo, StarContext

HOUSE_COUNT = 12
HOUSE_ARC_OFFSET = 0.125  # gavor_frac where order=1 arc starts
HOUSE_ARC_WIDTH = 1.0 / HOUSE_COUNT


def _active_house_order(gavor_frac: float) -> int:
    """Return the 1-based order (1..12) of the seasonal house at gavor_frac."""
    adjusted = (gavor_frac - HOUSE_ARC_OFFSET) % 1.0
    return math.floor(adjusted * HOUSE_COUNT) + 1


def _make_house_info(cfg: HouseConfig) -> HouseInfo:
    return HouseInfo(
        id=cfg.id,
        name=cfg.name,
        shape=cfg.shape,
        stars=cfg.stars,
        lore=cfg.lore,
        season_span=cfg.season_span,
        personality=cfg.personality,
    )


def _make_star_info(cfg: FixedStarConfig) -> FixedStarInfo:
    return FixedStarInfo(
        id=cfg.id,
        name=cfg.name,
        season=cfg.season,
        brightness=cfg.brightness,
        color=cfg.color,
        variable=cfg.variable,
        trait=cfg.trait,
        position=cfg.position,
        epithet=cfg.epithet,
        lore=cfg.lore,
    )


def get_star_context(pulse: int, config: AppConfig) -> StarContext:
    """Return the star context for the given pulse.

    Uses only time_constants, seasons, stars, and houses from config;
    civil-calendar config is never consulted.
    """
    gavor_frac = _orbital_position(pulse, config.time_constants.astro_year_pulses)
    si = season_info(pulse, config)
    season_id = si.season_id
    active_order = _active_house_order(gavor_frac)

    active_house_cfg = next(h for h in config.houses if h.order == active_order)
    circumpolar_cfgs = [h for h in config.houses if h.house_type == "circumpolar"]

    visible_stars = [s for s in config.stars if s.perennial or s.season == season_id]

    return StarContext(
        pulse=pulse,
        season=season_id,
        house_of_the_equinox=_make_house_info(active_house_cfg),
        circumpolar_houses=tuple(_make_house_info(h) for h in circumpolar_cfgs),
        visible_fixed_stars=tuple(_make_star_info(s) for s in visible_stars),
    )

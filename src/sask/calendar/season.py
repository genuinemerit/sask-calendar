"""Astronomical season and event proximity (SPEC-004).

Seasons and events are derived purely from AstroYear orbital position;
civil calendar leap rules never affect the result.
"""

from __future__ import annotations

from sask.calendar.pulse import orbital_position as _orbital_position
from sask.config_loader import AppConfig, EventConfig, SeasonConfig
from sask.message import SeasonInfo


def _angular_distance(pos: float, event_pos: float) -> float:
    """Shortest circular distance between two orbital positions in [0.0, 1.0)."""
    diff = abs(pos - event_pos)
    return min(diff, 1.0 - diff)


def _find_season(pos: float, seasons: tuple[SeasonConfig, ...]) -> SeasonConfig:
    """Return the season whose orbital_start is the largest value <= pos."""
    result = seasons[0]
    for s in seasons:
        if s.orbital_start <= pos:
            result = s
    return result


def _find_near_event(
    pos: float,
    events: tuple[EventConfig, ...],
    tolerance: float,
) -> EventConfig | None:
    """Return the first event within tolerance of pos (circular), or None."""
    for event in events:
        if _angular_distance(pos, event.orbital_position) <= tolerance:
            return event
    return None


def season_info(pulse: int, cfg: AppConfig) -> SeasonInfo:
    """Return the astronomical season and event proximity for a pulse."""
    pos = _orbital_position(pulse, cfg.time_constants.astro_year_pulses)
    season = _find_season(pos, cfg.seasons.seasons)
    near = _find_near_event(pos, cfg.seasons.events, cfg.seasons.near_tolerance)
    return SeasonInfo(
        season_id=season.id,
        name=season.name,
        orbital_position=pos,
        near_event_id=near.id if near else None,
        near_event_name=near.name if near else None,
    )

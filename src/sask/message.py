"""Message-unit dataclasses for the sask engine (REQ-OPS-008).

All message units are frozen dataclasses with snake_case fields.
Downstream callers (UI, tests) import only from this module — never
from internal engine modules directly.
"""

from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(frozen=True)
class PulseInfo:
    """Core quantities derived from a raw pulse (SPEC-002)."""

    pulse: int
    astro_day: int
    pulse_of_day: int
    orbital_position: float  # AstroYear position [0.0, 1.0)


@dataclass(frozen=True)
class CalendarDate:
    """A date expressed in one specific calendar (scaffold for SPEC-003)."""

    calendar_id: str  # "astro" | "fatunik" | "terpin"
    year: int
    month: int
    day: int


@dataclass(frozen=True)
class SeasonInfo:
    """Astronomical season for a pulse (scaffold for SPEC-004)."""

    season_id: str  # "greening" | "blazing" | "withering" | "stillness"
    name: str
    orbital_position: float  # position within the AstroYear


def validate(unit: object) -> list[str]:
    """Return a list of field-level errors for a message-unit dataclass.

    Checks that no required field (any field whose type is not Optional)
    holds None.  Returns an empty list when the unit is valid.
    """
    errors: list[str] = []
    for f in fields(unit):  # type: ignore[arg-type]
        value = getattr(unit, f.name)
        if value is None:
            errors.append(f"{type(unit).__name__}.{f.name} must not be None")
    return errors

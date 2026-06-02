"""Presentation translator: PulseInfo message unit → PulseViewModel (SPEC-005).

Converts raw engine output into display-ready strings. No Flask dependency.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..message import PulseInfo


@dataclass(frozen=True)
class PulseViewModel:
    """Display-ready representation of a PulseInfo result."""

    pulse: int
    astro_day: int
    day_pulse_offset: int
    orbital_position: float
    time_of_day: str  # HH:MM:SS (1 pulse = 1 second, from Astro midnight)
    orbital_position_pct: str  # "25.0000%" of AstroYear elapsed


def to_pulse_view(info: PulseInfo) -> PulseViewModel:
    """Translate a PulseInfo message unit into a PulseViewModel for the template."""
    h = info.day_pulse_offset // 3600
    m = (info.day_pulse_offset % 3600) // 60
    s = info.day_pulse_offset % 60
    return PulseViewModel(
        pulse=info.pulse,
        astro_day=info.astro_day,
        day_pulse_offset=info.day_pulse_offset,
        orbital_position=info.orbital_position,
        time_of_day=f"{h:02d}:{m:02d}:{s:02d}",
        orbital_position_pct=f"{info.orbital_position * 100:.4f}%",
    )

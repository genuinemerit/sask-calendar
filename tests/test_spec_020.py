"""SPEC-020 tests — co-fullness next-event early exit (REQ-OPS-011, DD-0012).

Covers:
  - next_cofullness matches get_cofullness(...)[0] for representative pulses.
  - get_cofullness's full-range output is unchanged (golden snapshot captured
    from the pre-refactor implementation).
  - get_sky_scene's next_co_fullness value is unchanged (golden snapshot).
  - next_cofullness returns None when nothing qualifies within the horizon.
"""

from __future__ import annotations

from pathlib import Path

from sask.config_loader import load_config
from sask.calendar.lunar import get_cofullness, next_cofullness
from sask.calendar.scene import get_sky_scene

CONFIG = load_config(Path(__file__).parent.parent / "config")
PPD = CONFIG.time_constants.pulses_per_day
STORY = CONFIG.timeline.story_now_pulse

# Captured from the pre-refactor get_cofullness(STORY, STORY + 14*PPD, CONFIG).
GOLDEN_COFULLNESS_14D = [
    (104548147200, 5, ("sella", "jembor", "calumbra", "zehembra", "kanka")),
    (104548233600, 6, ("sella", "lelako", "jembor", "calumbra", "zehembra", "kanka")),
    (104548320000, 5, ("sella", "lelako", "jembor", "calumbra", "kanka")),
    (104548406400, 6, ("sella", "lelako", "jembor", "calumbra", "shunna", "kanka")),
    (104548492800, 6, ("endor", "sella", "jembor", "calumbra", "shunna", "kanka")),
    (104548579200, 5, ("endor", "sella", "jembor", "shunna", "kanka")),
    (104548665600, 3, ("endor", "jembor", "kanka")),
    (104548752000, 2, ("endor", "jembor")),
    (104548838400, 2, ("endor", "jembor")),
    (104548924800, 2, ("endor", "jembor")),
]

# Captured from the pre-refactor get_sky_scene(...).next_co_fullness.
GOLDEN_NEXT_COFULLNESS = {
    STORY: (104548147200, 5, ("sella", "jembor", "calumbra", "zehembra", "kanka")),
    STORY + 200 * PPD: (104565427200, 2, ("jembor", "zehembra")),
}


def test_get_cofullness_full_range_unchanged():
    events = get_cofullness(STORY, STORY + 14 * PPD, CONFIG)
    assert [(e.pulse, e.count, e.moons) for e in events] == GOLDEN_COFULLNESS_14D


def test_get_sky_scene_next_cofullness_unchanged():
    for pulse, expected in GOLDEN_NEXT_COFULLNESS.items():
        nc = get_sky_scene(pulse, CONFIG).next_co_fullness
        assert (nc.pulse, nc.count, nc.moons) == expected


def test_next_cofullness_matches_get_cofullness_first():
    for pulse in (STORY, STORY + 200 * PPD, STORY + 1000 * PPD, 0):
        expected = get_cofullness(pulse, pulse + 5 * 365 * PPD, CONFIG)[0]
        actual = next_cofullness(pulse, CONFIG)
        assert actual == expected


def test_next_cofullness_none_when_horizon_too_short():
    # The midnight right after the golden run's last qualifying night (which
    # itself does not qualify, confirmed via get_cofullness): a horizon of 0
    # days checks only that one midnight, so no event is found.
    after_run = 104548924800 + PPD
    assert next_cofullness(after_run, CONFIG, horizon_days=0) is None


def test_next_cofullness_is_a_prefix_of_get_cofullness():
    """Confirms next_cofullness never skips over an earlier qualifying night."""
    start = STORY
    full = get_cofullness(start, start + 14 * PPD, CONFIG)
    nc = next_cofullness(start, CONFIG, horizon_days=14)
    assert nc == full[0]

"""SPEC-021 tests — ephemeris kinematic rendering reuses body positions
(REQ-OPS-012, DD-0013).

Covers:
  - get_sky_scene returns an identical SkyScene whether or not body_states/
    sky_positions are passed in explicitly.
  - get_sky_series's stored per-step body_states/sky_positions match a
    direct all_body_states/all_sky_positions call for that step's pulse.
  - render_kinematic_json's output is unchanged (golden-snapshot regression
    captured from the pre-refactor implementation).
"""

from __future__ import annotations

from pathlib import Path

from sask.calendar.bodies import all_body_states
from sask.config_loader import load_config
from sask.calendar.ephemeris import get_sky_series, render_kinematic_json
from sask.calendar.scene import get_sky_scene
from sask.calendar.sky import all_sky_positions

CONFIG = load_config(Path(__file__).parent.parent / "config")
PPD = CONFIG.time_constants.pulses_per_day
STORY = CONFIG.timeline.story_now_pulse

# Captured from the pre-refactor render_kinematic_json(get_sky_series(STORY,
# STORY + 600, 300, CONFIG), CONFIG).
GOLDEN_KINEMATIC_3STEP = """{
  "profile": "kinematic",
  "start_pulse": 104548096103,
  "end_pulse": 104548096703,
  "step_pulses": 300,
  "step_count": 3,
  "tracked_bodies": [
    "endor",
    "sella",
    "lelako",
    "jembor",
    "calumbra",
    "zehembra",
    "shunna",
    "kanka",
    "aesthra",
    "lethra",
    "beyarus",
    "dramond",
    "thurnak",
    "zelven",
    "kreetha"
  ],
  "steps": [
    {
      "pulse": 104548096103,
      "bodies": {
        "endor": {
          "alt": 54.3172,
          "az": 261.4184,
          "ill": 0.6423,
          "up": true
        },
        "sella": {
          "alt": 66.3467,
          "az": 191.9626,
          "ill": 0.8866,
          "up": true
        },
        "lelako": {
          "alt": 45.6447,
          "az": 272.4104,
          "ill": 0.5476,
          "up": true
        },
        "jembor": {
          "alt": 63.3515,
          "az": 145.9073,
          "ill": 0.9658,
          "up": true
        },
        "calumbra": {
          "alt": 64.0108,
          "az": 176.8339,
          "ill": 0.9211,
          "up": true
        },
        "zehembra": {
          "alt": 44.9632,
          "az": 131.9192,
          "ill": 0.9998,
          "up": true
        },
        "shunna": {
          "alt": 31.3113,
          "az": 274.37,
          "ill": 0.4304,
          "up": true
        },
        "kanka": {
          "alt": 52.8798,
          "az": 143.8572,
          "ill": 0.9881,
          "up": true
        },
        "aesthra": {
          "alt": -57.5839,
          "az": 332.3757,
          "ill": 0.2382,
          "up": false
        },
        "lethra": {
          "alt": -34.6962,
          "az": 302.9345,
          "ill": 0.9393,
          "up": false
        },
        "beyarus": {
          "alt": -64.6207,
          "az": 4.0348,
          "ill": 0.2052,
          "up": false
        },
        "dramond": {
          "alt": 66.6452,
          "az": 170.5647,
          "ill": 0.9533,
          "up": true
        },
        "thurnak": {
          "alt": -42.7163,
          "az": 304.1225,
          "ill": 0.9997,
          "up": false
        },
        "zelven": {
          "alt": -23.6676,
          "az": 310.0602,
          "ill": 0.9991,
          "up": false
        },
        "kreetha": {
          "alt": -38.7299,
          "az": 301.4379,
          "ill": 1.0,
          "up": false
        }
      }
    },
    {
      "pulse": 104548096403,
      "bodies": {
        "endor": {
          "alt": 53.3397,
          "az": 262.304,
          "ill": 0.6426,
          "up": true
        },
        "sella": {
          "alt": 66.1022,
          "az": 194.8245,
          "ill": 0.8868,
          "up": true
        },
        "lelako": {
          "alt": 44.7259,
          "az": 273.0092,
          "ill": 0.5486,
          "up": true
        },
        "jembor": {
          "alt": 63.8861,
          "az": 148.3247,
          "ill": 0.9658,
          "up": true
        },
        "calumbra": {
          "alt": 64.0257,
          "az": 179.5281,
          "ill": 0.9213,
          "up": true
        },
        "zehembra": {
          "alt": 45.6554,
          "az": 133.2939,
          "ill": 0.9998,
          "up": true
        },
        "shunna": {
          "alt": 30.3647,
          "az": 275.0047,
          "ill": 0.431,
          "up": true
        },
        "kanka": {
          "alt": 53.4475,
          "az": 145.6597,
          "ill": 0.9882,
          "up": true
        },
        "aesthra": {
          "alt": -58.0385,
          "az": 334.5474,
          "ill": 0.2383,
          "up": false
        },
        "lethra": {
          "alt": -35.54,
          "az": 304.0508,
          "ill": 0.9393,
          "up": false
        },
        "beyarus": {
          "alt": -64.5238,
          "az": 6.8894,
          "ill": 0.2052,
          "up": false
        },
        "dramond": {
          "alt": 66.7856,
          "az": 173.6341,
          "ill": 0.9533,
          "up": true
        },
        "thurnak": {
          "alt": -43.5505,
          "az": 305.3902,
          "ill": 0.9997,
          "up": false
        },
        "zelven": {
          "alt": -24.4403,
          "az": 311.0807,
          "ill": 0.9991,
          "up": false
        },
        "kreetha": {
          "alt": -39.5927,
          "az": 302.6027,
          "ill": 1.0,
          "up": false
        }
      }
    },
    {
      "pulse": 104548096703,
      "bodies": {
        "endor": {
          "alt": 52.3602,
          "az": 263.1634,
          "ill": 0.6428,
          "up": true
        },
        "sella": {
          "alt": 65.8108,
          "az": 197.6297,
          "ill": 0.887,
          "up": true
        },
        "lelako": {
          "alt": 43.8076,
          "az": 273.6001,
          "ill": 0.5495,
          "up": true
        },
        "jembor": {
          "alt": 64.3839,
          "az": 150.8271,
          "ill": 0.9659,
          "up": true
        },
        "calumbra": {
          "alt": 63.9947,
          "az": 182.2209,
          "ill": 0.9216,
          "up": true
        },
        "zehembra": {
          "alt": 46.3311,
          "az": 134.7021,
          "ill": 0.9998,
          "up": true
        },
        "shunna": {
          "alt": 29.419,
          "az": 275.635,
          "ill": 0.4316,
          "up": true
        },
        "kanka": {
          "alt": 53.9889,
          "az": 147.5086,
          "ill": 0.9882,
          "up": true
        },
        "aesthra": {
          "alt": -58.4578,
          "az": 336.7709,
          "ill": 0.2384,
          "up": false
        },
        "lethra": {
          "alt": -36.3725,
          "az": 305.1914,
          "ill": 0.9392,
          "up": false
        },
        "beyarus": {
          "alt": -64.3768,
          "az": 9.7196,
          "ill": 0.2052,
          "up": false
        },
        "dramond": {
          "alt": 66.8716,
          "az": 176.7306,
          "ill": 0.9532,
          "up": true
        },
        "thurnak": {
          "alt": -44.3714,
          "az": 306.6918,
          "ill": 0.9997,
          "up": false
        },
        "zelven": {
          "alt": -25.2009,
          "az": 312.1183,
          "ill": 0.9991,
          "up": false
        },
        "kreetha": {
          "alt": -40.4441,
          "az": 303.7959,
          "ill": 1.0,
          "up": false
        }
      }
    }
  ]
}"""


def test_get_sky_scene_unchanged_with_explicit_positions():
    for pulse in (STORY, STORY + 200 * PPD, 0):
        body_states = all_body_states(pulse, CONFIG)
        sky_positions = all_sky_positions(pulse, body_states, CONFIG)
        with_args = get_sky_scene(
            pulse, CONFIG, body_states=body_states, sky_positions=sky_positions
        )
        without_args = get_sky_scene(pulse, CONFIG)
        assert with_args == without_args


def test_get_sky_series_step_positions_match_direct_call():
    series = get_sky_series(STORY, STORY + 900, 300, CONFIG)
    for step in series.steps:
        expected_body_states = all_body_states(step.pulse, CONFIG)
        expected_sky_positions = all_sky_positions(
            step.pulse, expected_body_states, CONFIG
        )
        assert step.body_states == expected_body_states
        assert step.sky_positions == expected_sky_positions


def test_render_kinematic_json_unchanged():
    series = get_sky_series(STORY, STORY + 600, 300, CONFIG)
    assert render_kinematic_json(series, CONFIG) == GOLDEN_KINEMATIC_3STEP

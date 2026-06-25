"""SPEC-018 Layer 1 — pytest-benchmark microbenchmarks over engine hot paths.

Excluded from default collection (pyproject.toml norecursedirs); run
explicitly via `pytest tests/perf/` or `tools/run_perf.sh`. No assertions
about absolute timing live here — REQ-OPS-010's budgets are checked by
Layer 2 (tools/perf_http.py) against medians read back from the saved
results, not by failing this suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from perf_config import EPHEMERIS_GRID, WORST_CASE

from sask.calendar.apparitions import get_apparitions
from sask.calendar.ephemeris import (
    get_sky_series,
    render_kinematic_json,
    render_scribal_json,
)
from sask.calendar.lore import render_lore_date, render_lore_time
from sask.calendar.lunar import get_cofullness, get_lunar_date
from sask.calendar.pulse import astro_to_fatunik
from sask.calendar.scene import get_sky_scene
from sask.calendar.stars import get_star_context
from sask.config_loader import load_config

REAL_CONFIG = Path(__file__).parent.parent.parent / "config"
CONFIG = load_config(REAL_CONFIG)
STORY = CONFIG.timeline.story_now_pulse
PPD = CONFIG.time_constants.pulses_per_day

LUNAR_CALENDAR_IDS = ("untamed", "warren", "hearth", "terpin_lunar")


@pytest.fixture(scope="module")
def worst_case_series():
    return get_sky_series(
        STORY, STORY + WORST_CASE.range_pulses, WORST_CASE.step_pulses, CONFIG
    )


# ── Single-pulse surfaces ───────────────────────────────────────────────────────


def test_get_sky_scene(benchmark):
    benchmark(get_sky_scene, STORY, CONFIG)


def test_get_apparitions(benchmark):
    benchmark(get_apparitions, STORY, CONFIG)


def test_get_star_context(benchmark):
    benchmark(get_star_context, STORY, CONFIG)


@pytest.mark.parametrize("calendar_id", LUNAR_CALENDAR_IDS)
def test_get_lunar_date(benchmark, calendar_id):
    benchmark(get_lunar_date, STORY, calendar_id, CONFIG)


def test_get_cofullness_one_year(benchmark):
    benchmark(get_cofullness, STORY, STORY + 365 * PPD, CONFIG)


# ── Lore renderers (SPEC-017) ───────────────────────────────────────────────────


@pytest.mark.parametrize("culture", ("fatunik", "terpin"))
def test_render_lore_time(benchmark, culture):
    benchmark(render_lore_time, STORY, culture, CONFIG)


def test_render_lore_date_solar(benchmark):
    date = astro_to_fatunik(STORY, CONFIG)
    benchmark(render_lore_date, date, "fatunik_solar", CONFIG)


def test_render_lore_date_lunar(benchmark):
    date = get_lunar_date(STORY, "untamed", CONFIG)
    benchmark(render_lore_date, date, "untamed", CONFIG)


# ── Ephemeris sweep (SPEC-015) ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    "grid_point", EPHEMERIS_GRID, ids=lambda gp: f"{gp.range_label}-{gp.step_label}"
)
def test_get_sky_series(benchmark, grid_point):
    benchmark(
        get_sky_series,
        STORY,
        STORY + grid_point.range_pulses,
        grid_point.step_pulses,
        CONFIG,
    )


def test_render_scribal_json_worst_case(benchmark, worst_case_series):
    benchmark(render_scribal_json, worst_case_series, CONFIG)


def test_render_kinematic_json_worst_case(benchmark, worst_case_series):
    benchmark(render_kinematic_json, worst_case_series, CONFIG)

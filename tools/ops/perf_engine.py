#!/usr/bin/env python3
"""SPEC-025 — stdlib-only engine timing, runnable locally or over SSH.

The dependency-free sibling of tests/perf/test_engine_benchmarks.py: times
the same SPEC-018 hot paths and ephemeris grid with plain time.perf_counter()
instead of pytest-benchmark, so it runs unchanged against the production
droplet's venv (where dev dependencies are deliberately absent). The same
invocation also runs locally for an apples-to-apples comparison.

Usage:
    PYTHONPATH=src poetry run python3 tools/ops/perf_engine.py [--config-dir DIR] [--out PATH]

When --out is omitted, only the JSON result is printed to stdout (and
nothing else), so `ssh sask-droplet "..." > local.json` captures a clean
file.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

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

LUNAR_CALENDAR_IDS = ("untamed", "warren", "hearth", "terpin_lunar")


def _time_call(label: str, fn, *args, repeats: int) -> dict:
    fn(*args)  # one untimed warmup call, same rationale as perf_http.py
    timings = [_elapsed(fn, *args) for _ in range(repeats)]
    return {
        "label": label,
        "repeats": repeats,
        "median_s": statistics.median(timings),
        "min_s": min(timings),
        "max_s": max(timings),
    }


def _elapsed(fn, *args) -> float:
    start = time.perf_counter()
    fn(*args)
    return time.perf_counter() - start


def _run(config_dir: Path, *, fast_repeats: int, slow_repeats: int) -> dict:
    config = load_config(config_dir)
    story = config.timeline.story_now_pulse
    ppd = config.time_constants.pulses_per_day

    fast = [
        _time_call("get_sky_scene", get_sky_scene, story, config, repeats=fast_repeats),
        _time_call(
            "get_apparitions", get_apparitions, story, config, repeats=fast_repeats
        ),
        _time_call(
            "get_star_context", get_star_context, story, config, repeats=fast_repeats
        ),
        *(
            _time_call(
                f"get_lunar_date_{calendar_id}",
                get_lunar_date,
                story,
                calendar_id,
                config,
                repeats=fast_repeats,
            )
            for calendar_id in LUNAR_CALENDAR_IDS
        ),
        _time_call(
            "get_cofullness_one_year",
            get_cofullness,
            story,
            story + 365 * ppd,
            config,
            repeats=fast_repeats,
        ),
        *(
            _time_call(
                f"render_lore_time_{culture}",
                render_lore_time,
                story,
                culture,
                config,
                repeats=fast_repeats,
            )
            for culture in ("fatunik", "terpin")
        ),
    ]

    solar_date = astro_to_fatunik(story, config)
    fast.append(
        _time_call(
            "render_lore_date_solar",
            render_lore_date,
            solar_date,
            "fatunik_solar",
            config,
            repeats=fast_repeats,
        )
    )
    lunar_date = get_lunar_date(story, "untamed", config)
    fast.append(
        _time_call(
            "render_lore_date_lunar",
            render_lore_date,
            lunar_date,
            "untamed",
            config,
            repeats=fast_repeats,
        )
    )

    grid = [
        _time_call(
            f"get_sky_series_{gp.range_label}_{gp.step_label}",
            get_sky_series,
            story,
            story + gp.range_pulses,
            gp.step_pulses,
            config,
            repeats=slow_repeats,
        )
        for gp in EPHEMERIS_GRID
    ]

    worst_case_series = get_sky_series(
        story, story + WORST_CASE.range_pulses, WORST_CASE.step_pulses, config
    )
    worst_case_render = [
        _time_call(
            "render_scribal_json_worst_case",
            render_scribal_json,
            worst_case_series,
            config,
            repeats=slow_repeats,
        ),
        _time_call(
            "render_kinematic_json_worst_case",
            render_kinematic_json,
            worst_case_series,
            config,
            repeats=slow_repeats,
        ),
    ]

    return {
        "config_dir": str(config_dir),
        "story_now_pulse": story,
        "fast_repeats": fast_repeats,
        "slow_repeats": slow_repeats,
        "fast": fast,
        "grid": grid,
        "worst_case_render": worst_case_render,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", type=Path, default=Path("config"))
    parser.add_argument("--fast-repeats", type=int, default=11)
    parser.add_argument("--slow-repeats", type=int, default=3)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    result = _run(
        args.config_dir, fast_repeats=args.fast_repeats, slow_repeats=args.slow_repeats
    )

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2))
        print(f"Wrote results to {args.out}\n")
        print(f"{'label':40s} {'median_ms':>10s} {'min_ms':>10s} {'max_ms':>10s}")
        for entry in result["fast"] + result["grid"] + result["worst_case_render"]:
            print(
                f"{entry['label']:40s} {entry['median_s'] * 1000:10.2f} "
                f"{entry['min_s'] * 1000:10.2f} {entry['max_s'] * 1000:10.2f}"
            )
    else:
        print(json.dumps(result))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

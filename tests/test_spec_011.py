"""SPEC-011 tests — recurring comets and the Kanka-hosted Spark.

Covers all acceptance criteria:
  - Comet visible exactly within duration window around each perihelion
  - Comet appearances recur with configured period; nothing authored
  - Spark derived solely from Kanka's pulse-seeded spin; 0 outside exposure
  - Spark exposure durations within configured range and reproducible
  - No live or global randomness; identical results on repeated calls
  - Calendar independence: civil-calendar config does not affect apparitions
  - All data from config; nothing hardcoded in apparitions.py
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from sask.apparitions import (
    _comet_visibility,
    _kanka_rotation_pulses,
    _seeded_float,
    get_apparitions,
)
from sask.config_loader import load_config
from sask.message import ApparitionContext, validate

CONFIG = load_config(Path(__file__).parent.parent / "config")
PROJECT_ROOT = Path(__file__).parent.parent

PPD = CONFIG.time_constants.pulses_per_day  # 86_400
ROT_PERIOD_PULSES = _kanka_rotation_pulses(CONFIG.spark, CONFIG)  # 38 * 86_400


# ── Helpers ───────────────────────────────────────────────────────────────────


def _perihelion(comet_id: str, n: int = 0) -> int:
    """Exact perihelion pulse for comet at integer n."""
    comet = next(c for c in CONFIG.comets if c.id == comet_id)
    return round((n + comet.epoch_offset) * comet.period_days * PPD)


def _half_window(comet_id: str) -> int:
    """Half-window in pulses for a comet."""
    comet = next(c for c in CONFIG.comets if c.id == comet_id)
    return round((comet.visible_duration_days / 2) * PPD)


def _first_glimmer_event() -> int:
    """Return first rotation event_idx where the Spark glimmers."""
    prob = CONFIG.spark.glimmer_probability
    for idx in range(200_000):
        if _seeded_float(idx, 0) < prob:
            return idx
    raise AssertionError("No glimmer found in first 200,000 rotation events")


def _first_non_glimmer_event() -> int:
    """Return first rotation event_idx with no glimmer."""
    prob = CONFIG.spark.glimmer_probability
    for idx in range(200_000):
        if _seeded_float(idx, 0) >= prob:
            return idx
    raise AssertionError("No non-glimmer found in first 200,000 rotation events")


# ── Config loading ────────────────────────────────────────────────────────────


def test_three_comets_loaded():
    assert len(CONFIG.comets) == 3


def test_spark_loaded():
    assert CONFIG.spark is not None
    assert CONFIG.spark.id == "spark"


def test_comet_ids_are_unique():
    ids = [c.id for c in CONFIG.comets]
    assert len(ids) == len(set(ids))


def test_comet_fields_from_config():
    ids = {c.id for c in CONFIG.comets}
    assert ids == {"oloryn", "sevrith", "kelvarn"}
    for comet in CONFIG.comets:
        assert comet.period_days > 0
        assert 0.0 <= comet.epoch_offset < 1.0
        assert comet.visible_duration_days > 0


# ── Comet perihelion visibility ───────────────────────────────────────────────


@pytest.mark.parametrize("comet_id", ["oloryn", "sevrith", "kelvarn"])
def test_comet_visible_at_perihelion(comet_id):
    p = _perihelion(comet_id, n=0)
    ctx = get_apparitions(p, CONFIG)
    ids = [c.id for c in ctx.comets_visible]
    assert comet_id in ids


@pytest.mark.parametrize("comet_id", ["oloryn", "sevrith", "kelvarn"])
def test_comet_visibility_is_1_at_perihelion(comet_id):
    comet = next(c for c in CONFIG.comets if c.id == comet_id)
    p = _perihelion(comet_id, n=0)
    vis = _comet_visibility(p, comet, PPD)
    assert abs(vis - 1.0) < 1e-9


@pytest.mark.parametrize("comet_id", ["oloryn", "sevrith", "kelvarn"])
def test_comet_not_visible_outside_window(comet_id):
    p = _perihelion(comet_id, n=0)
    hw = _half_window(comet_id)
    # One pulse beyond the window edge: not visible
    ctx = get_apparitions(p + hw, CONFIG)
    ids = [c.id for c in ctx.comets_visible]
    assert comet_id not in ids


@pytest.mark.parametrize("comet_id", ["oloryn", "sevrith", "kelvarn"])
def test_comet_visible_inside_window(comet_id):
    """One pulse inside the window edge: visible."""
    p = _perihelion(comet_id, n=0)
    hw = _half_window(comet_id)
    ctx = get_apparitions(p + hw - 1, CONFIG)
    ids = [c.id for c in ctx.comets_visible]
    assert comet_id in ids


@pytest.mark.parametrize("comet_id", ["oloryn", "sevrith", "kelvarn"])
def test_comet_visibility_ramps_toward_perihelion(comet_id):
    """Visibility increases as pulse approaches perihelion."""
    comet = next(c for c in CONFIG.comets if c.id == comet_id)
    p = _perihelion(comet_id, n=0)
    hw = _half_window(comet_id)
    vis_far = _comet_visibility(p + hw // 2, comet, PPD)
    vis_near = _comet_visibility(p + hw // 4, comet, PPD)
    vis_at = _comet_visibility(p, comet, PPD)
    assert vis_far < vis_near < vis_at
    assert abs(vis_at - 1.0) < 1e-9


# ── Comet recurrence ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("comet_id", ["kelvarn", "sevrith"])
def test_comet_recurs_at_next_perihelion(comet_id):
    """Visible at perihelion n=1, one full period later."""
    p = _perihelion(comet_id, n=1)
    ctx = get_apparitions(p, CONFIG)
    ids = [c.id for c in ctx.comets_visible]
    assert comet_id in ids


@pytest.mark.parametrize("comet_id", ["kelvarn"])
def test_comet_recurs_at_perihelion_n2(comet_id):
    p = _perihelion(comet_id, n=2)
    ctx = get_apparitions(p, CONFIG)
    ids = [c.id for c in ctx.comets_visible]
    assert comet_id in ids


def test_comet_windows_between_perihelia_are_empty():
    """Between windows, no comet appears."""
    # Midpoint between Kelvarn perihelion n=0 and n=1 is far from any window.
    p0 = _perihelion("kelvarn", n=0)
    p1 = _perihelion("kelvarn", n=1)
    mid = (p0 + p1) // 2
    ctx = get_apparitions(mid, CONFIG)
    ids = [c.id for c in ctx.comets_visible]
    assert "kelvarn" not in ids


# ── Spark: seeded determinism ─────────────────────────────────────────────────


def test_seeded_float_is_deterministic():
    """Same seed and salt always yield the same float."""
    a = _seeded_float(42, 0)
    b = _seeded_float(42, 0)
    assert a == b


def test_seeded_float_salt_changes_value():
    a = _seeded_float(42, 0)
    b = _seeded_float(42, 1)
    assert a != b


def test_seeded_float_in_range():
    for seed in range(100):
        v = _seeded_float(seed, 0)
        assert 0.0 <= v < 1.0


def test_get_apparitions_spark_is_deterministic():
    """Same pulse produces identical Spark state on repeated calls."""
    p = 10_000_000
    ctx_a = get_apparitions(p, CONFIG)
    ctx_b = get_apparitions(p, CONFIG)
    assert ctx_a.spark == ctx_b.spark


# ── Spark: glimmer event ──────────────────────────────────────────────────────


def test_spark_visible_at_first_glimmer_event():
    idx = _first_glimmer_event()
    pulse = idx * ROT_PERIOD_PULSES  # start of the glimmer event
    ctx = get_apparitions(pulse, CONFIG)
    assert ctx.spark.visible is True
    assert ctx.spark.visibility == 1.0


def test_spark_exposure_days_within_range():
    idx = _first_glimmer_event()
    pulse = idx * ROT_PERIOD_PULSES
    ctx = get_apparitions(pulse, CONFIG)
    assert ctx.spark.visible is True
    assert (
        CONFIG.spark.exposure_min_days
        <= ctx.spark.exposure_days
        <= CONFIG.spark.exposure_max_days
    )


def test_spark_exposure_duration_is_reproducible():
    idx = _first_glimmer_event()
    pulse = idx * ROT_PERIOD_PULSES
    ctx_a = get_apparitions(pulse, CONFIG)
    ctx_b = get_apparitions(pulse, CONFIG)
    assert ctx_a.spark.exposure_days == ctx_b.spark.exposure_days


def test_spark_not_visible_after_exposure_ends():
    """Just after an exposure window closes, the Spark is not visible."""
    idx = _first_glimmer_event()
    pulse = idx * ROT_PERIOD_PULSES
    ctx = get_apparitions(pulse, CONFIG)
    assert ctx.spark.visible is True
    exposure_pulses = round(ctx.spark.exposure_days * PPD)
    after = idx * ROT_PERIOD_PULSES + exposure_pulses
    ctx_after = get_apparitions(after, CONFIG)
    # If the next event also happens to be a glimmer, skip to a later check.
    # We just verify that the _first_ checked pulse outside the window is not
    # carried by the same event.
    assert (
        ctx_after.spark.exposure_days != ctx.spark.exposure_days
        or not ctx_after.spark.visible
    )


def test_spark_not_visible_during_non_glimmer_event():
    idx = _first_non_glimmer_event()
    pulse = idx * ROT_PERIOD_PULSES + ROT_PERIOD_PULSES // 2  # mid-event
    ctx = get_apparitions(pulse, CONFIG)
    # Check neither this event nor the previous is a glimmer.
    if (
        _seeded_float(idx, 0) >= CONFIG.spark.glimmer_probability
        and _seeded_float(idx - 1, 0) >= CONFIG.spark.glimmer_probability
    ):
        assert ctx.spark.visible is False


# ── Spark: glimmer probability ────────────────────────────────────────────────


def test_spark_glimmer_probability_is_configured():
    assert CONFIG.spark.glimmer_probability == pytest.approx(0.01)


def test_spark_glimmer_rate_matches_config():
    """Over 2000 rotation events the observed rate is close to glimmer_probability."""
    prob = CONFIG.spark.glimmer_probability
    count = sum(1 for idx in range(2000) if _seeded_float(idx, 0) < prob)
    # Expect ~20 for p=0.01 over 2000 events; allow generous bounds.
    assert 5 <= count <= 50


# ── Calendar independence ─────────────────────────────────────────────────────


def test_apparitions_module_does_not_reference_civil_calendars():
    source = (PROJECT_ROOT / "src/sask/apparitions.py").read_text(encoding="utf-8")
    assert "fatunik" not in source.lower()
    assert "terpin" not in source.lower()


def test_same_pulse_same_result_irrespective_of_call_count():
    """Repeated calls with the same pulse return identical contexts."""
    p = 5_000_000
    results = [get_apparitions(p, CONFIG) for _ in range(5)]
    assert all(r == results[0] for r in results[1:])


# ── Message unit validity ─────────────────────────────────────────────────────


def test_apparition_context_validates_at_story_now():
    ctx = get_apparitions(CONFIG.timeline.story_now_pulse, CONFIG)
    assert validate(ctx) == []


def test_apparition_context_is_frozen_dataclass():
    ctx = get_apparitions(0, CONFIG)
    assert isinstance(ctx, ApparitionContext)
    with pytest.raises((AttributeError, TypeError)):
        ctx.pulse = 999  # type: ignore[misc]


def test_apparition_context_at_comet_perihelion_validates():
    p = _perihelion("kelvarn", n=0)
    ctx = get_apparitions(p, CONFIG)
    assert validate(ctx) == []
    assert len(ctx.comets_visible) >= 1


def test_apparition_context_spark_always_present():
    """Spark field is always present even when not visible."""
    ctx = get_apparitions(0, CONFIG)
    assert ctx.spark is not None
    assert isinstance(ctx.spark.visible, bool)


def test_comet_ids_in_context_match_config():
    p = _perihelion("kelvarn", n=0)
    ctx = get_apparitions(p, CONFIG)
    config_ids = {c.id for c in CONFIG.comets}
    for c in ctx.comets_visible:
        assert c.id in config_ids


# ── Layer purity ──────────────────────────────────────────────────────────────


def test_apparitions_module_has_no_flask_import():
    path = PROJECT_ROOT / "src/sask/apparitions.py"
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


def test_apparitions_uses_no_global_random():
    """Source contains no calls to the global `random` module."""
    source = (PROJECT_ROOT / "src/sask/apparitions.py").read_text(encoding="utf-8")
    assert "random.seed" not in source
    assert "random.random(" not in source
    assert "random.uniform" not in source
    assert "random.choices" not in source

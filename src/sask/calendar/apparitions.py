"""Recurring comets and the Kanka-hosted Spark (SPEC-011).

get_apparitions(pulse, config) is a pure function of pulse and config:
  1. For each comet in config.comets, compute visibility from the perihelion
     formula: perihelion_n = (n + epoch_offset) * period_in_pulses.
     Visibility ramps linearly from 1.0 at perihelion to 0.0 at the window edge.
  2. For the Spark, derive visibility from Kanka's deterministic spin:
     - Kanka's rotation events are spaced by rotation_period_days (38 days).
     - Each event: _seeded_float(event_idx, 0) < glimmer_probability → glimmer.
     - If a glimmer: exposure duration = seeded draw in [min, max] days.
     - No global or live RNG; fully reproducible from pulse and config alone.
"""

from __future__ import annotations

import hashlib
import math
import struct

from sask.config_loader import AppConfig, CometConfig, SparkConfig
from sask.message import ApparitionContext, CometInfo, SparkInfo


def _seeded_float(seed: int, salt: int = 0) -> float:
    """Deterministic float in [0.0, 1.0) from integer seed and salt (sha256)."""
    data = struct.pack(">qq", seed, salt)
    digest = hashlib.sha256(data).digest()
    val = struct.unpack(">Q", digest[:8])[0]
    return val / (2**64)


def _comet_visibility(pulse: int, comet: CometConfig, ppd: int) -> float:
    """Return comet visibility in [0.0, 1.0]; 0.0 means not visible.

    Linear ramp: 1.0 at perihelion, 0.0 at the half-window edge.
    """
    period_pulses = comet.period_days * ppd
    half_window = (comet.visible_duration_days / 2) * ppd
    n_float = pulse / period_pulses - comet.epoch_offset
    best_vis = 0.0
    for n in [math.floor(n_float), math.ceil(n_float)]:
        perihelion = (n + comet.epoch_offset) * period_pulses
        dist = abs(pulse - perihelion)
        if dist < half_window:
            vis = 1.0 - dist / half_window
            best_vis = max(best_vis, vis)
    return best_vis


def _kanka_rotation_pulses(spark_cfg: SparkConfig, config: AppConfig) -> int:
    """Return Kanka's rotation period in pulses from body config."""
    ppd = config.time_constants.pulses_per_day
    for body in config.bodies:
        if body.name.lower() == spark_cfg.host_moon.lower():
            if body.rotation_period_days is not None:
                return round(body.rotation_period_days * ppd)
    raise ValueError(
        f"spark host_moon {spark_cfg.host_moon!r} not found or has no rotation_period_days"
    )


def _spark_state(
    pulse: int, spark_cfg: SparkConfig, rot_period_pulses: int, ppd: int
) -> SparkInfo:
    """Derive Spark visibility from Kanka's deterministic spin.

    Checks the current and previous rotation event in case an exposure window
    started in the previous event and extends into the current one.
    """
    for delta in [0, -1]:
        event_idx = pulse // rot_period_pulses + delta
        if event_idx < 0:
            continue
        event_start = event_idx * rot_period_pulses
        if _seeded_float(event_idx, 0) >= spark_cfg.glimmer_probability:
            continue
        dur_range = spark_cfg.exposure_max_days - spark_cfg.exposure_min_days
        exposure_days = (
            spark_cfg.exposure_min_days + _seeded_float(event_idx, 1) * dur_range
        )
        exposure_pulses = round(exposure_days * ppd)
        if event_start <= pulse < event_start + exposure_pulses:
            return SparkInfo(
                visible=True,
                visibility=1.0,
                exposure_days=exposure_days,
                lore=spark_cfg.lore,
            )
    return SparkInfo(
        visible=False, visibility=0.0, exposure_days=0.0, lore=spark_cfg.lore
    )


def get_apparitions(pulse: int, config: AppConfig) -> ApparitionContext:
    """Return apparition context for the given pulse."""
    ppd = config.time_constants.pulses_per_day
    comets_visible = []
    for comet in config.comets:
        vis = _comet_visibility(pulse, comet, ppd)
        if vis > 0.0:
            comets_visible.append(
                CometInfo(
                    id=comet.id,
                    name=comet.name,
                    visibility=vis,
                    color=comet.color,
                    tail=comet.tail,
                    lore=comet.lore,
                )
            )
    rot_pulses = _kanka_rotation_pulses(config.spark, config)
    spark = _spark_state(pulse, config.spark, rot_pulses, ppd)
    return ApparitionContext(
        pulse=pulse,
        comets_visible=tuple(comets_visible),
        spark=spark,
    )

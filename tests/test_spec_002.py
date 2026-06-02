"""SPEC-002 tests — configuration and pulse/day core.

Covers:
  - astro_day() signed arithmetic (positive, zero, negative pulses)
  - day_pulse_offset() range and negative-pulse behaviour
  - orbital_position() stays in [0.0, 1.0)
  - civil_day() day_start_offset shifts day boundaries
  - pulse_info() message-unit constructor
  - validate() message-unit field checker
  - load_config() loads real config without error
  - load_config() raises ConfigError for malformed/missing inputs
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sask.config_loader import ConfigError, load_config
from sask.message import CalendarDate, PulseInfo, validate
from sask.pulse import (
    astro_day,
    civil_day,
    day_pulse_offset,
    orbital_position,
    pulse_info,
)

REAL_CONFIG = Path(__file__).parent.parent / "config"
PULSES_PER_DAY = 86_400
ASTRO_YEAR_PULSES = 31_556_926.08


# ── astro_day ─────────────────────────────────────────────────────────────────


def test_astro_day_start_of_day_1():
    assert astro_day(0) == 1


def test_astro_day_end_of_day_1():
    assert astro_day(PULSES_PER_DAY - 1) == 1


def test_astro_day_start_of_day_2():
    assert astro_day(PULSES_PER_DAY) == 2


def test_astro_day_arbitrary_positive():
    assert astro_day(PULSES_PER_DAY * 10) == 11


def test_astro_day_minus_one_is_day_zero():
    # -1 // 86400 = -1 (Python floor div); -1 + 1 = 0
    assert astro_day(-1) == 0


def test_astro_day_minus_full_day_is_day_zero():
    # -86400 // 86400 = -1; -1 + 1 = 0
    assert astro_day(-PULSES_PER_DAY) == 0


def test_astro_day_one_past_minus_full_day_is_day_negative_one():
    # -86401 // 86400 = -2; -2 + 1 = -1
    assert astro_day(-PULSES_PER_DAY - 1) == -1


def test_astro_day_two_full_negative_days():
    # -2 * 86400 // 86400 = -2; -2 + 1 = -1
    assert astro_day(-2 * PULSES_PER_DAY) == -1


# ── day_pulse_offset ──────────────────────────────────────────────────────────


def test_day_pulse_offset_zero():
    assert day_pulse_offset(0) == 0


def test_day_pulse_offset_end_of_day():
    assert day_pulse_offset(PULSES_PER_DAY - 1) == PULSES_PER_DAY - 1


def test_day_pulse_offset_start_of_second_day():
    assert day_pulse_offset(PULSES_PER_DAY) == 0


def test_day_pulse_offset_negative_one():
    # Python: -1 % 86400 = 86399
    assert day_pulse_offset(-1) == PULSES_PER_DAY - 1


def test_day_pulse_offset_negative_full_day():
    assert day_pulse_offset(-PULSES_PER_DAY) == 0


# ── orbital_position ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "pulse",
    [
        0,
        1,
        PULSES_PER_DAY,
        PULSES_PER_DAY * 365,
        -1,
        -PULSES_PER_DAY,
        int(ASTRO_YEAR_PULSES * 253),
        int(ASTRO_YEAR_PULSES * 1000),
    ],
)
def test_orbital_position_in_range(pulse):
    pos = orbital_position(pulse, ASTRO_YEAR_PULSES)
    assert 0.0 <= pos < 1.0, f"pulse={pulse} gave orbital_position={pos}"


def test_orbital_position_at_epoch_is_zero():
    assert orbital_position(0, ASTRO_YEAR_PULSES) == 0.0


def test_orbital_position_summer_solstice():
    # Summer solstice ≈ 0.25 (quarter AstroYear from spring equinox).
    solstice_pulse = ASTRO_YEAR_PULSES * 0.25
    pos = orbital_position(solstice_pulse, ASTRO_YEAR_PULSES)
    assert abs(pos - 0.25) < 1e-9


# ── civil_day (day_start_offset) ─────────────────────────────────────────────


SUNRISE_OFFSET = 21_600  # Fatunik: 6 hours after midnight


def test_civil_day_no_offset_matches_astro_day():
    for pulse in [0, PULSES_PER_DAY, -1, -PULSES_PER_DAY]:
        assert civil_day(pulse, day_start_offset=0) == astro_day(pulse)


def test_civil_day_pre_sunrise_is_day_zero():
    # Pulses 0 to SUNRISE_OFFSET-1 belong to Fatunik civil day 0 (before Day 1).
    assert civil_day(0, SUNRISE_OFFSET) == 0
    assert civil_day(SUNRISE_OFFSET - 1, SUNRISE_OFFSET) == 0


def test_civil_day_at_sunrise_is_day_one():
    assert civil_day(SUNRISE_OFFSET, SUNRISE_OFFSET) == 1


def test_civil_day_last_day_pulse_offset_one():
    assert civil_day(SUNRISE_OFFSET + PULSES_PER_DAY - 1, SUNRISE_OFFSET) == 1


def test_civil_day_start_of_day_two():
    assert civil_day(SUNRISE_OFFSET + PULSES_PER_DAY, SUNRISE_OFFSET) == 2


# ── pulse_info message unit ───────────────────────────────────────────────────


@pytest.fixture(scope="module")
def cfg():
    return load_config(REAL_CONFIG)


def test_pulse_info_day_1(cfg):
    info = pulse_info(0, cfg)
    assert isinstance(info, PulseInfo)
    assert info.pulse == 0
    assert info.astro_day == 1
    assert info.day_pulse_offset == 0
    assert info.orbital_position == 0.0


def test_pulse_info_day_2(cfg):
    info = pulse_info(PULSES_PER_DAY, cfg)
    assert info.astro_day == 2
    assert info.day_pulse_offset == 0


def test_pulse_info_negative_pulse(cfg):
    info = pulse_info(-1, cfg)
    assert info.astro_day == 0
    assert info.day_pulse_offset == PULSES_PER_DAY - 1


# ── validate helper ───────────────────────────────────────────────────────────


def test_validate_passes_complete_pulse_info():
    unit = PulseInfo(pulse=0, astro_day=1, day_pulse_offset=0, orbital_position=0.0)
    assert validate(unit) == []


def test_validate_catches_none_field():
    unit = CalendarDate(calendar_id=None, year=1, month=1, day=1)  # type: ignore[arg-type]
    errors = validate(unit)
    assert any("calendar_id" in e for e in errors)


# ── load_config: integration against real config/ ────────────────────────────


def test_load_config_succeeds(cfg):
    # Smoke: AppConfig loaded without error.
    assert cfg is not None


def test_time_constants(cfg):
    assert cfg.time_constants.pulses_per_day == 86_400
    assert cfg.time_constants.astro_year_pulses == pytest.approx(31_556_926.08)


def test_calendar_epoch_days(cfg):
    assert cfg.astro.epoch_astro_day == 1
    assert cfg.terpin.epoch_astro_day == 1
    assert cfg.fatunik.epoch_astro_day == 92_498


def test_fatunik_day_start_offset(cfg):
    assert cfg.fatunik.day_start_offset == 21_600


def test_terpin_day_start_offset(cfg):
    assert cfg.terpin.day_start_offset == 0


def test_seasons_count_and_order(cfg):
    s = cfg.seasons.seasons
    assert len(s) == 4
    assert s[0].id == "greening"
    assert s[0].orbital_start == 0.0
    assert s[1].orbital_start == 0.25
    assert s[2].orbital_start == 0.5
    assert s[3].orbital_start == 0.75


def test_timeline_story_now(cfg):
    assert cfg.timeline.story_now_pulse == 71_642_553_600


# ── load_config: ConfigError on malformed/missing input ──────────────────────


def _write_toml(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _minimal_config_dir(tmp_path: Path) -> Path:
    """Copy all real config files into tmp_path, returning tmp_path."""
    import shutil

    for f in REAL_CONFIG.glob("*.toml"):
        shutil.copy(f, tmp_path / f.name)
    return tmp_path


def test_missing_config_file_raises(tmp_path):
    d = _minimal_config_dir(tmp_path)
    (d / "time_constants.toml").unlink()
    with pytest.raises(ConfigError, match="not found"):
        load_config(d)


def test_bad_toml_raises(tmp_path):
    d = _minimal_config_dir(tmp_path)
    _write_toml(d / "time_constants.toml", "this = [broken}")
    with pytest.raises(ConfigError, match="parse error"):
        load_config(d)


def test_missing_pulses_per_day_raises(tmp_path):
    d = _minimal_config_dir(tmp_path)
    _write_toml(d / "time_constants.toml", "astro_year_pulses = 31556926.08\n")
    with pytest.raises(ConfigError, match="pulses_per_day"):
        load_config(d)


def test_missing_astro_year_pulses_raises(tmp_path):
    d = _minimal_config_dir(tmp_path)
    _write_toml(d / "time_constants.toml", "pulses_per_day = 86400\n")
    with pytest.raises(ConfigError, match="astro_year_pulses"):
        load_config(d)


def test_non_integer_pulses_per_day_raises(tmp_path):
    d = _minimal_config_dir(tmp_path)
    bad = 'pulses_per_day = "bad"\nastro_year_pulses = 31556926.08\n'
    _write_toml(d / "time_constants.toml", bad)
    with pytest.raises(ConfigError, match="pulses_per_day"):
        load_config(d)


def test_missing_epoch_astro_day_raises(tmp_path):
    d = _minimal_config_dir(tmp_path)
    # Write a calendars.toml with epoch_astro_day removed from [fatunik].
    broken = (
        "[astro]\nid = 'astro'\nepoch_astro_day = 1\nday_start_offset = 0\n"
        "[fatunik]\nid = 'fatunik'\nday_start_offset = 21600\n"  # epoch_astro_day missing
        "[fatunik.months]\nfestival_name='Gleaming'\nfestival_days_standard=5\n"
        "festival_days_leap=6\nregular_month_days=30\nregular_month_count=12\n"
        "[fatunik.leap]\ncycle_short=4\ncycle_skip=100\ncycle_restore=400\n"
        "[terpin]\nid='terpin'\nepoch_astro_day=1\nday_start_offset=0\n"
        "[terpin.months]\nfestival_name='festival'\nfestival_days_standard=5\n"
        "festival_days_long=37\nfestival_days_super_long=36\n"
        "regular_month_days=30\nregular_month_count=12\n"
        "[terpin.leap]\nlong_year_cycle=132\nsuper_long_year_cycle=4620\n"
    )
    _write_toml(d / "calendars.toml", broken)
    with pytest.raises(ConfigError, match="epoch_astro_day"):
        load_config(d)

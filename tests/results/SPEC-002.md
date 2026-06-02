# Test results: SPEC-002

**Date:** 2026-06-02
**Status:** PASS

```text
$ .venv/bin/pytest -v tests/test_spec_002.py
============================= test session starts ==============================
platform linux -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0 -- /home/dave/Code/sask-calendar/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /home/dave/Code/sask-calendar
configfile: pyproject.toml
collecting ... collected 46 items

tests/test_spec_002.py::test_astro_day_start_of_day_1 PASSED             [  2%]
tests/test_spec_002.py::test_astro_day_end_of_day_1 PASSED               [  4%]
tests/test_spec_002.py::test_astro_day_start_of_day_2 PASSED             [  6%]
tests/test_spec_002.py::test_astro_day_arbitrary_positive PASSED         [  8%]
tests/test_spec_002.py::test_astro_day_minus_one_is_day_zero PASSED      [ 10%]
tests/test_spec_002.py::test_astro_day_minus_full_day_is_day_zero PASSED [ 13%]
tests/test_spec_002.py::test_astro_day_one_past_minus_full_day_is_day_negative_one PASSED [ 15%]
tests/test_spec_002.py::test_astro_day_two_full_negative_days PASSED     [ 17%]
tests/test_spec_002.py::test_pulse_of_day_zero PASSED                    [ 19%]
tests/test_spec_002.py::test_pulse_of_day_end_of_day PASSED              [ 21%]
tests/test_spec_002.py::test_pulse_of_day_start_of_second_day PASSED     [ 23%]
tests/test_spec_002.py::test_pulse_of_day_negative_one PASSED            [ 26%]
tests/test_spec_002.py::test_pulse_of_day_negative_full_day PASSED       [ 28%]
tests/test_spec_002.py::test_orbital_position_in_range[0] PASSED         [ 30%]
tests/test_spec_002.py::test_orbital_position_in_range[1] PASSED         [ 32%]
tests/test_spec_002.py::test_orbital_position_in_range[86400] PASSED     [ 34%]
tests/test_spec_002.py::test_orbital_position_in_range[31536000] PASSED  [ 36%]
tests/test_spec_002.py::test_orbital_position_in_range[-1] PASSED        [ 39%]
tests/test_spec_002.py::test_orbital_position_in_range[-86400] PASSED    [ 41%]
tests/test_spec_002.py::test_orbital_position_in_range[7983902298] PASSED [ 43%]
tests/test_spec_002.py::test_orbital_position_in_range[31556926080] PASSED [ 45%]
tests/test_spec_002.py::test_orbital_position_at_epoch_is_zero PASSED    [ 47%]
tests/test_spec_002.py::test_orbital_position_summer_solstice PASSED     [ 50%]
tests/test_spec_002.py::test_civil_day_no_offset_matches_astro_day PASSED [ 52%]
tests/test_spec_002.py::test_civil_day_pre_sunrise_is_day_zero PASSED    [ 54%]
tests/test_spec_002.py::test_civil_day_at_sunrise_is_day_one PASSED      [ 56%]
tests/test_spec_002.py::test_civil_day_last_pulse_of_day_one PASSED      [ 58%]
tests/test_spec_002.py::test_civil_day_start_of_day_two PASSED           [ 60%]
tests/test_spec_002.py::test_pulse_info_day_1 PASSED                     [ 63%]
tests/test_spec_002.py::test_pulse_info_day_2 PASSED                     [ 65%]
tests/test_spec_002.py::test_pulse_info_negative_pulse PASSED            [ 67%]
tests/test_spec_002.py::test_validate_passes_complete_pulse_info PASSED  [ 69%]
tests/test_spec_002.py::test_validate_catches_none_field PASSED          [ 71%]
tests/test_spec_002.py::test_load_config_succeeds PASSED                 [ 73%]
tests/test_spec_002.py::test_time_constants PASSED                       [ 76%]
tests/test_spec_002.py::test_calendar_epoch_days PASSED                  [ 78%]
tests/test_spec_002.py::test_fatunik_day_start_offset PASSED             [ 80%]
tests/test_spec_002.py::test_terpin_day_start_offset PASSED              [ 82%]
tests/test_spec_002.py::test_seasons_count_and_order PASSED              [ 84%]
tests/test_spec_002.py::test_timeline_story_now PASSED                   [ 86%]
tests/test_spec_002.py::test_missing_config_file_raises PASSED           [ 89%]
tests/test_spec_002.py::test_bad_toml_raises PASSED                      [ 91%]
tests/test_spec_002.py::test_missing_pulses_per_day_raises PASSED        [ 93%]
tests/test_spec_002.py::test_missing_astro_year_pulses_raises PASSED     [ 95%]
tests/test_spec_002.py::test_non_integer_pulses_per_day_raises PASSED    [ 97%]
tests/test_spec_002.py::test_missing_epoch_astro_day_raises PASSED       [100%]

============================== 46 passed in 0.09s ==============================
```

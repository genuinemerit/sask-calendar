# Test results: SPEC-005

**Date:** 2026-06-02
**Status:** PASS

```text
$ .venv/bin/pytest -v tests/test_spec_005.py
============================= test session starts ==============================
platform linux -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0 -- /home/dave/Code/sask-calendar/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /home/dave/Code/sask-calendar
configfile: pyproject.toml
collecting ... collected 12 items

tests/test_spec_005.py::test_get_root_returns_200 PASSED                 [  8%]
tests/test_spec_005.py::test_default_pulse_prefilled PASSED              [ 16%]
tests/test_spec_005.py::test_no_script_tags PASSED                       [ 25%]
tests/test_spec_005.py::test_query_with_integer_pulse PASSED             [ 33%]
tests/test_spec_005.py::test_query_shows_astro_day PASSED                [ 41%]
tests/test_spec_005.py::test_float_pulse_rounded_to_int PASSED           [ 50%]
tests/test_spec_005.py::test_invalid_pulse_returns_200_with_error PASSED [ 58%]
tests/test_spec_005.py::test_day_pulse_offset_shown PASSED               [ 66%]
tests/test_spec_005.py::test_orbital_position_shown PASSED               [ 75%]
tests/test_spec_005.py::test_engine_module_has_no_flask_import[src/sask/pulse.py] PASSED [ 83%]
tests/test_spec_005.py::test_engine_module_has_no_flask_import[src/sask/message.py] PASSED [ 91%]
tests/test_spec_005.py::test_engine_module_has_no_flask_import[src/sask/config_loader.py] PASSED [100%]

============================== 12 passed in 0.13s ==============================
```

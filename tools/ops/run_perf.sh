#!/usr/bin/env bash
# Run the SPEC-018 Layer 1 engine benchmarks and save a baseline.
#
# Layer 2 (HTTP timings against a live gunicorn) is a separate manual step,
# since it needs a server running in another terminal:
#
#   PYTHONPATH=src poetry run gunicorn wsgi:app -w 1 -b 127.0.0.1:8000
#   PYTHONPATH=src poetry run python3 tools/ops/perf_http.py
#
# Usage:
#   bash tools/ops/run_perf.sh

set -euo pipefail

cd "$(dirname "$0")/../.."

poetry run pytest tests/perf/ \
    --benchmark-storage=file://./tests/results/perf/benchmarks \
    --benchmark-autosave \
    -v

printf '\nLayer 1 benchmarks saved under tests/results/perf/benchmarks/\n'
printf '\nFor Layer 2 (HTTP timings), in a separate terminal:\n'
printf '  PYTHONPATH=src poetry run gunicorn wsgi:app -w 1 -b 127.0.0.1:8000\n'
printf 'then:\n'
printf '  PYTHONPATH=src poetry run python3 tools/ops/perf_http.py\n'

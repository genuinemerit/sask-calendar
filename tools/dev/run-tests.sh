#!/usr/bin/env bash
# Run unit tests with configurable scope, verbosity, and result saving.
#
# Usage:
#   run-tests.sh                           — all tests, quiet
#   run-tests.sh -v                        — all tests, verbose
#   run-tests.sh --spec SPEC-002           — one spec, quiet
#   run-tests.sh --spec SPEC-002 -v --save — one spec, verbose, save results

set -uo pipefail

cd "$(dirname "$0")/../.." || exit 1

SPEC=""
VERBOSE=0
SAVE=0

usage() {
    cat <<'EOF'
Usage: run-tests.sh [OPTIONS]

  --spec SPEC-ID   Run only the tests for one spec (e.g. SPEC-002)
  -v, --verbose    Verbose pytest output
  --save           Save results to tests/results/<SPEC-ID>.md (requires --spec)
  -h, --help       Show this help and exit
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --spec)
            [[ $# -gt 1 ]] || { printf 'Error: --spec requires an argument\n' >&2; exit 1; }
            shift
            SPEC="$1"
            ;;
        -v|--verbose)
            VERBOSE=1
            ;;
        --save)
            SAVE=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf 'Error: unknown option: %s\n' "$1" >&2
            usage >&2
            exit 1
            ;;
    esac
    shift
done

if [[ $SAVE -eq 1 && -z "$SPEC" ]]; then
    printf 'Error: --save requires --spec\n' >&2
    exit 1
fi

# ── Build pytest argument list ────────────────────────────────────────────────

pytest_args=()
if [[ $VERBOSE -eq 1 ]]; then
    pytest_args+=("-v")
else
    pytest_args+=("-q")
fi

if [[ -n "$SPEC" ]]; then
    # SPEC-002 → tests/test_spec_002.py
    spec_slug="${SPEC//-/_}"
    spec_slug="${spec_slug,,}"
    test_file="tests/test_${spec_slug}.py"
    if [[ ! -f "$test_file" ]]; then
        printf 'Error: test file not found: %s\n' "$test_file" >&2
        exit 1
    fi
    pytest_args+=("$test_file")
else
    pytest_args+=("tests/")
fi

# ── Run ───────────────────────────────────────────────────────────────────────

if [[ $SAVE -eq 1 ]]; then
    results_file="tests/results/${SPEC}.md"
    mkdir -p tests/results

    # Capture output while still printing it to the terminal.
    tmp=$(mktemp)
    poetry run pytest "${pytest_args[@]}" 2>&1 | tee "$tmp"
    pytest_exit=${PIPESTATUS[0]}

    [[ $pytest_exit -eq 0 ]] && status_line="PASS" || status_line="FAIL"

    {
        printf '# Test results: %s\n\n' "$SPEC"
        printf '**Date:** %s\n' "$(date +%Y-%m-%d)"
        printf '**Status:** %s\n\n' "$status_line"
        printf '```text\n'
        printf '$ poetry run pytest %s\n' "${pytest_args[*]}"
        cat "$tmp"
        printf '```\n'
    } > "$results_file"

    rm "$tmp"
    printf '\nResults saved to %s\n' "$results_file"
else
    poetry run pytest "${pytest_args[@]}"
    pytest_exit=$?
fi

exit "$pytest_exit"

#!/usr/bin/env bash
# tools/dev/verify-clean-env.sh — clean-environment verification (SPEC-031 centerpiece).
#
# Checks, in order:
#   1. pyenv present and Python 3.12.x pinned via .python-version
#   2. Native-linked stdlib modules import (sqlite3, ssl, hashlib — the
#      libsqlite3/libssl watch-items called out in SPEC-031)
#   3. `poetry install` succeeds against the pinned 3.12 interpreter
#   4. The full test suite passes (count is printed for the devlog record,
#      not hard-asserted — a fixed expected number would go stale on every
#      legitimate test addition unrelated to this port)
#   5. The app boots locally and GET /health returns 200 with the expected body
#
# This script verifies; it does not install system packages. It is meant to
# run AFTER tools/dev/init-dev-host.sh on a host with no prior sask setup — if
# step 1 or 2 fails, that failure identifies a gap in init-dev-host.sh's
# package list, not something for this script to patch around.
#
# Read-only with respect to DigitalOcean / production — no network calls
# outside localhost. Like verify-do-secrets.sh, does NOT fail fast: every
# check runs so a single report shows the full picture.
#
# Usage:
#   bash tools/dev/verify-clean-env.sh

set -uo pipefail

PYTHON_MINOR="3.12"
HEALTH_PORT=5055
HEALTH_PATH="/health"

PASS_COUNT=0
FAIL_COUNT=0

ok()   { printf '[PASS] %s\n' "$*"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { printf '[FAIL] %s\n' "$*" >&2; FAIL_COUNT=$((FAIL_COUNT + 1)); }

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT" || exit 1

# Make a pyenv/poetry install reachable even in a non-interactive shell that
# hasn't sourced ~/.bashrc yet (same defensive PATH handling as init-dev-host.sh).
PYENV_ROOT="${PYENV_ROOT:-$HOME/.pyenv}"
if [[ -x "$PYENV_ROOT/bin/pyenv" ]]; then
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)"
fi
export PATH="$HOME/.local/bin:$PATH"

SERVER_PID=""
cleanup() {
    if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" &>/dev/null; then
        kill "$SERVER_PID" &>/dev/null
        wait "$SERVER_PID" 2>/dev/null
    fi
}
trap cleanup EXIT

# ── 1. pyenv + pinned Python 3.12.x ─────────────────────────────────────────
printf '\n[CHECK] pyenv present and Python %s.x pinned\n' "$PYTHON_MINOR"
if ! command -v pyenv &>/dev/null; then
    fail "pyenv not found on PATH — run tools/dev/init-dev-host.sh first"
elif [[ ! -f "$REPO_ROOT/.python-version" ]]; then
    fail "$REPO_ROOT/.python-version not found — run 'pyenv local 3.12.x' (or init-dev-host.sh)"
else
    PINNED="$(cat "$REPO_ROOT/.python-version")"
    if [[ "$PINNED" != "${PYTHON_MINOR}."* ]]; then
        fail ".python-version pins '$PINNED', expected ${PYTHON_MINOR}.x"
    else
        RESOLVED="$(python --version 2>&1)"
        if [[ "$RESOLVED" != "Python $PINNED" ]]; then
            fail "python resolves to '$RESOLVED' in $REPO_ROOT, expected 'Python $PINNED'"
        else
            ok "python resolves to $PINNED via pyenv pin"
        fi
    fi
fi

# ── 2. Native-linked stdlib watch-items ─────────────────────────────────────
printf '\n[CHECK] native-linked stdlib modules (sqlite3, ssl, hashlib)\n'
if python -c 'import sqlite3, ssl, hashlib' &>/dev/null; then
    ok "sqlite3, ssl, hashlib import cleanly (libsqlite3/libssl present)"
else
    fail "sqlite3/ssl/hashlib import failed — likely missing libsqlite3-dev/libssl-dev at Python build time"
fi

# ── 3. poetry install ────────────────────────────────────────────────────────
printf '\n[CHECK] poetry install\n'
if ! command -v poetry &>/dev/null; then
    fail "poetry not found on PATH — run tools/dev/init-dev-host.sh first"
elif poetry install; then
    ok "poetry install succeeded"
else
    fail "poetry install failed"
fi

# ── 4. Full test suite ───────────────────────────────────────────────────────
printf '\n[CHECK] full test suite\n'
PYTEST_OUTPUT="$(poetry run pytest -q 2>&1)"
PYTEST_STATUS=$?
SUMMARY_LINE="$(printf '%s\n' "$PYTEST_OUTPUT" | tail -1)"
if [[ "$PYTEST_STATUS" -eq 0 ]]; then
    ok "test suite passed — $SUMMARY_LINE"
else
    fail "test suite failed — $SUMMARY_LINE"
fi

# ── 5. App boot + /health route ─────────────────────────────────────────────
printf '\n[CHECK] app boots and serves %s\n' "$HEALTH_PATH"
PYTHONPATH="$REPO_ROOT/src" poetry run flask --app sask.web run --port "$HEALTH_PORT" \
    >/tmp/sask-verify-clean-env-flask.log 2>&1 &
SERVER_PID=$!

HEALTH_URL="http://127.0.0.1:${HEALTH_PORT}${HEALTH_PATH}"
BODY=""
HTTP_CODE="000"
for _ in $(seq 1 15); do
    if BODY="$(curl -s -o - -w '\n%{http_code}' "$HEALTH_URL" 2>/dev/null)"; then
        HTTP_CODE="$(printf '%s' "$BODY" | tail -1)"
        [[ "$HTTP_CODE" == "200" ]] && break
    fi
    sleep 1
done

if [[ "$HTTP_CODE" != "200" ]]; then
    fail "GET $HEALTH_URL did not return 200 (got '$HTTP_CODE') — see /tmp/sask-verify-clean-env-flask.log"
elif ! printf '%s' "$BODY" | head -1 | grep -q '"status": *"ok"'; then
    fail "GET $HEALTH_URL returned 200 but unexpected body: $(printf '%s' "$BODY" | head -1)"
else
    ok "GET $HEALTH_URL returned 200 with expected body"
fi

cleanup
SERVER_PID=""

# ── Summary ──────────────────────────────────────────────────────────────────
printf '\n── Summary ──────────────────────────────────────────────\n'
printf '  Pass: %d\n' "$PASS_COUNT"
printf '  Fail: %d\n' "$FAIL_COUNT"
if [[ "$FAIL_COUNT" -gt 0 ]]; then
    printf '\n[RESULT] FAIL — %d check(s) failed.\n' "$FAIL_COUNT" >&2
    exit 1
fi
printf '\n[RESULT] PASS — clean-environment verification succeeded.\n'

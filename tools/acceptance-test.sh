#!/usr/bin/env bash
# Layer 2 (SPEC-024): curl-based smoke test against the live HTTPS
# endpoint. Fast, human-readable, exits non-zero on first failure.
#
#   bash tools/acceptance-test.sh
#   SASK_BASE_URL=https://other.example bash tools/acceptance-test.sh

set -euo pipefail

BASE_URL="${SASK_BASE_URL:-https://sask.davidstitt.net}"
EXPECTED_PULSE="104548096103"

pass() { printf '[PASS]  %s\n' "$1"; }
fail() {
    printf '[FAIL]  %s\n' "$1" >&2
    exit 1
}

# A single request proves both TLS validity (curl fails without -k on a
# bad cert) and /health's status in one round-trip.
if ! response="$(curl -sS -w '\n%{http_code}' "$BASE_URL/health")"; then
    fail "TLS validation or connection failed for $BASE_URL/health"
fi
pass "TLS validates without -k"

code="$(tail -n1 <<<"$response")"
if [[ "$code" == "200" ]]; then
    pass "/health returns 200"
else
    fail "/health returned $code"
fi

body="$(curl -sS "$BASE_URL/")"
if [[ "$body" == *"$EXPECTED_PULSE"* ]]; then
    pass "root page contains the expected computed value ($EXPECTED_PULSE)"
else
    fail "root page did not contain the expected computed value ($EXPECTED_PULSE)"
fi

# SPEC-027: a known asset_catalog_data.toml entry resolves end to end
# (DNS -> TLS -> Caddy -> gunicorn -> Flask -> asset engine -> bytes).
ASSET_URL="$BASE_URL/asset/image/splash.bg"
EXPECTED_ASSET_CONTENT_TYPE="image/webp"

dummy_body=$(mktemp)
if ! code="$(curl -sS -o "$dummy_body" -w '%{http_code}' "$ASSET_URL")"; then
    rm -f "$dummy_body"
    fail "Request failed for $ASSET_URL"
fi
rm -f "$dummy_body"
if [[ "$code" == "200" ]]; then
    pass "$ASSET_URL returns 200"
else
    fail "$ASSET_URL returned $code"
fi

content_type="$(curl -sS -D - -o /dev/null "$ASSET_URL" | grep -i '^content-type:' | tr -d '\r' | awk '{print $2}')"
if [[ "$content_type" == "$EXPECTED_ASSET_CONTENT_TYPE" ]]; then
    pass "$ASSET_URL Content-Type is $EXPECTED_ASSET_CONTENT_TYPE"
else
    fail "$ASSET_URL Content-Type was '$content_type', expected $EXPECTED_ASSET_CONTENT_TYPE"
fi

printf '\n[ALL PASS] Acceptance suite complete.\n'

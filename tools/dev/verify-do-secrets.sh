#!/usr/bin/env bash
# tools/dev/verify-do-secrets.sh — verify DigitalOcean host secrets, read-only.
#
# Checks, in order:
#   1. ~/.config/sask/infra.env exists and DIGITALOCEAN_TOKEN is set
#   2. The token is accepted by the DigitalOcean API (GET /v2/account)
#   3. ~/.ssh/sask_ed25519 exists with private-key-safe permissions (600)
#   4. An SSH probe to the sask-droplet alias succeeds
#
# Read-only throughout — no DigitalOcean resource and no droplet state is
# created, changed, or destroyed. Unlike pre-commit-check.sh this script does
# NOT fail fast: every check runs so a single report shows the full picture,
# and the exit code reflects whether any check failed.
#
# Usage:
#   bash tools/dev/verify-do-secrets.sh

set -uo pipefail

# ── Config (paths/identifiers this script checks) ──────────────────────────
DO_API="https://api.digitalocean.com/v2"
INFRA_ENV="$HOME/.config/sask/infra.env"
SASK_KEY="$HOME/.ssh/sask_ed25519"
SSH_ALIAS="sask-droplet"

PASS_COUNT=0
FAIL_COUNT=0

ok()   { printf '[PASS] %s\n' "$*"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { printf '[FAIL] %s\n' "$*" >&2; FAIL_COUNT=$((FAIL_COUNT + 1)); }

# ── 1. infra.env / DIGITALOCEAN_TOKEN ───────────────────────────────────────
printf '\n[CHECK] infra.env and DIGITALOCEAN_TOKEN\n'
if [[ ! -f "$INFRA_ENV" ]]; then
    fail "$INFRA_ENV not found — copy secrets/infra.env.example there and fill in the token"
else
    ok "$INFRA_ENV present"
    set -a
    # shellcheck source=/dev/null
    source "$INFRA_ENV"
    set +a
    if [[ -z "${DIGITALOCEAN_TOKEN:-}" ]]; then
        fail "DIGITALOCEAN_TOKEN is not set after sourcing $INFRA_ENV"
    elif [[ "$DIGITALOCEAN_TOKEN" != dop_v1_* ]]; then
        fail "DIGITALOCEAN_TOKEN does not start with the expected 'dop_v1_' prefix"
    else
        ok "DIGITALOCEAN_TOKEN is set and has the expected format"
    fi
fi

# ── 2. DigitalOcean API reachability (read-only) ───────────────────────────
printf '\n[CHECK] DigitalOcean API token (GET /v2/account)\n'
if [[ -z "${DIGITALOCEAN_TOKEN:-}" ]]; then
    fail "Skipped — DIGITALOCEAN_TOKEN not available"
else
    HTTP_CODE="$(curl -s -o /dev/null -w '%{http_code}' \
        -H "Authorization: Bearer $DIGITALOCEAN_TOKEN" \
        "$DO_API/account")"
    case "$HTTP_CODE" in
        200) ok "DO API accepted the token (HTTP 200)" ;;
        401) fail "DO API rejected the token (HTTP 401) — invalid or revoked" ;;
        000) fail "DO API unreachable (no HTTP response — check network/DNS)" ;;
        *)   fail "DO API returned unexpected HTTP $HTTP_CODE" ;;
    esac
fi

# ── 3. sask_ed25519 key presence and permissions ────────────────────────────
printf '\n[CHECK] sask_ed25519 private key\n'
if [[ ! -f "$SASK_KEY" ]]; then
    fail "$SASK_KEY not found — copy it from the retired sask-dev VM (see docs/dev-setup.md)"
else
    KEY_PERMS="$(stat -c '%a' "$SASK_KEY")"
    if [[ "$KEY_PERMS" != "600" ]]; then
        fail "$SASK_KEY has permissions $KEY_PERMS, expected 600"
    else
        ok "$SASK_KEY present with correct permissions (600)"
    fi
fi

# ── 4. SSH probe to sask-droplet (non-destructive) ──────────────────────────
printf '\n[CHECK] SSH probe to %s\n' "$SSH_ALIAS"
if [[ ! -f "$SASK_KEY" ]]; then
    fail "Skipped — $SASK_KEY not present"
else
    if ssh -o BatchMode=yes -o ConnectTimeout=10 "$SSH_ALIAS" 'true' &>/dev/null; then
        ok "SSH to $SSH_ALIAS succeeded"
    else
        fail "SSH to $SSH_ALIAS failed — check the droplet is up, the firewall allows this IP, and $SASK_KEY is DO-trusted"
    fi
fi

# ── Summary ──────────────────────────────────────────────────────────────────
printf '\n── Summary ──────────────────────────────────────────────\n'
printf '  Pass: %d\n' "$PASS_COUNT"
printf '  Fail: %d\n' "$FAIL_COUNT"
if [[ "$FAIL_COUNT" -gt 0 ]]; then
    printf '\n[RESULT] FAIL — %d check(s) failed.\n' "$FAIL_COUNT" >&2
    exit 1
fi
printf '\n[RESULT] PASS — DigitalOcean token and SSH access verified.\n'

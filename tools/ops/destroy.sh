#!/usr/bin/env bash
# Tear down the sask droplet and every resource OpenTofu created for it.
#
# Run from the dev host (ubuvm), repo root:
#
#   bash tools/ops/destroy.sh        # interactive: tofu prompts before each destroy
#   bash tools/ops/destroy.sh -y     # non-interactive: tofu -auto-approve
#
# A droplet can't be destroyed while a reserved IP is still assigned to it,
# so the reserved-IP assignment is detached first, then everything else
# (droplet, reserved IP, DNS record, firewall, SSH key, the generated
# ~/.ssh/config.d/sask snippet) is destroyed in a second pass. Finally, the
# stale known_hosts entry for the reserved IP / alias is purged so the next
# provision's first connection isn't refused as "changed".
#
# Requires ~/.config/sask/infra.env (outside the repo) exporting
# DIGITALOCEAN_TOKEN — see secrets/infra.env.example for the template.

set -euo pipefail

cd "$(dirname "$0")/../.."

INFRA_ENV="$HOME/.config/sask/infra.env"
if [[ ! -f "$INFRA_ENV" ]]; then
    printf '[FAIL] %s not found.\n' "$INFRA_ENV" >&2
    printf '       Copy secrets/infra.env.example there and fill in your token.\n' >&2
    exit 1
fi

set -a
# shellcheck disable=SC1090
source "$INFRA_ENV"
set +a

if [[ -z "${DIGITALOCEAN_TOKEN:-}" ]]; then
    printf '[FAIL] DIGITALOCEAN_TOKEN is not set after sourcing %s.\n' "$INFRA_ENV" >&2
    exit 1
fi

AUTO_APPROVE=()
if [[ "${1:-}" == "-y" ]]; then
    AUTO_APPROVE=("-auto-approve")
fi

cd infra/tofu
tofu init -upgrade

# Capture the reserved IP before destroying, so its stale known_hosts entry
# can be purged — the next droplet provisioned at this IP will have a
# different host key, and ssh would otherwise refuse it as "changed"
# rather than treating it as new (see infra/tofu/ssh-config.tf).
RESERVED_IP="$(tofu output -raw reserved_ip 2>/dev/null || true)"

tofu destroy -target digitalocean_reserved_ip_assignment.sask "${AUTO_APPROVE[@]}"
tofu destroy "${AUTO_APPROVE[@]}"

if [[ -n "$RESERVED_IP" ]]; then
    ssh-keygen -R "$RESERVED_IP" >/dev/null 2>&1 || true
fi
ssh-keygen -R sask-droplet >/dev/null 2>&1 || true

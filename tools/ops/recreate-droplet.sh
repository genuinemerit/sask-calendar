#!/usr/bin/env bash
# Recreate only the droplet, leaving the reserved IP, DNS record, firewall
# definition, and SSH key registration untouched in Tofu state. This is
# what actually delivers DD-0014/REQ-OPS-013's guarantee that DNS and the
# SSH alias survive a redeploy with the *same* reserved IP — plain
# tools/ops/destroy.sh + provision.sh tears down everything, including the
# reserved IP resource itself, which is the right tool for a genuine full
# teardown (e.g. to stop paying for anything) but the wrong one for
# "rebuild the droplet, keep the network identity."
#
# Run from the dev host (ubuvm), repo root:
#
#   bash tools/ops/recreate-droplet.sh        # interactive
#   bash tools/ops/recreate-droplet.sh -y     # non-interactive: tofu -auto-approve
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

RESERVED_IP="$(tofu output -raw reserved_ip 2>/dev/null || true)"

# A reserved IP can't be assigned to a droplet that's being destroyed, so
# detach first. Only the droplet itself is then destroyed; everything
# else (reserved IP, DNS, firewall, SSH key) stays in state, and the
# following apply recreates just the droplet and reassigns the existing
# reserved IP to it.
tofu destroy -target digitalocean_reserved_ip_assignment.sask "${AUTO_APPROVE[@]}"
tofu destroy -target digitalocean_droplet.sask "${AUTO_APPROVE[@]}"
tofu apply "${AUTO_APPROVE[@]}"

# Same IP, new droplet, new host key — purge the stale known_hosts entry
# so the next connection is treated as new rather than refused as
# "changed" (see infra/tofu/ssh-config.tf).
if [[ -n "$RESERVED_IP" ]]; then
    ssh-keygen -R "$RESERVED_IP" >/dev/null 2>&1 || true
fi
ssh-keygen -R sask-droplet >/dev/null 2>&1 || true

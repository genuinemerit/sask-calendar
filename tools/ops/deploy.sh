#!/usr/bin/env bash
# Deploy (or re-converge) sask onto an already-provisioned droplet via
# Ansible.
#
#   bash tools/ops/deploy.sh
#
# Requires ~/.config/sask/infra.env (outside the repo, see
# secrets/infra.env.example) as a general setup-sanity precondition, even
# though Ansible itself doesn't need the DO token. Bootstraps the `dave`
# admin account on first run only (when it isn't already reachable as
# dave); every later run skips straight to the main site play.

set -euo pipefail

cd "$(dirname "$0")/../.."

INFRA_ENV="$HOME/.config/sask/infra.env"
if [[ ! -f "$INFRA_ENV" ]]; then
    printf '[FAIL] %s not found.\n' "$INFRA_ENV" >&2
    printf '       Copy secrets/infra.env.example there and fill in your token.\n' >&2
    exit 1
fi

bash tools/ops/export-requirements.sh

# Wait for the droplet's SSH daemon to come up before Ansible connects.
# A freshly created or recreated droplet can take ~60 s to be ready; not
# waiting here was the root cause of the SSH-readiness race flagged in the
# SPEC-029 addendum. Succeeds immediately when the droplet is already running.
_SSH_READY=false
for _I in $(seq 1 24); do
    if ssh -o BatchMode=yes -o ConnectTimeout=5 -o User=root sask-droplet true 2>/dev/null; then
        _SSH_READY=true
        break
    fi
    printf '[INFO] SSH not ready yet (%d/24); retrying in 5 s...\n' "$_I"
    sleep 5
done
if [[ "$_SSH_READY" != true ]]; then
    printf '[FAIL] Droplet SSH did not become reachable within 2 minutes.\n' >&2
    exit 1
fi

# cd into ansible/ rather than passing -i/--ANSIBLE_CONFIG explicitly:
# Ansible only auto-loads ansible.cfg (and its relative inventory= path)
# from the current directory, not from the playbook's own location.
cd ansible

if ! ssh -o BatchMode=yes -o ConnectTimeout=5 sask-droplet true 2>/dev/null; then
    printf '[INFO] dave not yet reachable — running the one-time root bootstrap.\n'
    ansible-playbook bootstrap.yml
fi

ansible-playbook site.yml

# Test results: SPEC-022

**Spec:** SPEC-022 — Droplet provisioning via OpenTofu
**Date:** 2026-06-22
**Status:** PARTIAL — provisioning, connectivity, DNS, and idempotency verified
against a real droplet; the destroy/recreate-cycle check is deferred to
SPEC-024's Layer 4 (full destroy -> reprovision -> redeploy test), since a
meaningful redeploy exercise wants SPEC-023's Ansible re-convergence too,
not bare Tofu alone.

---

## Local validation (before the real apply)

```text
$ tofu fmt -diff -recursive
main.tf   (one whitespace alignment fix, applied)

$ tofu init -input=false -backend=false && tofu validate
Success! The configuration is valid.
```

`ruff`, `pymarkdown`, `validate_specs.py`, and the `validate_specs` pytest
suite all pass (`tools/pre-commit-check.sh`, full run, all PASS).

## Real `tofu apply` (tools/provision.sh -y)

```text
Plan: 7 to add, 0 to change, 0 to destroy.

digitalocean_reserved_ip.sask: Creation complete after 1s [id=129.212.194.54]
digitalocean_ssh_key.sask: Creation complete after 1s [id=57296743]
local_file.ssh_config: Creation complete after 0s
digitalocean_record.sask: Creation complete after 1s [id=1823133105]
digitalocean_droplet.sask: Creation complete after 42s [id=579490216]
digitalocean_firewall.sask: Creation complete after 1s
digitalocean_reserved_ip_assignment.sask: Creation complete after 13s

Apply complete! Resources: 7 added, 0 changed, 0 destroyed.

Outputs:
droplet_id  = "579490216"
fqdn        = "sask.davidstitt.net"
reserved_ip = "129.212.194.54"
```

Status: PASS — all 7 resources created; matches the plan exactly.

## SSH connectivity

First connection attempt failed (`Permission denied (publickey)`) despite the
server correctly accepting the offered public key — root-caused via `ssh -vvv`
(key accepted, then no signing step, then "No more authentication methods")
and confirmed via `ssh-keygen -y -f ~/.ssh/sask_ed25519 -P ''`: the private key
was passphrase-protected with no agent caching it, so it couldn't be used
non-interactively. Fixed by stripping the passphrase (`ssh-keygen -p`, decided
acceptable since this is a single-purpose deploy key used only for this
project, mode 600, not the developer's personal key). Re-verified
non-destructively (empty-passphrase decrypt succeeds and still matches the
registered public key) before retrying.

```text
$ ssh -o User=root sask-droplet 'whoami && hostname && cat /etc/os-release | head -2'
root
sask-droplet
PRETTY_NAME="Ubuntu 24.04.3 LTS"
NAME="Ubuntu"
```

Status: PASS (after the passphrase fix above).

## DNS resolution

```text
$ python3 -c "import socket; print(socket.gethostbyname('sask.davidstitt.net'))"
129.212.194.54
```

Matches the reserved IP exactly. Status: PASS.

## Idempotency (second plan against the converged droplet)

```text
$ tofu plan -detailed-exitcode
No changes. Your infrastructure matches the configuration.
EXITCODE:0
```

Status: PASS — read-only equivalent of "re-running provision.sh is a no-op";
a literal second `provision.sh -y` run was not executed to avoid an
unnecessary second `tofu apply` cycle, since `plan` already proves zero drift.

## Out-of-band cleanup (unrelated to this SPEC's resources)

An old, unattached firewall (`bow-spt-firewall`, leftover from an unrelated
past project, confirmed by the developer as unused/years old) was found
during a DO API sanity check and deleted at the developer's request
(`DELETE /v2/firewalls/{id}` -> HTTP 204). Not part of SPEC-022's deliverables;
recorded here only because it was found and removed during this session.

---

## Acceptance criteria

| Item | Status |
| --- | --- |
| `tofu apply` creates every resource; DNS resolves to reserved IP; firewall exposes 22/80/443 correctly | PASS |
| `tofu destroy` detaches the reserved IP first; removes the `~/.ssh/config.d/sask` snippet | DEFERRED, SPEC-024 |
| Destroy/recreate keeps the reserved IP (DNS, SSH alias) unchanged while the droplet IP changes | DEFERRED, SPEC-024 |
| No token in any `.tf` file or in Tofu state; token read from the environment only | PASS (by construction) |
| Re-running provision is a no-op except on developer-IP change | PASS (`tofu plan`, zero drift) |

---

## Deviations and notes

- `outputs.tf`'s `next_steps` text was corrected during drafting: the SSH
  alias defaults to `User dave` (the long-term steady state once SPEC-023's
  Ansible bootstrap creates that account), so the *first* connection after
  `tofu apply` must override the user explicitly
  (`ssh -o User=root sask-droplet`) — documented in the output text itself.
- `sask_ed25519`'s passphrase was removed (see SSH connectivity section) —
  a deliberate, confirmed trade-off favoring full deploy automation
  (REQ-OPS-013's single-mainline-`redeploy` bar) over the sibling project's
  original agent-based approach, since this key has no other use.
- The droplet retains its own native public IP (`165.245.210.188`) in
  addition to the reserved IP (`129.212.194.54`) — standard DigitalOcean
  behavior, not a misconfiguration.

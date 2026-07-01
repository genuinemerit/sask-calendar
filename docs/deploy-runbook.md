# Deploy runbook — sask.davidstitt.net

Quick reference for operating the live droplet. Everything below runs
from the dev host (ubuvm), from the repo root, unless noted otherwise.

## Connect

```bash
bash tools/ops/connect.sh                          # interactive shell, as dave
bash tools/ops/connect.sh 'systemctl status sask'  # one-off command
```

Root login is disabled by design (REQ-SEC-003) — `dave` is the only login
account, with passwordless `sudo`.

## Check status

```bash
bash tools/ops/connect.sh 'sudo systemctl status sask caddy --no-pager'
bash tools/ops/connect.sh 'sudo journalctl -u sask -n 50 --no-pager'
bash tools/ops/connect.sh 'sudo journalctl -u caddy -n 50 --no-pager'
bash tools/ops/acceptance-test.sh                  # external: TLS, /health, rendered content
```

## Deploy a code change

```bash
bash tools/ops/deploy.sh
```

Re-syncs `src/sask/`, `config/`, `assets/<assets_version>/` (deploy-ready
assets only — `assets/local/` never leaves the controller, per DD-0016),
`wsgi.py`, and dependencies; restarts the service only if something
actually changed. Safe to run repeatedly — a second consecutive run
against an already-converged droplet reports `changed=0`.

## Full rebuild (destroy and recreate the droplet)

```bash
bash tools/ops/redeploy.sh -y
```

Runs `recreate-droplet.sh` (destroys/recreates *only* the droplet) ->
`deploy.sh` -> `acceptance-test.sh` as one act. The reserved IP, DNS
record, firewall, and SSH key registration all survive unchanged — only
`droplet_id` changes. Expect a few minutes of real downtime.

## Full teardown (stop paying for everything)

```bash
bash tools/ops/destroy.sh -y
```

Tears down *every* resource, including the reserved IP itself — this is
the one operation where the IP does NOT survive. To come back later, the
next `bash tools/ops/provision.sh -y` gets a brand-new reserved IP and DNS
gets repointed at it automatically; nothing manual to fix up.

## OS maintenance (occasional, manual — not part of any automated pipeline)

`unattended-upgrades` already applies security patches continuously in
the background. Every few months, or whenever convenient, catch up on
everything else:

```bash
bash tools/ops/connect.sh
sudo apt update && apt list --upgradable   # see what's pending first
sudo apt upgrade -y
[ -f /var/run/reboot-required ] && sudo reboot   # only if a kernel update needs it
```

Then, back on the dev host, confirm recovery:

```bash
bash tools/ops/acceptance-test.sh
```

Deliberately not automated or scheduled — see `docs/devlog.md`
(2026-06-22) for the reasoning: patch cadence and app-deploy cadence are
different concerns, and an unattended kernel-upgrade-plus-reboot with
nobody watching is the wrong default at this scale.

## Things to remember

- The SSH alias (`sask-droplet`, in `~/.ssh/config.d/sask`) connects as
  `dave`, never root, and is the *only* place an IP is ever referenced
  (REQ-OPS-014). If your own source IP changes, `bash tools/ops/provision.sh
  -y` (or any `redeploy.sh`/`recreate-droplet.sh` run) refreshes the
  firewall's allowed-SSH-IP rule automatically.
- `tools/ops/destroy.sh` (full teardown) and `tools/ops/recreate-droplet.sh`
  (droplet only) are deliberately different scripts — don't conflate
  them. `redeploy.sh` always uses the latter.
- The DigitalOcean Personal Access Token in `~/.config/sask/infra.env`
  expires ~2027-04-22 — renew it before then via the DO console, or any
  `provision.sh`/`deploy.sh`/`redeploy.sh` run will fail on auth.
- Caddy auto-issues and auto-renews its own Let's Encrypt certificate —
  no manual TLS renewal step exists or is needed.
- If SSH is ever refused entirely (e.g. a botched manual change), the DO
  web console is the out-of-band fallback (REQ-OPS-014) — from there you
  can inspect the droplet directly or fall back to `tools/ops/redeploy.sh
  -y` for a clean rebuild.

## Where to find more detail

- `design/decisions/dd-0014-deploy.toml` — the design and its rationale.
- `tests/results/SPEC-022.md`, `SPEC-023.md`, `SPEC-024.md` — full
  verification evidence, including the real bugs found running each
  piece for the first time.
- `docs/devlog.md` (entries dated 2026-06-22) — the narrative of what was
  built, broken, and fixed, in order.

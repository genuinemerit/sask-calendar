# Dev environment setup — sask

From-scratch procedure for Ubuntu 26.04 LTS (or any Debian-style Linux).
Replaces `docs/vm-setup.md`, which covered the retired NixOS `sask-dev` VM.

The system Python on Ubuntu 26.04 is 3.14. The project deliberately uses
3.12 via pyenv — the pin pre-dates 3.14 support validation in Werkzeug and
gunicorn. See DD-0019 for full rationale.

---

## 1. Clone the repo

```bash
git clone git@github.com:genuinemerit/sask.git
cd sask
```

## 2. Bootstrap the dev host (one command)

```bash
bash tools/dev/init-dev-host.sh
```

This installs all system-level prerequisites (see below for the list),
pyenv, Python 3.12 (latest patch), and Poetry. It is idempotent — safe to
re-run. It writes a `.python-version` file in the repo root that pins the
project to 3.12 without touching the system interpreter.

**System-prereq list (for reference / manual runs):** Empirically derived on
Ubuntu 26.04; see docs/devlog.md 2026-06-30. Native watch-items (libsqlite3,
libssl) confirmed: `import sqlite3, ssl, hashlib` passes with no extras.

```bash
# pyenv build dependencies
build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev
libsqlite3-dev libncursesw5-dev xz-utils tk-dev libxml2-dev
libxmlsec1-dev libffi-dev liblzma-dev

# runtime / harness / dev tooling
git curl wget ca-certificates openssh-client shellcheck tree ansible rsync

# deploy harness
snap install opentofu --classic
```

## 3. Install Python dependencies

```bash
poetry install
```

Verify the interpreter and venv:

```bash
python --version      # should print: Python 3.12.x
poetry env info       # venv path at ~/.cache/pypoetry/virtualenvs/...
```

## 4. Run the test suite

```bash
poetry run pytest -q
```

All tests should pass. The count grows with each SPEC; check
`docs/devlog.md` for the most recent recorded passing count.

## 5. Run the app locally

```bash
PYTHONPATH=src poetry run flask --app sask.web run
```

Then open <http://localhost:5000/>. The `/health` route returns
`{"status": "ok"}` and is useful for scripted checks.

## 6. Run pre-commit checks

Before every commit:

```bash
bash tools/dev/pre-commit-check.sh
```

Every check must exit 0.

---

## Host secrets (manual)

Two secrets are required to use the DigitalOcean deploy harness. They are
**never scripted or committed** — place them manually after step 2.

### DIGITALOCEAN_TOKEN

```bash
mkdir -p ~/.config/sask
cp secrets/infra.env.example ~/.config/sask/infra.env
# Edit ~/.config/sask/infra.env and set DIGITALOCEAN_TOKEN to a valid DO
# personal access token (read/write scopes for Droplets, Reserved IPs,
# Firewalls, Domain Records, SSH Keys).
```

### sask_ed25519 SSH key

The DO ssh-key resource trusts a specific keypair. Copy the existing key
from the previous dev host rather than generating a new one (a new key would
require updating the DO ssh-key resource and the droplet's authorized_keys).

```bash
# From old host to new host:
scp <old-host>:~/.ssh/sask_ed25519 ~/.ssh/sask_ed25519
scp <old-host>:~/.ssh/sask_ed25519.pub ~/.ssh/sask_ed25519.pub
chmod 600 ~/.ssh/sask_ed25519
```

Also ensure `~/.ssh/config` (or `~/.ssh/config.d/sask`) has the
`sask-droplet` alias pointing to the correct IP with `IdentityFile
~/.ssh/sask_ed25519`.

### Verify secrets

```bash
bash tools/dev/verify-do-secrets.sh
```

All 4 checks (infra.env, token format, DO API HTTP 200, SSH to
`sask-droplet`) must pass.

---

## Verify the full setup

```bash
bash tools/dev/verify-clean-env.sh
```

Confirms: pyenv + Python 3.12 pin, native stdlib modules (sqlite3/ssl/hashlib),
poetry install, full test suite pass, app boot + `GET /health` returns 200.

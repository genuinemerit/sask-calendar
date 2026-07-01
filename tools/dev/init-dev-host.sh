#!/usr/bin/env bash
# tools/dev/init-dev-host.sh — dev-host bootstrap for stock Ubuntu LTS.
#
# The portable, executable replacement for the retired NixOS
# infra/configuration.nix (DD-0019 / SPEC-031). Installs the NON-SECRET
# system-level prerequisites only: apt packages, OpenTofu, pyenv, a
# project-pinned Python 3.12, and Poetry. Contains no tokens or keys and is
# safe to commit and re-run (every step is idempotent).
#
# Usage:
#   bash tools/dev/init-dev-host.sh
#
# After this script completes:
#   poetry install
#   poetry run pytest -q
# Then place host secrets manually (never done by this script — see
# docs/dev-setup.md, "Host secrets (manual)") and run:
#   bash tools/dev/verify-do-secrets.sh

set -euo pipefail

# ── Pinned versions (the config-driven part of this script) ────────────────
# Only the Python MINOR version is pinned here; the latest available 3.12.x
# patch is resolved from pyenv at run time so this never goes stale.
PYTHON_MINOR="3.12"

# ── apt prerequisites ───────────────────────────────────────────────────────
# Derived from infra/configuration.nix (DD-0019 cross-check source) minus
# desktop/VM-guest plumbing and the user's personal CLI toolbelt, which are
# not sask dependencies. Two groups: pyenv's documented build dependencies
# (https://github.com/pyenv/pyenv/wiki#suggested-build-environment), and the
# runtime/harness/dev-tooling essentials configuration.nix also declared.
# The lint binary used by pre-commit-check.sh, the tree binary used by
# tools/helpers/make_tree.sh, and ansible + rsync used by the tools/ops/
# deploy harness are native tools, not Python packages, so they are listed
# here as apt prerequisites, not Poetry dev-deps. Ubuntu's `ansible` apt
# package (unlike pip's `ansible-core`) bundles the collections the deploy
# harness needs (e.g. ansible.posix.synchronize) — this replaces the
# `pkgs.ansible` + `pkgs.ansible-lint` the retired flake.nix devShell
# provided, which the DD-0019 port dropped without a replacement.
APT_PYENV_BUILD_DEPS=(
    build-essential
    libssl-dev
    zlib1g-dev
    libbz2-dev
    libreadline-dev
    libsqlite3-dev
    libncursesw5-dev
    xz-utils
    tk-dev
    libxml2-dev
    libxmlsec1-dev
    libffi-dev
    liblzma-dev
)
APT_ESSENTIALS=(
    git
    curl
    wget
    ca-certificates
    openssh-client
    shellcheck
    tree
    ansible
    rsync
)

# ── Helpers ──────────────────────────────────────────────────────────────────
step() { printf '\n[STEP] %s\n' "$*"; }
ok()   { printf '[PASS] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*" >&2; }
fail() { printf '[FAIL] %s\n' "$*" >&2; exit 1; }

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# ── OS guard ─────────────────────────────────────────────────────────────────
step "Check OS"
if [[ ! -r /etc/os-release ]]; then
    fail "Cannot detect OS — /etc/os-release not readable"
fi
# shellcheck source=/dev/null
. /etc/os-release
if [[ "${ID:-}" != "ubuntu" ]]; then
    fail "This script targets Ubuntu; detected ID='${ID:-unknown}' (${PRETTY_NAME:-unknown})"
fi
ok "OS: ${PRETTY_NAME:-Ubuntu}"

# ── apt prerequisites ────────────────────────────────────────────────────────
step "Install apt prerequisites"
sudo apt-get update -qq
sudo apt-get install -y "${APT_PYENV_BUILD_DEPS[@]}" "${APT_ESSENTIALS[@]}"
ok "apt prerequisites installed"

# ── OpenTofu (deploy-harness tool; via snap, classic confinement) ──────────
step "Install OpenTofu"
if command -v tofu &>/dev/null; then
    ok "OpenTofu already installed: $(tofu version | head -1)"
elif command -v snap &>/dev/null; then
    sudo snap install opentofu --classic
    ok "OpenTofu installed: $(tofu version | head -1)"
else
    warn "snap not available — install OpenTofu manually: https://opentofu.org/docs/intro/install/"
fi

# ── pyenv ────────────────────────────────────────────────────────────────────
step "Install pyenv"
PYENV_ROOT="${PYENV_ROOT:-$HOME/.pyenv}"
export PYENV_ROOT
if [[ -x "$PYENV_ROOT/bin/pyenv" ]]; then
    ok "pyenv already present at $PYENV_ROOT"
else
    curl -fsSL https://pyenv.run | bash
    ok "pyenv installed at $PYENV_ROOT"
fi

# Make pyenv available for the rest of THIS script's execution. The pyenv
# installer adds the equivalent lines to ~/.bashrc for future shells.
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

# ── Python (pinned minor, latest patch resolved at run time) ───────────────
step "Install Python ${PYTHON_MINOR} (latest patch) via pyenv"
PYTHON_FULL="$(pyenv install --list | grep -E "^[[:space:]]+${PYTHON_MINOR}\.[0-9]+$" | tail -1 | tr -d '[:space:]')"
if [[ -z "$PYTHON_FULL" ]]; then
    fail "Could not resolve a ${PYTHON_MINOR}.x release from 'pyenv install --list'"
fi
if pyenv versions --bare | grep -qxF "$PYTHON_FULL"; then
    ok "Python $PYTHON_FULL already installed via pyenv"
else
    pyenv install "$PYTHON_FULL"
    ok "Python $PYTHON_FULL installed via pyenv"
fi

step "Pin project-local Python version"
cd "$REPO_ROOT"
pyenv local "$PYTHON_FULL"
RESOLVED="$(python --version 2>&1)"
if [[ "$RESOLVED" != "Python $PYTHON_FULL" ]]; then
    fail "python resolves to '$RESOLVED' in $REPO_ROOT, expected 'Python $PYTHON_FULL'"
fi
ok ".python-version -> $PYTHON_FULL (system python3 is left untouched)"

# ── Poetry ───────────────────────────────────────────────────────────────────
step "Install Poetry"
if command -v poetry &>/dev/null; then
    ok "Poetry already installed: $(poetry --version)"
else
    curl -sSL https://install.python-poetry.org | python -
    export PATH="$HOME/.local/bin:$PATH"
    if ! command -v poetry &>/dev/null; then
        fail "Poetry install completed but 'poetry' not found on PATH (expected ~/.local/bin)"
    fi
    ok "Poetry installed: $(poetry --version)"
fi

# ── Host secrets — presence check ONLY, never installed or generated here ──
step "Check host secrets presence (manual placement required)"
INFRA_ENV="$HOME/.config/sask/infra.env"
SASK_KEY="$HOME/.ssh/sask_ed25519"

if [[ -f "$INFRA_ENV" ]]; then
    ok "$INFRA_ENV present"
else
    warn "$INFRA_ENV not found — see docs/dev-setup.md, 'Host secrets (manual)'"
fi

if [[ -f "$SASK_KEY" ]]; then
    ok "$SASK_KEY present"
else
    warn "$SASK_KEY not found — see docs/dev-setup.md, 'Host secrets (manual)'"
fi

# ── Done ─────────────────────────────────────────────────────────────────────
printf '\n[DONE] dev-host bootstrap complete.\n'
printf '       Next:\n'
printf '         cd %s\n' "$REPO_ROOT"
printf '         poetry install\n'
printf '         poetry run pytest -q\n'
printf '       Then verify DO access:\n'
printf '         bash tools/dev/verify-do-secrets.sh\n'

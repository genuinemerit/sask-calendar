# CLAUDE.md — sask project instructions

## Environment

- Dev host: **Ubuntu 26.04 LTS** (replaced the retired NixOS `sask-dev` VM — DD-0019).
- Python is pinned to **3.12** via pyenv (system python3 is 3.14 and left untouched).
- All Python tooling is managed by **Poetry**; use `poetry run <tool>` rather than
  activating the venv manually.
- `shellcheck` is installed via apt (see `tools/dev/init-dev-host.sh`).
- See `docs/dev-setup.md` for the from-scratch Ubuntu setup procedure.

## Before every commit

Run the pre-commit script; every check must exit 0 before staging:

```bash
bash tools/dev/pre-commit-check.sh
```

The script runs, in order:

```bash
poetry run ruff check tools/ tests/ src/
poetry run ruff format --check tools/ tests/ src/
shellcheck -S warning tools/*/*.sh
poetry run pymarkdown --config .pymarkdown scan README.md CLAUDE.md docs/ tests/results/ secrets/README.md
python3 tools/dev/validate_specs.py
poetry run pytest tests/test_validate_specs.py -q
```

## Design docs

Design documents live under `design/` as TOML. After any change to a design
doc or its schema, run `python3 tools/dev/validate_specs.py` and confirm exit 0.

## Infrastructure split

- `tools/dev/init-dev-host.sh` — dev-host bootstrap (apt prereqs, pyenv, Python
  3.12, Poetry). Safe to commit; contains no secrets. Run once on a fresh Ubuntu
  host, then `poetry install`.
- `infra/archive/configuration.nix` — retired NixOS dev-VM config, kept as
  historical reference for the system-prereq derivation (DD-0019).
- `infra/tofu/` — OpenTofu IaC for the *production* DigitalOcean droplet.
  See `docs/deploy-runbook.md` for day-to-day deploy operations.

## Git identity

```text
user.name  = David
user.email = david.stitt@pm.me
```

## Human review

All generated code and config files require human review before execution.
Present files for inspection; do not auto-run infrastructure or destructive
commands. Steps marked `[manual]` in specs are for the developer, not Claude.

## Do not reference saskan-lore

Do not explore or reference the `saskan-lore` project directory. Remove any
references to it from docs or code if encountered.

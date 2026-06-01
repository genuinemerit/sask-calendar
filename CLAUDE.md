# CLAUDE.md — sask project instructions

## Environment

- Claude Code runs on the **Ubuntu host laptop**; the NixOS VM (`sask-dev`) is
  the canonical dev environment, accessed via SSH.
- A local `.venv` at the project root contains `pymarkdownlnt` and `pytest`.
  `ruff` is provided by the NixOS system packages and nix devShell — do not
  use a pip-installed ruff (pre-compiled binaries fail on NixOS).

## Before every commit

Run all of the following; every check must exit 0 before staging:

```bash
ruff check tools/ tests/
ruff format --check tools/ tests/
nix develop --command .venv/bin/pymarkdown --config .pymarkdown scan README.md CLAUDE.md docs/ tests/results/ secrets/README.md
python3 tools/validate_specs.py
.venv/bin/pytest tests/test_validate_specs.py -q
```

## Design docs

Design documents live under `design/` as TOML. After any change to a design
doc or its schema, run `python3 tools/validate_specs.py` and confirm exit 0.

## Machine / project split

- `infra/configuration.nix` — canonical full replacement for
  `/etc/nixos/configuration.nix` on the `sask-dev` VM. Never add project
  tooling here; it belongs in `flake.nix`.
- `flake.nix` — pinned devShell for the project; pinned to `nixos-25.11`.

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

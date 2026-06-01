# Dev log

## 2026-06-01 — SPEC-001: VM steps complete, SPEC-001 fully PASS

Completed all manual VM steps from docs/vm-setup.md:

- `nixos-rebuild switch` applied; hostname confirmed `sask-dev`
- Key-only SSH verified (password auth rejected)
- `nix develop` confirmed: Python 3.12.13, Poetry 2.2.1, ruff 0.14.6
- `flake.lock`, `poetry.lock`, `requirements.txt` generated and committed

Fixes applied during VM steps:

- `flake.nix`: added `POETRY_VIRTUALENVS_PREFER_ACTIVE_PYTHON=true` and
  `LD_LIBRARY_PATH` fix — required for venv creation inside NixOS devShell
- `docs/vm-setup.md`: replaced `poetry export` with `poetry run pip freeze`
  (`poetry-plugin-export` not available in the pinned environment)
- `CLAUDE.md`: clarified ruff comes from nix devShell, not pip

SPEC-001 acceptance criteria all PASS.

## 2026-06-01 — SPEC-001: initial commit and VM configuration revised

Initial bootstrap commit pushed to `genuinemerit/sask-calendar` on GitHub.

VM approach updated: switched from provisioning a fresh headless NixOS VM to
reconfiguring an existing NixOS 25.11 KDE Plasma VM. Updated
`infra/configuration.nix` to a full replacement config (preserving KDE desktop,
adding key-only SSH hardening), pinned `flake.nix` to nixos-25.11, and rewrote
`docs/vm-setup.md`.

## 2026-05-31 — SPEC-001: repository scaffold

Stood up the sask repository from scratch on the Ubuntu host per DD-0001.

**Completed (Ubuntu host):**

- Full directory tree with `.gitkeep` in empty dirs
- Root files: `LICENSE`, `.gitignore`, `.editorconfig`, `pyproject.toml`, `flake.nix`
- Design schemas: `_schema.toml` for decisions, reqs, and specs
- Schema-enforcing `tools/validate_specs.py` and `tests/test_validate_specs.py`
- `infra/configuration.nix` — NixOS 25.11, user dave, key-only SSH, KDE desktop preserved
- Standard docs: `README.md`, `devlog.md`, `references.md`, `vm-setup.md`

**Deferred to VM (manual):**

- `nixos-rebuild switch` against `infra/configuration.nix`
- `flake.lock` and `poetry.lock` generation
- `requirements.txt` export

**Next:** DD-0002 — calendar engine representation (fixed-day core, 8 moons, wanderers).

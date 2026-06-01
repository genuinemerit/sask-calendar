# sask

Umbrella project for the Saskan calendar engine and related tools.
This repository is a deliberate evolutionary rebuild: lean scaffolding first,
functional areas added incrementally under `/src`.

## Quick start

**Prerequisites:** [Nix](https://nixos.org/download) with flakes enabled.

```bash
git clone https://github.com/genuinemerit/sask-calendar.git
cd sask-calendar
nix develop
```

Inside the shell:

```bash
python3 --version   # 3.12.x
poetry --version    # pinned via flake.lock
ruff --version
```

## Layout

```text
ansible/      future Ansible playbooks
design/       TOML design docs (decisions/, reqs/, specs/)
docs/         living documents and guides
infra/        NixOS configuration for the dev VM
resources/    reference data and assets
scripts/      one-off utility scripts
secrets/      local credentials — git-ignored except README.md and *.example
src/          Python source (package: sask)
tests/        pytest suites and test results
tools/        developer tooling (validate_specs.py, ...)
```

## Design docs

Design decisions, requirements, and specs live under `/design` as TOML.
Validate them with:

```bash
python3 tools/validate_specs.py
```

Run the validator test suite:

```bash
pytest tests/test_validate_specs.py -v
```

## Development environment

See [docs/vm-setup.md](docs/vm-setup.md) for configuring the NixOS dev VM.
The dev toolchain is pinned by `flake.lock`; `infra/configuration.nix` defines
the host. Destroying and re-cloning the repo fully restores the environment.

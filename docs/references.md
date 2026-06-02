# References

## Toolchain

- [NixOS 25.11](https://nixos.org/) — dev VM OS and flake channel pin
- [Nix flakes](https://nixos.wiki/wiki/Flakes) — reproducible dev shell
- [Poetry](https://python-poetry.org/docs/) — Python dependency management
- [Ruff](https://docs.astral.sh/ruff/) — Python linter and formatter
- [pytest](https://docs.pytest.org/) — Python test framework
- [tomllib](https://docs.python.org/3/library/tomllib.html) — TOML parsing (Python 3.11+ stdlib)
- [Flask](https://flask.palletsprojects.com/) — web framework (server-rendered Jinja UI)
- [gunicorn](https://gunicorn.org/) — WSGI server for production deployment

## Infrastructure

- [Virtual Machine Manager (virt-manager)](https://virt-manager.org/) — VM host UI
- [libvirt / QEMU / KVM](https://libvirt.org/) — VM backend

## Design document schemas

- `design/decisions/_schema.toml` — DD schema (id pattern `DD-\d{4}`)
- `design/reqs/_schema.toml` — REQ schema (id pattern `REQ-(FUN|OPS|SEC)-\d{3}`)
- `design/specs/_schema.toml` — SPEC schema (id pattern `SPEC-\d{3}`)

## Standards

- [TOML v1.0](https://toml.io/en/) — design document format
- [EditorConfig](https://editorconfig.org/) — cross-editor formatting consistency
- [MIT License](https://opensource.org/licenses/MIT)

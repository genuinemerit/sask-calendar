# References

## Toolchain

- [Ubuntu 26.04 LTS](https://ubuntu.com/) — dev host OS (DD-0019)
- [pyenv](https://github.com/pyenv/pyenv) — Python 3.12 version pin, independent of system Python
- [Poetry](https://python-poetry.org/docs/) — Python dependency management
- [Ruff](https://docs.astral.sh/ruff/) — Python linter and formatter
- [ShellCheck](https://www.shellcheck.net/) — shell-script linter (`tools/*/*.sh`)
- [pytest](https://docs.pytest.org/) — Python test framework
- [pytest-benchmark](https://pytest-benchmark.readthedocs.io/) — microbenchmark harness (SPEC-018)
- [tomllib](https://docs.python.org/3/library/tomllib.html) — TOML parsing (Python 3.11+ stdlib)
- [Flask](https://flask.palletsprojects.com/) — web framework (server-rendered Jinja UI)
- [gunicorn](https://gunicorn.org/) — WSGI server for production deployment

## Infrastructure

- [Virtual Machine Manager (virt-manager)](https://virt-manager.org/) — VM host UI
- [libvirt / QEMU / KVM](https://libvirt.org/) — VM backend
- [DigitalOcean](https://www.digitalocean.com/) — production droplet host
- [OpenTofu](https://opentofu.org/) — IaC provisioning (`infra/tofu/`)
- [Ansible](https://docs.ansible.com/) — droplet configuration management (`ansible/`)
- [ansible.posix](https://docs.ansible.com/ansible/latest/collections/ansible/posix/) — `synchronize`/`authorized_key` modules
- [Caddy](https://caddyserver.com/) — reverse proxy and automatic TLS
- [xcaddy](https://github.com/caddyserver/xcaddy) — builds the custom Caddy binary with plugins
- [caddy-ratelimit](https://github.com/mholt/caddy-ratelimit) — per-IP rate limiting plugin
- [requests](https://requests.readthedocs.io/) — HTTP client for the acceptance test suite (`tests/acceptance/`)

## Design document schemas

- `design/decisions/_schema.toml` — DD schema (id pattern `DD-\d{4}`)
- `design/reqs/_schema.toml` — REQ schema (id pattern `REQ-(FUN|OPS|SEC)-\d{3}`)
- `design/specs/_schema.toml` — SPEC schema (id pattern `SPEC-\d{3}`)

## Standards

- [TOML v1.0](https://toml.io/en/) — design document format
- [EditorConfig](https://editorconfig.org/) — cross-editor formatting consistency
- [MIT License](https://opensource.org/licenses/MIT)

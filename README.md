# sask

Umbrella project for the Saskan calendar engine and related tools.
This repository is a deliberate evolutionary rebuild: lean scaffolding first,
functional areas added incrementally under `/src`.

## Quick start

**Prerequisites:** Ubuntu 26.04 LTS (or Debian-style Linux). See
[docs/dev-setup.md](docs/dev-setup.md) for the full procedure.

```bash
git clone https://github.com/genuinemerit/sask.git
cd sask
bash tools/dev/init-dev-host.sh   # apt prereqs, pyenv, Python 3.12, Poetry
poetry install
```

Verify:

```bash
python --version    # 3.12.x (pyenv-pinned; system python3 is 3.14, untouched)
poetry --version
```

## Layout

```text
ansible/      Ansible playbooks deploying the app onto the production droplet
config/       TOML engine configuration (time constants, calendars, seasons, timeline)
design/       TOML design docs (decisions/, reqs/, specs/)
docs/         living documents and guides
infra/        infra/archive/ (retired NixOS artifacts) and infra/tofu/ (production droplet IaC)
assets/       local (dev/artist staging) + versioned (v0, deploy-ready) binary assets — see DD-0016
secrets/      local credentials — git-ignored except README.md and *.example
src/          Python source (package: sask)
tests/        pytest suites and test results
tools/        developer tooling and deploy orchestration (see docs/deploy-runbook.md)
```

## Web app

Five browser pages are available locally or live at
[sask.davidstitt.net](https://sask.davidstitt.net).

| Page | Description |
|---|---|
| `/` | Pulse lookup — enter a pulse and see Astro day, time of day, orbital position |
| `/moons` | Moons sky view — phase, illumination, albedo, eclipse, altitude/azimuth, rise/transit/set for all 8 moons |
| `/planets` | Planets sky view — same columns plus colour, brightness, and telescopic detail for all 7 planets |
| `/sky` | Unified sky for a date — lunar calendars, moons and wanderers above horizon, |
| | co-fullness, season, fixed stars and houses, night summary, image prompt; |
| | lore overlay: watch/shur/keyt time and era/Round/phase calendar dates |
| `/ephemeris` | Ephemeris generator — time-series of sky scenes at a configurable step; |
| | scribal and/or kinematic JSON preview with download links |

All pages accept four equivalent input forms: pulse number, Astro day,
Fatunik date, or Terpin date. After any query all four input fields are
cross-populated with the resolved equivalents. The `/ephemeris` page also
accepts a Duration (Days) field for date-mode ranges.

**Start the server:**

```bash
bash tools/dev/start_web.sh
```

Or manually (flask dev server):

```bash
PYTHONPATH=src poetry run flask --app sask.web run
```

Or with gunicorn:

```bash
PYTHONPATH=src poetry run gunicorn wsgi:app
```

## Pre-commit checks

Run before every commit; all checks must exit 0:

```bash
bash tools/dev/pre-commit-check.sh
```

## Testing

```bash
bash tools/dev/run-tests.sh                           # all tests, quiet
bash tools/dev/run-tests.sh -v                        # all tests, verbose
bash tools/dev/run-tests.sh --spec SPEC-002           # one spec, quiet
bash tools/dev/run-tests.sh --spec SPEC-002 -v --save # one spec, verbose, save results
```

## Design docs

Design decisions, requirements, and specs live under `/design` as TOML.
Validate them with:

```bash
python3 tools/dev/validate_specs.py
```

## Development environment

See [docs/dev-setup.md](docs/dev-setup.md) for the from-scratch Ubuntu setup.
Python is pinned to 3.12 via pyenv; all tooling is managed by Poetry.
`tools/dev/init-dev-host.sh` is the single-command system bootstrap.

## Deployment

The app runs live on a DigitalOcean droplet at
[sask.davidstitt.net](https://sask.davidstitt.net), provisioned with
OpenTofu (`infra/tofu/`) and configured with Ansible (`ansible/`). See
[docs/deploy-runbook.md](docs/deploy-runbook.md) for day-to-day operation
(connect, redeploy, full rebuild, full teardown) and
[design/decisions/dd-0014-deploy.toml](design/decisions/dd-0014-deploy.toml)
for the design.

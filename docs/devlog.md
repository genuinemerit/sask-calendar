# Dev log

## 2026-06-05 — SPEC-009 UAT: all tests pass; refactoring complete

**SPEC-009 UAT complete** — all 15 test cases pass (TC-009-01 through TC-009-13,
plus TC-009-07b and TC-009-11c added during the session). 298 tests total.

**Spec corrections surfaced by UAT:**

- *Endor eclipse (TC-009-03):* At pulse 0, Endor's synodic fraction (0.4778) is
  0.022 from opposition — within the 0.03 syzygy tolerance — and its ecliptic
  latitude is ≈ 0.27°, within the 0.8° node tolerance. Both conditions met →
  Lunar eclipse correctly fires. The original spec said "no eclipse"; the spec
  was wrong.
- *Zehembra illumination (TC-009-03):* `(1 − cos(2π × 0.823134)) / 2 ≈ 27.8%`,
  not 29.3% as the spec stated. The test doc contained a hand-calculation error.

**Bug fix — empty form fields (TC-009-06):**

All three fieldsets shared one `<form>`, so clicking any Query button submitted
all fields. Empty fields arrived as `""` (not absent), causing `float("")` to
raise ValueError and return an error instead of falling through to the intended
input type. Fixed with `or None` on every `request.args.get()` call in
`_resolve_pulse`.

**Input improvements:**

- Forms split into **four separate `<form>` elements** (one per fieldset); each
  Query button now submits only its own fields.
- **Terpin date input** added to `/moons` and `/planets` (priority chain: pulse
  \> astro\_day \> fatunik date \> terpin date).
- After any successful query, **all four input groups are cross-populated** with
  equivalent values (pulse, Astro day, Fatunik date, Terpin date) so the user
  can immediately re-query from any calendar system.
- Meta line above the results table simplified to show only Fatune horizon
  status; date equivalents are now visible in the populated input fields.

**Display improvements:**

- Removed duplicate illumination % from the Visible column (was shown in both
  Lit and Visible; kept only in Lit).
- Planets table restructured to a **two-row layout** per planet: main row
  (11 columns: name, colour, phase, lit, visible, altitude, azimuth,
  rise/transit/set, brightness) + light-grey detail row (spans full width:
  "Through a glass" | "Notes"). Eliminates the compressed Notes column of the
  previous 13-column single-row layout.
- "Through a glass" empty state now distinguishes: *"Appears as a plain disc;
  no notable features."* (visible, no rings/moons) vs *"Not currently
  visible."* (lost in glare). Previously showed a bare `—`.

**Design note — short-month date overflow (future consideration):**

Entering a day beyond the festival month's actual length (e.g., month=1, day=10
on a standard Fatunik year where the festival has only 5 days) silently overflows
into month 2. This is arithmetically consistent — both `fatunik_to_pulse` and
`terpin_to_pulse` use the correct festival-day count for the given year type
(standard / long / super-long). Marked for a future spec: add explicit validation
that rejects out-of-range festival-month day values with a user-visible error.

---

## 2026-06-04 — SPEC-006 through SPEC-009: orbital mechanics and sky UI

**SPEC-006** (26 tests) — Frozen orbital initial conditions committed to
`config/body_data.toml` for all 8 moons and 7 planets: epoch offset, sidereal
period, inclination, node, diameter, albedo, distance/semi-major axis.
Design docs DD-0004, REQ-FUN-010–014, SPEC-006–009 added.

**SPEC-007** (42 tests) — Body kinematics engine (`src/sask/bodies.py`):
sidereal/synodic fractions, ecliptic coordinates, illuminated fraction
(`(1−cosθ)/2` for moons; law-of-cosines phase angle for planets), visibility
scalar, eclipse detection (node-gated syzygy within configurable tolerances),
`BodyState` message unit, `all_body_states()`.

**SPEC-008** (26 tests) — Local-sky position engine (`src/sask/sky.py`):
ecliptic→equatorial→horizontal coordinate transform, rise/transit/set pulse
arithmetic, circumpolar/never-rising edge cases, Fatune sky position,
`SkyPosition` message unit, `all_sky_positions()`.

**SPEC-009** (48 tests) — Web UI for `/moons` and `/planets` pages:
`MoonViewModel`, `PlanetViewModel` and translators in `translator.py`;
routes in `routes.py`; Jinja templates (`moons.html`, `planets.html`);
eclipse row highlighting (solar = amber, lunar = blue); lore overlay
(apparent colour, ring description, visible moons, notes) layered at
the route, not in the engine.

**Calendar epoch corrections (same session):**

- Astro epoch: year 0, spring equinox, pulse 0 (midnight).
- Fatunik epoch: Astro year 1531, summer solstice, 6 AM → `epoch_astro_day = 559278`.
- Terpin epoch: Astro year 1043, spring equinox → `epoch_astro_day = 380948`.
- `story_now` locked to Astro year 3313, spring equinox; pulse = 104548096103
  → Fatunik T1782 M10 D29; Terpin T2271 M2 D2; season: Stillness / near Green Day.

252 tests total at end of this session.

---

## 2026-06-02 — SPEC-003 + SPEC-004: calendar conversions and seasonal context

**SPEC-003** (59 tests) — Astro↔Fatunik and Astro↔Terpin translators in
`src/sask/pulse.py`: `astro_to_fatunik`, `fatunik_to_pulse`,
`fatunik_turns_to_pulse_range`, `astro_to_terpin`, `terpin_to_pulse`,
`terpin_shell_of_turn`, `terpin_turn_within_shell`. Leap arithmetic for both
calendars (Fatunik long/super-long years; Terpin long years).

**SPEC-004** (25 tests) — Seasonal context (`src/sask/season.py`):
`SeasonInfo` message unit, `season_info()` — maps orbital position to one of
four seasons (Greening, Blazing, Harvest, Stillness) and detects proximity to
solstice/equinox events (Green Day, Blaze Day, Golden Day, Still Day).

UAT run as a Python REPL session on the VM; all TC-003-xx and TC-004-xx pass.
Results recorded in `tests/results/user_tests/`.

157 tests total (14 validate\_specs + 46 SPEC-002 + 13 SPEC-005 + 59 SPEC-003 + 25 SPEC-004).

---

## 2026-06-02 — SPEC-005: Flask UI thin vertical slice

**SPEC-005 implemented** — 12 tests, all pass (72 total):

- `src/sask/web/__init__.py` — `create_app()` factory; config loaded once, stored in
  `app.config`; template folder resolved relative to `__file__`
- `src/sask/web/routes.py` — `GET /?pulse=<n>`; float input rounded; errors rendered
  in-page
- `src/sask/web/translator.py` — `PulseViewModel` dataclass + `to_pulse_view()`; formats
  `day_pulse_offset` as `HH:MM:SS`, orbital position as `25.0000%`
- `src/sask/templates/base.html`, `index.html` — server-rendered Jinja, no JavaScript
- `wsgi.py` — gunicorn entry point at project root
- `pyproject.toml` — added `flask >= 3.0` and `gunicorn >= 22.0` runtime dependencies
- `tests/test_spec_005.py` — HTTP smoke, float rounding, error path, no-script, and
  AST layer-purity checks (engine files must not import flask)

Also in this session: `pulse_of_day` renamed to `day_pulse_offset` throughout
(`message.py`, `pulse.py`, `test_spec_002.py`).

**Next:** SPEC-003 (solar calendar conversions) + SPEC-004 (seasons).

## 2026-06-02 — SPEC-002: pulse/day core and config foundation

**Design documents added** (DD-0002, DD-0003, REQ-FUN-001–005, REQ-OPS-006–009,
SPEC-002–005, `docs/glossary.md`):

- DD-0002 — calendar engine architecture: pure functions over pulse + config, astronomy/civil
  separation, normalised [0,1) quantities, apparition model, message units
- DD-0003 — presentation architecture: Flask/Jinja in-process, message-unit seam, API-ready
- REQs and SPECs cover pulse core, solar calendars, seasons, and UI thin vertical slice

**SPEC-002 implemented** — 46 tests, all pass:

- `config/` — `time_constants.toml`, `calendars.toml` (astro, fatunik, terpin),
  `seasons.toml`, `timeline.toml`
- `src/sask/message.py` — frozen dataclasses: `PulseInfo`, `CalendarDate`, `SeasonInfo`
- `src/sask/config_loader.py` — typed config dataclasses, `load_config()`, `ConfigError`
- `src/sask/pulse.py` — `astro_day()`, `day_pulse_offset()`, `orbital_position()`,
  `civil_day()`, `pulse_info()`; translator stubs for SPEC-003
- `tests/test_spec_002.py` — signed pulse arithmetic, orbital position, day-start offset,
  config loading and validation
- `pyproject.toml` — added `pythonpath = ["src"]` for pytest

**Tooling:**

- `scripts/` removed; `tools/pre-commit-check.sh` and `tools/run-tests.sh` added
- `ruff` scope extended to `src/`; all 5 pre-commit checks pass
- 60 tests total: 14 validate_specs + 46 SPEC-002

Corrections applied during pre-commit: DD IDs fixed to 4-digit form; REQ schema
extended with `FUN` category; `rationale` added to all 9 new REQ docs; glossary
line lengths fixed.

**Next:** SPEC-005 (Flask UI thin vertical slice), then SPEC-003 + SPEC-004.

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

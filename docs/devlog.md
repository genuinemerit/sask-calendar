# Dev log

## 2026-06-14 — SPEC-017: UAT complete (all 10 TCs pass)

**SPEC-017 UAT passed** (all 10 test cases — TC-017-01 through TC-017-10).

Lore overlay display confirmed correct in the browser for story_now pulse:
watch/shur/keyt for Fatunik and Terpin; era-based lore dates for fatunik_solar
and terpin_solar; phase-quarter dates for untamed, warren, and terpin_lunar;
ordinal day/turning for hearth. One minor refinement during UAT: hearth day and
turning count now rendered as ordinals (e.g., "1st", "51st").

**Next:** performance testing, packaging, Digital Ocean deployment.

## 2026-06-14 — SPEC-017: lore overlays — dev complete, awaiting UAT

Implemented lore overlay renderers (`src/sask/lore.py`) with 21 passing unit
tests. Pre-commit checks pass.

**Deliverables:**

- `config/lore_time.toml` — `enabled = true` added to `[display]`; unchanged otherwise.
- `src/sask/config_loader.py` — four new frozen dataclasses (`LoreAge`,
  `LoreCulture`, `LoreTimeConfig`, `CalendarLoreConfig`) plus `_load_lore_time()`
  and `_load_calendar_lore()` loaders; `AppConfig` updated with `lore_time` and
  `lore_calendars` fields; `load_config()` reads all six calendar TOML files.
- `src/sask/lore.py` — `render_lore_time(pulse, culture, config)`,
  `render_lore_date(technical_date, calendar_id, config)`, and
  `apply_lore_overlay(scribal_record, culture, calendar_id, config)`.
- `src/sask/web/routes.py` — sky() route computes Fatunik/Terpin lore times and
  solar/lunar lore dates when `cfg.lore_time.enabled`; passes all to template.
- `src/sask/templates/sky.html` — "Lore Overlay" section added (inside
  `{% if lore_enabled %}`), showing time and date for all 6 calendars.
- `tests/test_spec_017.py` — 21 tests covering config loading, `render_lore_time`
  (two cultures, boundary wrap, invalid culture), `render_lore_date` (all 6
  calendar types, festival month, age boundary), and `apply_lore_overlay`
  (presence, immutability, determinism).
- `design/specs/spec-017-calendar-rendering.toml` — status updated to "accepted".

**Next:** UAT — load `/sky` for story_now and verify the Lore Overlay section.

## 2026-06-14 — SPEC-016: UAT complete; form refactoring and validation additions

**SPEC-016 UAT passed** (all 16 test cases — TC-016-01 through TC-016-16).

Changes made during UAT that preceded commit (all tested and passing — 35 tests total):

**Form refactoring:**

- Input groups reorganised by type: Pulse fieldset (explicit start + end); Astro Day,
  Fatunik Date, Terpin Date fieldsets (start only; end computed from Duration).
- **Duration (Days)** replaces explicit end-date inputs for date modes (end = start + days × 86400).
- **Reset button** implemented as `<a href="/ephemeris">` (navigates to clean URL,
  clearing all fields); `<button type="reset">` was unusable because it restores to
  rendered values (which are the query-param values), not to empty.
- Computed end displayed inline to the right of the start time in each date fieldset
  (`End: [value] · HH:MM:SS`), rather than in a separate paragraph.
- All input types cross-populated after Generate regardless of which input type was used
  to specify the start (removed `and pulse_mode` guard from Pulse fieldset value attributes).

**Validation additions:**

- **Step ≥ duration** check: if `step_pulses >= (end_pulse - start_pulse)` the route
  returns a form error (200) and the download endpoint returns 400. The engine itself
  (SPEC-015) is unchanged — it correctly returns 1 step for this case; the web layer
  refuses it as a non-useful request. TC-016-16 covers this.
- **Range cap raised from 7 days to 30 days** (`range_cap_pulses`: 604800 → 2592000).
  Maximum request size is 8640 records at 5-minute intervals for 30 days. Error message
  in `ephemeris.py` updated accordingly. `test_range_at_cap_is_accepted` in
  test_spec_016.py now uses a 1-day step to keep CI fast (30 scenes vs 8640).
- Duration input `max` attribute updated to `30` in the template.

**Test counts:** 35 (test_spec_016.py); 64 combined with test_spec_015.py; 558 total.

---

## 2026-06-13 — SPEC-016: ephemeris web page and regen-on-download export

**SPEC-016 implemented** (26 new tests; 26 pass; UAT required before commit):

- `src/sask/web/routes.py` — two new routes:
  - `_resolve_endpoint(prefix, cfg)`: like `_resolve_pulse` but with prefixed query
    param names, allowing independent start/end endpoint resolution using all four
    input forms (pulse / Astro day / Fatunik date / Terpin date).
  - `GET /ephemeris`: form accepts start, end, step (minutes), and profile
    (scribal / kinematic / both). Generates a preview (first 5 steps) and passes
    scribal/kinematic JSON to the template as a `<pre>` block. Download links carry
    all parameters in the query string.
  - `GET /ephemeris/download`: reads start/end/step/profile from query string as raw
    pulses; validates throttle; regenerates JSON; returns as `attachment` with filename
    `ephemeris_{profile}_p{start}-{end}_s{step}.json`. No temp file written.
- `src/sask/templates/ephemeris.html` — server-rendered only (no JavaScript). GET
  form with all four input forms for start and end; step minutes; profile selector;
  truncated preview per profile in a scrollable `<pre>` box; download link(s).
- `src/sask/templates/base.html` — "Ephemeris" nav link added.
- `tests/test_spec_016.py` — 26 tests covering HTTP smoke, preview rendering,
  throttle validation, download headers, determinism, and JSON structure.
- SPEC-016 design doc status: `proposed` → `accepted`.

UAT: [manual] load `/ephemeris` in a browser; submit a valid range; inspect the
preview; click each download link; verify the file saves correctly.

---

## 2026-06-13 — SPEC-015: sky-scene ephemeris generator and JSON renderers

**Phase 0 — Design doc housekeeping (same session):**

- DD-0009, DD-0010, REQ-FUN-010/011, SPEC-015–017 authored and validated.
- `dd-0010-caelndar-rending.toml` renamed to `dd-0010-calendar-rendering.toml`.
- SPEC-017 deliverable paths corrected from `config/lore/` to `config/` (flat layout).
- Nine new config files committed: `ephemeris_data.toml` (required by SPEC-015);
  `lore_time.toml`, `calendar_lore_template.toml`, and six per-calendar lore overlay
  files (`fatunik_solar`, `terpin_solar`, `terpin_lunar`, `untamed`, `warren`, `hearth`)
  — authored, pending SPEC-017 implementation.

**SPEC-015 implemented** (29 tests, 523 total — no UAT gate; backend-only spec):

- `src/sask/config_loader.py` — `EphemerisConfig` dataclass (step floor, range cap,
  tracked bodies); `_load_ephemeris_data()`; `AppConfig` extended with `ephemeris`.
- `src/sask/ephemeris.py` — new module:
  - `get_sky_series(start, end, step, config)`: validates throttle (step ≥ 300 pulses /
    5 min; range ≤ 604,800 pulses / 7 days), iterates `get_sky_scene()` at each pulse,
    computes per-day context (season, body rise/transit/set) once per distinct Astro day.
    Returns `EphemerisSeries`. Pure and deterministic.
  - `render_scribal_json(series, config)`: readable per-step record — pulse, Astro day,
    time-of-day (HH:MM:SS), bodies above horizon, stars, active house, co-fullness,
    prose summary. No Fatunik, Terpin, or lore terms.
  - `render_kinematic_json(series, config)`: compact per-body alt/az, illumination, and
    above-horizon flag for all 15 tracked bodies including below-horizon positions (for
    smooth animation arcs).

---

## 2026-06-11 — SPEC-014: UAT complete (all 20 TCs pass)

UAT surfaced several corrections applied before sign-off:

- **Day-start times:** Removed the 2 AM deep-night snap. Fatunik date input
  now resolves to 06:00:00 (Fatunik day-start offset); Terpin and Astro day
  to 00:00:00. Time of day displayed inline next to the Astro Day query button
  on both `/sky` and `/moons`.
- **Layout:** Removed redundant "Date & Time" panel; Co-fullness moved
  immediately below Moons Above Horizon; Season moved above Fixed Stars.
- **Visibility consistency:** Bodies above horizon now require both
  `above_horizon` and `is_visible` (illumination threshold) everywhere —
  fixed in `scene.py` bodies_up filter and `translator.py` view models.
- **Brightness:** Changed observer-facing brightness from
  `albedo × illuminated_fraction × apparent_size` (always near zero, always
  "Dim") to `albedo × illuminated_fraction`. Re-calibrated labels:
  Brilliant ≥ 0.32, Bright ≥ 0.20, Moderate ≥ 0.10, Faint ≥ 0.04, Dim.
  Albedo column added to `/moons` table.
- **Near-full definition corrected:** Replaced time-based tolerance
  (`full_tolerance_days / T_syn`) with illumination-based threshold
  (`illuminated_fraction >= 0.90`). Slow moons like Endor (T_syn = 37 d)
  were excluded despite looking full to any observer; the new definition
  treats all moons the same way a medieval observer would. Config key renamed
  `full_tolerance_days` → `full_illumination_threshold`.
- **Co-fullness wording:** "Tonight" → "This day" throughout; window broadened
  from single midnight to full Astro day; `observable` flag added to
  `CofullnessTonightRef`; "(below the horizon throughout this day)" note shown
  when no near-full moon rises during the day.
- **Cosmetic:** Moon names capitalised in Lunar Calendars and Co-fullness
  sections; Terpin "mean" label left lower-case.

---

## 2026-06-10 — SPEC-014: unified sky-for-a-date web view

**SPEC-014 implemented** (31 tests, 494 total — unit tests complete; UAT pending):

- `src/sask/web/routes.py` — new `/sky` route: accepts pulse, Astro day,
  Fatunik date, or Terpin date; resolves to calendar day-start time; computes
  all date equivalents (Fatunik, Terpin, 4 lunar calendars), season, full sky
  scene, night summary, and image prompt.
- `src/sask/templates/sky.html` — single server-rendered page with panels for:
  Lunar Calendars (display-only), Moons above the horizon (linked to /moons),
  Co-fullness this day and next, Wanderers (linked to /planets), Comets &
  the Spark (when visible), Season, Fixed Stars & Houses, Night Summary,
  Image Prompt.
- `src/sask/templates/base.html` — Sky nav link added.
- No JavaScript; pulse rides in query string for bookmarking; date inputs
  cross-populate to show the resolved pulse.

---

## 2026-06-10 — SPEC-013: sky-scene composition and text rendering

**SPEC-013 implemented** (27 tests, 463 total):

- `config/sky_style_data.toml` — already authored; loaded into `AppConfig`
  via `SkyStyleConfig` and `SkyStyleSettings` dataclasses.
- `src/sask/config_loader.py` — `SkyStyleConfig`, `SkyStyleSettings`;
  `_load_sky_styles()` (validates default_style exists); `AppConfig` extended.
- `src/sask/message.py` — `BodyInScene`, `StarInScene`, `HouseRef`,
  `CofullnessTonightRef`, `NextCofullnessRef`, `SkyScene` message units.
  `validate()` improved to skip `X | None` fields (Optional sentinel pattern).
- `src/sask/scene.py` — new module: `get_sky_scene(pulse, config)` composes
  the full scene from all existing engine surfaces (SPEC-004/007/008/010/011/012);
  `render_night_summary(scene, config)` produces deterministic plain prose;
  `render_image_prompt(scene, config, style_id=None)` appends the selected
  style's medium/palette/composition/extra directives. No network call; no Flask.

---

## 2026-06-10 — SPEC-012: lunar calendars and co-fullness tracking

**SPEC-012 implemented** (60 tests, 436 total):

- `config/lunar_calendar_data.toml` / `config/cofullness_data.toml` — already
  authored; now loaded into `AppConfig` via new dataclasses.
- `src/sask/config_loader.py` — `LunarCalendarConfig`, `LunarCalendarSettings`,
  `CofullnessConfig` dataclasses; `_load_lunar_calendar_entry`,
  `_load_lunar_calendars` (expects exactly 4 `[[calendar]]` entries),
  `_load_cofullness`; `AppConfig` extended with `lunar_calendars`,
  `lunar_settings`, `cofullness`.
- `src/sask/message.py` — `LunarDate` and `CofullnessEvent` message units.
- `src/sask/lunar.py` — new module: `_synodic_period_days` (T_syn =
  1/(1/T_sid − 1/AstroYear); "mean" = arithmetic mean of all 8 moons);
  `_epoch_pulse` (fatunik or terpin anchor + offset); `get_lunar_date`
  (lunation, day, month, turn, short_count, long_count); `_round_turns_for`
  (smallest K turns realigning with AstroYear within tolerance, lru_cached);
  `near_full` (synodic phase within full_tolerance_days of opposition);
  `get_cofullness` (all midnight pulses in range with ≥ min_moons near-full).
  No Flask imports; no civil-calendar leap arithmetic.
- Four calendars: Untamed/Sella (12 months/turn, fatunik anchor);
  Warren/Shunna (21 months/turn); Hearth/Jembor (no-turns, lunation+day only);
  Terpin Lunar/mean (12 months/turn, terpin anchor).

---

## 2026-06-10 — SPEC-011: apparitions — recurring comets and the Spark

**SPEC-011 implemented** (43 tests, 376 total):

- `config/comet_data.toml` / `config/spark_data.toml` — already authored; now
  loaded into `AppConfig` via `CometConfig` and `SparkConfig` dataclasses.
- `src/sask/config_loader.py` — `CometConfig`, `SparkConfig` dataclasses;
  `_load_comets()` (expects exactly 3 `[[comet]]` entries), `_load_spark()`
  (singleton `[spark]` table); `AppConfig` extended with `comets` and `spark`.
- `src/sask/message.py` — `CometInfo`, `SparkInfo`, `ApparitionContext`
  message units.
- `src/sask/apparitions.py` — `get_apparitions(pulse, config)`: comet
  visibility from `perihelion_n = (n + epoch_offset) * period_pulses`, linear
  ramp to 0 at window edge; Spark via `_seeded_float(event_idx, salt)` — sha256
  hash over Kanka's 38-day rotation events, glimmer_probability 0.01,
  seeded exposure in [0.5, 3.0] days. No live RNG; fully reproducible.

---

## 2026-06-10 — SPEC-010: fixed stars and Houses of the Equinox

**Design work (all accepted):** DD-0005 (stars/houses), DD-0006 (apparitions),
DD-0007 (lunar calendars), DD-0008 (unified sky view); REQ-FUN-007/008/009;
SPEC-010–014. Config files added for all five upcoming specs.

**SPEC-010 implemented** (35 tests, 333 total):

- `config/star_data.toml` / `config/house_data.toml` — 16 fixed stars and 14
  Houses of the Equinox. Both files reformatted to valid TOML (original drafts
  used invalid semicolon-separated key-value pairs).
- `src/sask/config_loader.py` — `FixedStarConfig`, `HouseConfig`,
  `HouseNamingConfig` dataclasses; loaders; `AppConfig` extended.
- `src/sask/message.py` — `HouseInfo`, `FixedStarInfo`, `StarContext` message
  units.
- `src/sask/stars.py` — `get_star_context(pulse, config)`: active house from
  sidereal-arc placement (`HOUSE_ARC_OFFSET = 0.125`; season points fall
  mid-group: spring equinox → house 11, solstices/equinoxes → houses 2/5/8);
  visible stars = 4 perennial + 3 seasonal; 2 circumpolar houses always
  present. No civil-calendar config consulted.

---

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

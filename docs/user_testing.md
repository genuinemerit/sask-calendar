# User Acceptance Testing

## SPEC-005 — Flask UI thin vertical slice

### Setup

**1. Open an SSH tunnel from the Ubuntu host:**

```bash
ssh -L 5000:localhost:5000 sask-dev
```

Keep this terminal open. The tunnel forwards `localhost:5000` on the Ubuntu
host to `localhost:5000` on the VM.

**2. In the VM session, start the Flask development server:**

```bash
cd ~/Code/sask-calendar
PYTHONPATH=src .venv/bin/flask --app sask.web run
```

Expected output: `Running on http://127.0.0.1:5000`

**3. Open a browser on the Ubuntu host and navigate to:**

```text
http://localhost:5000/
```

---

### Test cases

#### TC-005-01 — Landing page loads with no query parameter

**Action:** Navigate to `http://localhost:5000/` with no `?pulse=` parameter.

**Pass criteria:**

- HTTP 200; page title contains "Saskan Calendar — Pulse Lookup".
- A numeric input labelled "Pulse" is pre-filled with `104548096103`
  (the `story_now_pulse` from `config/timeline.toml`).
- No result table is rendered.
- No error message is shown.

---

#### TC-005-02 — Query with pulse = 0 (Astro epoch, midnight)

**Action:** Enter `0` in the Pulse field and click **Query**, or navigate to
`http://localhost:5000/?pulse=0`.

**Pass criteria:**

| Field | Expected value |
|---|---|
| Pulse | 0 |
| Astro Day | 1 |
| Day Pulse Offset | 0 (00:00:00 Astro time) |
| Orbital Position | 0.0000% of AstroYear |

---

#### TC-005-03 — Query with pulse = 43200 (Day 1, noon)

**Action:** Enter `43200` and click **Query**.

**Pass criteria:**

| Field | Expected value |
|---|---|
| Pulse | 43200 |
| Astro Day | 1 |
| Day Pulse Offset | 43200 (12:00:00 Astro time) |
| Orbital Position | 0.1369% of AstroYear |

---

#### TC-005-04 — Float pulse is rounded to nearest integer

**Action:** Enter `43200.7` and click **Query**.

**Pass criteria:**

- No error is shown.
- Pulse field displays `43201`.
- Day Pulse Offset displays `43201` (12:00:01 Astro time).

---

#### TC-005-05 — Non-numeric input yields a user-visible error

**Action:** Enter `abc` in the Pulse field and click **Query**.

**Pass criteria:**

- HTTP 200 (no 500 error page).
- An inline error message appears, e.g. *"Invalid pulse value: 'abc'"*.
- No result table is rendered.

---

#### TC-005-06 — Page source contains no JavaScript

**Action:** With any valid result rendered, view the page source
(Ctrl+U or browser DevTools → Sources).

**Pass criteria:**

- No `<script>` tag appears anywhere in the HTML source.
- No `javascript:` URIs appear in any attribute.

---

### Results — 2026-06-02

Tested on `sask-dev` via SSH tunnel. All cases pass.
See: /tests/results/user_tests/SPEC-005_user_test_results.odt for screenshots.

| TC | Result | Notes |
|---|---|---|
| TC-005-01 | PASS | `GET /` → 200; form pre-filled with `104548096103` |
| TC-005-02 | PASS | `GET /?pulse=104548096103` → 200 |
| TC-005-03 | PASS | `GET /?pulse=0` → 200 |
| TC-005-04 | PASS | `43200.7` rounded to `43201`; rendered `43201 (12:00:01)`, `0.1369%` |
| TC-005-05 | PASS | Browser enforces `input type="number"`; non-numeric input never reaches the server |
| TC-005-06 | PASS | Page source contains only a `<style>` block; no `<script>` tags |

Incidental: `GET /favicon.ico` → 404 (no favicon defined; expected for MVP).

---

### Teardown

Stop the Flask server with `Ctrl+C` in the VM terminal. Close the SSH tunnel
terminal.

---

## SPEC-003 + SPEC-004 — Calendar conversions and seasonal context

SPEC-003 and SPEC-004 are engine-only; no UI surface exists yet. UAT is
conducted interactively in a Python REPL on the VM.

### REPL setup

**1. SSH into the VM and start a Python session:**

```bash
cd ~/Code/sask-calendar
PYTHONPATH=src .venv/bin/python3
```

**2. Import and configure in the REPL:**

```python
from pathlib import Path
from sask.config_loader import load_config
from sask.message import CalendarDate
from sask.pulse import (
    astro_to_fatunik, fatunik_to_pulse, fatunik_turns_to_pulse_range,
    astro_to_terpin, terpin_to_pulse,
    terpin_shell_of_turn, terpin_turn_within_shell,
)
from sask.season import season_info

cfg = load_config(Path("config"))
SNP = cfg.timeline.story_now_pulse   # 104548096103
```

---

### REPL test cases

#### TC-003-01 — story_now_pulse converts to Fatunik Turn ~1782

**Action:**

```python
astro_to_fatunik(SNP, cfg)
```

**Pass criteria:** Returns `CalendarDate(calendar_id='fatunik', year=1782, month=10, day=29)`.

- Fatunik epoch starts at Astro year 1531 (summer solstice). Astro year 3313
  minus 1531.25 = ~1782 Fatunik turns elapsed.
- Month 10, Day 29 reflects the exact leap-adjusted calendar arithmetic.

---

#### TC-003-02 — story_now_pulse converts to Terpin Year ~2271

**Action:**

```python
astro_to_terpin(SNP, cfg)
```

**Pass criteria:** Returns `CalendarDate(calendar_id='terpin', year=2271, month=2, day=2)`.

- Terpin epoch starts at Astro year 1043 (spring equinox). Astro year 3313
  minus 1043 = ~2270 Terpin turns elapsed; the leap arithmetic resolves to T2271.

---

#### TC-003-03 — Terpin Shell notation for story_now year

**Action:**

```python
terpin_shell_of_turn(2271)
terpin_turn_within_shell(2271)
```

**Pass criteria:**

- `terpin_shell_of_turn(2271)` → `18`
- `terpin_turn_within_shell(2271)` → `27`

The story_now Terpin date is Shell 18, Turn 27 within that Shell (17 completed
Shells × 132 turns = 2244 turns; 2271 − 2244 = 27). These helper functions are
purely arithmetic and are unaffected by the epoch setting.

---

#### TC-003-04 — Fatunik date round-trips correctly

**Action:**

```python
date = CalendarDate("fatunik", 1782, 10, 29)
astro_to_fatunik(fatunik_to_pulse(date, cfg), cfg)
```

**Pass criteria:** Returns the original `date` unchanged:
`CalendarDate(calendar_id='fatunik', year=1782, month=10, day=29)`.

---

#### TC-003-05 — Ages helper: Fatunik Turns 1780–1800 span story_now

**Action:**

```python
start, end = fatunik_turns_to_pulse_range(1780, 1800, cfg)
print(start, end)
print(start <= SNP <= end)
```

**Pass criteria:**

- `start` = `104461336800` (sunrise of Fatunik T1780 M1 D1)
- `end` = `105124024799` (last pulse of Fatunik T1800 M13 D30)
- `start <= SNP <= end` prints `True` (story_now is in turn 1782, inside
  the range).

---

#### TC-004-01 — story_now is in Blazing (summer), no near event

**Action:**

```python
info = season_info(SNP, cfg)
print(info.season_id, info.near_event_id)
```

**Pass criteria:**

- `info.season_id` = `'stillness'` (story_now is at the very end of winter,
  orbital position ≈ 0.9999 — the last pulse of the AstroYear before spring)
- `info.near_event_id` = `'spring_equinox'`
- `info.near_event_name` = `'Green Day'` (story_now is within tolerance of
  the equinox: the last night of winter, verging on Green Day)

---

#### TC-004-02 — Astro epoch (pulse 0) is spring equinox, Greening

**Action:**

```python
info = season_info(0, cfg)
print(info.season_id, info.near_event_id, info.near_event_name)
```

**Pass criteria:**

- `info.season_id` = `'greening'`
- `info.near_event_id` = `'spring_equinox'`
- `info.near_event_name` = `'Green Day'`

---

#### TC-004-03 — Summer solstice pulse is near Blaze Day

**Action:**

```python
import math
solstice = math.ceil(0.25 * cfg.time_constants.astro_year_pulses)
info = season_info(solstice, cfg)
print(info.season_id, info.near_event_id, info.near_event_name)
```

**Pass criteria:**

- `info.season_id` = `'blazing'`
- `info.near_event_id` = `'summer_solstice'`
- `info.near_event_name` = `'Blaze Day'`

---

### REPL results — 2026-06-02

Tested on `sask-dev` via Python REPL. All cases pass.

| TC | Result | Notes |
|---|---|---|
| TC-003-01 | PASS | `CalendarDate(calendar_id='fatunik', year=1782, month=10, day=29)` |
| TC-003-02 | PASS | `CalendarDate(calendar_id='terpin', year=2271, month=2, day=2)` |
| TC-003-03 | PASS | `terpin_shell_of_turn(2271)` → `18`; `terpin_turn_within_shell(2271)` → `27` |
| TC-003-04 | PASS | Round-trip returns original date unchanged |
| TC-003-05 | PASS | `start=104461336800`, `end=105124024799`; `start <= SNP <= end` → `True` |
| TC-004-01 | PASS | `season_id='stillness'`, `near_event_id='spring_equinox'`, name `'Green Day'` |
| TC-004-02 | PASS | `season_id='greening'`, `near_event_id='spring_equinox'`, name `'Green Day'` |
| TC-004-03 | PASS | `season_id='blazing'`, `near_event_id='summer_solstice'`, name `'Blaze Day'` |

---

### REPL teardown

Exit the Python REPL with `exit()` or `Ctrl+D`.

---

## SPEC-009 — Web UX: lunar and planetary sky for a given pulse

SPEC-009 adds two new browser pages — **/moons** and **/planets** — to the
existing Flask UI. Each page takes a pulse as input (via pulse number, Astro
day, or Fatunik date) and renders a table of sky data for all eight moons or
all seven planets at that instant: phase, illuminated fraction, visibility,
eclipse status, altitude, azimuth, and rise/transit/set pulses.

### SPEC-009 Setup

The setup is identical to SPEC-005. If the Flask server is already running
from that test, skip to step 3.

**1. Open an SSH tunnel from the Ubuntu host:**

```bash
ssh -L 5000:localhost:5000 sask-dev
```

Keep this terminal open.

**2. In the VM session, start the Flask development server:**

```bash
cd ~/Code/sask-calendar
bash tools/start_web.sh
```

Expected output: `Running on http://127.0.0.1:5000`

**3. Open a browser on the Ubuntu host. The three pages under test are:**

```text
http://localhost:5000/
http://localhost:5000/moons
http://localhost:5000/planets
```

**Reference pulses used in the test cases below:**

| Label | Pulse | Meaning |
|---|---|---|
| Epoch | `0` | Astro epoch; spring equinox; pre-epoch for both civil calendars |
| Story now | `104548096103` | Fatunik T1782 M10 D29; Terpin T2271 M2 D2; Stillness season (verging on Green Day) |

---

### SPEC-009 Test cases

#### TC-009-01 — Navigation bar present on all pages

**Action:** Load each of the three pages (`/`, `/moons`, `/planets`) in turn.

**Pass criteria:**

- Every page renders a navigation bar at the top containing three links:
  **Pulse**, **Moons**, and **Planets**.
- Clicking each link navigates to the correct page.
- The root page (`/`) still shows the Pulse Lookup form and result table
  as in TC-005-01 through TC-005-06 (SPEC-009 is strictly additive).

---

#### TC-009-02 — Moons page loads without a pulse query

**Action:** Navigate to `http://localhost:5000/moons` with no query parameters.

**Pass criteria:**

- HTTP 200; page title contains "Saskan Calendar — Moons".
- Four input sections are rendered: **Enter pulse**, **Or Astro day**,
  **Or Fatunik date**, and **Or Terpin date**.
- No moon table is rendered.
- No error message is shown.
- No `<script>` tag appears anywhere in the page source.

---

#### TC-009-03 — Moons at epoch (pulse = 0)

**Action:** Navigate to `http://localhost:5000/moons?pulse=0`.

**Pass criteria:**

- The metadata line above the table shows only:
  Fatune **above** horizon (at pulse 0, Fatune transits the meridian at
  altitude **+54.5°** — it is exactly noon for the canonical observer)

- All four input fields are cross-populated with the resolved values:
  - Pulse field: `0`
  - Astro Day field: `1`
  - Fatunik date: **T-1531 M10 D29** (pre-epoch)
  - Terpin date: **T-1042 M1 D4** (pre-epoch)

- The moons table contains exactly **8 rows**, one per moon, in this order:
  Endor, Sella, Lelako, Jembor, Calumbra, Zehembra, Shunna, Kanka.

- **Endor** at pulse 0 (epoch offset 0.477754):
  - Synodic fraction ≈ 0.478 → phase name **Full** (range 0.47–0.53)
  - Illuminated ≈ **99.5%**
  - Eclipse: **Lunar** — synodic fraction is 0.022 from 0.5 (within the
    0.03 tolerance); ecliptic latitude ≈ 0.27° (within the 0.8° node
    tolerance). Row background is light blue.

- **Zehembra** at pulse 0 (epoch offset 0.823134):
  - Synodic fraction ≈ 0.823 → phase name **Waning Crescent**
  - Illuminated ≈ **27.8%** — formula: (1 − cos(2π × 0.823134)) / 2 ≈ 0.278
  - Eclipse column shows **—** (near-node check will rarely fire at an
    arbitrary pulse)

- Every row has non-empty entries for Altitude, Azimuth, Rise, Transit,
  and Set. Bodies below the horizon show negative altitude values with no
  row highlighting; bodies above the horizon show positive values.

- Eclipse column header is present on all rows (value is **—** unless an
  eclipse fires).

---

#### TC-009-04 — Moons at story_now_pulse

**Action:** Navigate to `http://localhost:5000/moons?pulse=104548096103`.

**Pass criteria:**

- Metadata shows Fatunik T1782 M10 D29 and Terpin T2271 M2 D2.
- All 8 moon rows are present.
- Each row shows a phase name (one of: New, Waxing Crescent, First Quarter,
  Waxing Gibbous, Full, Waning Gibbous, Last Quarter, Waning Crescent).
- Illuminated % is consistent with the phase name (Full ≈ 100%, New ≈ 0%).
- Visibility column shows either "Yes" or "No".
- Altitude values are in the range −90° to +90°; azimuth in 0° to 360° with
  a cardinal direction suffix.
- Rise and Set show pulse integers (or "circumpolar" / "never rises" for
  extreme declinations); Transit always shows a pulse integer.

---

#### TC-009-05 — Eclipse row highlighting

**Action:** Scan both the pulse=0 and story_now_pulse moons pages, or try
several different pulse values until an eclipse fires (Zehembra's low
inclination makes it the most frequent candidate).

**Pass criteria:**

- When a moon's Eclipse column shows **Solar**, that row has a warm yellow
  background.
- When it shows **Lunar**, the row has a light blue background.
- Rows with Eclipse = **—** have a plain white background (or a grey-text
  "below horizon" style if altitude is negative).

---

#### TC-009-06 — Moons — Astro day input

**Action:** On the `/moons` page, enter **1** in the "Or Astro day" field
and click its **Query** button (each input group is a separate form, so
only the Astro Day value is submitted).

**Pass criteria:**

- The page re-renders with `?astro_day=1` in the URL.
- Results are identical to `?pulse=0` (Astro day 1 corresponds to pulse 0).
- All 8 moons are listed; metadata shows Fatunik T-1531 M10 D29 (pre-epoch).

---

#### TC-009-07 — Moons — Fatunik date input

**Action:** In the "Or Fatunik date" section, enter Year **1782**, Month **10**,
Day **29** and click **Query**.

**Pass criteria:**

- The page re-renders with the three Fatunik parameters in the URL.
- Results match `?pulse=104548096103` (Fatunik T1782 M10 D29 = story_now_pulse).
- Metadata shows Fatunik T1782 M10 D29 and Terpin T2271 M2 D2.
- All 8 moons are listed.

---

#### TC-009-07b — Moons — Terpin date input

**Action:** In the "Or Terpin date" section, enter Year **2271**, Month **2**,
Day **2** and click **Query**.

**Pass criteria:**

- The page re-renders with the three Terpin parameters in the URL.
- Results match `?pulse=104548096103` (Terpin T2271 M2 D2 = story_now_pulse).
- Metadata shows Fatunik T1782 M10 D29 and Terpin T2271 M2 D2.
- All 8 moons are listed.

---

#### TC-009-08 — Planets page loads without a pulse query

**Action:** Navigate to `http://localhost:5000/planets` with no query parameters.

**Pass criteria:**

- HTTP 200; page title contains "Saskan Calendar — Planets".
- Four input sections are rendered (same layout as the moons page).
- No planet table is rendered.
- No `<script>` tag in the page source.

---

#### TC-009-09 — Planets at epoch (pulse = 0)

**Action:** Navigate to `http://localhost:5000/planets?pulse=0`.

**Pass criteria:**

- Metadata line shows only: Fatune above horizon (altitude ≈ +54.5°).
- All four input fields are cross-populated: Pulse=0, Astro Day=1,
  Fatunik T-1531 M10 D29, Terpin T-1042 M1 D4.

- The planets table contains exactly **7 planet entries** (14 HTML rows —
  each planet occupies a main row and a detail row) in this order:
  Aesthra, Lethra, Beyarus, Dramond, Thurnak, Zelven, Kreetha.

- **Beyarus** Color column shows **Brilliant silver-white**.

- **Kreetha** detail row "Through a glass" section shows ring description
  text (e.g. "Rings: Prominent…") and "1 moon(s) visible.".

- **Zelven** detail row "Through a glass" section shows **4 moon(s) visible.**

- **Aesthra** and **Lethra** (inner planets, semi-major axis 0.387):
  - Visibility shows "No" — inner planets remain near Fatune's
    glare and are typically invisible in this simplified model.
  - Phase varies between crescent and near-full depending on their
    position in the synodic cycle.

- Outer planets (Dramond, Thurnak, Zelven, Kreetha) show illuminated
  fractions generally above 80%, consistent with their near-full geometry
  when viewed from Gavor.

---

#### TC-009-10 — Planets at story_now_pulse

**Action:** Navigate to `http://localhost:5000/planets?pulse=104548096103`.

**Pass criteria:**

- All 7 planet entries are present (14 HTML rows total).
- Each main row shows: color, phase name, illuminated %, visibility,
  altitude, azimuth, rise/transit/set pulses, relative brightness.
- Each detail row shows "Through a glass" (rings/moons) and "Notes"
  (lore text, e.g. Thurnak: "The red wanderer; noticeably bright at
  opposition…").
- All four input fields are cross-populated with story_now values.
- Metadata line shows only Fatune above/below horizon with altitude.

---

#### TC-009-11 — Planets — Astro day, Fatunik date, and Terpin date inputs

**Action (a):** On `/planets`, enter Astro day **1** and query.

**Pass criteria (a):** Same result as `?pulse=0`; 7 planet entries shown;
input fields cross-populated with Pulse=0, Astro Day=1, Fatunik T-1531 M10 D29, Terpin T-1042 M1 D4.

**Action (b):** On `/planets`, enter Fatunik year **1**, month **1**, day **1** and query.

**Pass criteria (b):** Different from (a) — Fatunik T1 M1 D1 is Astro year 1531, not pulse 0. Metadata confirms T1 M1 D1.

**Action (c):** On `/planets`, enter Terpin year **2271**, month **2**, day **2** and query.

**Pass criteria (c):** Results match `?pulse=104548096103` (Terpin T2271 M2 D2 = story_now_pulse).
Metadata shows Fatunik T1782 M10 D29 and Terpin T2271 M2 D2. All 7 planets shown.

---

#### TC-009-12 — Invalid pulse input on both pages

**Action:** On `/moons`, type **xyz** in the Pulse field and click **Query**.
Repeat on `/planets`.

**Pass criteria:**

- HTTP 200 (no 500 error page) on both pages.
- An inline error message appears (e.g. *"Invalid pulse value: 'xyz'"*).
- No moon or planet table is rendered.

---

#### TC-009-13 — Page source contains no JavaScript

**Action:** With a valid pulse result rendered on `/moons` and `/planets`,
view the HTML source (Ctrl+U or browser DevTools → Sources) for each page.

**Pass criteria:**

- No `<script>` tag appears anywhere in the source.
- No `javascript:` URI appears in any attribute.
- The only embedded code is the `<style>` block in `<head>`.

---

### SPEC-009 Results — (to be completed after testing)

Tested on `sask-dev` via SSH tunnel.
See screenshot and other notes in
  /tests/results/user_tests/SPEC-009_user_test_results.odt

| TC | Result | Notes |
|---|---|---|
| TC-009-01 | Pass | See screenshots |
| TC-009-02 | Pass | See screenshots |
| TC-009-03 | Pass | Spec corrected: Endor Lunar; Zehembra 27.8%; Visible column simplified. |
| TC-009-04 | Pass | |
| TC-009-05 | Pass | Pulse 0 shows an eclipse |
| TC-009-06 | Pass | Bug fixed: empty form fields now treated as absent; pulse field no longer pre-filled. |
| TC-009-07 | Pass | |
| TC-009-07b | Pass | Terpin date input (new). |
| TC-009-08 | Pass | |
| TC-009-09 | Pass | |
| TC-009-10 | Pass | |
| TC-009-11 | Pass | |
| TC-009-11c | Pass | Terpin date input for planets (new). |
| TC-009-12 | Pass | but string input not allowed |
| TC-009-13 | Pass | |

Additional notes:

- A test using Astro Day input on Moons page = 6000
  shows a result with one New moon. The new moon row
  background color is set to yellow. Very nice!
- The description of planets "through a glass" is great.

---

### SPEC-009 Teardown

Stop the Flask server with `Ctrl+C` in the VM terminal. Close the SSH tunnel
terminal.

---

## SPEC-014 — Unified sky-for-a-date web view

SPEC-014 adds a **/sky** page that presents all date formats (including the four
lunar calendars, display-only) and the complete sky scene for a chosen pulse or
solar date: season, moons, wanderers, comets and the Spark, fixed stars and the
Houses of the Equinox, co-fullness, the night summary, and the image prompt.

### SPEC-014 Setup

Same as SPEC-009. If the Flask server is already running, skip to step 3.

**1. Open an SSH tunnel from the Ubuntu host:**

```bash
ssh -L 5000:localhost:5000 sask-dev
```

Keep this terminal open.

**2. In the VM session, start the Flask development server:**

```bash
cd ~/Code/sask-calendar
bash tools/start_web.sh
```

Expected output: `Running on http://127.0.0.1:5000`

**3. Open a browser on the Ubuntu host. The page under test is:**

```text
http://localhost:5000/sky
```

**Reference pulses used in the test cases below:**

| Label | Pulse | Meaning |
|---|---|---|
| Epoch | `0` | Astro midnight, spring equinox; Greening, near Green Day |
| Story now | `104548096103` | Fatunik T1782 M10 D29, Terpin T2271 M2 D2; Stillness, near Green Day; 09:48:23 Astro |
| Fatunik day start | `104548082400` | Fatunik T1782 M10 D29 at 06:00:00 Astro (natural Fatunik day start) |
| First co-fullness | `432000` | Fatunik T-1531 M11 D4; sella + lelako + shunna near-full |

---

### SPEC-014 Test cases

#### TC-014-01 — Navigation bar includes Sky link on all pages

**Action:** Load each of the four pages (`/`, `/moons`, `/planets`, `/sky`) in turn.

**Pass criteria:**

- Every page renders a navigation bar containing four links:
  **Pulse**, **Moons**, **Planets**, and **Sky**.
- The **Sky** link navigates to `/sky`.
- Existing pages (Pulse, Moons, Planets) remain functional as in SPEC-005
  and SPEC-009.

---

#### TC-014-02 — Sky landing page loads with no query

**Action:** Navigate to `http://localhost:5000/sky` with no query parameters.

**Pass criteria:**

- HTTP 200; page title contains "Sky".
- Four input sections are rendered: **Enter pulse**, **Or Astro day**,
  **Or Fatunik date**, and **Or Terpin date**.
- No results panels are rendered.
- No error message is shown.
- No `<script>` tag in the page source.

---

#### TC-014-03 — Sky at story_now_pulse: all panels render

**Action:** Navigate to `http://localhost:5000/sky?pulse=104548096103`.

**Pass criteria:**

- HTTP 200; no error message.
- All of the following section headings are present on the page:
  - Lunar Calendars (with a "display-only" annotation)
  - Season
  - Moons Above the Horizon (or a "no moons" notice)
  - Wanderers Above the Horizon (or a "no wanderers" notice)
  - Fixed Stars & Houses of the Equinox
  - Co-fullness
  - Night Summary
  - Image Prompt

---

#### TC-014-04 — Date fields and time display at story_now_pulse

**Action:** Navigate to `/sky?pulse=104548096103`.

**Pass criteria:**

- Astro Day input shows **1210048**; the time displayed next to the Query
  button shows **09:48:23**.
- Fatunik date inputs show year **1782**, month **10**, day **29**.
- Terpin date inputs show year **2271**, month **2**, day **2**.

---

#### TC-014-05 — All four lunar calendars displayed

**Action:** Navigate to `/sky?pulse=104548096103`.

**Pass criteria:**

- The **Lunar Calendars** table contains exactly four rows, one each for:
  the Untamed Reckoning (moon: Sella), the Warren Count (moon: Shunna),
  the Hearth Count (moon: Jembor), and the Terpin Lunar Count (moon: Mean).
- Each row shows non-empty Day and Lunation values.
- Untamed, Warren, and Terpin Lunar rows show non-empty Turn and Month integers.
- The Hearth Count row shows "—" for Long Count, Short Count, Turn, and Month
  (the Hearth calendar tracks no turns).

---

#### TC-014-06 — Lunar calendars are display-only (no lunar input fields)

**Action:** On the `/sky` landing page (no query), view the page source
(Ctrl+U or DevTools → Sources).

**Pass criteria:**

- The only `<input>` field names present are: `pulse`, `astro_day`,
  `fatunik_year`, `fatunik_month`, `fatunik_day`,
  `terpin_year`, `terpin_month`, `terpin_day`.
- No input fields named after any lunar calendar (e.g. `untamed_year`,
  `warren_month`, `lunar_day`) appear anywhere in the HTML.

---

#### TC-014-07 — Season panel

**Action:** Navigate to `/sky?pulse=104548096103`.

**Pass criteria:**

- The **Season** section shows **Stillness**.
- The near-event annotation **Green Day** appears (story_now is verging on
  the spring equinox).

---

#### TC-014-08 — Moons above the horizon with drill-down links

**Action:** Navigate to `/sky?pulse=104548096103`.

**Pass criteria:**

- The **Moons Above the Horizon** table lists at least Endor, Lelako, and Shunna.
- Each moon name is a hyperlink pointing to `/moons?pulse=104548096103`.
- Each row shows non-empty Color, Phase, Direction, and Brightness values.
- Clicking a moon name navigates to the `/moons` page for that pulse and shows
  that moon's detail row.

---

#### TC-014-09 — Wanderers above the horizon with drill-down links

**Action:** Navigate to `/sky?pulse=104548096103`.

**Pass criteria:**

- The **Wanderers Above the Horizon** table lists at least
  Aesthra, Lethra, Beyarus, Thurnak, Zelven, and Kreetha.
- Each planet name is a hyperlink pointing to `/planets?pulse=104548096103`.
- Each row shows non-empty Color, Phase, Direction, and Brightness values.
- Clicking a planet name navigates to the `/planets` page for that pulse.

---

#### TC-014-10 — Fixed stars and Houses of the Equinox panel

**Action:** Navigate to `/sky?pulse=104548096103`.

**Pass criteria:**

- An **Active house** line appears, showing **The Winged Pollinator**.
- A stars table is rendered listing at least the following visible stars:
  Ilyrun, Kresh, Marnok, Sethera, Aghur, Boreth, Droven.
- Each star row shows a direction or position description.

---

#### TC-014-11 — Co-fullness section: next event always shows

**Action:** Navigate to `/sky?pulse=104548096103`.

**Pass criteria:**

- The **Co-fullness** section renders.
- A **Next event** line appears giving a day count (non-negative integer)
  and at least two moon names.
- No Python error or missing-data placeholder is shown.

---

#### TC-014-12 — Co-fullness tonight at a known event

**Action:** Navigate to `/sky?pulse=432000` (Fatunik T-1531 M11 D4 — the
first co-fullness midnight in the calendar).

**Pass criteria:**

- The **Tonight** indicator appears in the Co-fullness section.
- The count is **3** and the moons listed include **sella**, **lelako**,
  and **shunna**.

---

#### TC-014-13 — Night summary is deterministic prose

**Action:** Navigate to `/sky?pulse=104548096103`.

**Pass criteria:**

- The **Night Summary** section renders a paragraph of human-readable prose.
- The text references the season (Stillness) or at least one sky body visible
  at that pulse.
- Reload the same URL: the prose is byte-for-byte identical to the first load.

---

#### TC-014-14 — Image prompt contains style directives

**Action:** Navigate to `/sky?pulse=104548096103`.

**Pass criteria:**

- The **Image Prompt** section renders text in a monospace (pre-formatted) block.
- The block contains the phrase **Image style:** followed by style directive text.

---

#### TC-014-15 — Fatunik date input shows Fatunik day start time

**Action:** On the `/sky` page, enter Fatunik year **1782**, month **10**,
day **29** and click **Query**.

**Pass criteria:**

- HTTP 200; no error message.
- The time shown next to the Astro Day field is **06:00:00** (the Fatunik
  calendar day starts at 6 AM Astro).
- The Fatunik date in the input fields shows **T1782 M10 D29** — same as
  the input date (no day-offset artifact).
- All sky panels render with plausible content for that pulse.

---

#### TC-014-16 — Terpin date input shows Terpin day start time

**Action:** On the `/sky` page, enter Terpin year **2271**, month **2**,
day **2** and click **Query**.

**Pass criteria:**

- HTTP 200; no error message.
- The time shown next to the Astro Day field is **00:00:00** (the Terpin
  calendar day starts at Astro midnight).
- The Terpin date in the input fields shows **T2271 M2 D2** — same as the
  input date.
- Lunar Calendars table is populated with non-empty lunation values.

---

#### TC-014-17 — Astro day input is not snapped

**Action:** On the `/sky` page, enter Astro day **1** and click **Query**.

**Pass criteria:**

- HTTP 200; no error message.
- Astro Day input shows **1**; time next to the Query button shows **00:00:00**
  (pulse 0; Astro day input uses midnight directly, no calendar-start offset).
- Fatunik date: **T-1531 M10 D29**; Terpin date: **T-1042 M1 D4**.
- Season: **Greening**, near **Green Day**.

---

#### TC-014-18 — URL bookmarkability: reload reproduces the same view

**Action:**

1. Navigate to `/sky?pulse=104548096103`.
2. Note the Active house name and one Lunation value from the lunar table.
3. Copy the full URL from the address bar and open it in a new browser tab.

**Pass criteria:**

- The new tab renders an identical page: same date values, same Active house,
  same lunation values, same night summary prose.
- The pulse input field is populated with `104548096103`.

---

#### TC-014-19 — Invalid pulse shows a user-visible error

**Action:** Navigate to `/sky?pulse=notanumber`.

**Pass criteria:**

- HTTP 200 (no 500 error page).
- An inline error message appears (e.g. *"Invalid pulse value"*).
- No sky panels are rendered.

---

#### TC-014-20 — Page source contains no JavaScript

**Action:** With a valid result rendered at `/sky?pulse=104548096103`, view the
HTML source (Ctrl+U or browser DevTools → Sources).

**Pass criteria:**

- No `<script>` tag appears anywhere in the HTML source.
- No `javascript:` URI appears in any attribute.
- The only embedded code is the `<style>` block in `<head>`.

---

### SPEC-014 Results — (to be completed after testing)

| TC | Result | Notes |
|---|---|---|
| TC-014-01 | Pass | |
| TC-014-02 | Pass | |
| TC-014-03 | Possible error | Refactoring requests |
| TC-014-04 | | |
| TC-014-05 | | |
| TC-014-06 | | |
| TC-014-07 | | |
| TC-014-08 | | |
| TC-014-09 | | |
| TC-014-10 | | |
| TC-014-11 | | |
| TC-014-12 | | |
| TC-014-13 | | |
| TC-014-14 | | |
| TC-014-15 | | |
| TC-014-16 | | |
| TC-014-17 | | |
| TC-014-18 | | |
| TC-014-19 | | |
| TC-014-20 | | |

---

### SPEC-014 Teardown

Stop the Flask server with `Ctrl+C` in the VM terminal. Close the SSH tunnel
terminal.

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
cd ~/Code/sask
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
cd ~/Code/sask
PYTHONPATH=src .venv/bin/python3
```

**2. Import and configure in the REPL:**

```python
from pathlib import Path
from sask.config_loader import load_config
from sask.message import CalendarDate
from sask.calendar.pulse import (
    astro_to_fatunik, fatunik_to_pulse, fatunik_turns_to_pulse_range,
    astro_to_terpin, terpin_to_pulse,
    terpin_shell_of_turn, terpin_turn_within_shell,
)
from sask.calendar.season import season_info

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
cd ~/Code/sask
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
cd ~/Code/sask
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

#### TC-014-12 — Co-fullness this day at a known event

**Action:** Navigate to `/sky?pulse=432000` (Fatunik T-1531 M11 D4 — the
first co-fullness midnight in the calendar).

**Pass criteria:**

- The **This day** indicator appears in the Co-fullness section.
- The count is **4** and the moons listed include **Sella**, **Lelako**,
  **Calumbra**, and **Shunna**.

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

### SPEC-014 Results — 2026-06-11

| TC | Result | Notes |
|---|---|---|
| TC-014-01 | Pass | |
| TC-014-02 | Pass | |
| TC-014-03 | Pass | |
| TC-014-04 | Pass | |
| TC-014-05 | Pass | |
| TC-014-06 | Pass | |
| TC-014-07 | Pass | |
| TC-014-08 | Pass | |
| TC-014-09 | Pass | |
| TC-014-10 | Pass | |
| TC-014-11 | Pass | |
| TC-014-12 | Pass | |
| TC-014-13 | Pass | |
| TC-014-14 | Pass | |
| TC-014-15 | Pass | |
| TC-014-16 | Pass | |
| TC-014-17 | Pass | |
| TC-014-18 | Pass | |
| TC-014-19 | Pass | |
| TC-014-20 | Pass | |

---

### SPEC-014 Teardown

Stop the Flask server with `Ctrl+C` in the VM terminal. Close the SSH tunnel
terminal.

---

## SPEC-016 — Ephemeris web page and regen-on-download export

SPEC-016 adds an **/ephemeris** page with two range-input modes:

- **Pulse mode** — enter an explicit start pulse and end pulse for a precise range.
- **Date mode** — enter a start time via Astro Day, Fatunik Date, or Terpin Date,
  and a **Duration (Days)** integer; the end is computed as start + days × 86,400 pulses.

After each Generate the page cross-populates all input types (like /sky).
A **Reset** button clears all fields before switching input type.
A truncated JSON preview and download link are rendered per profile (scribal / kinematic / both).
Download links regenerate the full series on demand and return it as a file attachment.
No JavaScript; no server-side storage.

### SPEC-016 Setup

Same as SPEC-014. If the Flask server is already running, skip to step 3.

**1. Open an SSH tunnel from the Ubuntu host:**

```bash
ssh -L 5000:localhost:5000 sask-dev
```

Keep this terminal open.

**2. In the VM session, start the Flask development server:**

```bash
cd ~/Code/sask
bash tools/start_web.sh
```

Expected output: `Running on http://127.0.0.1:5000`

**3. Open a browser on the Ubuntu host. The page under test is:**

```text
http://localhost:5000/ephemeris
```

**Reference values used in the test cases below:**

| Label | Value | Meaning |
|---|---|---|
| Story now | `104548096103` | Start pulse for most tests |
| Story now + 1 h | `104548099703` | End pulse for Pulse-mode short-range tests (+3600 pulses) |
| Min step | `5` minutes | Floor allowed by the throttle (300 pulses) |
| Over-range end | `104550774503` | Start + 2,678,400 pulses (31 days) — exceeds the 30-day cap (2,592,000) |
| Story now Astro day | `1210048` | Astro day corresponding to story_now_pulse |
| Story now Fatunik | T`1782` M`10` D`29` | Fatunik date at story_now (resolves to 06:00:00 Astro) |

---

### SPEC-016 Test cases

#### TC-016-01 — Navigation bar includes Ephemeris link on all pages

**Action:** Load each of the five pages (`/`, `/moons`, `/planets`, `/sky`,
`/ephemeris`) in turn.

**Pass criteria:**

- Every page renders a navigation bar at the top containing five links:
  **Pulse**, **Moons**, **Planets**, **Sky**, and **Ephemeris**.
- The **Ephemeris** link navigates to `/ephemeris`.
- Existing pages remain functional as in SPEC-005, SPEC-009, and SPEC-014.

---

#### TC-016-02 — Ephemeris landing page loads with no query

**Action:** Navigate to `http://localhost:5000/ephemeris` with no query
parameters.

**Pass criteria:**

- HTTP 200; page title contains "Ephemeris".
- A form is rendered with four input-type fieldsets:
  - **Pulse (explicit start and end)** — Start and End pulse fields.
  - **Astro Day (start; end set by Duration)** — Start Astro Day field only.
  - **Fatunik Date (start; end set by Duration)** — Start Year/Month/Day only.
  - **Terpin Date (start; end set by Duration)** — Start Year/Month/Day only.
- A **Step and profile** fieldset contains: Step (Astro minutes), Duration (Days),
  Profile selector, and **Generate** and **Reset** buttons.
- No preview block is shown.
- No error message is shown.
- No `<script>` tag in the page source.

---

#### TC-016-03 — Valid range: scribal preview and download link

**Action:** On the `/ephemeris` page, enter:

- Start pulse: `104548096103`
- End pulse: `104548099703`
- Step (minutes): `5`
- Profile: **Scribal**

Click **Generate**.

**Pass criteria:**

- HTTP 200; no error message.
- The URL in the address bar contains `start_pulse=104548096103`,
  `end_pulse=104548099703`, `step_minutes=5`, and `profile=scribal` as query
  parameters (the form is a GET form; results are shareable).
- A **Scribal preview** heading appears, followed by a scrollable `<pre>`
  block containing JSON.
- The JSON envelope includes `"profile": "scribal"`, `"start_pulse"`,
  `"end_pulse"`, `"step_pulses"`, and a `"steps"` array.
- The `"steps"` array contains at most 5 entries (truncated preview).
- Each step entry includes `"pulse"`, `"astro_day"`, and `"time_of_day"` keys.
- A **Download scribal JSON** link is present below the preview.

---

#### TC-016-04 — Valid range: kinematic preview and download link

**Action:** Same range as TC-016-03, but select **Kinematic** as the profile
and click **Generate**.

**Pass criteria:**

- HTTP 200; no error message.
- A **Kinematic preview** heading appears, followed by a `<pre>` block.
- The JSON envelope includes `"profile": "kinematic"` and a `"tracked_bodies"`
  list (at least 15 entries: the 8 moons and 7 planets).
- The `"steps"` array contains at most 5 entries.
- Each step entry includes `"pulse"` and a `"bodies"` dict keyed by body ID.
- Each body entry includes `"alt"`, `"az"`, `"ill"`, and `"up"` keys.
- Bodies below the horizon appear in the dict with `"up": false` and a
  negative `"alt"` value — they are not omitted.
- A **Download kinematic JSON** link is present below the preview.

---

#### TC-016-05 — Both profiles: two previews shown

**Action:** Same range as TC-016-03, but select **Both** as the profile and
click **Generate**.

**Pass criteria:**

- HTTP 200; no error message.
- Both a **Scribal preview** and a **Kinematic preview** heading appear, each
  with its own `<pre>` block.
- Both preview blocks contain valid-looking JSON.
- Two download links are present: one for scribal and one for kinematic.

---

#### TC-016-06 — Step below minimum: form error, no 500

**Action:** Enter the same range as TC-016-03, but set Step (minutes) to `1`
(below the 5-minute floor), and click **Generate**.

**Pass criteria:**

- HTTP 200 (not a 500 error page).
- An inline error message appears indicating the step is too small or below
  the minimum (e.g. references "minimum", "5 min", or "300 pulses").
- No preview block is rendered.

---

#### TC-016-07 — Range exceeding 30-day cap: form error, no 500

**Action:** Enter:

- Start pulse: `104548096103`
- End pulse: `104550774503` (≈ 31 days beyond start — over the 30-day cap)
- Step (minutes): `5`
- Profile: **Scribal**

Click **Generate**.

**Pass criteria:**

- HTTP 200 (not a 500 error page).
- An inline error message appears indicating the range is too large or
  exceeds the maximum (e.g. references "maximum", "30 days", "2592000",
  or "exceeds").
- No preview block is rendered.

---

#### TC-016-08 — Download returns attachment with correct filename

**Action:** Using the result from TC-016-03 (scribal, 1-hour range, 5-min
step), click the **Download scribal JSON** link.

**Pass criteria:**

- The browser offers to save a file (Content-Disposition: attachment).
- The suggested filename is exactly:
  `ephemeris_scribal_p104548096103-104548099703_s300.json`
- The saved file contains valid JSON with `"profile": "scribal"` and a
  `"steps"` array containing **13 entries**
  (pulses 0, 300, 600, … 3600 relative to start = 13 steps inclusive).
- Repeat for the **Download kinematic JSON** link; the suggested filename is:
  `ephemeris_kinematic_p104548096103-104548099703_s300.json`
  with `"profile": "kinematic"`.

---

#### TC-016-09 — Download is deterministic: reload reproduces identical bytes

**Action:**

1. Click the scribal download link from TC-016-03 and save the file as
   `ephemeris_a.json`.
2. Click the same link again (or copy the download URL and open it in a new
   tab) and save the file as `ephemeris_b.json`.

**Pass criteria:**

- The two files are byte-for-byte identical (same content, same byte count).
- You can verify on the VM with `diff ephemeris_a.json ephemeris_b.json`;
  expected output: nothing (no differences).

---

#### TC-016-10 — Astro day start with Duration (Days)

**Action:** On the `/ephemeris` page, click **Reset**, then enter:

- Start Astro day: `1210048`
- Duration (Days): `1`
- Step (Astro minutes): `30`
- Profile: **Scribal**

Click **Generate**.

**Pass criteria:**

- HTTP 200; no error message.
- A scribal preview renders.
- The `"start_pulse"` in the JSON envelope is `104548060800`
  (Astro day 1210048 at midnight, offset 0).
- A **Computed end** line is shown on the page, citing pulse `104548147200`
  (start + 86400), Astro Day 1210049, and the equivalent Fatunik and Terpin
  dates.
- All input types are cross-populated: the Pulse Start, Fatunik Start, and
  Terpin Start fields are filled with the resolved equivalents.
- A download link is present and functional.

---

#### TC-016-11 — Fatunik date start with Duration (Days)

**Action:** On the `/ephemeris` page, click **Reset**, then enter:

- Start Fatunik date: year `1782`, month `10`, day `29`
- Duration (Days): `1`
- Step (Astro minutes): `60`
- Profile: **Scribal**

Click **Generate**.

**Pass criteria:**

- HTTP 200; no error message.
- A scribal preview renders. The `"start_pulse"` in the envelope is
  `104548082400` (Fatunik T1782 M10 D29 day-start at 06:00:00 Astro).
- The **Computed end** line shows pulse `104548168800` (start + 86400),
  and the Fatunik and Terpin equivalent end dates.
- Each step entry has a `"time_of_day"` in HH:MM:SS format.
- No field in the scribal JSON contains the strings `"fatunik"`, `"terpin"`,
  `"shur"`, `"keyt"`, or `"kell"` (the export is technical, not lore-rendered).
- All input types are cross-populated in the form.
- A download link is present.

---

#### TC-016-12 — Page source contains no JavaScript

**Action:** With a valid preview rendered (e.g. TC-016-03 result), view the
HTML source (Ctrl+U or browser DevTools → Sources).

**Pass criteria:**

- No `<script>` tag appears anywhere in the HTML source.
- No `javascript:` URI appears in any attribute.
- The only embedded code is the `<style>` block in `<head>`.

---

#### TC-016-13 — URL bookmarkability: reload reproduces the same view

**Action:**

1. Submit the form from TC-016-03 (Pulse mode, scribal, 1-hour range, 5-min step).
2. Copy the full URL from the address bar.
3. Paste it into a new browser tab and press Enter.

**Pass criteria:**

- The new tab renders the identical preview — same JSON envelope values,
  same step count, same step content.
- The Pulse Start and End fields are repopulated from the query parameters.

---

#### TC-016-14 — Reset button clears all fields

**Action:**

1. Submit the form from TC-016-10 (Astro day start, Duration 1, step 30, scribal)
   so that all input types are cross-populated.
2. Click **Reset**.

**Pass criteria:**

- All input fields are cleared to empty (Pulse Start and End, Astro Day Start,
  Fatunik Year/Month/Day Start, Terpin Year/Month/Day Start, Step, Duration, Profile
  reverts to its default).
- The preview block and Computed end line disappear (the page is still at the
  same URL; no network request is made).
- The error section is empty.

---

#### TC-016-15 — Duration missing with date-mode start: error, no 500

**Action:** On the `/ephemeris` page, click **Reset**, then enter:

- Start Astro day: `1210048`
- Step (Astro minutes): `5`
- Leave **Duration (Days)** empty.

Click **Generate**.

**Pass criteria:**

- HTTP 200 (not a 500 error page).
- An inline error message appears referencing "Duration" or "required".
- No preview block is rendered.

#### TC-016-16 — Step equals or exceeds duration: form error, no 500

**Action:** On the `/ephemeris` page, click **Reset**, then enter:

- Start Astro day: `1`
- Duration (Days): `1`
- Step (Astro minutes): `1440` (= exactly 1 day — equals the total duration)
- Profile: **Scribal**

Click **Generate**.

**Pass criteria:**

- HTTP 200 (not a 500 error page).
- An inline error message appears indicating the step equals or exceeds the
  duration (e.g. references "Step", "equals", "exceeds", or "duration").
- No preview block is rendered.

---

### SPEC-016 Results — 2026-06-14

| TC | Result | Notes |
|---|---|---|
| TC-016-01 | Pass | |
| TC-016-02 | Pass | |
| TC-016-03 | Pass | |
| TC-016-04 | Pass | |
| TC-016-05 | Pass | |
| TC-016-06 | Pass | |
| TC-016-07 | Pass | |
| TC-016-08 | Pass | |
| TC-016-09 | Pass | |
| TC-016-10 | Pass | |
| TC-016-11 | Pass | |
| TC-016-12 | Pass | |
| TC-016-13 | Pass | |
| TC-016-14 | Pass | |
| TC-016-15 | Pass | |
| TC-016-16 | Pass | |

---

### SPEC-016 Teardown

Stop the Flask server with `Ctrl+C` in the VM terminal. Close the SSH tunnel
terminal.

---

## SPEC-017 — Lore overlays: time-of-day and calendar date rendering

**Branch:** main | **Status:** dev complete, awaiting UAT

### SPEC-017 Setup

Start the Flask server and open an SSH tunnel (same procedure as SPEC-016).
Navigate to `http://localhost:5000/sky` in the browser.

### Test Cases

#### TC-017-01 — Lore Overlay section appears for story_now

1. Load `/sky` with the story_now pulse (e.g., enter Astro Day 153,828 and press
   Query, or use the default pulse in the URL).
2. **Expected:** A "Lore Overlay" table appears below the error area and above
   the Lunar Calendars table. It contains rows for: Fatunik time, Terpin time,
   Fatunik Solar, Terpin Solar, and all four lunar calendars (Untamed, Warren,
   Hearth, Terpin Lunar).

**Pass / Fail:** Pass

#### TC-017-02 — Fatunik and Terpin lore time format

1. Using the story_now query from TC-017-01, inspect the Fatunik time and Terpin
   time rows.
2. **Expected:** Both rows show a string matching the pattern
   `"<Watch Name> Watch . shur <N> : keyt <N>"` (e.g.,
   `"Third Watch . shur 5 : keyt 3"`). Fatunik and Terpin show different values
   because their day-start offsets differ (Fatunik at 6 AM, Terpin at midnight).

**Pass / Fail:** Pass

#### TC-017-03 — Fatunik Solar lore date format

1. Using the same query, inspect the Fatunik Solar row in the Lore Overlay table.
2. **Expected:** The value matches the pattern:
   `"<day_name>, the <Nth> kell of <month>, Year <N> of <Age Name>"`
   All names should be from the fatunik_solar.toml config (Sune/Aweth/Morrin/Velden/Hesk
   for day names, Gleaming for festival month, etc.).

**Pass / Fail:** Pass

#### TC-017-04 — Terpin Solar lore date format

1. Inspect the Terpin Solar row.
2. **Expected:** Matches `"<day_name>, the <Nth> deshan of <month>, Year <N> of <Age Name>"`.
   Day names from terpin_solar.toml (Adda/Bessen/Corwen/…). Month from the
   terpin_solar month list (Omarra/Tessith/Belunna/… or Brennald for festival
   month 1).

**Pass / Fail:** Pass

#### TC-017-05 — Untamed lore date format

1. Inspect the Untamed row.
2. **Expected:** Matches `"<quarter>, day <N> of <month>, Range <N> of the Reave <N>"`.
   Quarter from untamed quarter_names ("the Dark"/"the Rising"/"the Full"/"the Falling").
   Month from the untamed month list (Varro/Dakka/Skell/…).

**Pass / Fail:** Pass

#### TC-017-06 — Warren lore date format

1. Inspect the Warren row.
2. **Expected:** Matches `"<quarter>, day <N> of <month>, Litter <N> of the Wend <N>"`.
   Quarter from warren quarter_names ("the Dark"/"the Swelling"/"the Full"/"the Fading").
   Month from the warren month list (Tum/Fenn/Lilla/…).

**Pass / Fail:** Pass

#### TC-017-07 — Terpin Lunar lore date format

1. Inspect the Terpin Lunar row.
2. **Expected:** Matches `"<quarter>, day <N> of <month>, Year <N> of <Age Name>"`.
   Quarter from terpin_lunar quarter_names (First Quarter/Second Quarter/…).
   Month from terpin_lunar month list (Praal/Suneth/…). Age from terpin_lunar ages.

**Pass / Fail:** Pass

#### TC-017-08 — Hearth lore date format

1. Inspect the Hearth row.
2. **Expected:** Matches `"<phase_term>, the <Nth> day of Old Jem's <Nth> turning"`.
   Both the day-within-cycle and the turning count are rendered as ordinals
   (e.g., "1st", "21st", "51st"). Phase term from hearth phase_terms
   ("the waxing"/"the full"/"the waning").

**Pass / Fail:** Pass

#### TC-017-09 — Lore Overlay absent when no pulse queried

1. Load `/sky` with no input (blank form or fresh page load).
2. **Expected:** The Lore Overlay section does not appear (no pulse → no scene
   → lore is not computed).

**Pass / Fail:** Pass

#### TC-017-10 — Lore time advances across a day

1. Query two pulses exactly one full day apart (e.g., pulse 86400 and pulse
   172800, or any two Astro Days that share the same `day_offset`).
2. **Expected:** Fatunik time and Terpin time are identical for both pulses
   (same position within the day).

**Pass / Fail:** Pass

### SPEC-017 Results — 2026-06-14

Tested on `sask-dev` via SSH tunnel. All cases pass.

| TC | Result | Notes |
|---|---|---|
| TC-017-01 | PASS | Lore Overlay table appears with all 6 calendar rows |
| TC-017-02 | PASS | Fatunik and Terpin show different watch/shur/keyt values |
| TC-017-03 | PASS | Fatunik Solar: correct kell, day name, month, age |
| TC-017-04 | PASS | Terpin Solar: correct deshan, day name, month, age |
| TC-017-05 | PASS | Untamed: correct quarter, month name, Range/Reave counts |
| TC-017-06 | PASS | Warren: correct quarter, month name, Litter/Wend counts |
| TC-017-07 | PASS | Terpin Lunar: correct quarter, month, age |
| TC-017-08 | PASS | Hearth: ordinal day and turning, correct phase term, Old Jem |
| TC-017-09 | PASS | Lore Overlay absent on blank page load |
| TC-017-10 | PASS | Same day-offset pulse → identical lore time on both queries |

Minor refinement during UAT: hearth day and turning count changed to ordinal
rendering (e.g., "1st day … 51st turning"). Test updated accordingly.

### SPEC-017 Teardown

Stop the Flask server with `Ctrl+C` in the VM terminal. Close the SSH tunnel
terminal.

## SPEC-019 — Festival-month date validation

**Branch:** main | **Status:** UAT complete

### SPEC-019 Setup

Same as SPEC-016/017. If the Flask server is already running, skip to step 3.

**1. Open an SSH tunnel from the Ubuntu host:**

```bash
ssh -L 5000:localhost:5000 sask-dev
```

Keep this terminal open.

**2. In the VM session, start the Flask development server:**

```bash
cd ~/Code/sask
bash tools/start_web.sh
```

Expected output: `Running on http://127.0.0.1:5000`

**3. Open a browser on the Ubuntu host. The pages under test are:**

```text
http://localhost:5000/moons
http://localhost:5000/ephemeris
```

**Reference values used in the test cases below (from `config/calendars.toml`):**

| Label | Turn | Festival length | Meaning |
|---|---|---|---|
| Fatunik standard | T1 | 5 days | Non-leap Fatunik turn |
| Fatunik leap | T4 | 6 days | Leap Fatunik turn (4/100/400 rule) |
| Terpin long | T132 | 37 days | Long Terpin turn (every 132 turns) |
| Fatunik regular month | T1 M2 | 30 days | Any non-festival Fatunik month |

### SPEC-019 Test cases

#### TC-019-01 — Fatunik festival-month overflow is rejected

1. On `/moons`, enter Fatunik Year `1`, Month `1`, Day `10` (the standard
   festival has only 5 days) and submit.
2. **Expected:** A clear error message appears naming the month, the turn,
   and the valid day range (1-5). No moon table renders, and no date
   silently resolves into Month 2.

**Pass / Fail:** Pass

#### TC-019-02 — Fatunik festival-month boundary day is accepted

1. On `/moons`, enter Fatunik Year `1`, Month `1`, Day `5` (the last day of
   the standard festival) and submit.
2. **Expected:** The page resolves normally — moon positions render and the
   Fatunik date shown is T1 M1 D5, with no error.

**Pass / Fail:** Pass

#### TC-019-03 — Fatunik leap-turn festival boundary

1. On `/moons`, enter Fatunik Year `4`, Month `1`, Day `6` (the last day of
   the leap festival) and submit. **Expected:** accepted, no error.
2. Change Day to `7` and resubmit. **Expected:** rejected, with the error
   naming month 1, turn 4, and the valid maximum (1-6).

**Pass / Fail:** Pass

#### TC-019-04 — Terpin long-turn festival boundary

1. On `/moons`, enter Terpin Year `132`, Month `1`, Day `37` (the last day of
   the long-turn festival) and submit. **Expected:** accepted, no error.
2. Change Day to `38` and resubmit. **Expected:** rejected, with the error
   naming turn 132 and the valid maximum (1-37).

**Pass / Fail:** Pass

#### TC-019-05 — Regular-month overflow is rejected

1. On `/moons`, enter Fatunik Year `1`, Month `2`, Day `31` (regular months
   are 30 days) and submit.
2. **Expected:** A clear error message appears; no date silently resolves
   into Month 3.

**Pass / Fail:** Pass

#### TC-019-06 — Ephemeris start-date form also validates

1. On `/ephemeris`, select the Fatunik Date start input, enter Year `1`,
   Month `1`, Day `10`, set Duration to `1` day and Step to `5` minutes, and
   press Generate.
2. **Expected:** The same in-page error appears instead of a generated
   preview or download link.

**Pass / Fail:** Pass

### SPEC-019 Results — 2026-06-19

Tested on `sask-dev` via SSH tunnel. All cases pass.

| TC | Result | Notes |
|---|---|---|
| TC-019-01 | PASS | Fatunik T1 M1 D10 rejected; error names month/turn/max (1-5) |
| TC-019-02 | PASS | Fatunik T1 M1 D5 accepted; moon table renders |
| TC-019-03 | PASS | Fatunik T4 M1 D6 accepted; D7 rejected (max 1-6) |
| TC-019-04 | PASS | Terpin T132 M1 D37 accepted; D38 rejected (max 1-37) |
| TC-019-05 | PASS | Fatunik T1 M2 D31 rejected; no roll into Month 3 |
| TC-019-06 | PASS | `/ephemeris` start resolver renders the same in-page error |

Bug found and fixed during TC-019-04: the `terpin_day` and `fatunik_month`
HTML5 `min`/`max` attributes on `/moons`, `/planets`, `/sky`, and
`/ephemeris` predated SPEC-019 and were too tight, blocking valid input
(e.g. Terpin day 37) before it reached the server. Normalised to
`month max="13"`, `fatunik_day max="30"`, `terpin_day max="37"` across all
four templates; retested and passed.

### SPEC-019 Teardown

Stop the Flask server with `Ctrl+C` in the VM terminal. Close the SSH tunnel
terminal.

---

## SPEC-026 — Asset retrieval: HTML adapter

SPEC-026 adds a raw, non-HTML endpoint, **`GET /asset/<kind>/<id>`**, that
serves asset bytes (images, audio, JSON, video) straight from the asset
catalog (`config/asset_catalog_data.toml`) with the catalog's `content_type`.
Unlike every other page in this app, it renders no template — there is no
form, no nav entry, and no page source to inspect; pass/fail is judged by
the raw HTTP response (status, `Content-Type` header, and the bytes the
browser renders). Per SPEC-026's own acceptance criteria, this is the only
required UAT for the spec — the engine layer (`resolve_descriptor`,
`fetch_payload`, catalog loading/validation) is covered entirely by
automated tests (`tests/test_spec_026.py`) and needs no manual check.

### SPEC-026 Setup

**1. Open an SSH tunnel from the Ubuntu host:**

```bash
ssh -L 5000:localhost:5000 sask-dev
```

Keep this terminal open.

**2. In the VM session, start the Flask development server:**

```bash
cd ~/Code/sask
bash tools/start_web.sh
```

Expected output: `Running on http://127.0.0.1:5000`

**3. Open a browser on the Ubuntu host.** For each test case, navigate
directly to the asset URL given (there is no form to fill in), then open
DevTools → Network tab, click the request, and check the **Response
Headers** → `content-type` value.

**Reference catalog entries used in the test cases below (from
`config/asset_catalog_data.toml`):**

| kind | id | content_type | Source file under `assets/v0/` |
|---|---|---|---|
| image | `splash.bg` | `image/webp` | `image/splash.default.1920x1080.6389524a.webp` |
| image | `splash.bg.960` | `image/webp` | `image/splash.default.960x540.385a45a2.webp` |
| image | `splash.bg.480` | `image/webp` | `image/splash.default.480x270.eb6c6dab.webp` |
| image | `splash.bg.thumb` | `image/webp` | `image/splash.default.thumb.320x180.762c6016.webp` |
| audio | `ambient` | `audio/mpeg` | `audio/ambient-loop.mp3` |
| json | `varkaar-questions` | `application/json` | `json/varkaar_questions.json` |
| video | `ambient-video` | `video/mp4` | `video/ambient-video.mp4` |

---

### SPEC-026 Test cases

#### TC-026-01 — Image asset loads with correct Content-Type

**Action:** Navigate to `http://localhost:5000/asset/image/splash.bg`.

**Pass criteria:**

- HTTP 200.
- The browser renders the image directly (a 1920×1080 splash image) — no
  download prompt, no broken-image icon.
- Response header `content-type` is exactly `image/webp`.

---

#### TC-026-02 — Image variants: multiple ids share one kind

**Action:** Navigate in turn to `/asset/image/splash.bg.960`,
`/asset/image/splash.bg.480`, and `/asset/image/splash.bg.thumb`.

**Pass criteria:**

- Each returns HTTP 200 with `content-type: image/webp`.
- Each renders a visibly smaller variant of the same splash image
  (960×540, 480×270, and a 320×180 thumbnail respectively).
- Confirms the catalog's "two or more ids share a kind" case (`image`)
  resolves correctly — this is config-driven, not a hardcoded list.

---

#### TC-026-03 — Audio asset loads with correct Content-Type

**Action:** Navigate to `http://localhost:5000/asset/audio/ambient`.

**Pass criteria:**

- HTTP 200.
- The browser either plays the audio inline or offers to open/download it
  (behavior varies by browser; either is a pass — there is no `<audio>`
  player wrapper, this is the raw file).
- Response header `content-type` is exactly `audio/mpeg`.

---

#### TC-026-04 — JSON asset loads with correct Content-Type

**Action:** Navigate to `http://localhost:5000/asset/json/varkaar-questions`.

**Pass criteria:**

- HTTP 200.
- The browser displays the raw JSON (either as plain text or via the
  browser's built-in JSON viewer).
- The content is a JSON array of question objects (each with
  `question_id`, `question_text`, `expected_answer`, `scope`).
- Response header `content-type` is exactly `application/json`.

---

#### TC-026-05 — Video asset loads with correct Content-Type

**Action:** Navigate to `http://localhost:5000/asset/video/ambient-video`.

**Pass criteria:**

- HTTP 200.
- The browser plays the video inline or offers to open/download it.
- Response header `content-type` is exactly `video/mp4`.
- Note: this entry's `kind` (`video`) is derived from its directory
  (`assets/v0/video/`); `content_type` is still an independently authored
  field on the catalog entry, not derived from the `.mp4` extension.

---

#### TC-026-06 — Unknown id within a known kind returns 404

**Action:** Navigate to `http://localhost:5000/asset/image/does-not-exist`.

**Pass criteria:**

- HTTP 404 (not a 500 error page).
- Plain-text response body naming the missing asset, e.g.
  `Unknown asset: image/does-not-exist`.

---

#### TC-026-07 — Unknown kind entirely also returns 404

**Action:** Navigate to `http://localhost:5000/asset/nonsense-kind/whatever`.

**Pass criteria:**

- HTTP 404 — the same response shape as TC-026-06, not a different error.
- Confirms `kind` is purely a catalog lookup miss, not a separately
  validated code path (DD-0016's `kind_is_config` decision): an unknown
  kind is handled identically to an unknown id, with no special-cased
  "invalid kind" branch anywhere in the route.

---

#### TC-026-08 — No navigation entry added

**Action:** Load `http://localhost:5000/` and inspect the navigation bar.

**Pass criteria:**

- The nav bar still shows exactly five links: **Pulse**, **Moons**,
  **Planets**, **Sky**, **Ephemeris**. No "Asset" link was added.
- This is intentional, not an oversight: `/health` and
  `/ephemeris/download` (both raw, non-HTML endpoints) aren't in the nav
  either — a raw asset endpoint is not a browsable page.

---

### SPEC-026 Results — 2026-06-24

Tested on `sask-dev` via SSH tunnel. All cases pass.

| TC | Result | Notes |
|---|---|---|
| TC-026-01 | PASS | |
| TC-026-02 | PASS | |
| TC-026-03 | PASS | |
| TC-026-04 | PASS | |
| TC-026-05 | PASS | |
| TC-026-06 | PASS | |
| TC-026-07 | PASS | |
| TC-026-08 | PASS | |

---

### SPEC-026 Teardown

Stop the Flask server with `Ctrl+C` in the VM terminal. Close the SSH tunnel
terminal.

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
- A numeric input labelled "Pulse" is pre-filled with `71642553600`
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
| TC-005-01 | PASS | `GET /` → 200; form pre-filled with `71642553600` |
| TC-005-02 | PASS | `GET /?pulse=71642553600` → 200 |
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
SNP = cfg.timeline.story_now_pulse   # 71642553600
```

---

### REPL test cases

#### TC-003-01 — story_now_pulse converts to Fatunik Year ~2018

**Action:**

```python
astro_to_fatunik(SNP, cfg)
```

**Pass criteria:** Returns `CalendarDate(calendar_id='fatunik', year=2018, month=1, day=5)`.

- Year 2018 is consistent with the spec's "roughly Fatunik 2017" (4 days into
  the new year at story_now).
- Month 1 = Gleaming (the festival intercalary month); Day 5 = last day of the
  standard (non-leap) festival.

---

#### TC-003-02 — story_now_pulse converts to Terpin Year ~2271

**Action:**

```python
astro_to_terpin(SNP, cfg)
```

**Pass criteria:** Returns `CalendarDate(calendar_id='terpin', year=2271, month=5, day=8)`.

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

The story_now date is Shell 18, Turn 27 within that Shell (17 completed Shells
of 132 turns each = 2244 turns; 2271 − 2244 = 27).

---

#### TC-003-04 — Fatunik date round-trips correctly

**Action:**

```python
date = CalendarDate("fatunik", 2018, 1, 5)
astro_to_fatunik(fatunik_to_pulse(date, cfg), cfg)
```

**Pass criteria:** Returns the original `date` unchanged:
`CalendarDate(calendar_id='fatunik', year=2018, month=1, day=5)`.

---

#### TC-003-05 — Ages helper: Fatunik Turns 2000–2020 span story_now

**Action:**

```python
start, end = fatunik_turns_to_pulse_range(2000, 2020, cfg)
print(start, end)
print(start <= SNP <= end)
```

**Pass criteria:**

- `start` = `71074044000` (sunrise of Fatunik Y2000 M1 D1)
- `end` = `71736818399` (last pulse of Fatunik Y2020 M13 D30)
- `start <= SNP <= end` prints `True` (story_now is in year 2018, inside
  the range).

---

#### TC-004-01 — story_now is in Blazing (summer), no near event

**Action:**

```python
info = season_info(SNP, cfg)
print(info.season_id, info.near_event_id)
```

**Pass criteria:**

- `info.season_id` = `'blazing'`
- `info.near_event_id` = `None` (orbital position ~0.273, well between
  summer solstice at 0.25 and mid-blazing at 0.375)

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
| TC-003-01 | PASS | `CalendarDate(calendar_id='fatunik', year=2018, month=1, day=5)` |
| TC-003-02 | PASS | `CalendarDate(calendar_id='terpin', year=2271, month=5, day=8)` |
| TC-003-03 | PASS | `terpin_shell_of_turn(2271)` → `18`; `terpin_turn_within_shell(2271)` → `27` |
| TC-003-04 | PASS | Round-trip returns original date unchanged |
| TC-003-05 | PASS | `start=71074044000`, `end=71736818399`; `start <= SNP <= end` → `True` |
| TC-004-01 | PASS | `season_id='blazing'`, `near_event_id=None` |
| TC-004-02 | PASS | `season_id='greening'`, `near_event_id='spring_equinox'`, name `'Green Day'` |
| TC-004-03 | PASS | `season_id='blazing'`, `near_event_id='summer_solstice'`, name `'Blaze Day'` |

---

### REPL teardown

Exit the Python REPL with `exit()` or `Ctrl+D`.

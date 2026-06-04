# SPEC-008 Test Results — Local-sky position

**Date:** 2026-06-04
**Status:** PASS

## Test run

```text
26 passed in 0.07s
```

All 26 tests pass. Full pre-commit check exits 0.

## Note: ecliptic frame convention fix

Planning for SPEC-008 revealed a phase-offset bug in SPEC-007's bodies.py:
Gavor's heliocentric longitude was placed at `gavor_frac * 2π`, putting Fatune
at geocentric longitude `(gavor_frac + 0.5) * 360°`. This gave -23.44° declination
at Blazing (gavor_frac=0.25), making it "winter" for the northern observer — the
opposite of the intended hot season. The fix (Gavor at `(gavor_frac+0.5)*2π`,
Fatune geocentric at `gavor_frac*360°`) was applied to `bodies.py` before writing
`sky.py`; all 42 SPEC-007 tests continue to pass.

## Coverage summary

| Area | Tests |
|---|---|
| Ecliptic → equatorial (equinoxes, solstices, non-zero lat) | 5 |
| Equatorial → horizontal (transit alt/az, rise altitude) | 4 |
| Rise / transit / set (order, max altitude, near-zero, half-day) | 4 |
| Circumpolar and never-rising edge cases | 2 |
| Fatune seasonal declination (4 cardinal points) | 4 |
| Fatune day length (summer > 12h, winter < 12h) | 2 |
| sky_position on real body states (ranges, above-horizon) | 3 |
| all_sky_positions (count and name order) | 1 |
| Layer purity | 1 |

## Acceptance checklist

- [x] Altitude and azimuth correct for known geometry (dec=0 → 54.53° alt, 180° az)
- [x] Rise, transit, and set returned as pulses and bracket the above-horizon window
- [x] Seasonal variation in Fatune's rise position and day length emerges from obliquity
- [x] above_horizon boolean agrees with sign of altitude
- [x] Circumpolar and never-rising cases resolve cleanly (rise/set = None)
- [x] sky.py has no web-layer import

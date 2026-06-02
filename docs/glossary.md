# sask-calendar — Glossary

Living document. Two conventions:

- **Technical terms** are the authoritative meanings used in code and config.
- **Lore terms** are cultural/display names that *map onto* a technical meaning.
Specific instances (individual moons, stars, houses, wanderers) live in config,
not here. Items marked **(TBD)** await design.

## Time & canonical units

- **Pulse** — the canonical atomic time unit; an integer count from the epoch. 86,400 pulses
  per day (equal to seconds in an Earth day). Astro Epoch Pulse 0 = midnight in the Saskan Lands.
- **Astro Day** — derived integer day: `day = floor(pulse / 86,400) + 1`. Astro Epoch Day 1 =
  the first day of Spring in the Saskan Lands.
- **AstroYear** — the precise, leap-free solar year: 365.2422 days = 31,556,926.08 pulses. The
  astronomical constant from which seasons and orbital positions derive.
- **Turn** — a *civil* solar year, with leap adjustments. Distinct from the AstroYear, which never leaps.

## Reference frames, positions & angles

All cyclic quantities are normalized 0.0–1.0 and use circular (modular) math.

- **Synodic position / period** — measured relative to Fatune (the sun); drives phase and
  visibility. 0/1 = conjunction, 0.5 = opposition.
- **Sidereal position / period** — measured relative to the fixed stars; drives star context. A separate cycle from synodic.
- **Latitude** — a body's position relative to its orbital nodes; the optional second cycle that gates eclipses.
- **Inclination** — the tilt of a body's orbit relative to the reference plane.
- **Node** — the points where an inclined orbit crosses the reference plane (latitude ≈ 0).
- **Elongation** — angular distance from Fatune; 0 at conjunction, maximum at opposition.
- **Conjunction** (astronomical) — a body aligned with Fatune (synodic 0/1). Distinct from the lore "Conjunction" — see `co_fullness`.
- **Opposition** — a body opposite Fatune (synodic 0.5); fully lit, maximum visibility.
- **Illumination phase** — the lit fraction of a body's disk; for a moon it tracks synodic position.
- **Retrograde** — a planet's apparent backward drift near opposition; a window of its synodic cycle.

## Visibility, phases & events

- **Visibility** — a 0.0–1.0 scalar from synodic position; visible band ≈ 0.1–0.9,
  "lost in glare" near conjunction. A "visible tonight" boolean is derived by threshold.
  Fixed stars use a seasonal visibility window instead.
- **Fuzzy tolerance window** — the shared "within a tolerance of a precise moment" concept used
  by seasonal events, fullness, and conjunctions.
- **co_fullness** — engine predicate: N named moons within the fuzzy "full" tolerance on the
  same night, regardless of sky position. This is the Saskan lore "Conjunction."
- **positional_conjunction** — engine predicate: N bodies within an angular tolerance of the
  same apparent sky position. The rarer "true conjunction."
- **Apparition** — a window during which an episodic object (comet, the Spark) is visible:
  an epoch plus a duration, driven by authored events and/or seeded generators. Never per-day randomness.
- **Eclipse** — synodic position near conjunction *and* latitude near a node at the same time (hence rare).

## Bodies & sky entities

Code uses these stable categories; lore overloads several names (see below).

- **planet** — the world entity.
- **landmass** — a land entity (the Saskan Lands are the relevant observation region).
- **world_ocean** — the planetary ocean.
- **star** — the system's sun, Fatune.
- **moon** — one of the eight bodies orbiting the planet.
- **wanderer** — a planet (other than the world) or a comet visible from the world.
- **fixed star** — a sidereal background star with seasonal visibility.
- **constellation / house** — a fixed-star grouping; the "House of the Equinox" is the
  constellation tied to a given orbital position.

## Lore vocabulary → technical meaning

- **Saskantinon / the Saskan Lands** → the observation `landmass` (~Mexico-sized, northern hemisphere).
- **Gavor** → `planet` (colloquial) or `landmass` (strict) — overloaded in lore; code disambiguates.
- **Havorra** → `world_ocean`.
- **Gavor-Havorra** → `planet` (the whole world).
- **Fatune** → `star` (the sun).
- **Fatunik** → solar / of-Fatune; also the dominant culture.
- **Lunar** → the `moon` bodies, collectively.
- **Terpin** → an older culture (long-lived sentient tortoises).
- **Wanderer** → a `wanderer` (planet or comet).
- **Day** → one rotation of the world = 86,400 pulses.
- **Astro time** → the `pulse` count.
- **Astro / Astronomical calendar** → the canonical calendar, in pulses and days from epoch.
- **Turn** → a civil (Fatunik) solar year, leap-adjusted.
- **AstroYear** → the precise solar year, no leaps.
- **Solar / Fatunik calendar** → civil calendar on seasons and solar events (intercalary month + extra day every 5 turns).
- **Terpin calendar** → the Terpin civil calendar; long-cycle, floats, with a coarse correction (~one month every 32 turns).
- **Lunar calendar** → any calendar driven by moon cycles. **(TBD — design pending.)**
- **SolarLunar / FatunikLunar / LuniSolar / LuniFatunik** → a combined solar-and-lunar calendar. **(TBD.)**
- **Star Context** → the simplified constellation / fixed-star framework (astrological, not a star map).
- **Conjunction** (lore) → `co_fullness`. A true sky alignment → `positional_conjunction`.
- **The Spark** → an `apparition` object; in lore an omen near a moon, in reality a starship on a moon's dark side.
- **Seasons** (Fatunik): **Stillness, Greening, Blazing, Withering** → the four astronomical
  quarters, each with named observances (e.g., Greening's "Green Day" and "Leafcrest").

## Engineering terms

- **Config** — the source of truth for all bodies, calendars, names, and lore.
- **Authored event** — a hand-crafted fact, the only persisted source of truth besides config.
- **Derived data** — anything computable from config (phases, conjunctions, ephemerides); regenerable, cacheable, never authoritative.
- **Message unit** — a defined, typed, snake_case return shape (DTO) validated against its meta-definition.
- **Lore overlay** — culture/language-specific names and observances applied to the computed model via translators.
- **Seeded generator** — a deterministic pseudo-random function keyed on the pulse (e.g., for Kanka),
  regenerable rather than stored.

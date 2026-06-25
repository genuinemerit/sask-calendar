"""Sky-scene composition and text rendering (SPEC-013).

get_sky_scene(pulse, config):
  Composes the full sky scene from existing engine surfaces:
  - season from SPEC-004; bodies above the horizon from SPEC-007/008;
  - visible comets and Spark from SPEC-011;
  - visible fixed stars and active House from SPEC-010;
  - co-fullness tonight and next from SPEC-012.

render_night_summary(scene, config):
  Deterministic plain-prose description of the scene.

render_image_prompt(scene, config, style_id=None):
  Night summary with the selected style's directives appended.
  No AI or network call is made; output is text only.
"""

from __future__ import annotations

from sask.calendar.apparitions import get_apparitions
from sask.calendar.bodies import all_body_states
from sask.calendar.lunar import (
    DEFAULT_COFULLNESS_HORIZON_DAYS,
    get_cofullness,
    next_cofullness,
)
from sask.calendar.season import season_info
from sask.calendar.sky import all_sky_positions
from sask.calendar.stars import get_star_context
from sask.config_loader import AppConfig
from sask.message import (
    BodyInScene,
    BodyState,
    CofullnessTonightRef,
    HouseRef,
    NextCofullnessRef,
    SkyPosition,
    SkyScene,
    StarInScene,
)

_COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

_SEASON_MOOD: dict[str, str] = {
    "greening": "A greening night: the air carries new growth and lengthening light.",
    "blazing": "A blazing night: summer warmth, short darkness, the sky vivid overhead.",
    "withering": "A withering night: the harvest season, the air cooling, darkness returning.",
    "stillness": "A night of stillness: deep winter, the sky long and cold.",
}


def _direction_label(altitude_deg: float, azimuth_deg: float) -> str:
    """Compass direction plus altitude band from horizontal coordinates."""
    compass_idx = int((azimuth_deg + 22.5) / 45.0) % 8
    compass = _COMPASS[compass_idx]
    if altitude_deg < 20.0:
        height = "low"
    elif altitude_deg < 55.0:
        height = "mid"
    else:
        height = "high"
    return f"{compass} {height}"


def _phase_label(synodic_frac: float) -> str:
    """Named lunar phase from synodic fraction [0, 1)."""
    if synodic_frac < 0.0625 or synodic_frac >= 0.9375:
        return "new"
    if synodic_frac < 0.1875:
        return "waxing crescent"
    if synodic_frac < 0.3125:
        return "first quarter"
    if synodic_frac < 0.4375:
        return "waxing gibbous"
    if synodic_frac < 0.5625:
        return "full"
    if synodic_frac < 0.6875:
        return "waning gibbous"
    if synodic_frac < 0.8125:
        return "last quarter"
    return "waning crescent"


def get_sky_scene(
    pulse: int,
    config: AppConfig,
    *,
    body_states: tuple[BodyState, ...] | None = None,
    sky_positions: tuple[SkyPosition, ...] | None = None,
) -> SkyScene:
    """Compose the full sky scene for the given pulse.

    body_states/sky_positions are computed internally if omitted. A caller
    that already has them for this exact pulse (e.g. get_sky_series, which
    also needs them for the kinematic ephemeris renderer) can pass them in
    to avoid recomputing - the result is identical either way.
    """
    si = season_info(pulse, config)

    if body_states is None:
        body_states = all_body_states(pulse, config)
    if sky_positions is None:
        sky_positions = all_sky_positions(pulse, body_states, config)
    sky_pos_map = {sp.name: sp for sp in sky_positions}
    body_cfg_map = {b.name: b for b in config.bodies}

    bodies_up: list[BodyInScene] = []

    # Moons and planets above the horizon and visually detectable (SPEC-007/008)
    for bs in body_states:
        sp = sky_pos_map[bs.name]
        if not sp.above_horizon or not bs.is_visible:
            continue
        bodies_up.append(
            BodyInScene(
                id=bs.name.lower(),
                name=bs.name,
                body_type=bs.body_type,
                direction=_direction_label(sp.altitude_deg, sp.azimuth_deg),
                altitude=sp.altitude_deg,
                color=body_cfg_map[bs.name].apparent_color,
                brightness=body_cfg_map[bs.name].albedo * bs.illuminated_fraction,
                phase=_phase_label(bs.synodic_fraction),
            )
        )

    # Visible comets (SPEC-011) — no orbital position available; altitude is nominal
    app = get_apparitions(pulse, config)
    for comet_info in app.comets_visible:
        bodies_up.append(
            BodyInScene(
                id=comet_info.id,
                name=comet_info.name,
                body_type="comet",
                direction="above horizon",
                altitude=45.0,
                color=comet_info.color,
                brightness=comet_info.visibility,
                phase="tail visible",
            )
        )

    # Spark (SPEC-011) — shown near its host moon if that moon is above the horizon
    if app.spark.visible:
        host_body = next(
            (
                b
                for b in config.bodies
                if b.name.lower() == config.spark.host_moon.lower()
            ),
            None,
        )
        if host_body and sky_pos_map[host_body.name].above_horizon:
            sp = sky_pos_map[host_body.name]
            direction = _direction_label(sp.altitude_deg, sp.azimuth_deg)
            altitude = sp.altitude_deg
        else:
            direction = "above horizon"
            altitude = 45.0
        bodies_up.append(
            BodyInScene(
                id=config.spark.id,
                name="the Spark",
                body_type="spark",
                direction=direction,
                altitude=altitude,
                color=config.spark.color,
                brightness=app.spark.visibility,
                phase="glimpsed",
            )
        )

    # Stars and houses (SPEC-010)
    sc = get_star_context(pulse, config)
    star_cfg_map = {s.id: s for s in config.stars}
    stars_up = tuple(
        StarInScene(
            id=fs.id,
            name=fs.name,
            direction=star_cfg_map[fs.id].position,
        )
        for fs in sc.visible_fixed_stars
    )
    active_house = HouseRef(
        id=sc.house_of_the_equinox.id,
        name=sc.house_of_the_equinox.name,
    )
    circumpolar_houses = tuple(
        HouseRef(id=h.id, name=h.name) for h in sc.circumpolar_houses
    )

    # Co-fullness this Astro day and next (SPEC-012)
    ppd = config.time_constants.pulses_per_day
    today_midnight = (pulse // ppd) * ppd

    tonight_events = get_cofullness(today_midnight, today_midnight + ppd - 1, config)
    co_fullness_tonight: CofullnessTonightRef | None = None
    if tonight_events:
        ev = tonight_events[0]
        # Observable if any near-full moon is already above the horizon or will
        # rise before the end of the current Astro day. Illumination changes
        # slowly enough that a moon near-full at midnight remains near-full at rise.
        observable = any(
            sky_pos_map[mid.capitalize()].above_horizon
            or (
                sky_pos_map[mid.capitalize()].rise_pulse is not None
                and sky_pos_map[mid.capitalize()].rise_pulse < today_midnight + ppd
            )
            for mid in ev.moons
        )
        co_fullness_tonight = CofullnessTonightRef(
            count=ev.count, moons=ev.moons, observable=observable
        )

    next_start = today_midnight + ppd
    nev = next_cofullness(next_start, config)
    if nev is not None:
        next_cofullness_ref = NextCofullnessRef(
            pulse=nev.pulse, count=nev.count, moons=nev.moons
        )
    else:
        # Sentinel: no co-fullness found within the horizon
        next_cofullness_ref = NextCofullnessRef(
            pulse=next_start + DEFAULT_COFULLNESS_HORIZON_DAYS * ppd,
            count=0,
            moons=(),
        )

    return SkyScene(
        pulse=pulse,
        season=si.season_id,
        bodies_up=tuple(bodies_up),
        stars_up=stars_up,
        active_house=active_house,
        circumpolar_houses=circumpolar_houses,
        co_fullness_tonight=co_fullness_tonight,
        next_co_fullness=next_cofullness_ref,
    )


def render_night_summary(scene: SkyScene, config: AppConfig) -> str:
    """Deterministic plain-prose description of the sky scene."""
    lines: list[str] = []

    lines.append(_SEASON_MOOD.get(scene.season, f"Season: {scene.season}."))

    moons = [b for b in scene.bodies_up if b.body_type == "moon"]
    if moons:
        descs = [f"{b.name} ({b.color}, {b.phase}) {b.direction}" for b in moons]
        lines.append("Moons above the horizon: " + "; ".join(descs) + ".")
    else:
        lines.append("No moons are above the horizon.")

    planets = [b for b in scene.bodies_up if b.body_type == "planet"]
    if planets:
        descs = [f"{b.name} ({b.color}) {b.direction}" for b in planets]
        lines.append("Wanderers visible: " + "; ".join(descs) + ".")

    for c in [b for b in scene.bodies_up if b.body_type == "comet"]:
        lines.append(f"The comet {c.name} traces the sky with a {c.color} tail.")

    for s in [b for b in scene.bodies_up if b.body_type == "spark"]:
        lines.append(f"The Spark glimmers briefly, {s.direction}.")

    house_line = f"The active House of the Equinox is {scene.active_house.name}."
    n = len(scene.stars_up)
    if n:
        star_list = ", ".join(s.name for s in scene.stars_up[:3])
        if n > 3:
            more = n - 3
            star_list += f" and {more} other{'s' if more > 1 else ''}"
        verb = "are" if n != 1 else "is"
        noun = "stars" if n != 1 else "star"
        house_line += f" {n} fixed {noun} {verb} visible, including {star_list}."
    lines.append(house_line)

    if scene.co_fullness_tonight:
        moon_names = ", ".join(m.capitalize() for m in scene.co_fullness_tonight.moons)
        c = scene.co_fullness_tonight.count
        obs = "" if scene.co_fullness_tonight.observable else " (below the horizon)"
        lines.append(
            f"This day, {c} moon{'s' if c != 1 else ''} are near-full together: "
            f"{moon_names}{obs}."
        )

    ppd = config.time_constants.pulses_per_day
    days = max(0, (scene.next_co_fullness.pulse - scene.pulse + ppd - 1) // ppd)
    lines.append(
        f"Next night of co-fullness: {days} day{'s' if days != 1 else ''} away."
    )

    return " ".join(lines)


def render_image_prompt(
    scene: SkyScene, config: AppConfig, style_id: str | None = None
) -> str:
    """Night summary with the selected style's image-generation directives appended.

    No AI or network call is made. Output is deterministic text only.
    """
    effective_id = (
        style_id if style_id is not None else config.sky_style_settings.default_style
    )
    style = next(s for s in config.sky_styles if s.id == effective_id)

    summary = render_night_summary(scene, config)

    directives = [style.medium, style.palette, style.composition]
    if style.extra:
        directives.append(style.extra)

    return f"{summary}\n\nImage style: {'. '.join(directives)}."

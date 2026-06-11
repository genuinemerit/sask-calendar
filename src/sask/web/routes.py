"""Route handlers for the sask web UI (SPEC-005, SPEC-009).

All engine calls go through message-unit functions (pulse_info, body_state,
sky_position, etc.) and return typed message units. No engine internals are
accessed directly from routes; lore overlay (color, rings, notes) is read
from AppConfig and passed to the translator, not mixed into engine calls.
"""

from __future__ import annotations

from flask import Blueprint, current_app, render_template, request

from ..bodies import all_body_states
from ..config_loader import AppConfig
from ..lunar import get_lunar_date
from ..message import CalendarDate, PulseInfo
from ..pulse import (
    astro_to_fatunik,
    astro_to_terpin,
    fatunik_to_pulse,
    pulse_info,
    terpin_to_pulse,
)
from ..scene import get_sky_scene, render_image_prompt, render_night_summary
from ..season import season_info
from ..sky import all_sky_positions, fatune_sky_position
from .translator import (
    to_moon_view,
    to_planet_view,
    to_pulse_view,
)

bp = Blueprint("main", __name__)


# ── Pulse resolution ───────────────────────────────────────────────────────────


def _resolve_pulse(
    cfg: AppConfig,
) -> tuple[int | None, str | None]:
    """Parse request args into a pulse integer, or return an error string.

    Priority: pulse > astro_day > fatunik date > terpin date.
    Returns (pulse, None) on success; (None, error_msg) on bad input;
    (None, None) when no input was given (form should render empty).
    """
    # treat empty strings (unset form fields) the same as absent
    pulse_p = request.args.get("pulse") or None
    astro_day_p = request.args.get("astro_day") or None
    fat_y = request.args.get("fatunik_year") or None
    fat_m = request.args.get("fatunik_month") or None
    fat_d = request.args.get("fatunik_day") or None
    ter_y = request.args.get("terpin_year") or None
    ter_m = request.args.get("terpin_month") or None
    ter_d = request.args.get("terpin_day") or None

    if pulse_p is not None:
        try:
            return int(round(float(pulse_p))), None
        except ValueError:
            return None, f"Invalid pulse value: {pulse_p!r} — enter a number."

    if astro_day_p is not None:
        try:
            day = int(astro_day_p)
            return (day - 1) * cfg.time_constants.pulses_per_day, None
        except ValueError:
            return None, f"Invalid Astro day: {astro_day_p!r} — enter an integer."

    if fat_y and fat_m and fat_d:
        try:
            date = CalendarDate("fatunik", int(fat_y), int(fat_m), int(fat_d))
            return fatunik_to_pulse(date, cfg), None
        except (ValueError, KeyError) as exc:
            return None, f"Invalid Fatunik date: {exc}"

    if ter_y and ter_m and ter_d:
        try:
            date = CalendarDate("terpin", int(ter_y), int(ter_m), int(ter_d))
            return terpin_to_pulse(date, cfg), None
        except (ValueError, KeyError) as exc:
            return None, f"Invalid Terpin date: {exc}"

    return None, None


# ── Routes ─────────────────────────────────────────────────────────────────────


@bp.route("/")
def index() -> str:
    cfg = current_app.config["SASK_CONFIG"]
    default_pulse = cfg.timeline.story_now_pulse

    view = None
    error = None
    pulse_param = request.args.get("pulse")

    if pulse_param is not None:
        try:
            pulse = round(float(pulse_param))
            info: PulseInfo = pulse_info(pulse, cfg)
            view = to_pulse_view(info)
        except ValueError:
            error = f"Invalid pulse value: {pulse_param!r} — enter a number."

    return render_template(
        "index.html",
        view=view,
        error=error,
        default_pulse=default_pulse,
    )


@bp.route("/moons")
def moons() -> str:
    cfg: AppConfig = current_app.config["SASK_CONFIG"]
    pulse, error = _resolve_pulse(cfg)

    moon_views = None
    fatune_pos = None
    fatunik_date = terpin_date = None
    queried_astro_day = None
    time_of_day = None

    if pulse is not None and error is None:
        ppd = cfg.time_constants.pulses_per_day
        queried_astro_day = pulse // ppd + 1
        day_offset = pulse % ppd
        h, rem = day_offset // 3600, day_offset % 3600
        time_of_day = f"{h:02d}:{rem // 60:02d}:{rem % 60:02d}"
        all_states = all_body_states(pulse, cfg)
        all_positions = all_sky_positions(pulse, all_states, cfg)
        fatune_pos = fatune_sky_position(pulse, cfg.gavor, cfg.time_constants)

        body_cfg_map = {b.name: b for b in cfg.bodies}
        moon_views = [
            to_moon_view(state, pos, body_cfg_map[state.name].notes or "")
            for state, pos in zip(all_states, all_positions)
            if state.body_type == "moon"
        ]
        fatunik_date = astro_to_fatunik(pulse, cfg)
        terpin_date = astro_to_terpin(pulse, cfg)

    return render_template(
        "moons.html",
        moon_views=moon_views,
        fatune_pos=fatune_pos,
        fatunik_date=fatunik_date,
        terpin_date=terpin_date,
        time_of_day=time_of_day,
        error=error,
        queried_pulse=pulse,
        queried_astro_day=queried_astro_day,
    )


@bp.route("/planets")
def planets() -> str:
    cfg: AppConfig = current_app.config["SASK_CONFIG"]
    pulse, error = _resolve_pulse(cfg)

    planet_views = None
    fatune_pos = None
    fatunik_date = terpin_date = None
    queried_astro_day = None

    if pulse is not None and error is None:
        queried_astro_day = pulse // cfg.time_constants.pulses_per_day + 1
        all_states = all_body_states(pulse, cfg)
        all_positions = all_sky_positions(pulse, all_states, cfg)
        fatune_pos = fatune_sky_position(pulse, cfg.gavor, cfg.time_constants)

        body_cfg_map = {b.name: b for b in cfg.bodies}
        planet_views = [
            to_planet_view(
                state,
                pos,
                apparent_color=body_cfg_map[state.name].apparent_color,
                rings=body_cfg_map[state.name].rings,
                visible_moons=body_cfg_map[state.name].visible_moons,
                notes=body_cfg_map[state.name].notes or "",
            )
            for state, pos in zip(all_states, all_positions)
            if state.body_type == "planet"
        ]
        fatunik_date = astro_to_fatunik(pulse, cfg)
        terpin_date = astro_to_terpin(pulse, cfg)

    return render_template(
        "planets.html",
        planet_views=planet_views,
        fatune_pos=fatune_pos,
        fatunik_date=fatunik_date,
        terpin_date=terpin_date,
        error=error,
        queried_pulse=pulse,
        queried_astro_day=queried_astro_day,
    )


@bp.route("/sky")
def sky() -> str:
    cfg: AppConfig = current_app.config["SASK_CONFIG"]
    ppd = cfg.time_constants.pulses_per_day
    pulse, error = _resolve_pulse(cfg)

    scene = None
    lunar_entries = None
    si = None
    moons_up: list = []
    planets_up: list = []
    apparitions_up: list = []
    night_summary = None
    image_prompt = None
    cofullness_days = None
    time_of_day = None
    fatunik_date = terpin_date = None
    queried_astro_day = None

    if pulse is not None and error is None:
        queried_astro_day = pulse // ppd + 1
        day_offset = pulse % ppd
        h, m, s = day_offset // 3600, (day_offset % 3600) // 60, day_offset % 60
        time_of_day = f"{h:02d}:{m:02d}:{s:02d}"

        fatunik_date = astro_to_fatunik(pulse, cfg)
        terpin_date = astro_to_terpin(pulse, cfg)

        lunar_entries = [
            (cal, get_lunar_date(pulse, cal.id, cfg)) for cal in cfg.lunar_calendars
        ]

        si = season_info(pulse, cfg)
        scene = get_sky_scene(pulse, cfg)
        night_summary = render_night_summary(scene, cfg)
        image_prompt = render_image_prompt(scene, cfg)

        moons_up = [b for b in scene.bodies_up if b.body_type == "moon"]
        planets_up = [b for b in scene.bodies_up if b.body_type == "planet"]
        apparitions_up = [
            b for b in scene.bodies_up if b.body_type in ("comet", "spark")
        ]
        cofullness_days = max(
            0, (scene.next_co_fullness.pulse - pulse + ppd - 1) // ppd
        )

    return render_template(
        "sky.html",
        error=error,
        queried_pulse=pulse,
        queried_astro_day=queried_astro_day,
        fatunik_date=fatunik_date,
        terpin_date=terpin_date,
        time_of_day=time_of_day,
        lunar_entries=lunar_entries,
        si=si,
        scene=scene,
        moons_up=moons_up,
        planets_up=planets_up,
        apparitions_up=apparitions_up,
        night_summary=night_summary,
        image_prompt=image_prompt,
        cofullness_days=cofullness_days,
    )

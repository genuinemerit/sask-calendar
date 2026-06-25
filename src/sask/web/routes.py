"""Route handlers for the sask web UI (SPEC-005, SPEC-009, SPEC-016, SPEC-017).

All engine calls go through message-unit functions (pulse_info, body_state,
sky_position, etc.) and return typed message units. No engine internals are
accessed directly from routes; lore overlay (color, rings, notes) is read
from AppConfig and passed to the translator, not mixed into engine calls.
"""

from __future__ import annotations

from flask import (
    Blueprint,
    Response,
    current_app,
    make_response,
    render_template,
    request,
)

from sask.asset.retrieval import AssetNotFoundError, fetch_payload, resolve_descriptor
from sask.calendar.bodies import all_body_states
from sask.calendar.ephemeris import (
    get_sky_series,
    render_kinematic_json,
    render_scribal_json,
)
from sask.calendar.lore import render_lore_date, render_lore_time
from sask.calendar.lunar import get_lunar_date
from sask.calendar.pulse import (
    astro_to_fatunik,
    astro_to_terpin,
    fatunik_to_pulse,
    pulse_info,
    terpin_to_pulse,
)
from sask.calendar.scene import get_sky_scene, render_image_prompt, render_night_summary
from sask.calendar.season import season_info
from sask.calendar.sky import all_sky_positions, fatune_sky_position

from ..config_loader import AppConfig
from ..message import CalendarDate, PulseInfo
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


def _resolve_endpoint(
    prefix: str,
    cfg: AppConfig,
) -> tuple[int | None, str | None]:
    """Like _resolve_pulse but with prefixed query param names (e.g. 'start_').

    Priority: {prefix}pulse > {prefix}astro_day > fatunik date > terpin date.
    """
    pulse_p = request.args.get(f"{prefix}pulse") or None
    astro_day_p = request.args.get(f"{prefix}astro_day") or None
    fat_y = request.args.get(f"{prefix}fatunik_year") or None
    fat_m = request.args.get(f"{prefix}fatunik_month") or None
    fat_d = request.args.get(f"{prefix}fatunik_day") or None
    ter_y = request.args.get(f"{prefix}terpin_year") or None
    ter_m = request.args.get(f"{prefix}terpin_month") or None
    ter_d = request.args.get(f"{prefix}terpin_day") or None

    if pulse_p is not None:
        try:
            return int(round(float(pulse_p))), None
        except ValueError:
            return None, f"Invalid {prefix}pulse {pulse_p!r} — enter a number."

    if astro_day_p is not None:
        try:
            day = int(astro_day_p)
            return (day - 1) * cfg.time_constants.pulses_per_day, None
        except ValueError:
            return (
                None,
                f"Invalid {prefix}astro_day {astro_day_p!r} — enter an integer.",
            )

    if fat_y and fat_m and fat_d:
        try:
            date = CalendarDate("fatunik", int(fat_y), int(fat_m), int(fat_d))
            return fatunik_to_pulse(date, cfg), None
        except (ValueError, KeyError) as exc:
            return None, f"Invalid {prefix}Fatunik date: {exc}"

    if ter_y and ter_m and ter_d:
        try:
            date = CalendarDate("terpin", int(ter_y), int(ter_m), int(ter_d))
            return terpin_to_pulse(date, cfg), None
        except (ValueError, KeyError) as exc:
            return None, f"Invalid {prefix}Terpin date: {exc}"

    return None, None


# ── Routes ─────────────────────────────────────────────────────────────────────


@bp.route("/health")
def health() -> Response:
    """Liveness check — process up and responding, no engine/config dependency."""
    return make_response({"status": "ok"}, 200)


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
            to_moon_view(
                state,
                pos,
                body_cfg_map[state.name].notes or "",
                albedo=body_cfg_map[state.name].albedo,
            )
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
    fatunik_lore_time = terpin_lore_time = None
    fatunik_lore_date = terpin_lore_date = None
    lore_lunar_dates: list[tuple] = []

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

        if cfg.lore_time.enabled:
            fatunik_lore_time = render_lore_time(pulse, "fatunik", cfg)
            terpin_lore_time = render_lore_time(pulse, "terpin", cfg)
            fatunik_lore_date = render_lore_date(fatunik_date, "fatunik_solar", cfg)
            terpin_lore_date = render_lore_date(terpin_date, "terpin_solar", cfg)
            lore_lunar_dates = [
                (cal, ld, render_lore_date(ld, cal.id, cfg))
                for cal, ld in lunar_entries
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
        lore_enabled=cfg.lore_time.enabled,
        fatunik_lore_time=fatunik_lore_time,
        terpin_lore_time=terpin_lore_time,
        fatunik_lore_date=fatunik_lore_date,
        terpin_lore_date=terpin_lore_date,
        lore_lunar_dates=lore_lunar_dates,
    )


def _pulse_time_of_day(pulse: int, ppd: int) -> str:
    off = pulse % ppd
    h, m, s = off // 3600, (off % 3600) // 60, off % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


@bp.route("/ephemeris")
def ephemeris() -> str:
    cfg: AppConfig = current_app.config["SASK_CONFIG"]
    ppd = cfg.time_constants.pulses_per_day

    # Start resolves from whichever input type is supplied (pulse priority).
    start_pulse, start_err = _resolve_endpoint("start_", cfg)
    error = start_err

    # End mode:
    #   Pulse mode  — end_pulse supplied directly via "end_pulse" param.
    #   Date mode   — end_pulse computed as start + duration_days × ppd.
    # The presence of "end_pulse" in the query string selects Pulse mode.
    end_pulse_raw = request.args.get("end_pulse") or None
    duration_days_p = request.args.get("duration_days") or None
    step_min_p = request.args.get("step_minutes") or None
    pulse_mode = end_pulse_raw is not None

    end_pulse: int | None = None
    duration_days: int | None = None

    if pulse_mode:
        try:
            end_pulse = int(round(float(end_pulse_raw)))  # type: ignore[arg-type]
        except ValueError:
            error = error or f"Invalid end_pulse {end_pulse_raw!r} — enter a number."

    profile = request.args.get("profile", "scribal")
    step_pulses = None
    series = None
    scribal_preview = None
    kinematic_preview = None

    # Cross-calendar equivalents for cross-populating all input fields.
    start_astro_day = start_fatunik_date = start_terpin_date = start_time_of_day = None
    end_astro_day = end_fatunik_date = end_terpin_date = end_time_of_day = None

    if start_pulse is not None:
        start_astro_day = start_pulse // ppd + 1
        start_time_of_day = _pulse_time_of_day(start_pulse, ppd)
        start_fatunik_date = astro_to_fatunik(start_pulse, cfg)
        start_terpin_date = astro_to_terpin(start_pulse, cfg)

    # Validate and generate when any relevant field has been submitted.
    any_input = bool(
        start_pulse is not None
        or end_pulse_raw is not None
        or duration_days_p is not None
        or step_min_p is not None
    )

    if error is None and any_input:
        if start_pulse is None:
            error = "Start time is required."
        elif step_min_p is None:
            error = "Step (Astro minutes) is required."
        else:
            try:
                step_pulses = int(step_min_p) * 60
            except ValueError:
                error = f"Invalid step_minutes {step_min_p!r} — enter an integer."

            if error is None:
                if pulse_mode:
                    if end_pulse is None:
                        error = "End pulse is required."
                else:
                    if duration_days_p is None:
                        error = "Duration (Days) is required."
                    else:
                        try:
                            duration_days = int(duration_days_p)
                            if duration_days < 1:
                                error = "Duration (Days) must be at least 1."
                            else:
                                end_pulse = start_pulse + duration_days * ppd
                        except ValueError:
                            error = (
                                f"Invalid duration_days {duration_days_p!r}"
                                " — enter an integer."
                            )

        if error is None and end_pulse is not None and step_pulses is not None:
            span = end_pulse - start_pulse
            if step_pulses >= span:
                step_min = step_pulses // 60
                span_min = span // 60
                error = (
                    f"Step ({step_min} min) equals or exceeds the total duration "
                    f"({span_min} min) — reduce Step or increase Duration (Days)."
                )
            else:
                try:
                    series = get_sky_series(start_pulse, end_pulse, step_pulses, cfg)
                    preview_end = min(end_pulse, start_pulse + 4 * step_pulses)
                    preview_series = get_sky_series(
                        start_pulse, preview_end, step_pulses, cfg
                    )
                    if profile in ("scribal", "both"):
                        scribal_preview = render_scribal_json(preview_series, cfg)
                    if profile in ("kinematic", "both"):
                        kinematic_preview = render_kinematic_json(preview_series, cfg)
                except ValueError as exc:
                    error = str(exc)
                    series = None

    # Compute end cross-calendar display after end_pulse is finalised.
    if end_pulse is not None:
        end_astro_day = end_pulse // ppd + 1
        end_time_of_day = _pulse_time_of_day(end_pulse, ppd)
        end_fatunik_date = astro_to_fatunik(end_pulse, cfg)
        end_terpin_date = astro_to_terpin(end_pulse, cfg)

    return render_template(
        "ephemeris.html",
        error=error,
        pulse_mode=pulse_mode,
        start_pulse=start_pulse,
        end_pulse=end_pulse,
        duration_days=duration_days,
        start_astro_day=start_astro_day,
        end_astro_day=end_astro_day,
        start_fatunik_date=start_fatunik_date,
        end_fatunik_date=end_fatunik_date,
        start_terpin_date=start_terpin_date,
        end_terpin_date=end_terpin_date,
        start_time_of_day=start_time_of_day,
        end_time_of_day=end_time_of_day,
        step_pulses=step_pulses,
        profile=profile,
        series=series,
        scribal_preview=scribal_preview,
        kinematic_preview=kinematic_preview,
    )


@bp.route("/ephemeris/download")
def ephemeris_download() -> Response:
    cfg: AppConfig = current_app.config["SASK_CONFIG"]

    try:
        start_pulse = int(request.args["start"])
        end_pulse = int(request.args["end"])
        step_pulses = int(request.args["step"])
    except (KeyError, ValueError) as exc:
        resp = make_response(f"Missing or invalid parameter: {exc}", 400)
        resp.content_type = "text/plain"
        return resp

    profile = request.args.get("profile", "scribal")
    if profile not in ("scribal", "kinematic"):
        resp = make_response(
            f"Invalid profile {profile!r} — use 'scribal' or 'kinematic'.", 400
        )
        resp.content_type = "text/plain"
        return resp

    span = end_pulse - start_pulse
    if step_pulses >= span:
        resp = make_response(
            f"step {step_pulses} pulses equals or exceeds range {span} pulses"
            " — no intermediate steps would be generated.",
            400,
        )
        resp.content_type = "text/plain"
        return resp

    try:
        series = get_sky_series(start_pulse, end_pulse, step_pulses, cfg)
    except ValueError as exc:
        resp = make_response(str(exc), 400)
        resp.content_type = "text/plain"
        return resp

    if profile == "scribal":
        body = render_scribal_json(series, cfg)
    else:
        body = render_kinematic_json(series, cfg)

    filename = f"ephemeris_{profile}_p{start_pulse}-{end_pulse}_s{step_pulses}.json"
    resp = make_response(body)
    resp.headers["Content-Type"] = "application/json"
    resp.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return resp


@bp.route("/asset/<kind>/<id>")
def get_asset(kind: str, id: str) -> Response:
    cfg: AppConfig = current_app.config["SASK_CONFIG"]

    try:
        descriptor = resolve_descriptor(kind, id, cfg)
        payload = fetch_payload(descriptor, cfg)
    except AssetNotFoundError:
        resp = make_response(f"Unknown asset: {kind}/{id}", 404)
        resp.content_type = "text/plain"
        return resp

    resp = make_response(payload.data)
    resp.content_type = payload.descriptor.content_type
    return resp

"""Route handlers for the sask web UI (SPEC-005).

All engine calls go through pulse_info() and return PulseInfo message units.
No engine internals are accessed directly from routes.
"""

from __future__ import annotations

from flask import Blueprint, current_app, render_template, request

from ..message import PulseInfo
from ..pulse import pulse_info
from .translator import to_pulse_view

bp = Blueprint("main", __name__)


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

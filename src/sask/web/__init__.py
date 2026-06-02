"""Flask application factory for the sask web UI (SPEC-005)."""

from __future__ import annotations

from pathlib import Path

from flask import Flask

from ..config_loader import load_config


def create_app(config_dir: Path | None = None) -> Flask:
    """Create and configure the Flask application.

    config_dir defaults to <project_root>/config/, detected by walking up
    from this file's location.
    """
    if config_dir is None:
        # src/sask/web/__init__.py → src/sask/web/ → src/sask/ → src/ → root
        config_dir = Path(__file__).resolve().parent.parent.parent.parent / "config"

    template_dir = Path(__file__).resolve().parent.parent / "templates"
    app = Flask(__name__, template_folder=str(template_dir))

    cfg = load_config(config_dir)
    app.config["SASK_CONFIG"] = cfg

    from .routes import bp

    app.register_blueprint(bp)

    return app

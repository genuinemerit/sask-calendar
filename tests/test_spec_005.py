"""SPEC-005 tests — UI thin vertical slice.

Covers:
  - GET / returns 200 with default pulse pre-filled
  - Pulse query renders correct engine result
  - Float pulse input is rounded to nearest integer
  - Invalid input returns 200 with an error message (no 500)
  - Rendered HTML contains no <script> tags
  - Engine source files do not import flask (layer-purity AST check)
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from sask.web import create_app

REAL_CONFIG = Path(__file__).parent.parent / "config"
PROJECT_ROOT = Path(__file__).parent.parent


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def app():
    return create_app(config_dir=REAL_CONFIG)


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


# ── HTTP smoke tests ──────────────────────────────────────────────────────────


def test_get_root_returns_200(client):
    assert client.get("/").status_code == 200


def test_default_pulse_prefilled(client):
    # story_now_pulse from config should appear as the form's default value.
    assert b"71642553600" in client.get("/").data


def test_no_script_tags(client):
    assert b"<script" not in client.get("/").data


def test_query_with_integer_pulse(client):
    resp = client.get("/?pulse=86400")
    assert resp.status_code == 200
    assert b"Astro Day" in resp.data
    assert b"86400" in resp.data


def test_query_shows_astro_day(client):
    # pulse 86400 → astro_day = 2
    resp = client.get("/?pulse=86400")
    assert b"86400" in resp.data  # pulse displayed
    # The table cell for Astro Day should contain "2"
    html = resp.data.decode()
    assert "<td>2</td>" in html


def test_float_pulse_rounded_to_int(client):
    # round(86400.7) = 86401
    resp = client.get("/?pulse=86400.7")
    assert resp.status_code == 200
    assert b"86401" in resp.data


def test_invalid_pulse_returns_200_with_error(client):
    resp = client.get("/?pulse=not_a_number")
    assert resp.status_code == 200
    assert b"Invalid" in resp.data


def test_day_pulse_offset_shown(client):
    # pulse 43200 = noon; day_pulse_offset = 43200; time_of_day = 12:00:00
    resp = client.get("/?pulse=43200")
    assert b"12:00:00" in resp.data


def test_orbital_position_shown(client):
    # pulse 0 → orbital position 0.0000%
    resp = client.get("/?pulse=0")
    assert b"0.0000%" in resp.data


# ── Layer-purity: engine must not import flask ────────────────────────────────


def _flask_imports_in(path: Path) -> list[str]:
    """Return a list of flask-related import lines found in path."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "flask" in alias.name.lower():
                    found.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if "flask" in module.lower():
                found.append(f"from {module} import ...")
    return found


@pytest.mark.parametrize(
    "rel_path",
    [
        "src/sask/pulse.py",
        "src/sask/message.py",
        "src/sask/config_loader.py",
    ],
)
def test_engine_module_has_no_flask_import(rel_path):
    hits = _flask_imports_in(PROJECT_ROOT / rel_path)
    assert hits == [], f"{rel_path} contains flask imports: {hits}"

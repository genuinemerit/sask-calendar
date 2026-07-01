"""Pytest suite for tools/helpers/make_tree.sh.

The script locates the repo root relative to its own path
(cd "$(dirname "$0")/../.."), so each test copies it into an isolated
tmp_path/tools/helpers/ tree rather than running it against the real repo —
that keeps the test from writing a stray tree.txt into the working tree.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "tools" / "helpers" / "make_tree.sh"
# Resolved once, up front: the unhappy-path test strips PATH down to
# exclude any directory containing `tree`, which on this host also strips
# /usr/bin — i.e. bash's own directory. Passing bash's absolute path keeps
# subprocess from needing to resolve "bash" via the (deliberately) reduced
# PATH.
BASH = shutil.which("bash")


def make_fake_repo(tmp_path: Path) -> Path:
    helpers_dir = tmp_path / "tools" / "helpers"
    helpers_dir.mkdir(parents=True)
    script_copy = helpers_dir / "make_tree.sh"
    shutil.copy(SCRIPT, script_copy)
    script_copy.chmod(0o755)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "placeholder.py").write_text("", encoding="utf-8")
    return script_copy


def make_stub_tree_bin(tmp_path: Path) -> Path:
    """A minimal `tree` stand-in so the test doesn't depend on it being
    installed on the host (it isn't part of tools/dev/init-dev-host.sh)."""
    bin_dir = tmp_path / "stub-bin"
    bin_dir.mkdir()
    stub = bin_dir / "tree"
    stub.write_text("#!/usr/bin/env bash\nfind . | sort\n", encoding="utf-8")
    stub.chmod(0o755)
    return bin_dir


# ── Happy path ──────────────────────────────────────────────────────────────


def test_writes_tree_txt_at_repo_root(tmp_path):
    script_copy = make_fake_repo(tmp_path)
    stub_bin_dir = make_stub_tree_bin(tmp_path)

    result = subprocess.run(
        [BASH, str(script_copy)],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PATH": f"{stub_bin_dir}{os.pathsep}{os.environ['PATH']}"},
    )

    assert result.returncode == 0, result.stderr
    output = tmp_path / "tree.txt"
    assert output.exists()
    assert "placeholder.py" in output.read_text()
    assert "Wrote" in result.stdout


# ── Unhappy path ────────────────────────────────────────────────────────────


def test_missing_tree_binary_fails_cleanly(tmp_path):
    script_copy = make_fake_repo(tmp_path)

    # PATH stripped down to just enough for bash/coreutils, no `tree`.
    bin_only_path = os.pathsep.join(
        p
        for p in os.environ.get("PATH", "").split(os.pathsep)
        if not (Path(p) / "tree").exists()
    )

    result = subprocess.run(
        [BASH, str(script_copy)],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PATH": bin_only_path},
    )

    assert result.returncode == 1
    assert "'tree' is not installed" in result.stderr
    assert not (tmp_path / "tree.txt").exists()

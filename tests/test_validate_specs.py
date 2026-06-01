"""Pytest suite for tools/validate_specs.py.

Each test builds a self-contained temp design tree (schema + one or more docs),
calls validate_specs.run(), and asserts on the returned error list.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import validate_specs  # noqa: E402


# ── Shared fixtures ────────────────────────────────────────────────────────────

DD_SCHEMA = """\
[_meta]
type = "dd"

[fields.id]
required = true
pattern  = "^DD-\\\\d{4}$"

[fields.title]
required = true

[fields.status]
required = true

[sections]
required = ["context", "decision"]
"""

VALID_DD = """\
id     = "DD-0001"
title  = "Test decision"
status = "proposed"

[context]
problem = "none"

[decision]
summary = "none"
"""


def make_design_tree(tmp_path: Path, subdir: str, schema: str, *docs: str) -> Path:
    """Write schema and docs into tmp_path/subdir; return tmp_path as design root.

    The other two required subdirs are created with empty schemas so run()
    sees a complete valid design tree.
    """
    for other in {"decisions", "reqs", "specs"} - {subdir}:
        d = tmp_path / other
        d.mkdir(parents=True)
        (d / "_schema.toml").write_text("", encoding="utf-8")
    d = tmp_path / subdir
    d.mkdir(parents=True)
    (d / "_schema.toml").write_text(schema, encoding="utf-8")
    for i, doc in enumerate(docs):
        (d / f"doc-{i:03d}.toml").write_text(doc, encoding="utf-8")
    return tmp_path


# ── Happy path ────────────────────────────────────────────────────────────────


def test_valid_document_passes(tmp_path):
    design = make_design_tree(tmp_path, "decisions", DD_SCHEMA, VALID_DD)
    assert validate_specs.run(design) == []


def test_empty_directory_passes(tmp_path):
    design = make_design_tree(tmp_path, "decisions", DD_SCHEMA)
    assert validate_specs.run(design) == []


def test_multiple_valid_documents_pass(tmp_path):
    second = VALID_DD.replace("DD-0001", "DD-0002").replace("Test decision", "Second")
    design = make_design_tree(tmp_path, "decisions", DD_SCHEMA, VALID_DD, second)
    assert validate_specs.run(design) == []


# ── Missing required field ─────────────────────────────────────────────────────


def test_missing_required_field_title(tmp_path):
    doc = 'id = "DD-0001"\nstatus = "proposed"\n[context]\n[decision]\n'
    design = make_design_tree(tmp_path, "decisions", DD_SCHEMA, doc)
    errors = validate_specs.run(design)
    assert any("missing required field 'title'" in e for e in errors)


def test_missing_required_field_id(tmp_path):
    doc = 'title = "x"\nstatus = "proposed"\n[context]\n[decision]\n'
    design = make_design_tree(tmp_path, "decisions", DD_SCHEMA, doc)
    errors = validate_specs.run(design)
    assert any("missing required field 'id'" in e for e in errors)


# ── Bad id pattern ─────────────────────────────────────────────────────────────


def test_id_too_few_digits(tmp_path):
    doc = 'id = "DD-001"\ntitle = "x"\nstatus = "y"\n[context]\n[decision]\n'
    design = make_design_tree(tmp_path, "decisions", DD_SCHEMA, doc)
    errors = validate_specs.run(design)
    assert any("does not match pattern" in e for e in errors)


def test_id_wrong_prefix(tmp_path):
    doc = 'id = "XX-0001"\ntitle = "x"\nstatus = "y"\n[context]\n[decision]\n'
    design = make_design_tree(tmp_path, "decisions", DD_SCHEMA, doc)
    errors = validate_specs.run(design)
    assert any("does not match pattern" in e for e in errors)


def test_id_non_numeric(tmp_path):
    doc = 'id = "DD-ABCD"\ntitle = "x"\nstatus = "y"\n[context]\n[decision]\n'
    design = make_design_tree(tmp_path, "decisions", DD_SCHEMA, doc)
    errors = validate_specs.run(design)
    assert any("does not match pattern" in e for e in errors)


# ── Missing required section ───────────────────────────────────────────────────


def test_missing_section_decision(tmp_path):
    doc = 'id = "DD-0001"\ntitle = "x"\nstatus = "y"\n[context]\nproblem = "p"\n'
    design = make_design_tree(tmp_path, "decisions", DD_SCHEMA, doc)
    errors = validate_specs.run(design)
    assert any("missing required section '[decision]'" in e for e in errors)


def test_missing_section_context(tmp_path):
    doc = 'id = "DD-0001"\ntitle = "x"\nstatus = "y"\n[decision]\nsummary = "s"\n'
    design = make_design_tree(tmp_path, "decisions", DD_SCHEMA, doc)
    errors = validate_specs.run(design)
    assert any("missing required section '[context]'" in e for e in errors)


# ── Unparseable TOML ───────────────────────────────────────────────────────────


def test_unparseable_toml(tmp_path):
    design = make_design_tree(tmp_path, "decisions", DD_SCHEMA, "this = [broken toml}")
    errors = validate_specs.run(design)
    assert any("parse error" in e for e in errors)


# ── Infrastructure errors ──────────────────────────────────────────────────────


def test_missing_schema(tmp_path):
    d = tmp_path / "decisions"
    d.mkdir()
    errors = validate_specs.run(tmp_path)
    assert any("missing schema" in e for e in errors)


def test_missing_directory(tmp_path):
    errors = validate_specs.run(tmp_path)
    assert any("directory missing" in e for e in errors)


def test_corrupted_schema(tmp_path):
    d = tmp_path / "decisions"
    d.mkdir()
    (d / "_schema.toml").write_text("this = [broken}", encoding="utf-8")
    errors = validate_specs.run(tmp_path)
    assert any("schema parse error" in e for e in errors)

"""Validate dd, req, and spec TOML files against their per-type schemas.

Exit codes:
  0 — all files valid
  1 — one or more files invalid
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESIGN = ROOT / "design"
SCHEMA_FILE = "_schema.toml"

_SUBDIRS = [
    ("decisions", "Decisions"),
    ("reqs", "Requirements"),
    ("specs", "Specifications"),
]


def _load_toml(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def validate_doc(doc: dict, schema: dict, path: Path) -> list[str]:
    """Check a single document against its schema; return error strings."""
    errors: list[str] = []

    for field_name, field_spec in schema.get("fields", {}).items():
        if field_spec.get("required") and field_name not in doc:
            errors.append(f"{path.name}: missing required field '{field_name}'")
            continue
        if field_name in doc and "pattern" in field_spec:
            value = str(doc[field_name])
            if not re.fullmatch(field_spec["pattern"], value):
                errors.append(
                    f"{path.name}: '{field_name}' value '{value}' "
                    f"does not match pattern '{field_spec['pattern']}'"
                )

    for section in schema.get("sections", {}).get("required", []):
        if section not in doc:
            errors.append(f"{path.name}: missing required section '[{section}]'")

    return errors


def validate_dir(dir_path: Path, label: str) -> list[str]:
    """Validate all non-schema TOML files in dir_path; return error strings."""
    errors: list[str] = []
    schema_path = dir_path / SCHEMA_FILE

    if not schema_path.exists():
        errors.append(f"{label}: missing schema at {schema_path}")
        return errors

    try:
        schema = _load_toml(schema_path)
    except Exception as e:
        errors.append(f"{label}: schema parse error: {e}")
        return errors

    for doc_path in sorted(dir_path.glob("*.toml")):
        if doc_path.name == SCHEMA_FILE:
            continue
        try:
            doc = _load_toml(doc_path)
        except Exception as e:
            errors.append(f"{label}: {doc_path.name}: parse error: {e}")
            continue
        errors.extend(validate_doc(doc, schema, doc_path))

    return errors


def run(design_root: Path) -> list[str]:
    """Validate all design docs under design_root; return list of error strings."""
    all_errors: list[str] = []
    for subdir, label in _SUBDIRS:
        dir_path = design_root / subdir
        if not dir_path.exists():
            all_errors.append(f"{label}: directory missing: {dir_path}")
            continue
        all_errors.extend(validate_dir(dir_path, label))
    return all_errors


def main() -> int:
    errors = run(DESIGN)
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    print("All spec files valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

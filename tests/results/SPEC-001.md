# Test results: SPEC-001

**Spec:** SPEC-001 — Scaffold sask repository and development environment
**Date:** 2026-06-01
**Status:** Partial — host-side tests pass; VM smoke tests deferred

---

## Host-side tests (Ubuntu host)

### pytest tests/test_validate_specs.py

```text
$ python3 -m pytest tests/test_validate_specs.py -v
14 passed in 0.12s
```

Status: PASS — 14 tests (spec anticipated 13; `test_corrupted_schema` added during
implementation, bringing the total to 14).

### python tools/validate_specs.py

```text
$ python3 tools/validate_specs.py
All spec files valid.
```

Status: PASS

### git check-ignore (REQ-SEC-002)

```text
$ git check-ignore -v secrets/some-secret.key
.gitignore:17:secrets/*    secrets/some-secret.key     ← ignored ✓

$ git check-ignore -v secrets/README.md
.gitignore:18:!secrets/README.md    secrets/README.md  ← negation, not ignored ✓
```

Status: PASS

---

## VM smoke tests (deferred)

These require the NixOS dev VM to be reconfigured per docs/vm-setup.md.

| Test | Status |
| --- | --- |
| `nix develop` succeeds on fresh clone | DEFERRED |
| `python3 --version` matches flake.lock pin | DEFERRED |
| `poetry --version` matches flake.lock pin | DEFERRED |
| `ruff --version` runs inside devShell | DEFERRED |

---

## Acceptance criteria

| Item | Status |
| --- | --- |
| All linked requirements' acceptance criteria pass | PASS (host-side); VM criteria DEFERRED |
| First push lands on GitHub main with full tree and doc set | PENDING (push step) |
| Applying configuration.nix on the VM + clean clone reproduces a working devShell | DEFERRED |

---

## Deviations and notes

- `docs/vm-setup.md` added to deliverables (approved, outside original SPEC-001 scope).
- VM approach changed from fresh headless install to reconfiguring an existing NixOS 25.11
  KDE Plasma VM. `infra/configuration.nix` updated accordingly; spec and vm-setup.md revised.
- `flake.lock`, `poetry.lock`, and `requirements.txt` deferred to VM step.
- 14 pytest cases rather than the anticipated 13; `test_corrupted_schema` was added during
  implementation of the test suite.
- `tests/test_validate_specs.py::make_design_tree` helper fixed to create all three required
  subdirs with empty schemas, so happy-path tests see a complete valid design tree.

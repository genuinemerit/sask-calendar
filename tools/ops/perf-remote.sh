#!/usr/bin/env bash
# SPEC-025 — remote performance re-validation, one repeatable act (REQ-OPS-016).
#
# Two measurements, merged into one dated, host-stamped result:
#   1. On-droplet engine timing over SSH (tools/ops/perf_engine.py) — no
#      Caddy, network, or rate limit in the path; the authoritative
#      per-core number. The same script also runs locally for an
#      apples-to-apples comparison.
#   2. End-to-end HTTP against the live domain (tools/ops/perf_http.py) —
#      the four interactive pages plus a couple of spaced
#      ephemeris-download samples, staying well inside the 4-events/minute
#      download budget.
#
# Non-destructive: no rate-limit change, no dependency added to the
# production venv, and the droplet-side timing script is removed (via a
# trap, even on failure) before this script exits.
#
# Run from the dev host (ubuvm), repo root:
#
#   bash tools/ops/perf-remote.sh

set -euo pipefail

cd "$(dirname "$0")/../.."

BASE_URL="${SASK_BASE_URL:-https://sask.davidstitt.net}"
REMOTE_VENV_PY="/opt/sask/.venv/bin/python3"
REMOTE_SRC="/opt/sask/src"
REMOTE_CONFIG="/opt/sask/config"

echo "[1/6] Acceptance precondition..."
bash tools/ops/acceptance-test.sh
echo

echo "[2/6] Host identity (tofu output)..."
pushd infra/tofu >/dev/null
DROPLET_ID="$(tofu output -raw droplet_id)"
DROPLET_SIZE="$(tofu output -raw droplet_size)"
DROPLET_REGION="$(tofu output -raw droplet_region)"
DROPLET_VCPUS="$(tofu output -raw droplet_vcpus)"
popd >/dev/null
echo "  droplet_id=$DROPLET_ID size=$DROPLET_SIZE region=$DROPLET_REGION vcpus=$DROPLET_VCPUS"
echo

echo "[3/6] On-droplet engine timing..."
REMOTE_TMP="$(ssh sask-droplet mktemp -d)"
cleanup() {
    # sudo, not plain rm: the timed run below writes __pycache__ as root
    # (it runs via sudo too), and dave can't unlink root-owned files inside
    # a root-owned directory even within dave's own tmp dir.
    ssh sask-droplet "sudo rm -rf '$REMOTE_TMP'" >/dev/null 2>&1 || true
}
trap cleanup EXIT

scp -q tools/ops/perf_engine.py tools/ops/perf_config.py "sask-droplet:$REMOTE_TMP/"
ENGINE_REMOTE_JSON="$(mktemp)"
# /opt/sask is sask:sask, mode 0750 — dave can't read the venv or config
# directly (REQ-OPS-015 hardening); dave has passwordless sudo, and root
# can read dave's own tmp dir, so the whole invocation runs via sudo.
# PYTHONDONTWRITEBYTECODE keeps root from leaving a __pycache__ behind.
ssh sask-droplet \
    "sudo env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REMOTE_SRC $REMOTE_VENV_PY $REMOTE_TMP/perf_engine.py --config-dir $REMOTE_CONFIG" \
    >"$ENGINE_REMOTE_JSON"
echo

echo "[4/6] Local engine timing (comparison baseline)..."
ENGINE_LOCAL_JSON="$(mktemp)"
PYTHONPATH=src poetry run python3 tools/ops/perf_engine.py --config-dir config \
    >"$ENGINE_LOCAL_JSON"
echo

echo "[5/6] Remote HTTP timing (interactive + spaced ephemeris-download)..."
HTTP_REMOTE_JSON="$(mktemp)"
# A non-zero exit here means a budget check failed, not a script error —
# perf_http.py still writes --out before returning, so don't let `set -e`
# skip the merge step below; the merged results are the point of this run
# regardless of pass/fail.
PYTHONPATH=src poetry run python3 tools/ops/perf_http.py \
    --base-url "$BASE_URL" \
    --skip-preview --warmup 0 --repeats 3 \
    --download-warmup 0 --download-repeats 1 --download-delay-s 20 \
    --out "$HTTP_REMOTE_JSON" || true
echo

echo "[6/6] Merging results..."
DATE_STAMP="$(date +%F)"
RESULTS_DIR="tests/results/perf"
mkdir -p "$RESULTS_DIR"
OUT_JSON="$RESULTS_DIR/REMOTE-$DATE_STAMP.json"
OUT_MD="$RESULTS_DIR/REMOTE-$DATE_STAMP.md"

python3 - "$ENGINE_REMOTE_JSON" "$ENGINE_LOCAL_JSON" "$HTTP_REMOTE_JSON" \
    "$OUT_JSON" "$OUT_MD" "$DATE_STAMP" \
    "$DROPLET_ID" "$DROPLET_SIZE" "$DROPLET_REGION" "$DROPLET_VCPUS" "$BASE_URL" <<'PYEOF'
import json
import sys
from pathlib import Path

(
    engine_remote_path,
    engine_local_path,
    http_remote_path,
    out_json_path,
    out_md_path,
    date_stamp,
    droplet_id,
    droplet_size,
    droplet_region,
    droplet_vcpus,
    base_url,
) = sys.argv[1:]

engine_remote = json.loads(Path(engine_remote_path).read_text())
engine_local = json.loads(Path(engine_local_path).read_text())
http_remote = json.loads(Path(http_remote_path).read_text())

host = {
    "droplet_id": droplet_id,
    "size": droplet_size,
    "region": droplet_region,
    "vcpus": int(droplet_vcpus),
}

merged = {
    "date": date_stamp,
    "base_url": base_url,
    "host": host,
    "engine_remote": engine_remote,
    "engine_local": engine_local,
    "http_remote": http_remote,
}
Path(out_json_path).write_text(json.dumps(merged, indent=2) + "\n")

GROUPS = ("fast", "grid", "worst_case_render")


def engine_rows():
    local_by_label = {
        entry["label"]: entry for group in GROUPS for entry in engine_local[group]
    }
    rows = []
    for group in GROUPS:
        for entry in engine_remote[group]:
            label = entry["label"]
            remote_ms = entry["median_s"] * 1000
            local_entry = local_by_label.get(label)
            local_ms = local_entry["median_s"] * 1000 if local_entry else None
            rows.append((label, remote_ms, local_ms))
    return rows


lines = [
    f"# Remote performance re-validation — {date_stamp}",
    "",
    f"**Host:** droplet `{host['droplet_id']}`, size `{host['size']}`, "
    f"region `{host['region']}`, vcpus {host['vcpus']}",
    f"**Target:** {base_url}",
    "",
    "## Interactive pages (end-to-end HTTP, client wall-clock — informational)",
    "",
    "| label | median_ms | budget_ms | pass |",
    "| --- | --- | --- | --- |",
]
for check in http_remote["budget_checks"]:
    if "budget_ms" in check:
        lines.append(
            f"| {check['label']} | {check['median_ms']} | {check['budget_ms']} "
            f"| {'PASS' if check['pass'] else 'FAIL'} |"
        )

lines += [
    "",
    "## Ephemeris download (end-to-end HTTP, judged against REQ-OPS-010)",
    "",
    "| label | median_s | budget_s | pass |",
    "| --- | --- | --- | --- |",
]
for check in http_remote["budget_checks"]:
    if "budget_s" in check:
        lines.append(
            f"| {check['label']} | {check['median_s']} | {check['budget_s']} "
            f"| {'PASS' if check['pass'] else 'FAIL'} |"
        )

lines += [
    "",
    "## On-droplet engine timing — remote vs local (authoritative per-core cost)",
    "",
    "| label | remote_median_ms | local_median_ms |",
    "| --- | --- | --- |",
]
for label, remote_ms, local_ms in engine_rows():
    local_str = f"{local_ms:.3f}" if local_ms is not None else "n/a"
    lines.append(f"| {label} | {remote_ms:.3f} | {local_str} |")

Path(out_md_path).write_text("\n".join(lines) + "\n")
print(f"Host identity: {host}")
PYEOF

echo
printf '[DONE] Wrote %s\n       and %s\n' "$OUT_JSON" "$OUT_MD"

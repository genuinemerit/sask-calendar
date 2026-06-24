# Test results: SPEC-027

**Spec:** SPEC-027 — Deployed asset sync and rate-limited delivery
**Date:** 2026-06-24
**Status:** PASS — all acceptance criteria verified for real against
`sask.davidstitt.net`, including the manual rate-limit-trip check (run by
Dave, not Claude, per SPEC-027's own `[manual]` uat text). Accepted.

---

## Layer 1 — unit suite gate

```text
.venv/bin/pytest tests/ -q
626 passed in 1.79s
```

Confirmed before the deploy, and again after, with no regressions.

## Layer 2 — tools/acceptance-test.sh

```text
bash tools/acceptance-test.sh
[PASS]  TLS validates without -k
[PASS]  /health returns 200
[PASS]  root page contains the expected computed value (104548096103)
[PASS]  https://sask.davidstitt.net/asset/image/splash.bg returns 200
[PASS]  https://sask.davidstitt.net/asset/image/splash.bg Content-Type is image/webp

[ALL PASS] Acceptance suite complete.
```

(The script originally captured the binary response body into a shell
variable for the new asset checks, which triggered a harmless but noisy
"ignored null byte in input" warning — fixed to discard the body to a
temp file and read only `%{http_code}`, verified clean on a re-run.)

## Layer 3 — pytest acceptance suite (tests/acceptance/)

```text
.venv/bin/pytest tests/acceptance/ -v
test_health_returns_200 PASSED
test_tls_certificate_is_valid PASSED
test_root_page_renders_expected_value PASSED
test_asset_bytes_match_local PASSED
test_unknown_asset_returns_404 PASSED
5 passed in 1.00s
```

`test_asset_bytes_match_local`: sha256 of the live
`/asset/image/splash.bg` response body matches the committed
`assets/v0/image/splash.default.1920x1080.6389524a.webp` exactly.

## Layer 4 — operational tests

**Deploy run** (`bash tools/deploy.sh`, first run shipping SPEC-027):

```text
PLAY RECAP: sask-droplet : ok=35  changed=10  unreachable=0  failed=0  skipped=1
```

New tasks both fired: `app : Ensure the assets/ parent directory exists`
(changed — created `/opt/sask/assets`) and
`app : Sync the versioned assets/ data tree` (changed — synced
`assets/v0/`). Both `runtime : Restart sask service` and
`caddy : Restart caddy` handlers fired (Caddy restarted because the
Caddyfile template changed — the new `zone asset` block). No crash on
restart, confirming the catalog config and its payload files landed
together as designed.

**Idempotency:** a second consecutive `deploy.sh` reported
`ok=32 changed=0` — full convergence, including the new assets-sync task.

**Parity/isolation**, checked directly on the droplet
(`sudo find /opt/sask/assets -type f`):

```text
/opt/sask/assets/v0/audio/ambient-loop.mp3
/opt/sask/assets/v0/image/splash.default.1920x1080.6389524a.webp
/opt/sask/assets/v0/image/splash.default.480x270.eb6c6dab.webp
/opt/sask/assets/v0/image/splash.default.960x540.385a45a2.webp
/opt/sask/assets/v0/image/splash.default.thumb.320x180.762c6016.webp
/opt/sask/assets/v0/json/varkaar_questions.json
/opt/sask/assets/v0/video/ambient-video.mp4
```

Exactly the seven real catalog entries — no more, no less.
`sudo test -d /opt/sask/assets/local` confirmed absent: `assets/local/`
never leaves the controller.

**Caddy rate-limit zone**, confirmed via the rendered config on the
droplet (`sudo cat /etc/caddy/Caddyfile`):

```text
zone asset {
    match {
        path /asset/*
    }
    key {remote_host}
    events 20
    window 1m
}
```

Matches the design exactly — distinct from `zone interactive` (60/1m) and
`zone download` (4/1m).

**Delete semantics**, tested with a disposable probe asset rather than a
real catalog entry (so a mid-test inconsistency could never crash the
live catalog loader): added a probe file
(`assets/v0/json/_delete_semantics_probe.json`) together with a matching
catalog entry, deployed (`changed=4`), confirmed present on the droplet
and serving 200 at `/asset/json/delete-semantics-probe`. Removed both the
file and the catalog entry, deployed again (`changed=4`), confirmed the
file was gone from the droplet (`sudo test -f ... || echo
CORRECTLY_REMOVED`) and the route now returns a 404 response. A final
no-op deploy confirmed `changed=0` reconvergence. Full local suite (626)
and the live acceptance suite (5) both green throughout.

**Rate-limit trip** — **PASS, [manual], run by Dave:** multiple rapid
refreshes of `https://sask.davidstitt.net/asset/image/splash.bg` produced
a 429 response, confirming the `zone asset` limit (20 events/1m) is
actually enforced, not just present in the rendered config.

---

## Acceptance criteria

| Item | Status |
| --- | --- |
| A redeploy syncs assets/v0/ under app_root; assets/local/ never appears on the droplet | PASS |
| A second consecutive deploy reports changed=0 for the new sync task | PASS |
| The new sync task notifies the same restart handler as the existing src/config tasks | PASS |
| A live GET for a known (kind, id) returns 200, the catalog content_type, and matching sha256 bytes | PASS |
| A live GET for an unknown (kind, id) returns the adapter's not-found response | PASS |
| The asset Caddy rate-limit zone is active and distinct from the others | PASS (config + manual 429 trip) |
| Removing or renaming a local asset and redeploying removes/renames it on the droplet | PASS |
| tests/results/SPEC-027.md records all of the above | DONE (this file) |

---

## Deviations and notes

- During SPEC-026 implementation, the catalog's `kind` field changed from
  authored to derived (computed from each asset's top-level subdirectory
  under `ASSETS_DIR`) — see DD-0016's amended `kind_is_config` section.
  Doesn't affect SPEC-027's deploy mechanics, only how
  `asset_catalog_data.toml` entries are shaped.
- `assets/<world>.manifest.json` remains `{}` and is not part of this
  spec's sync or load path — it's a deployed-state ledger tied to a
  not-yet-built publish pipeline, out of scope per DD-0016.
- `tools/acceptance-test.sh`'s asset check was fixed during this run (see
  Layer 2) to discard the binary response body instead of capturing it in
  a shell variable.
- REQ-OPS-017/SPEC-027 flipped to "accepted" 2026-06-24 after Dave
  confirmed the rate-limit trip.

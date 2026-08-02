# PIF Action Summary, Artifacts, and Legacy Cleanup Design

Date: 2026-08-02
Status: Approved for implementation
Scope: `external/Pixel-AutoPIF` only; no DeviceMasker app changes.

## Goal

Make every canary crawl run self-explanatory in the GitHub Actions Summary,
publish both a runtime JSON mirror and a diagnostic artifact, and remove stale
legacy producer leftovers from the local PIF checkout.

## Canonical data boundary

`pif.json` on `main` remains the canonical app source. The
runtime artifact is an exact copy of the same validated JSON for run inspection
or later handoff; the Android app must not depend on artifact retention,
artifact IDs, or the Actions API.

## Workflow summary

The crawl workflow will write `$GITHUB_STEP_SUMMARY` with:

- event, ref, commit SHA, run URL, and UTC timestamp;
- crawl and validation success/failure status;
- generated entry count and model list;
- minimum/maximum security patch dates;
- before/after JSON SHA-256 values and changed/unchanged result;
- direct-main publish status when a data diff exists;
- names and retention of the uploaded artifacts.

The summary will never include Flash Station API keys, request URLs containing
keys, or raw source HTML.

## Artifact contract

The workflow uploads two artifacts with `actions/upload-artifact`:

1. `pif-runtime-${{ github.run_id }}`
   - `pif.json`, exactly the validated four-field array;
   - retention: 14 days;
   - purpose: run-scoped runtime mirror and handoff, not the app endpoint.
2. `pif-diagnostics-${{ github.run_id }}`
   - `summary.md`;
   - `data.diff`;
   - `crawl.log` and `validation.log`;
   - `metadata.txt` with non-secret hashes, counts, and statuses;
   - retention: 14 days.

Both upload steps use `if: always()` and `if-no-files-found: warn`, so a
failed crawl still leaves the available evidence without replacing committed
JSON. The job remains failed when crawling or validation fails.

## Failure and no-change behavior

- A successful unchanged crawl writes a summary and artifacts, then exits
  without a commit or pull request.
- A successful changed crawl commits only `pif.json` directly to
  `main`; no automation branch or pull request is created.
- A failed crawl or validation never commits data and still uploads diagnostics
  plus any existing runtime JSON.

## Legacy cleanup

Only the nested PIF checkout is in scope. Remove stale local-only legacy
directories and generated files:

```text
catalog/
public-keys/
schemas/
templates/
dist/
.tmp-dist/
scripts/__pycache__/
tests/__pycache__/
```

These paths contain no tracked files in the current repository. Their removal
must not touch `pif.json`, current shell scripts/tests, the root app, or any root
research report. No placeholder files will be added to preserve empty legacy
directories.

## Validation

- `actionlint` passes for both workflows;
- `bash tests/test-pixel-data.sh` passes;
- `bash scripts/validate-pixel-data.sh pif.json` passes;
- `git diff --check` passes;
- a hosted `workflow_dispatch` run shows the new Summary and both artifacts;
- nested PIF `main` contains only the intended commits and remains clean.

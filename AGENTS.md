# Pixel-AutoPIF Agent Guide

- Scope: this standalone producer only; do not edit the DeviceMasker app.
- Canonical output: `data/pif-data.json` on `main`.
- Each entry has exactly `fingerprint`, `securityPatch`, `manufacturer`, and `model`.
- Source policy: use the newest Android/Flash Station canary build; canary details
  may be documented, but filenames stay neutral.
- Supported devices: Pixel 6 and newer phones, Pixel Fold, and Pixel Tablet.
- Crawler: `scripts/crawl-pixel-data.sh`.
- Validator: `scripts/validate-pixel-data.sh`.
- Metrics helper: `scripts/pixel-data-metrics.sh`.
- Focused check: `bash tests/test-pixel-data.sh`.
- Additional checks: `bash scripts/validate-pixel-data.sh data/pif-data.json`,
  `actionlint`, and `git diff --check`.
- Scheduled/manual workflow: `.github/workflows/crawl-pixel-data.yml`.
- Validation workflow: `.github/workflows/validate.yml` runs on `main` and manually.
- The crawl workflow writes `$GITHUB_STEP_SUMMARY` and uploads run-scoped
  `pif-runtime-*` and `pif-diagnostics-*` artifacts for 14 days.
- A validated changed crawl commits only `data/pif-data.json` directly to `main`.
- No pull requests, automation branches, releases, or release assets are used.
- Failed crawls must leave the previous canonical JSON untouched.
- Never place API keys, signed URLs, or raw source HTML in summaries or artifacts.
- Keep the `CANARY` fingerprint contract and Pixel 6+ filtering intact.
- Pin GitHub Actions to full commit SHAs; Dependabot checks Actions weekly.
- Keep generated data deterministic and avoid manual/recommended/synthetic entries.
- Preserve unrelated root worktree changes and never force-push `main`.
- Commit and push only with explicit user authorization.

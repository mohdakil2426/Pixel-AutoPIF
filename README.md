# Pixel AutoPIF

Owner-controlled Pixel canary data crawler. The crawler follows the
PlayIntegrityFix discovery sequence: Android release tables, Flash Station
builds, the newest `canary` build, and the Pixel security bulletin.

This repository does not modify Play Integrity verdicts and does not contain
the Android app. It produces one generated JSON file for the app to fetch
later:

```text
data/pif-data.json
```

Each entry contains exactly four fields:

```json
{
  "fingerprint": "google/akita_beta/akita:CANARY/...:user/release-keys",
  "securityPatch": "2026-07-05",
  "manufacturer": "Google",
  "model": "Pixel 8a"
}
```

Only Pixel 6 and newer phones, Pixel Fold, and Pixel Tablet are accepted.
The crawler does not add manual profiles, recommendations, prefixes, stable
entries, or synthetic defaults.

## Local checks

Run from the repository root:

```bash
bash tests/test-pixel-data.sh
```

## Generate current data

The live crawl requires Bash, curl, Perl with the standard JSON::PP module,
grep, sed, sort, tac, and paste:

```bash
bash scripts/crawl-pixel-data.sh --output data/pif-data.json
bash scripts/validate-pixel-data.sh data/pif-data.json
```

The crawler writes a temporary file and replaces the tracked JSON only after
the complete crawl and validation succeed.

## App fetch URL

For the public repository, the future app action will fetch:

```text
https://raw.githubusercontent.com/mohdakil2426/Pixel-AutoPIF/main/data/pif-data.json
```

The app integration is intentionally separate from this repository change.
The committed JSON is the canonical app source. Each crawl also uploads a
run-scoped runtime mirror and diagnostic artifact for inspection; the app does
not depend on artifact retention or the Actions API. There are no GitHub
Releases, release assets, or signing keys.

## Automation

`.github/workflows/crawl-pixel-data.yml` runs daily at 03:17 UTC and supports
`workflow_dispatch`. It writes a detailed GitHub Actions Summary, uploads the
runtime/diagnostic artifacts, and pushes only changed `data/pif-data.json`
bytes directly to `main`. No PR or automation branch is created. A failed
crawl leaves the previous committed file untouched.

# Pixel AutoPIF

Owner-controlled Pixel canary data crawler. The crawler follows the
PlayIntegrityFix discovery sequence: Android release tables, Flash Station
builds, the newest `canary` build, and the Pixel security bulletin.

This repository does not modify Play Integrity verdicts and does not contain
the Android app. It produces one generated JSON file for the app to fetch
later:

```text
data/pif-canary.json
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
bash tests/test-canary.sh
```

## Generate current data

The live crawl requires Bash, curl, Perl with the standard JSON::PP module,
grep, sed, sort, tac, and paste:

```bash
bash scripts/crawl-canary.sh --output data/pif-canary.json
bash scripts/validate-canary.sh data/pif-canary.json
```

The crawler writes a temporary file and replaces the tracked JSON only after
the complete crawl and validation succeed.

## App fetch URL

For the public repository, the future app action will fetch:

```text
https://raw.githubusercontent.com/mohdakil2426/Pixel-AutoPIF/main/data/pif-canary.json
```

The app integration is intentionally separate from this repository change.
There are no GitHub Releases, release assets, signing keys, or workflow
artifacts required by the runtime contract.

## Automation

`.github/workflows/crawl-canary.yml` runs daily at 03:17 UTC and supports
`workflow_dispatch`. It commits `data/pif-canary.json` to `main` only when
serialized bytes change. A failed crawl leaves the previous committed file
untouched.

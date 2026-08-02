# Canary crawler operations

This repository is the owner-controlled source for the DeviceMasker Pixel
canary list. It does not publish a catalog release. GitHub Actions writes one
generated file directly to `main`:

```text
data/pif-canary.json
```

## Local validation

Run from the repository root:

```bash
bash tests/test-canary.sh
```

To perform a live crawl locally:

```bash
bash scripts/crawl-canary.sh --output data/pif-canary.json
bash scripts/validate-canary.sh data/pif-canary.json
```

The live crawler follows the same sequence as PlayIntegrityFix:

1. Fetch the Android platform versions page.
2. Select the newest version page and its full-image/OTA tables.
3. Select the table with the larger device set and pair model/product rows.
4. Filter to Pixel 6+ phones, Fold, and Tablet; append `_beta` to products.
5. Extract the Flash Station public API key from `flash.android.com`.
6. Query the builds API with `Referer: https://flash.android.com`.
7. Select the newest block marked `"canary": true`.
8. Resolve the security patch from the Pixel bulletin, using the canary date
   fallback only when an exact bulletin row is unavailable.
9. Emit exactly `fingerprint`, `securityPatch`, `manufacturer`, and `model`.

## Scheduled workflow

The `crawl-canary.yml` workflow runs at `03:17 UTC` and can also be started
manually from the Actions tab. The workflow:

1. checks out `main`;
2. runs the shell crawler into a temporary candidate path;
3. validates the complete JSON array;
4. stages only `data/pif-canary.json`;
5. exits without a commit when bytes are unchanged;
6. commits and pushes the changed file with the repository `GITHUB_TOKEN`.

The workflow uses one concurrency group so two crawls cannot publish over one
another. It does not upload an artifact, create a tag, or create a release.

## Output contract

The top-level value is a non-empty JSON array. Every object must contain
exactly these keys:

```json
[
  {
    "fingerprint": "google/akita_beta/akita:CANARY/...:user/release-keys",
    "securityPatch": "YYYY-MM-DD",
    "manufacturer": "Google",
    "model": "Pixel 8a"
  }
]
```

No manually curated, recommended, prefixed, stable, or synthetic object may
be committed. If the crawl returns no valid entries or any required value is
missing, the workflow fails before touching the tracked file.

## App boundary

The Android app will later fetch the public raw URL and adapt this four-field
array into its local profile list. It will not execute this shell crawler,
access Google directly, consume workflow artifacts, or depend on a GitHub
Release. App integration is intentionally not part of this repository change.

## Recovery

- Source/API failure: keep the previous `data/pif-canary.json` and inspect the
  failed workflow log.
- Malformed output: fix the crawler or upstream parser, run the local shell
  checks, then dispatch the workflow again.
- Unexpected model or fingerprint: do not add a manual entry; correct the
  discovery/filter logic and rerun.
- Accidental data commit: revert the generated JSON commit normally; do not
  force-push `main`.

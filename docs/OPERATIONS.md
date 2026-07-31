# Catalog operations

The scheduled update runs daily at `03:17 UTC`. Discovery never publishes a
release. It prepares one fixed automation branch for human review; a separate,
manual workflow publishes only reviewed `main` bytes through the protected
`catalog-production` environment.

## Local validation

Run from the repository root:

```powershell
python -m pip install --require-hashes -r requirements.txt
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/validate_coverage.py --templates templates/pixel-devices.json --verified data/verified-candidates.json
python scripts/build_catalog.py --templates templates/pixel-devices.json --verified data/verified-candidates.json --output dist --previous catalog/pixel-catalog-current.json
python scripts/validate_catalog.py --catalog dist/pixel-catalog-v1.json --schema schemas/pixel-catalog.schema.json
```

## Daily update and review

Trigger an unscheduled review when needed:

```powershell
gh workflow run update-catalog.yml --repo mohdakil2426/Pixel-AutoPIF
gh run list --repo mohdakil2426/Pixel-AutoPIF --workflow update-catalog.yml --limit 5
gh run watch <run-id> --repo mohdakil2426/Pixel-AutoPIF --exit-status
```

No catalog diff is a successful no-op: no commit, branch update, PR, or release
is required. When bytes change, review all of the following before merging:

- every candidate disposition and rejection reason;
- every official Google full-OTA URL and published SHA-256;
- fingerprint, Build ID, incremental, SDK metadata, and security patch
  extracted from the same OTA;
- all 35 model templates and at most the newest three retained stable builds;
- deterministic catalog bytes and an expected version change only;
- the required `producer` check on the exact PR head.

GitHub currently couples Actions-created PRs with permission for Actions to
approve reviews. Keep that broader capability disabled. If the workflow pushes
`automation/pixel-catalog-update` but cannot create the PR, the owner creates or
updates the PR with `gh pr create`/`gh pr edit`, then reviews and merges it
normally. Do not weaken branch protection to make automation merge itself.

## Protected release

After the reviewed update is merged, choose the next unused integer version and
dispatch from `main`:

```powershell
gh workflow run release-catalog.yml --repo mohdakil2426/Pixel-AutoPIF --ref main -f version=<version>
gh run list --repo mohdakil2426/Pixel-AutoPIF --workflow release-catalog.yml --limit 5
gh run watch <run-id> --repo mohdakil2426/Pixel-AutoPIF --exit-status
```

Inspect the pending `catalog-production` deployment and approve only the exact
reviewed commit/version. The job reruns tests and coverage, rebuilds canonical
bytes, signs the catalog and manifest separately, refuses an existing tag or
release, and publishes immutable assets. Existing app snapshots remain usable
when an older build rotates out.

## Independent verification

Download all four assets from an immutable `v<version>` release, then run:

```powershell
python scripts/verify_release.py `
  --manifest pixel-catalog.manifest.json `
  --manifest-signature pixel-catalog.manifest.json.sig `
  --catalog pixel-catalog-v<version>.json `
  --catalog-signature pixel-catalog-v<version>.json.sig `
  --public-key public-keys/pixel-autopif-p256-v1.spki.der.base64
gh release verify v<version> --repo mohdakil2426/Pixel-AutoPIF
```

The production public key is
`public-keys/pixel-autopif-p256-v1.spki.der.base64`. Verification must never
download, print, or expose the protected environment signing secret.

## Failure recovery

- Discovery/source failure: retain the last reviewed catalog, inspect the
  failed run artifact/log, repair with tests, and rerun update. Never publish
  partial coverage.
- Invalid candidate or unexpected diff: do not merge; correct source parsing or
  disposition data on a reviewed branch.
- Release failure before publication: keep the version unused, fix through a
  protected PR, and rerun only after review. Never replace existing immutable
  assets.
- Release exists but client verification fails: stop new releases, preserve all
  evidence, and treat it as a signing/supply-chain incident.

Permissions stay job-local. Analysis defaults to `contents: read`; only the
automation-branch job adds `contents: write` and `pull-requests: write`; release
alone gets `contents: write`. All external Actions are pinned to full commit
SHAs.

## Signing-key recovery and compromise

The provisioning-time recovery directory is temporary. Copy its encrypted key
and recovery passphrase to separate durable locations, verify recovery once,
then remove the staging directory. Never publish its private local path, commit
either value, or store both together.

Key rotation is app-update-bound. On suspected compromise:

1. disable protected releases and remove the environment secret;
2. audit published releases and preserve immutable evidence;
3. generate a new offline P-256 key and configure a new protected secret;
4. update the Android app's pinned SPKI and key ID;
5. release the updated app before publishing catalogs signed only by the new
   key;
6. resume releases after independent verification.

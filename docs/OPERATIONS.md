# Catalog operations

1. The weekly update job discovers candidates and opens/updates one review PR.
2. A maintainer reviews every candidate disposition, official OTA URL/digest,
   extracted tuple, newest-three rotation, and canonical diff.
3. After merge, an operator manually dispatches release from the protected
   default branch. The `catalog-production` environment requires a reviewer.
4. Release rebuilds from reviewed source, tests, signs exact catalog bytes,
   signs exact manifest bytes, and publishes immutable versioned assets.
5. Existing selected snapshots remain usable if a revision rotates out.

Permissions are job-local. Analysis defaults to `contents: read`; the PR job
adds `contents: write` and `pull-requests: write`; release alone gets
`contents: write`. All external actions are pinned to full commit SHAs.

Key rotation is app-update-bound. On compromise, disable releases, remove the
secret, audit releases, create a new offline P-256 key, update the app's pinned
SPKI/key ID, release the app, then resume catalog publication.

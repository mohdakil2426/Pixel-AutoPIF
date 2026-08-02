# Security policy

The repository owner is the publisher trust boundary for the generated
canary list. This design intentionally has no signing key, protected release,
release asset, or workflow-artifact runtime dependency.

The crawler still enforces basic data-quality rules before publishing:

- all requests use HTTPS and bounded timeouts;
- the Flash Station API request includes its required `Referer`;
- every entry has exactly four fields;
- the fingerprint is a Google `CANARY` fingerprint;
- the manufacturer is `Google`;
- the security patch is a valid date;
- only Pixel 6+, Fold, and Tablet models are accepted;
- failed or partial crawls never replace the committed file.

Report a crawler or repository compromise privately to the repository owner.
Do not add manually trusted entries or bypass the validator to recover from a
source/API failure. If the repository trust boundary changes in the future,
a detached signature can be added without changing the four-field payload.

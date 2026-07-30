# Pixel AutoPIF

Review-first Pixel catalog producer. It discovers
candidate builds, verifies coherent tuples from official Google full-OTA
metadata, retains the newest three stable builds per model, and emits exact-byte
JSON assets for ECDSA P-256 signing.

Nothing in this directory claims to alter Play Integrity verdicts. The Android
client consumes only a pinned-key verified last-known-good catalog.

## Local validation

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/build_catalog.py --templates templates/pixel-devices.json --verified tests/fixtures/verified-candidates.json --output dist
python scripts/validate_catalog.py --catalog dist/pixel-catalog-v1.json --schema schemas/pixel-catalog.schema.json
```

Repository creation, GitHub secrets/environments, and releases remain separate
operator-approved actions.

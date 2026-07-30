from __future__ import annotations

if __package__ in (None, ""):
    import os
    import sys

    script_directory = os.path.dirname(os.path.abspath(__file__))
    sys.path = [
        entry
        for entry in sys.path
        if os.path.abspath(entry or os.curdir) != script_directory
    ]
    sys.path.insert(0, os.path.dirname(script_directory))

import argparse
import base64
import json
from datetime import datetime
from pathlib import Path

from scripts.catalog import sha256, validate_catalog, validate_manifest
from scripts.sign_catalog import verify


def verify_release(
    manifest: bytes,
    manifest_signature: bytes,
    catalog: bytes,
    catalog_signature: bytes,
    public_spki: bytes,
    now: datetime | None = None,
) -> None:
    verify(manifest, manifest_signature, public_spki)
    manifest_value = json.loads(manifest)
    validate_manifest(manifest_value, now)
    if manifest_value["catalogSizeBytes"] != len(catalog):
        raise ValueError("catalog size mismatch")
    if manifest_value["catalogSha256"] != sha256(catalog):
        raise ValueError("catalog digest mismatch")
    verify(catalog, catalog_signature, public_spki)
    validate_catalog(json.loads(catalog))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-signature", required=True, type=Path)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--catalog-signature", required=True, type=Path)
    parser.add_argument("--public-key", required=True, type=Path)
    args = parser.parse_args()
    verify_release(
        args.manifest.read_bytes(),
        args.manifest_signature.read_bytes(),
        args.catalog.read_bytes(),
        args.catalog_signature.read_bytes(),
        base64.b64decode(args.public_key.read_text().strip()),
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import sys
from datetime import timedelta
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.catalog import canonical_bytes, load_json, parse_time, sha256, validate_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--key-id", default="pixel-autopif-p256-v1")
    args = parser.parse_args()
    path = Path(args.catalog)
    data = path.read_bytes()
    catalog = load_json(path)
    version = catalog["catalogVersion"]
    generated = parse_time(catalog["generatedAt"])
    base = (
        "https://github.com/mohdakil2426/Pixel-AutoPIF/"
        f"releases/download/v{version}"
    )
    manifest = {
        "schemaVersion": 1,
        "catalogVersion": version,
        "catalogUrl": f"{base}/{path.name}",
        "catalogSha256": sha256(data),
        "catalogSizeBytes": len(data),
        "catalogSignatureUrl": f"{base}/{path.name}.sig",
        "generatedAt": generated.isoformat().replace("+00:00", "Z"),
        "expiresAt": (generated + timedelta(days=30)).isoformat().replace("+00:00", "Z"),
        "keyId": args.key_id,
    }
    validate_manifest(manifest)
    Path(args.output).write_bytes(canonical_bytes(manifest))


if __name__ == "__main__":
    main()

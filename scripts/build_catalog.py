from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.catalog import LABELS, canonical_bytes, load_json, validate_catalog

EXCLUDED_MARKERS = ("beta", "preview", "developer", "canary")


def resolve_version(previous: dict, current: dict, templates: list[dict]) -> int:
    if previous["models"] == current["models"]:
        return previous["catalogVersion"]
    required = {item["device"] for item in templates}
    previous_devices = {item["device"] for item in previous["models"]}
    if previous_devices != required:
        if previous_devices > required:
            return previous["catalogVersion"] + 1
        return previous["catalogVersion"]
    return previous["catalogVersion"] + 1


def build_catalog(templates: list[dict], verified: list[dict], version: int, generated_at: str) -> dict:
    by_device = {item["device"]: item for item in templates}
    grouped: dict[str, list[dict]] = {}
    for candidate in verified:
        text = " ".join(str(value) for value in candidate.values()).lower()
        if candidate.get("status") != "verified" or any(
            marker in text for marker in EXCLUDED_MARKERS
        ):
            continue
        if candidate["modelKey"] not in by_device:
            continue
        grouped.setdefault(candidate["modelKey"], []).append(candidate)
    models: list[dict] = []
    global_fingerprints: set[str] = set()
    for device, candidates in sorted(grouped.items()):
        template = by_device[device]
        deduplicated: dict[str, dict] = {}
        for candidate in candidates:
            deduplicated[candidate["fingerprint"]] = candidate
        selected = sorted(
            deduplicated.values(),
            key=lambda item: (
                item["securityPatch"], item["buildId"], item["incremental"]
            ),
            reverse=True,
        )[:3]
        builds: list[dict] = []
        for rank, candidate in enumerate(selected):
            fingerprint = candidate["fingerprint"]
            if fingerprint in global_fingerprints:
                raise ValueError("fingerprint is shared across models")
            global_fingerprints.add(fingerprint)
            builds.append(
                {
                    "rank": rank,
                    "label": LABELS[rank],
                    "fingerprint": fingerprint,
                    "buildId": candidate["buildId"],
                    "incremental": candidate["incremental"],
                    "sdkInt": candidate["sdkInt"],
                    "securityPatch": candidate["securityPatch"],
                    "otaUrl": candidate["otaUrl"],
                    "otaSha256": candidate["otaSha256"],
                    "verifiedAt": candidate["verifiedAt"],
                }
            )
        models.append(
            {
                key: template[key]
                for key in (
                    "profileId", "manufacturer", "brand", "model",
                    "device", "product", "board"
                )
            }
            | {"builds": builds}
        )
    catalog = {
        "schemaVersion": 1,
        "catalogVersion": version,
        "generatedAt": generated_at,
        "sourcePolicy": "official-google-full-ota-metadata",
        "models": models,
    }
    validate_catalog(catalog)
    return catalog


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--templates", required=True)
    parser.add_argument("--verified", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--version", type=int, default=1)
    parser.add_argument("--generated-at")
    parser.add_argument("--previous")
    args = parser.parse_args()
    verified = load_json(args.verified)
    generated = args.generated_at or max(item["verifiedAt"] for item in verified)
    templates = load_json(args.templates)
    version = args.version
    catalog = build_catalog(templates, verified, version, generated)
    if args.previous and Path(args.previous).exists():
        previous = load_json(args.previous)
        same_models = previous["models"] == catalog["models"]
        version = resolve_version(previous, catalog, templates)
        generated = previous["generatedAt"] if same_models else generated
        catalog = build_catalog(templates, verified, version, generated)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    target = output / f"pixel-catalog-v{version}.json"
    target.write_bytes(canonical_bytes(catalog))
    print(target)


if __name__ == "__main__":
    main()

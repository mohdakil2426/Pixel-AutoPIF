from __future__ import annotations

if __package__ in (None, ""):
    import os
    import sys

    script_directory = os.path.dirname(os.path.abspath(__file__))
    sys.path = [
        entry for entry in sys.path
        if os.path.abspath(entry or os.curdir) != script_directory
    ]
    sys.path.insert(0, os.path.dirname(script_directory))

import argparse
from datetime import datetime, timezone
from pathlib import Path

from scripts.catalog import canonical_bytes, load_json
from scripts.discover_flashstation import discover_stable
from scripts.extract_ota_metadata import extract_remote
from scripts.verify_candidate import verify


def refresh(templates: list[dict], existing: list[dict], observed_at: str):
    by_fingerprint = {item["fingerprint"]: item for item in existing}
    dispositions: list[dict] = []
    for template in templates:
        device = template["device"]
        try:
            candidates = discover_stable(device, observed_at)
            for candidate in candidates:
                try:
                    verified = verify(candidate, template, extract_remote(candidate["otaUrl"]))
                    by_fingerprint.setdefault(verified["fingerprint"], verified)
                    dispositions.append(
                        {"modelKey": device, "buildLabel": candidate["buildLabel"], "status": "verified"}
                    )
                except (OSError, ValueError) as error:
                    dispositions.append(
                        {
                            "modelKey": device,
                            "buildLabel": candidate.get("buildLabel", "unknown"),
                            "status": "manual_review",
                            "reason": type(error).__name__,
                        }
                    )
        except (OSError, ValueError) as error:
            dispositions.append(
                {"modelKey": device, "status": "manual_review", "reason": type(error).__name__}
            )
    verified = sorted(
        by_fingerprint.values(),
        key=lambda item: (item["modelKey"], item["securityPatch"], item["fingerprint"]),
    )
    return verified, dispositions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--templates", required=True)
    parser.add_argument("--existing", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--dispositions", required=True)
    args = parser.parse_args()
    observed = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    verified, dispositions = refresh(
        load_json(args.templates), load_json(args.existing), observed
    )
    Path(args.output).write_bytes(canonical_bytes(verified))
    Path(args.dispositions).write_bytes(canonical_bytes(dispositions))


if __name__ == "__main__":
    main()

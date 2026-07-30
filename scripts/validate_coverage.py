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

from scripts.catalog import load_json


def validate_coverage(templates: list[dict], verified: list[dict]) -> None:
    required = {item["device"] for item in templates}
    observed = {item["modelKey"] for item in verified}
    missing = sorted(required - observed)
    if missing:
        raise ValueError("missing verified models: " + ", ".join(missing))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--templates", required=True)
    parser.add_argument("--verified", required=True)
    args = parser.parse_args()
    validate_coverage(load_json(args.templates), load_json(args.verified))


if __name__ == "__main__":
    main()

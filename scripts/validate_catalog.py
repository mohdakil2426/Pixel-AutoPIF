from __future__ import annotations

import argparse
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.catalog import load_json, validate_catalog


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--schema", required=True)
    args = parser.parse_args()
    catalog = load_json(args.catalog)
    Draft202012Validator(load_json(args.schema)).validate(catalog)
    validate_catalog(catalog)
    print(f"valid catalog v{catalog['catalogVersion']}: {len(catalog['models'])} models")


if __name__ == "__main__":
    main()

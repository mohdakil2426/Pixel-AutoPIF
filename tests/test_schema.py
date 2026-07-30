import copy
import unittest
from datetime import datetime, timezone

from jsonschema import Draft202012Validator

from scripts.build_catalog import build_catalog
from scripts.catalog import load_json, validate_catalog, validate_manifest


def valid_catalog():
    return build_catalog(
        load_json("templates/pixel-devices.json"),
        load_json("tests/fixtures/verified-candidates.json"),
        1,
        "2026-07-30T00:00:00Z",
    )


class SchemaTests(unittest.TestCase):
    def test_valid_catalog_matches_schema_and_semantics(self):
        catalog = valid_catalog()
        Draft202012Validator(load_json("schemas/pixel-catalog.schema.json")).validate(catalog)
        validate_catalog(catalog)

    def test_rejects_unknown_duplicate_invalid_hash_url_fingerprint_and_rank(self):
        mutations = []
        extra = valid_catalog()
        extra["unknown"] = True
        mutations.append(extra)
        duplicate_id = valid_catalog()
        duplicate_id["models"].append(copy.deepcopy(duplicate_id["models"][0]))
        mutations.append(duplicate_id)
        duplicate_fingerprint = valid_catalog()
        duplicate_fingerprint["models"][0]["builds"].append(
            copy.deepcopy(duplicate_fingerprint["models"][0]["builds"][0])
        )
        duplicate_fingerprint["models"][0]["builds"][1]["rank"] = 1
        duplicate_fingerprint["models"][0]["builds"][1]["label"] = "Previous"
        mutations.append(duplicate_fingerprint)
        for field, value in (
            ("otaSha256", "bad"),
            ("otaUrl", "http://dl.google.com/a.zip"),
            ("fingerprint", "bad"),
            ("securityPatch", "2026-99-99"),
        ):
            item = valid_catalog()
            item["models"][0]["builds"][0][field] = value
            mutations.append(item)
        rank = valid_catalog()
        rank["models"][0]["builds"][0]["rank"] = 1
        mutations.append(rank)
        for catalog in mutations:
            with self.assertRaises((ValueError, TypeError)):
                validate_catalog(catalog)

    def test_manifest_expiry_is_at_most_45_days(self):
        manifest = {
            "schemaVersion": 1,
            "catalogVersion": 1,
            "catalogUrl": "https://github.com/mohdakil2426/Pixel-AutoPIF/releases/download/v1/pixel-catalog-v1.json",
            "catalogSha256": "0" * 64,
            "catalogSizeBytes": 10,
            "catalogSignatureUrl": "https://github.com/mohdakil2426/Pixel-AutoPIF/releases/download/v1/pixel-catalog-v1.json.sig",
            "generatedAt": "2026-07-30T00:00:00Z",
            "expiresAt": "2026-09-13T00:00:00Z",
            "keyId": "pixel-autopif-p256-v1",
        }
        validate_manifest(manifest, datetime(2026, 7, 30, tzinfo=timezone.utc))
        with self.assertRaises(ValueError):
            validate_manifest(manifest | {"expiresAt": "2026-09-14T00:00:01Z"})


if __name__ == "__main__":
    unittest.main()

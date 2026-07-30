import unittest

from scripts.build_catalog import build_catalog, resolve_version
from scripts.catalog import canonical_bytes, load_json


class BuildCatalogTests(unittest.TestCase):
    def setUp(self):
        self.templates = load_json("templates/pixel-devices.json")
        self.base = load_json("tests/fixtures/verified-candidates.json")[0]

    def candidate(self, patch, build_id, incremental, status="verified"):
        return self.base | {
            "status": status,
            "securityPatch": patch,
            "buildId": build_id,
            "buildLabel": build_id,
            "incremental": incremental,
            "fingerprint": f"google/comet/comet:15/{build_id}/{incremental}:user/release-keys",
            "otaUrl": f"https://dl.google.com/dl/android/aosp/comet-ota-{build_id.lower()}-{incremental}.zip",
            "otaSha256": (incremental[-1] * 64),
        }

    def test_newest_three_stable_builds_are_retained_and_ranked(self):
        candidates = [
            self.candidate("2026-01-05", "BP4A.260105.001", "1001"),
            self.candidate("2026-02-05", "BP4A.260205.001", "1002"),
            self.candidate("2026-03-05", "CP1A.260305.001", "1003"),
            self.candidate("2026-04-05", "CP1A.260405.001", "1004"),
            self.candidate("2026-05-05", "BETA.1", "1005"),
        ]
        catalog = build_catalog(
            self.templates, candidates, 2, "2026-07-30T00:00:00Z"
        )
        builds = catalog["models"][0]["builds"]
        self.assertEqual([item["incremental"] for item in builds], ["1004", "1003", "1002"])
        self.assertEqual([item["label"] for item in builds], ["Recommended", "Previous", "Earlier"])

    def test_same_input_is_byte_identical_and_tuple_change_changes_bytes(self):
        first = build_catalog(
            self.templates, [self.base], 1, "2026-07-30T00:00:00Z"
        )
        second = build_catalog(
            self.templates, [self.base], 1, "2026-07-30T00:00:00Z"
        )
        self.assertEqual(canonical_bytes(first), canonical_bytes(second))
        changed = build_catalog(
            self.templates,
            [self.base | {"securityPatch": "2025-03-05"}],
            2,
            "2026-07-30T00:00:00Z",
        )
        self.assertNotEqual(canonical_bytes(first), canonical_bytes(changed))

    def test_bootstrap_stays_v1_until_previous_catalog_has_complete_coverage(self):
        required = [{"device": "alpha"}, {"device": "beta"}]
        partial = {"catalogVersion": 1, "models": [{"device": "alpha"}]}
        complete = {
            "catalogVersion": 1,
            "models": [{"device": "alpha"}, {"device": "beta"}],
        }
        changed = {
            "catalogVersion": 1,
            "models": [{"device": "alpha"}, {"device": "beta", "changed": True}],
        }
        self.assertEqual(1, resolve_version(partial, complete, required))
        self.assertEqual(2, resolve_version(complete, changed, required))


if __name__ == "__main__":
    unittest.main()

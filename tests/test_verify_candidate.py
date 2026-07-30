import unittest
from pathlib import Path

from scripts.catalog import load_json
from scripts.extract_ota_metadata import parse_metadata
from scripts.verify_candidate import verify


class CandidateVerificationTests(unittest.TestCase):
    def setUp(self):
        self.candidate = load_json("tests/fixtures/flashstation-response.json")[0] | {
            "status": "discovered_untrusted",
            "otaSha256": "5b998617ac3dc94ed3951b4ff8bb0cbf5e12e9381e559abc2f185d1588db499d",
            "observedAt": "2026-07-30T00:00:00Z",
        }
        self.template = next(
            item for item in load_json("templates/pixel-devices.json")
            if item["device"] == "comet"
        )
        self.metadata = parse_metadata(
            Path("tests/fixtures/official-ota-metadata.txt").read_bytes()
        )

    def test_exact_tuple_is_promoted_to_verified(self):
        self.assertEqual(verify(self.candidate, self.template, self.metadata)["status"], "verified")

    def test_mismatches_and_manual_review_do_not_publish(self):
        cases = [
            (self.candidate | {"buildLabel": "WRONG"}, self.template, self.metadata),
            (self.candidate, self.template | {"device": "komodo"}, self.metadata),
            (self.candidate | {"status": "manual_review"}, self.template, self.metadata),
        ]
        for candidate, template, metadata in cases:
            with self.assertRaises(ValueError):
                verify(candidate, template, metadata)


if __name__ == "__main__":
    unittest.main()

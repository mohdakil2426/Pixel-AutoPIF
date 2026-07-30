import unittest

from scripts.validate_coverage import validate_coverage


class CoverageTests(unittest.TestCase):
    def test_coverage_requires_every_template_model(self):
        templates = [{"device": "alpha"}, {"device": "beta"}]
        verified = [{"modelKey": "alpha", "fingerprint": "a"}]
        with self.assertRaisesRegex(ValueError, "beta"):
            validate_coverage(templates, verified)

    def test_coverage_accepts_one_or_more_verified_builds_per_model(self):
        validate_coverage(
            [{"device": "alpha"}],
            [{"modelKey": "alpha", "fingerprint": "a"}],
        )

import unittest

from jsonschema import Draft202012Validator

from scripts.catalog import load_json


class TemplateTests(unittest.TestCase):
    def setUp(self):
        self.templates = load_json("templates/pixel-devices.json")

    def test_schema_and_unique_stable_identity(self):
        Draft202012Validator(load_json("schemas/pixel-devices.schema.json")).validate(
            self.templates
        )
        self.assertEqual(len(self.templates), 35)
        for field in ("profileId", "device", "sourceId"):
            values = [item[field] for item in self.templates]
            self.assertEqual(len(values), len(set(values)))

    def test_templates_contain_no_mutable_build_values(self):
        forbidden = {
            "fingerprint", "buildId", "incremental", "sdkInt", "securityPatch"
        }
        self.assertTrue(all(not forbidden.intersection(item) for item in self.templates))

    def test_first_and_current_official_models_are_covered_without_invented_fold_xl(self):
        names = {item["model"] for item in self.templates}
        self.assertIn("Pixel", names)
        self.assertIn("Pixel 10a", names)
        self.assertIn("Pixel 10 Pro Fold", names)
        self.assertNotIn("Pixel 10 Pro Fold XL", names)


if __name__ == "__main__":
    unittest.main()

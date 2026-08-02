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
        self.assertEqual(len(self.templates), 21)
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
        self.assertIn("Pixel 6", names)
        self.assertIn("Pixel 10a", names)
        self.assertIn("Pixel 10 Pro Fold", names)
        self.assertIn("Pixel Fold", names)
        self.assertIn("Pixel Tablet", names)
        self.assertNotIn("Pixel", names)
        self.assertNotIn("Pixel XL", names)
        self.assertFalse(any(name.startswith("Pixel 2") for name in names))
        self.assertFalse(any(name.startswith("Pixel 3") for name in names))
        self.assertFalse(any(name.startswith("Pixel 4") for name in names))
        self.assertFalse(any(name.startswith("Pixel 5") for name in names))
        self.assertNotIn("Pixel 10 Pro Fold XL", names)


if __name__ == "__main__":
    unittest.main()

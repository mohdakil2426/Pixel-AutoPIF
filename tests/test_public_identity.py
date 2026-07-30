from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = (
    "Device" + "Masker",
    "Device" + " Masker",
    "com.astrixforge." + "device" + "masker",
    "Device" + "Masker-Pixel-Catalog",
    "device-profile-" + "improvements",
)
SKIP_PARTS = {".git", "__pycache__", ".venv", "dist"}


class PublicIdentityTests(unittest.TestCase):
    def test_public_tree_has_no_private_identity_or_path(self):
        violations = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or any(part in SKIP_PARTS for part in path.parts):
                continue
            if path.suffix in {".pyc", ".der", ".sig"}:
                continue
            text = path.read_text(encoding="utf-8")
            for forbidden in FORBIDDEN:
                if forbidden.lower() in text.lower():
                    violations.append(f"{path.relative_to(ROOT)}:{forbidden}")
        self.assertEqual([], violations)

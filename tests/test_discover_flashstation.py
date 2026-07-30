import copy
import unittest
from unittest.mock import patch

from scripts.catalog import load_json
from scripts.discover_flashstation import (
    discover_stable,
    normalize,
    parse_official_candidates,
    parse_ota_page,
)


OFFICIAL_ROWS_FIXTURE = """
<table>
  <tr id="sailfishstable1">
    <td>8.1.0 (OPM1.171019.011)</td>
    <td><a href="https://googledownloads.cn/dl/android/aosp/sailfish-1.zip">Link</a></td>
    <td>1111111111111111111111111111111111111111111111111111111111111111</td>
  </tr>
  <tr id="sailfishpreview">
    <td>Developer preview (DP1)</td>
    <td><a href="https://googledownloads.cn/dl/android/aosp/sailfish-preview.zip">Link</a></td>
    <td>2222222222222222222222222222222222222222222222222222222222222222</td>
  </tr>
  <tr id="sailfishstable2">
    <td>8.1.0 (OPM1.171019.012)</td>
    <td><a href="https://googledownloads.cn/dl/android/aosp/sailfish-2.zip">Link</a></td>
    <td>3333333333333333333333333333333333333333333333333333333333333333</td>
  </tr>
  <tr id="marlinstable">
    <td>8.1.0 (OPM1.171019.013)</td>
    <td><a href="https://googledownloads.cn/dl/android/aosp/marlin.zip">Link</a></td>
    <td>4444444444444444444444444444444444444444444444444444444444444444</td>
  </tr>
  <tr id="sailfishstable3">
    <td>8.1.0 (OPM1.171019.014)</td>
    <td><a href="https://googledownloads.cn/dl/android/aosp/sailfish-3.zip">Link</a></td>
    <td>5555555555555555555555555555555555555555555555555555555555555555</td>
  </tr>
  <tr id="sailfishstable4">
    <td>8.1.0 (OPM1.171019.015)</td>
    <td><a href="https://googledownloads.cn/dl/android/aosp/sailfish-4.zip">Link</a></td>
    <td>6666666666666666666666666666666666666666666666666666666666666666</td>
  </tr>
</table>
"""


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.payload = load_json("tests/fixtures/flashstation-response.json")

    def test_discovery_is_deterministic_and_quarantined(self):
        result = normalize(self.payload, "2026-07-30T00:00:00Z")
        self.assertEqual(result[0]["status"], "discovered_untrusted")
        self.assertNotIn("fingerprint", result[0])

    def test_rejects_unapproved_url_missing_model_and_duplicate(self):
        for mutation in (
            [{"modelKey": "comet", "otaUrl": "http://dl.google.com/a", "buildLabel": "A"}],
            [{"modelKey": "", "otaUrl": "https://dl.google.com/a", "buildLabel": "A"}],
            self.payload + copy.deepcopy(self.payload),
        ):
            with self.assertRaises(ValueError):
                normalize(mutation, "2026-07-30T00:00:00Z")

    def test_matches_flash_build_to_exact_official_ota_row(self):
        page = """
        <tr id="cometap4a.250205.002">
          <td>15.0.0 (AP4A.250205.002)</td>
          <td><a href="https://googledownloads.cn/dl/android/aosp/comet.zip">Link</a></td>
          <td>5b998617ac3dc94ed3951b4ff8bb0cbf5e12e9381e559abc2f185d1588db499d</td>
        </tr>
        """
        url, digest = parse_ota_page(page, "comet", "AP4A.250205.002")
        self.assertEqual(url, "https://dl.google.com/dl/android/aosp/comet.zip")
        self.assertTrue(digest.startswith("5b998617"))

    def test_official_fallback_returns_only_exact_product_stable_rows(self):
        candidates = parse_official_candidates(
            OFFICIAL_ROWS_FIXTURE,
            "sailfish",
            "2026-07-31T00:00:00Z",
        )
        self.assertEqual(3, len(candidates))
        self.assertTrue(all(item["modelKey"] == "sailfish" for item in candidates))
        self.assertTrue(
            all(item["otaUrl"].startswith("https://dl.google.com/") for item in candidates)
        )
        self.assertFalse(
            any("beta" in item["buildLabel"].lower() for item in candidates)
        )

    @patch("scripts.discover_flashstation.get")
    def test_discovery_uses_official_fallback_only_when_flash_has_no_stable_build(
        self,
        get,
    ):
        get.side_effect = [
            (200, {}, b'<div data-client-config="AIzaPublicKey123"></div>'),
            (200, {}, b'{"flashstationBuild":[]}'),
            (200, {}, OFFICIAL_ROWS_FIXTURE.encode()),
        ]
        candidates = discover_stable("sailfish", "2026-07-31T00:00:00Z")
        self.assertEqual(
            ["OPM1.171019.011", "OPM1.171019.012", "OPM1.171019.014"],
            [item["buildLabel"] for item in candidates],
        )

    @patch("scripts.discover_flashstation.get")
    def test_discovery_prefers_flash_stable_builds(self, get):
        page = """
        <tr id="sailfishopm1.171019.099">
          <td>8.1.0 (OPM1.171019.099)</td>
          <td><a href="https://googledownloads.cn/dl/android/aosp/flash.zip">Link</a></td>
          <td>7777777777777777777777777777777777777777777777777777777777777777</td>
        </tr>
        """ + OFFICIAL_ROWS_FIXTURE
        get.side_effect = [
            (200, {}, b'<div data-client-config="AIzaPublicKey123"></div>'),
            (
                200,
                {},
                b'{"flashstationBuild":[{"product":"sailfish",'
                b'"releaseCandidateName":"OPM1.171019.099"}]}',
            ),
            (200, {}, page.encode()),
        ]
        candidates = discover_stable("sailfish", "2026-07-31T00:00:00Z")
        self.assertEqual(["OPM1.171019.099"], [item["buildLabel"] for item in candidates])


if __name__ == "__main__":
    unittest.main()

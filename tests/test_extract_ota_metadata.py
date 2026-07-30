import io
import unittest
import zipfile
from pathlib import Path

from scripts.extract_ota_metadata import (
    ENTRY,
    extract_from_ranges,
    extract_from_zip_bytes,
    parse_metadata,
)


def ota_zip(metadata: bytes, compression=zipfile.ZIP_DEFLATED, allow_zip64=True):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=compression, allowZip64=allow_zip64) as archive:
        archive.writestr(ENTRY, metadata)
    return output.getvalue()


class OtaMetadataTests(unittest.TestCase):
    def setUp(self):
        self.metadata = Path("tests/fixtures/official-ota-metadata.txt").read_bytes()

    def test_stored_deflated_and_zip64_capable_archives(self):
        for compression in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            archive = ota_zip(self.metadata, compression)
            parsed = extract_from_zip_bytes(archive)
            self.assertEqual(parsed["pre-device"], "comet")
            ranged = extract_from_ranges(
                len(archive), lambda start, end: archive[start : end + 1]
            )
            self.assertEqual(ranged, parsed)

    def test_rejects_truncated_missing_oversized_and_duplicate_metadata(self):
        invalid = [
            b"not-a-zip",
            ota_zip(b"x=y\n"),
            ota_zip(self.metadata + b"pre-device=comet\n"),
            ota_zip(b"x" * 16385),
        ]
        for value in invalid:
            with self.assertRaises(ValueError):
                extract_from_zip_bytes(value)

    def test_rejects_duplicate_property(self):
        with self.assertRaises(ValueError):
            parse_metadata(self.metadata + b"post-sdk-level=35\n")

    def test_missing_or_truncated_ranges_fail_closed(self):
        archive = ota_zip(self.metadata)
        for fetch in (
            lambda start, end: archive + b"unexpected-full-response",
            lambda start, end: archive[start:end],
        ):
            with self.assertRaises(ValueError):
                extract_from_ranges(len(archive), fetch)


if __name__ == "__main__":
    unittest.main()

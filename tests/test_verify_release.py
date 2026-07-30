import base64
import unittest
from datetime import datetime, timezone
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from scripts.catalog import canonical_bytes, load_json, sha256
from scripts.sign_catalog import sign
from scripts.verify_release import verify_release


class VerifyReleaseTests(unittest.TestCase):
    def test_exact_release_round_trips_and_tampering_fails(self):
        key = ec.generate_private_key(ec.SECP256R1())
        public = key.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        catalog = Path("tests/fixtures/pixel-catalog-v1.json").read_bytes()
        manifest = load_json("tests/fixtures/pixel-catalog.manifest.json") | {
            "catalogSizeBytes": len(catalog),
            "catalogSha256": sha256(catalog),
        }
        manifest_bytes = canonical_bytes(manifest)
        catalog_signature = sign(catalog, key)
        manifest_signature = sign(manifest_bytes, key)

        verify_release(
            manifest_bytes,
            manifest_signature,
            catalog,
            catalog_signature,
            public,
            now=datetime(2026, 7, 31, tzinfo=timezone.utc),
        )
        with self.assertRaises(InvalidSignature):
            verify_release(
                manifest_bytes + b"\n",
                manifest_signature,
                catalog,
                catalog_signature,
                public,
                now=datetime(2026, 7, 31, tzinfo=timezone.utc),
            )

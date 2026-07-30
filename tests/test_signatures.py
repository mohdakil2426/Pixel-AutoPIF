import base64
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from scripts.catalog import canonical_bytes
from scripts.catalog import load_json, sha256, validate_manifest
from scripts.sign_catalog import load_private_key, sign, verify
from tests.test_schema import valid_catalog


class SignatureTests(unittest.TestCase):
    def setUp(self):
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.private_der = self.key.private_bytes(
            serialization.Encoding.DER,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        self.public_der = self.key.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def test_exact_catalog_and_manifest_bytes_verify(self):
        catalog = canonical_bytes(valid_catalog())
        manifest = canonical_bytes({"catalogSha256": "0" * 64, "catalogVersion": 1})
        for payload in (catalog, manifest):
            signature = sign(payload, load_private_key(base64.b64encode(self.private_der).decode()))
            verify(payload, signature, self.public_der)
            with self.assertRaises(InvalidSignature):
                verify(payload + b"\n", signature, self.public_der)

    def test_frozen_exact_byte_fixtures_verify_with_public_key_only(self):
        public_der = base64.b64decode(
            Path("tests/fixtures/test-public-key.der.base64").read_text().strip()
        )
        for name in ("pixel-catalog-v1", "pixel-catalog.manifest"):
            payload = Path(f"tests/fixtures/{name}.json").read_bytes()
            signature = base64.b64decode(
                Path(f"tests/fixtures/{name}.sig.base64").read_text().strip()
            )
            verify(payload, signature, public_der)
        catalog = Path("tests/fixtures/pixel-catalog-v1.json").read_bytes()
        manifest = load_json("tests/fixtures/pixel-catalog.manifest.json")
        validate_manifest(manifest)
        self.assertEqual(manifest["catalogSizeBytes"], len(catalog))
        self.assertEqual(manifest["catalogSha256"], sha256(catalog))

    def test_missing_private_key_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = Path(directory, "catalog.json")
            payload.write_bytes(b"{}")
            environment = os.environ.copy()
            environment.pop("CATALOG_SIGNING_KEY_PKCS8_BASE64", None)
            result = subprocess.run(
                [sys.executable, "scripts/sign_catalog.py", str(payload)],
                env=environment,
                capture_output=True,
                check=False,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(Path(f"{payload}.sig").exists())

    def test_rejects_non_p256_key(self):
        key = ec.generate_private_key(ec.SECP384R1())
        encoded = base64.b64encode(
            key.private_bytes(
                serialization.Encoding.DER,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        ).decode()
        with self.assertRaises(ValueError):
            load_private_key(encoded)


if __name__ == "__main__":
    unittest.main()

import base64
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization

from scripts.generate_signing_material import generate_material


class SigningMaterialTests(unittest.TestCase):
    def test_generated_material_round_trips_and_backup_is_encrypted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            secret = root / "secret.txt"
            encrypted = root / "recovery.pem"
            public = root / "public.txt"
            passphrase = root / "passphrase.txt"

            generate_material(secret, encrypted, public, passphrase)

            secret_der = base64.b64decode(secret.read_text())
            private_key = serialization.load_der_private_key(secret_der, password=None)
            recovery = serialization.load_pem_private_key(
                encrypted.read_bytes(),
                password=passphrase.read_text().strip().encode(),
            )
            self.assertEqual(private_key.private_numbers(), recovery.private_numbers())
            self.assertEqual(
                b"-----BEGIN ENCRYPTED PRIVATE KEY-----",
                encrypted.read_bytes().splitlines()[0],
            )
            self.assertEqual(
                private_key.public_key().public_bytes(
                    serialization.Encoding.DER,
                    serialization.PublicFormat.SubjectPublicKeyInfo,
                ),
                base64.b64decode(public.read_text()),
            )

    def test_generation_refuses_to_overwrite_any_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            secret = root / "secret.txt"
            secret.write_text("occupied")
            with self.assertRaises(FileExistsError):
                generate_material(
                    secret,
                    root / "recovery.pem",
                    root / "public.txt",
                    root / "passphrase.txt",
                )

from __future__ import annotations

import argparse
import base64
import secrets
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def generate_material(
    secret_path: Path,
    encrypted_path: Path,
    public_path: Path,
    passphrase_path: Path,
) -> None:
    destinations = (secret_path, encrypted_path, public_path, passphrase_path)
    occupied = [path for path in destinations if path.exists()]
    if occupied:
        raise FileExistsError(f"destination exists: {occupied[0]}")

    key = ec.generate_private_key(ec.SECP256R1())
    passphrase = secrets.token_urlsafe(48)
    secret = base64.b64encode(
        key.private_bytes(
            serialization.Encoding.DER,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    encrypted = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(passphrase.encode()),
    )
    public = base64.b64encode(
        key.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

    for path, payload in (
        (secret_path, secret),
        (encrypted_path, encrypted),
        (public_path, public),
        (passphrase_path, passphrase.encode()),
    ):
        with path.open("xb") as destination:
            destination.write(payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--secret", required=True, type=Path)
    parser.add_argument("--encrypted", required=True, type=Path)
    parser.add_argument("--public", required=True, type=Path)
    parser.add_argument("--passphrase", required=True, type=Path)
    args = parser.parse_args()
    generate_material(args.secret, args.encrypted, args.public, args.passphrase)
    for path in (args.secret, args.encrypted, args.public, args.passphrase):
        print(path)


if __name__ == "__main__":
    main()

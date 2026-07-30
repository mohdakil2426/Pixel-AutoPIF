from __future__ import annotations

import argparse
import base64
import os
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


def load_private_key(value: str):
    key = serialization.load_der_private_key(base64.b64decode(value), password=None)
    if not isinstance(key, ec.EllipticCurvePrivateKey) or not isinstance(
        key.curve, ec.SECP256R1
    ):
        raise ValueError("signing key must be ECDSA P-256")
    return key


def sign(data: bytes, key) -> bytes:
    return key.sign(data, ec.ECDSA(hashes.SHA256(), deterministic_signing=True))


def verify(data: bytes, signature: bytes, public_der: bytes) -> None:
    key = serialization.load_der_public_key(public_der)
    if not isinstance(key, ec.EllipticCurvePublicKey) or not isinstance(
        key.curve, ec.SECP256R1
    ):
        raise ValueError("verification key must be ECDSA P-256")
    key.verify(signature, data, ec.ECDSA(hashes.SHA256()))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()
    encoded = os.environ.get("CATALOG_SIGNING_KEY_PKCS8_BASE64")
    if not encoded:
        raise SystemExit("CATALOG_SIGNING_KEY_PKCS8_BASE64 is required")
    key = load_private_key(encoded)
    for raw_path in args.paths:
        path = Path(raw_path)
        path.with_suffix(path.suffix + ".sig").write_bytes(sign(path.read_bytes(), key))


if __name__ == "__main__":
    main()

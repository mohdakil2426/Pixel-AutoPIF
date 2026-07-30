from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

FINGERPRINT = re.compile(
    r"^google/(?P<product>[a-z0-9_]+)/(?P<device>[a-z0-9_]+):"
    r"(?P<release>[0-9]+)/(?P<build>[A-Z0-9.]+)/(?P<incremental>[0-9]+):"
    r"user/release-keys$"
)
SHA256 = re.compile(r"^[0-9a-f]{64}$")
LABELS = ("Recommended", "Previous", "Earlier")


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: str | Path) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def require_https(url: str, hosts: set[str]) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in hosts:
        raise ValueError(f"unapproved URL: {url}")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError(f"ambiguous URL: {url}")


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def validate_catalog(catalog: dict) -> None:
    if set(catalog) != {
        "schemaVersion", "catalogVersion", "generatedAt", "sourcePolicy", "models"
    }:
        raise ValueError("catalog root fields do not match schema")
    if catalog["schemaVersion"] != 1 or catalog["catalogVersion"] < 1:
        raise ValueError("unsupported catalog version")
    parse_time(catalog["generatedAt"])
    if catalog["sourcePolicy"] != "official-google-full-ota-metadata":
        raise ValueError("unapproved source policy")
    models = catalog["models"]
    if not isinstance(models, list) or not 1 <= len(models) <= 64:
        raise ValueError("invalid model count")
    profile_ids: set[str] = set()
    fingerprints: set[str] = set()
    for model in models:
        expected = {
            "profileId", "manufacturer", "brand", "model", "device", "product",
            "board", "builds"
        }
        if set(model) != expected:
            raise ValueError("model fields do not match schema")
        if model["profileId"] in profile_ids:
            raise ValueError("duplicate profileId")
        profile_ids.add(model["profileId"])
        if model["manufacturer"] != "Google" or model["brand"] != "google":
            raise ValueError("non-Google model")
        if model["model"] != "Pixel" and not model["model"].startswith("Pixel "):
            raise ValueError("invalid Pixel marketing name")
        builds = model["builds"]
        if not 1 <= len(builds) <= 3:
            raise ValueError("invalid build retention")
        if [item["rank"] for item in builds] != list(range(len(builds))):
            raise ValueError("rank gap")
        for build in builds:
            if build["label"] != LABELS[build["rank"]]:
                raise ValueError("rank label mismatch")
            match = FINGERPRINT.fullmatch(build["fingerprint"])
            if not match:
                raise ValueError("malformed fingerprint")
            if (
                match["device"] != model["device"]
                or match["product"] != model["product"]
                or match["build"] != build["buildId"]
                or match["incremental"] != build["incremental"]
            ):
                raise ValueError("tuple mismatch")
            if build["fingerprint"] in fingerprints:
                raise ValueError("duplicate fingerprint")
            fingerprints.add(build["fingerprint"])
            if not isinstance(build["sdkInt"], int) or not 21 <= build["sdkInt"] <= 100:
                raise ValueError("invalid SDK")
            date.fromisoformat(build["securityPatch"])
            require_https(build["otaUrl"], {"dl.google.com"})
            if not SHA256.fullmatch(build["otaSha256"]):
                raise ValueError("invalid OTA digest")
            parse_time(build["verifiedAt"])


def validate_manifest(manifest: dict, now: datetime | None = None) -> None:
    if set(manifest) != {
        "schemaVersion", "catalogVersion", "catalogUrl", "catalogSha256",
        "catalogSizeBytes", "catalogSignatureUrl", "generatedAt", "expiresAt", "keyId"
    }:
        raise ValueError("manifest fields do not match schema")
    if manifest["schemaVersion"] != 1 or manifest["catalogVersion"] < 1:
        raise ValueError("unsupported manifest")
    require_https(manifest["catalogUrl"], {"github.com"})
    require_https(manifest["catalogSignatureUrl"], {"github.com"})
    if not SHA256.fullmatch(manifest["catalogSha256"]):
        raise ValueError("invalid catalog digest")
    if not 1 <= manifest["catalogSizeBytes"] <= 2_000_000:
        raise ValueError("invalid catalog size")
    generated = parse_time(manifest["generatedAt"])
    expires = parse_time(manifest["expiresAt"])
    if expires <= generated or (expires - generated).days > 45:
        raise ValueError("invalid expiry window")
    if now and expires < now.astimezone(timezone.utc):
        raise ValueError("manifest expired")
    if not re.fullmatch(r"pixel-autopif-p256-v[0-9]+", manifest["keyId"]):
        raise ValueError("invalid keyId")

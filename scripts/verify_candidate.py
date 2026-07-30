from __future__ import annotations

from datetime import date

from scripts.catalog import FINGERPRINT, SHA256


def verify(candidate: dict, template: dict, metadata: dict) -> dict:
    if candidate.get("status") != "discovered_untrusted":
        raise ValueError("candidate must enter through discovery quarantine")
    if metadata["pre-device"] != template["device"]:
        raise ValueError("OTA codename mismatch")
    match = FINGERPRINT.fullmatch(metadata["post-build"])
    if not match:
        raise ValueError("malformed fingerprint")
    if (
        match["device"] != template["device"]
        or match["product"] != template["product"]
        or match["incremental"] != metadata["post-build-incremental"]
    ):
        raise ValueError("OTA tuple mismatch")
    if candidate.get("buildLabel") and candidate["buildLabel"] != match["build"]:
        raise ValueError("discovery build mismatch")
    sdk = int(metadata["post-sdk-level"])
    date.fromisoformat(metadata["post-security-patch-level"])
    digest = candidate.get("otaSha256", "")
    if not SHA256.fullmatch(digest):
        raise ValueError("official OTA digest required")
    return {
        **candidate,
        "status": "verified",
        "fingerprint": metadata["post-build"],
        "buildId": match["build"],
        "incremental": metadata["post-build-incremental"],
        "sdkInt": sdk,
        "securityPatch": metadata["post-security-patch-level"],
        "verifiedAt": candidate["observedAt"],
    }

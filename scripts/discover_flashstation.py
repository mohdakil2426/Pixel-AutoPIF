from __future__ import annotations

if __package__ in (None, ""):
    import os
    import sys

    script_directory = os.path.dirname(os.path.abspath(__file__))
    sys.path = [
        entry for entry in sys.path
        if os.path.abspath(entry or os.curdir) != script_directory
    ]
    sys.path.insert(0, os.path.dirname(script_directory))

import argparse
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from scripts.catalog import canonical_bytes, require_https
from scripts.http import get

FLASH_HOME = "https://flash.android.com"
FLASH_API = "https://content-flashstation-pa.googleapis.com/v1/builds"
OTA_PAGE = "https://developers.google.cn/android/ota?hl=en"


def normalize(payload: object, observed_at: str) -> list[dict]:
    if not isinstance(payload, list) or len(payload) > 256:
        raise ValueError("invalid discovery response")
    output: list[dict] = []
    urls: set[str] = set()
    for row in payload:
        if set(row) != {"modelKey", "otaUrl", "buildLabel"}:
            raise ValueError("invalid discovery candidate")
        model_key = row["modelKey"]
        if not isinstance(model_key, str) or not model_key:
            raise ValueError("missing model key")
        require_https(row["otaUrl"], {"dl.google.com"})
        if row["otaUrl"] in urls:
            raise ValueError("duplicate candidate URL")
        urls.add(row["otaUrl"])
        output.append(
            {
                "modelKey": model_key,
                "otaUrl": row["otaUrl"],
                "buildLabel": row["buildLabel"],
                "observedAt": observed_at,
                "status": "discovered_untrusted",
            }
        )
    return sorted(output, key=lambda item: (item["modelKey"], item["otaUrl"]))


def parse_ota_page(page: str, product: str, build_label: str) -> tuple[str, str]:
    row_id = re.escape(product + build_label.lower())
    match = re.search(
        rf'<tr id="{row_id}">.*?<a href="(https://googledownloads\.cn/[^"]+)">'
        rf".*?</a></td>\s*<td>([0-9a-f]{{64}})</td>",
        page,
        re.DOTALL,
    )
    if not match:
        raise ValueError("official OTA row not found")
    ota_url = match.group(1).replace("https://googledownloads.cn/", "https://dl.google.com/")
    require_https(ota_url, {"dl.google.com"})
    return ota_url, match.group(2)


def parse_official_candidates(
    page: str,
    product: str,
    observed_at: str,
) -> list[dict]:
    rows = re.findall(
        rf'<tr id="{re.escape(product)}[^"]*">(.*?)</tr>',
        page,
        re.DOTALL,
    )
    output = []
    for row in rows:
        plain = html.unescape(re.sub(r"<[^>]+>", " ", row))
        lowered = plain.lower()
        if any(
            marker in lowered
            for marker in ("beta", "preview", "canary", "developer")
        ):
            continue
        label_match = re.search(r"\(([A-Za-z0-9][A-Za-z0-9._-]+)\)", plain)
        asset_match = re.search(
            r'href="(https://googledownloads\.cn/[^"]+)".*?'
            r"<td>([0-9a-f]{64})</td>",
            row,
            re.DOTALL,
        )
        if not label_match or not asset_match:
            continue
        ota_url = asset_match.group(1).replace(
            "https://googledownloads.cn/",
            "https://dl.google.com/",
        )
        require_https(ota_url, {"dl.google.com"})
        output.append(
            {
                "modelKey": product,
                "otaUrl": ota_url,
                "otaSha256": asset_match.group(2),
                "buildLabel": label_match.group(1),
                "observedAt": observed_at,
                "status": "discovered_untrusted",
            }
        )
        if len(output) == 3:
            break
    if not output:
        raise ValueError("no stable official OTA candidates")
    return output


def discover_stable(product: str, observed_at: str) -> list[dict]:
    _, _, flash_html = get(FLASH_HOME, limit=100_000, hosts={"flash.android.com"})
    config_match = re.search(r'data-client-config="([^"]+)"', flash_html.decode())
    if not config_match:
        raise ValueError("Flash Station client config missing")
    config = html.unescape(config_match.group(1))
    key_match = re.search(r"AIza[0-9A-Za-z_-]+", config)
    if not key_match:
        raise ValueError("Flash Station public API key missing")
    api_url = f"{FLASH_API}?product={product}&key={key_match.group(0)}"
    _, _, api_bytes = get(
        api_url,
        limit=1_000_000,
        hosts={"content-flashstation-pa.googleapis.com"},
        extra_headers={"Referer": FLASH_HOME},
    )
    builds = json.loads(api_bytes).get("flashstationBuild", [])
    stable = [
        item for item in builds
        if item.get("product") == product and not item.get("previewMetadata")
    ]
    _, _, ota_bytes = get(
        OTA_PAGE, limit=1_000_000, hosts={"developers.google.cn"}
    )
    ota_page = ota_bytes.decode("utf-8")
    if not stable:
        return parse_official_candidates(ota_page, product, observed_at)
    output = []
    for item in stable[-3:]:
        build_label = item["releaseCandidateName"]
        ota_url, ota_sha256 = parse_ota_page(ota_page, product, build_label)
        output.append(
            {
                "modelKey": product,
                "otaUrl": ota_url,
                "otaSha256": ota_sha256,
                "buildLabel": build_label,
                "observedAt": observed_at,
                "status": "discovered_untrusted",
            }
        )
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input")
    source.add_argument("--product")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    observed = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if args.input:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        candidates = normalize(payload, observed)
    else:
        candidates = discover_stable(args.product, observed)
    Path(args.output).write_bytes(canonical_bytes(candidates))


if __name__ == "__main__":
    main()

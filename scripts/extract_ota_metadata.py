from __future__ import annotations

import io
import re
import zipfile
from collections.abc import Callable

from scripts.http import get

REQUIRED = {
    "post-build", "post-build-incremental", "post-sdk-level",
    "post-security-patch-level", "pre-device"
}
ENTRY = "META-INF/com/android/metadata"
MAX_METADATA = 16_384
MAX_ARCHIVE = 10_000_000_000
CHUNK = 65_536


class RangeReader(io.RawIOBase):
    def __init__(self, size: int, fetch: Callable[[int, int], bytes]):
        if not 1 <= size <= MAX_ARCHIVE:
            raise ValueError("invalid OTA size")
        self.size = size
        self.fetch = fetch
        self.position = 0
        self.cache: dict[tuple[int, int], bytes] = {}

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=io.SEEK_SET):
        target = (
            offset
            if whence == io.SEEK_SET
            else self.position + offset
            if whence == io.SEEK_CUR
            else self.size + offset
        )
        if not 0 <= target <= self.size:
            raise ValueError("invalid range seek")
        self.position = target
        return target

    def readinto(self, buffer):
        if self.position >= self.size:
            return 0
        end = min(self.size, self.position + len(buffer))
        start = (self.position // CHUNK) * CHUNK
        fetch_end = min(self.size, max(end, start + CHUNK))
        key = (start, fetch_end)
        data = self.cache.get(key)
        if data is None:
            data = self.fetch(start, fetch_end - 1)
            if len(data) != fetch_end - start:
                raise ValueError("range response length mismatch")
            self.cache[key] = data
        offset = self.position - start
        count = min(len(buffer), len(data) - offset, self.size - self.position)
        buffer[:count] = data[offset : offset + count]
        self.position += count
        return count


def parse_metadata(data: bytes) -> dict[str, str]:
    if len(data) > MAX_METADATA or b"\x00" in data:
        raise ValueError("invalid metadata size/content")
    output: dict[str, str] = {}
    for raw_line in data.decode("utf-8").splitlines():
        if not raw_line or raw_line.startswith("#"):
            continue
        if "=" not in raw_line:
            raise ValueError("malformed metadata line")
        key, value = raw_line.split("=", 1)
        if key in output:
            raise ValueError("duplicate metadata key")
        output[key] = value
    if not REQUIRED.issubset(output):
        raise ValueError("required OTA metadata is missing")
    return {key: output[key] for key in sorted(REQUIRED)}


def extract_from_zip_bytes(data: bytes) -> dict[str, str]:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            matches = [item for item in archive.infolist() if item.filename == ENTRY]
            if len(matches) != 1 or matches[0].file_size > MAX_METADATA:
                raise ValueError("invalid metadata entry")
            return parse_metadata(archive.read(matches[0]))
    except zipfile.BadZipFile as error:
        raise ValueError("invalid OTA ZIP") from error


def extract_from_ranges(
    size: int, fetch: Callable[[int, int], bytes]
) -> dict[str, str]:
    reader = io.BufferedReader(RangeReader(size, fetch), buffer_size=CHUNK)
    try:
        with zipfile.ZipFile(reader) as archive:
            matches = [item for item in archive.infolist() if item.filename == ENTRY]
            if len(matches) != 1 or matches[0].file_size > MAX_METADATA:
                raise ValueError("invalid metadata entry")
            return parse_metadata(archive.read(matches[0]))
    except (OSError, zipfile.BadZipFile) as error:
        raise ValueError("safe range extraction unavailable") from error


def extract_remote(url: str) -> dict[str, str]:
    status, headers, body = get(url, start=0, end=0, limit=1)
    content_range = headers.get("Content-Range", "")
    match = re.fullmatch(r"bytes 0-0/([0-9]+)", content_range)
    if status != 206 or not match or len(body) != 1:
        raise ValueError("server does not support safe byte ranges")
    size = int(match.group(1))

    def fetch(start: int, end: int) -> bytes:
        range_status, range_headers, data = get(
            url, start=start, end=end, limit=end - start + 1
        )
        expected = f"bytes {start}-{end}/{size}"
        if range_status != 206 or range_headers.get("Content-Range") != expected:
            raise ValueError("invalid range response")
        return data

    return extract_from_ranges(size, fetch)

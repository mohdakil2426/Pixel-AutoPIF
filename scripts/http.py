from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request

from scripts.catalog import require_https

USER_AGENT = "Pixel-AutoPIF/1 (+https://github.com/mohdakil2426/Pixel-AutoPIF)"
REDIRECTS = {301, 302, 303, 307, 308}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def get(
    url: str,
    *,
    start: int | None = None,
    end: int | None = None,
    limit: int,
    hosts: set[str] = frozenset({"dl.google.com"}),
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, dict, bytes]:
    headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
    headers.update(extra_headers or {})
    if start is not None:
        headers["Range"] = f"bytes={start}-{'' if end is None else end}"
    opener = urllib.request.build_opener(NoRedirect)
    current = url
    for _ in range(4):
        require_https(current, set(hosts))
        request = urllib.request.Request(current, headers=headers)
        try:
            response = opener.open(request, timeout=20)
        except urllib.error.HTTPError as error:
            if error.code not in REDIRECTS or "Location" not in error.headers:
                raise
            current = urllib.parse.urljoin(current, error.headers["Location"])
            continue
        with response:
            data = response.read(limit + 1)
            if len(data) > limit:
                raise ValueError("response exceeds byte limit")
            return response.status, dict(response.headers), data
    raise ValueError("redirect limit exceeded")

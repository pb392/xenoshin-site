"""Open every link on the hosted portfolio and report its HTTP status.

Starts from the given page paths, collects every <a href> (internal and
external), requests each URL once and writes a Markdown table. mailto: links
are listed but not opened. A few sites refuse automated requests (LinkedIn
answers 999); those (999, or 429 after retries) are reported as "blocked automated check" instead of
passing or failing, and are covered by the manual walkthrough.

Usage: python scripts/check_links.py BASE_URL OUT.md PATH [PATH ...]
Busy or rate-limited answers (429, 5xx) are retried after 5, 15 and 30 seconds.
Exits 1 if any link is still broken (status 400+ other than a known bot block, or no response).
"""

from __future__ import annotations

import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urldefrag

BOT_BLOCKED = {("www.linkedin.com", 999), ("linkedin.com", 999), ("www.linkedin.com", 429), ("linkedin.com", 429)}
RETRY_STATUSES = {429, 500, 502, 503, 504}  # busy or rate-limited: wait and try again before calling it broken
HEADERS = {"User-Agent": "xenoshin-link-check/1.0 (+https://github.com/pb392/xenoshin-site)"}


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.hrefs.append(href)


def fetch(url: str) -> tuple[int | None, str]:
    status, body = _fetch_once(url)
    for wait in (5, 15, 30):
        if status not in RETRY_STATUSES:
            break
        time.sleep(wait)
        status, body = _fetch_once(url)
    return status, body


def _fetch_once(url: str) -> tuple[int | None, str]:
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.status, resp.read().decode("utf-8", "replace") if method == "GET" else ""
        except urllib.error.HTTPError as exc:
            if method == "HEAD" and exc.code in (403, 405, 501, 503):
                continue  # some servers refuse HEAD; retry with GET
            return exc.code, ""
        except Exception as exc:  # noqa: BLE001 - report any network failure
            if method == "HEAD":
                continue
            return None, str(exc)
    return None, "no response"


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    base, out, paths = sys.argv[1].rstrip("/"), sys.argv[2], sys.argv[3:]
    found: dict[str, set[str]] = {}
    for path in paths:
        page_url = base + path
        status, _ = fetch(page_url)
        req = urllib.request.Request(page_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as resp:
            parser = Links()
            parser.feed(resp.read().decode("utf-8", "replace"))
        for href in parser.hrefs:
            target = href if href.startswith("mailto:") else urldefrag(urljoin(page_url, href))[0]
            found.setdefault(target, set()).add(path)

    rows, broken = [], 0
    for url in sorted(found):
        if url.startswith("mailto:"):
            result = "not opened (email link)"
        else:
            time.sleep(1)  # be polite to GitHub and others
            status, error = fetch(url)
            host = urllib.request.urlparse(url).hostname or ""
            if status is not None and status < 400:
                result = f"ok ({status})"
            elif (host, status) in BOT_BLOCKED:
                result = f"blocked automated check ({status}); checked by hand"
            else:
                result = f"**broken** ({status or error})"
                broken += 1
        rows.append(f"| {url} | {result} | {', '.join(sorted(found[url]))} |")
        print(rows[-1])

    with open(out, "w", encoding="utf-8") as f:
        f.write(f"# Link check · {base}\n\n{len(found)} unique links, {broken} broken.\n\n")
        f.write("| Link | Result | Found on |\n|---|---|---|\n" + "\n".join(rows) + "\n")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())

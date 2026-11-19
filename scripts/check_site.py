"""Static checks for the portfolio: every local link resolves, every page has
a language, a title, one h1, a skip link target and a viewport meta tag."""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "portfolio"


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids, self.h1, self.lang, self.title, self.viewport = [], set(), 0, False, False, False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a" and "href" in a:
            self.links.append(a["href"])
        if tag == "h1":
            self.h1 += 1
        if tag == "html" and a.get("lang"):
            self.lang = True
        if tag == "title":
            self.title = True
        if tag == "meta" and a.get("name") == "viewport":
            self.viewport = True


def main() -> int:
    pages = {p: Page() for p in ROOT.rglob("*.html")}
    for path, parser in pages.items():
        parser.feed(path.read_text(encoding="utf-8"))
    problems = []
    for path, parser in pages.items():
        name = path.relative_to(ROOT)
        if not (parser.lang and parser.title and parser.viewport):
            problems.append(f"{name}: missing lang, title or viewport")
        if parser.h1 != 1:
            problems.append(f"{name}: has {parser.h1} h1 elements")
        for href in parser.links:
            if re.match(r"^(https?:|mailto:)", href):
                continue
            target, _, anchor = href.partition("#")
            file = path if not target else (ROOT / target.lstrip("/") if target.startswith("/") else path.parent / target)
            if file.is_dir() or target.endswith("/") or target == "":
                file = file / "index.html" if target else path
            if not file.exists():
                problems.append(f"{name}: broken link {href}")
            elif anchor and anchor not in pages.get(file.resolve(), pages.get(file, Page())).ids:
                problems.append(f"{name}: missing anchor {href}")
    for p in problems:
        print("FAIL", p)
    print(f"Checked {len(pages)} pages: {'OK' if not problems else str(len(problems)) + ' problem(s)'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

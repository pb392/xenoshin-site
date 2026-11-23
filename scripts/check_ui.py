"""Browser checks for keyboard use and phone-width readability.

For every page given:
  * keyboard: pressing Tab from the top reaches every visible link and control
    (links inside a closed <details> count once it is opened, so they are skipped),
    the first stop is the skip link on pages with navigation, and each focused element shows a visible
    focus indicator (outline or box-shadow);
  * phone width (375 x 740): the page does not scroll sideways and body text is
    at least 14px.

Usage: python scripts/check_ui.py BASE_URL PATH [PATH ...]
Writes a short report to stdout and exits 1 if any page fails.
"""

from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

FOCUS_STYLE = """el => {
  const s = getComputedStyle(el);
  const outline = s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0;
  const shadow = s.boxShadow && s.boxShadow !== 'none';
  return outline || shadow;
}"""

TARGETS = """() => { const els = [...document.querySelectorAll('a[href], button, input, textarea, select, summary')]
  .filter(el => !(el.tagName !== 'SUMMARY' && el.closest('details:not([open])')))
  .filter(el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
                  return (r.width > 0 && r.height > 0 && s.visibility !== 'hidden') || el.classList.contains('skip'); });
  els.forEach((el, i) => el.dataset.uiCheck = String(i));
  return els.map(el => (el.innerText || el.value || el.getAttribute('href') || '').trim().slice(0, 40)); }"""


def check_keyboard(page, url: str) -> list[str]:
    problems: list[str] = []
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(url)
    labels = page.evaluate(TARGETS)
    expected = len(labels)
    has_nav = page.evaluate("() => !!document.querySelector('nav')")
    seen: list[str] = []
    for i in range(expected + 5):
        page.keyboard.press("Tab")
        info = page.evaluate("""() => { const el = document.activeElement;
            if (!el || el === document.body) return null;
            return {key: el.dataset.uiCheck || el.outerHTML.slice(0, 120), tag: el.tagName, text: (el.innerText || el.value || el.getAttribute('aria-label') || '').trim().slice(0, 40)}; }""")
        if info is None or info["key"] in seen:
            break
        if i == 0 and has_nav and "skip" not in info["text"].lower():
            problems.append(f"first Tab stop is not the skip link ({info['text']!r})")
        if not page.evaluate(FOCUS_STYLE, page.evaluate_handle("document.activeElement")):
            problems.append(f"no visible focus on {info['tag']} {info['text']!r}")
        seen.append(info["key"])
    if len(set(seen)) < expected:
        missed = [labels[i] for i in range(expected) if str(i) not in seen]
        problems.append(f"Tab reached {len(set(seen))} of {expected} links/controls; missed {missed}")
    return problems


def check_phone(page, url: str) -> list[str]:
    problems: list[str] = []
    page.set_viewport_size({"width": 375, "height": 740})
    page.goto(url)
    sizes = page.evaluate("""() => ({scroll: document.documentElement.scrollWidth,
                                     client: document.documentElement.clientWidth,
                                     font: parseFloat(getComputedStyle(document.body).fontSize)})""")
    if sizes["scroll"] > sizes["client"] + 1:
        problems.append(f"scrolls sideways at 375px (content {sizes['scroll']}px wide)")
    if sizes["font"] < 14:
        problems.append(f"body text is {sizes['font']}px at phone width")
    return problems


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    base, paths = sys.argv[1].rstrip("/"), sys.argv[2:]
    failed = False
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for path in paths:
            url = base + path
            problems = check_keyboard(page, url) + check_phone(page, url)
            print(f"{'FAIL' if problems else 'ok  '} {url}")
            for problem in problems:
                print(f"     - {problem}")
            failed = failed or bool(problems)
        browser.close()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

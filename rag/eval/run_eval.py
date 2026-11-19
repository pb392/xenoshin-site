"""Run the evaluation questions against a running app and record actual results.

    python eval/run_eval.py https://rag.xenoshin.com eval/results

Writes results.json (raw API responses) and results.md (pass/fail table).
A pass means: the status matches, at least one citation comes from an expected
source, every expected term appears in the answer, and no forbidden term does.
It checks support and refusal behavior; it does not prove every sentence true.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def ask(base: str, question: str) -> dict:
    url = f"{base.rstrip('/')}/api/ask?q={urllib.parse.quote(question)}"
    with urllib.request.urlopen(url, timeout=90) as response:
        return json.loads(response.read().decode())


def judge(item: dict, body: dict) -> tuple[bool, list[str]]:
    problems = []
    status, answer = body.get("status"), body.get("answer", "")
    cited_sources = {c.split("#")[0] for c in body.get("citations", [])}
    if item["expect_status"] == "insufficient" and status not in ("insufficient", "withheld", "no_sources"):
        problems.append(f"expected a refusal, got status {status}")
    if item["expect_status"] == "answered":
        if status != "answered":
            problems.append(f"expected an answer, got status {status}")
        if item["expect_sources"] and not cited_sources & set(item["expect_sources"]):
            problems.append(f"no citation from {item['expect_sources']} (cited {sorted(cited_sources)})")
        for term in item["expect_terms"]:
            if term.lower() not in answer.lower():
                problems.append(f"answer missing '{term}'")
    for term in item.get("forbid_terms", []):
        if term.lower() in answer.lower():
            problems.append(f"answer contains forbidden '{term}'")
    return not problems, problems


def main() -> int:
    base, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    questions = json.loads((Path(__file__).parent / "questions.json").read_text())["questions"]
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    health = json.loads(urllib.request.urlopen(f"{base.rstrip('/')}/health", timeout=30).read().decode())
    rows, raw = [], []
    for item in questions:
        try:
            body = ask(base, item["question"])
        except Exception as exc:  # record the failure rather than hiding it
            body = {"status": "request_failed", "answer": str(exc), "citations": []}
        passed, problems = judge(item, body)
        raw.append({"item": item, "response": body, "passed": passed, "problems": problems})
        rows.append((item, body, passed, problems))
        time.sleep(8)  # stay under the app's per-visitor rate limit
    (out / "results.json").write_text(json.dumps({"base": base, "started": started, "health": health, "results": raw}, indent=2))
    passed_count = sum(1 for _, _, p, _ in rows if p)
    lines = [
        f"# Hosted evaluation · {started}",
        "",
        f"Target: {base} · commit `{health.get('commit')}` · embed `{health.get('embed_model')}` · generation `{health.get('generation_model')}`",
        "",
        f"**{passed_count}/{len(rows)} passed.** Expected behavior was written in questions.json before this run.",
        "",
        "| ID | Tests | Status | Pass | Citations | Answer | Problems |",
        "|---|---|---|---|---|---|---|",
    ]
    for item, body, passed, problems in rows:
        answer = body.get("answer", "").replace("|", "/").replace("\n", " ")
        lines.append(
            f"| {item['id']} | {item['tests']} | {body.get('status')} | {'yes' if passed else '**no**'} | "
            f"{', '.join(body.get('citations', []))} | {answer} | {'; '.join(problems)} |"
        )
    (out / "results.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())

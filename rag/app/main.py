"""FastAPI web app: chat page, JSON API, sources, import record, health, admin import."""

from __future__ import annotations

import hmac
import html
import json
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from .answer import AnswerResult, answer_question
from .config import Settings, load_settings
from .db import connect
from .facts import STATUS_LABEL, slug
from .importer import run_import
from .providers import GeminiEmbedder, GeminiGenerator

FAN_NOTICE = (
    "This content is unofficial Fan Content permitted under and not endorsed or approved by Elestrals. "
    "Portions of the materials used are the property of Elestrals LLC. All rights reserved by Elestrals LLC. "
    'For more information, see the <a href="https://www.elestrals.com/fan-content-policy">Elestrals Fan Content Policy</a>.'
)

EXAMPLES = [
    "Who won the last tournament?",
    "Which decks run Neandersloth CoKhione?",
    "How many copies of Gorgon's Gaze were in the October 24 Premier winning deck?",
    "What archetype won the 2026 World Championship?",
    "Which bosses are hardest to beat right now?",
]


class RateLimiter:
    """In-memory limits: per visitor per minute, and for the whole site per day."""

    def __init__(self, per_minute: int, per_day: int):
        self.per_minute, self.per_day = per_minute, per_day
        self.hits: dict[str, deque] = defaultdict(deque)
        self.day, self.day_count = "", 0
        self.lock = threading.Lock()

    def allow(self, key: str) -> tuple[bool, str]:
        now = time.time()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self.lock:
            if today != self.day:
                self.day, self.day_count = today, 0
            if self.day_count >= self.per_day:
                return False, "The daily question limit for this demo has been reached. Please try again tomorrow."
            window = self.hits[key]
            while window and now - window[0] > 60:
                window.popleft()
            if len(window) >= self.per_minute:
                return False, "Too many questions in the last minute. Please wait a moment."
            window.append(now)
            self.day_count += 1
            return True, ""


def create_app(settings: Settings | None = None, embedder=None, generator=None, conn=None) -> FastAPI:
    settings = settings or load_settings()
    conn = conn or connect(settings.db_path)
    if embedder is None and settings.gemini_api_key:
        embedder = GeminiEmbedder(settings.gemini_api_key, settings.embed_model, settings.embed_dims, settings.gemini_base_url)
    if generator is None and settings.gemini_api_key:
        generator = GeminiGenerator(settings.gemini_api_key, settings.gen_model, settings.gemini_base_url)
    limiter = RateLimiter(settings.per_ip_per_minute, settings.global_per_day)
    db_lock = threading.Lock()
    app = FastAPI(title="Elestrals Meta Assistant", docs_url=None, redoc_url=None)

    def client_key(request: Request) -> str:
        # Traefik appends the real client address last; earlier entries can be forged by the client.
        forwarded = request.headers.get("x-forwarded-for", "")
        return forwarded.split(",")[-1].strip() or (request.client.host if request.client else "unknown")

    def ask(question: str, request: Request) -> AnswerResult | str:
        question = " ".join(question.split())
        if not question:
            return "Please type a question."
        if len(question) > settings.max_question_chars:
            return f"Please keep questions under {settings.max_question_chars} characters."
        ok, message = limiter.allow(client_key(request))
        if not ok:
            return message
        with db_lock:
            return answer_question(conn, question, embedder, generator, settings.top_k)

    def require_admin(authorization: str | None) -> None:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Admin token required")
        if not settings.admin_token or not hmac.compare_digest(authorization[7:], settings.admin_token):
            raise HTTPException(status_code=403, detail="Not allowed")

    @app.get("/health")
    def health() -> dict:
        with db_lock:
            chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            embedded = conn.execute("SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL").fetchone()[0]
            sources = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
            last = conn.execute("SELECT finished_at FROM import_runs ORDER BY id DESC LIMIT 1").fetchone()
        return {
            "status": "ok", "commit": settings.commit, "sources": sources, "chunks": chunks,
            "chunks_with_embeddings": embedded, "last_import": last[0] if last else None,
            "embed_model": getattr(embedder, "model", None), "generation_model": getattr(generator, "model", None),
        }

    @app.get("/api/ask")
    def api_ask(q: str, request: Request):
        result = ask(q, request)
        if isinstance(result, str):
            status = 429 if "limit" in result.lower() or "too many" in result.lower() else 400
            return JSONResponse({"error": result}, status_code=status)
        return {
            "question": result.question, "answer": result.answer, "status": result.status,
            "citations": result.citations, "removed_citations": result.removed_citations,
            "coverage": result.coverage, "model": result.model, "warnings": result.warnings,
            "retrieval_mode": result.retrieval.mode if result.retrieval else None,
            "keyword_hits": result.retrieval.keyword_hits if result.retrieval else [],
            "vector_hits": [(i, round(s, 4)) for i, s in (result.retrieval.vector_hits if result.retrieval else [])],
            "evidence": [
                {"id": e.id, "kind": e.kind, "source_id": e.source_id, "status": e.status, "text": e.text, "scores": e.scores}
                for e in result.evidence
            ],
            "commit": settings.commit,
        }

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request, q: str = "") -> str:
        body = _ask_form(q) + _examples()
        if q:
            result = ask(q, request)
            body += f'<p class="notice" role="alert">{html.escape(result)}</p>' if isinstance(result, str) else _render_answer(result)
        else:
            body += _intro()
        return _page("Elestrals Meta Assistant", body, settings.commit)

    @app.get("/sources", response_class=HTMLResponse)
    def sources() -> str:
        with db_lock:
            rows = conn.execute("SELECT * FROM sources ORDER BY id").fetchall()
        items = "".join(
            f"<tr><td><a href='/sources/{quote(r['id'])}'>{html.escape(r['id'])}</a></td><td>{html.escape(r['title'])}</td>"
            f"<td>{html.escape(r['owner'])}</td><td>{html.escape(STATUS_LABEL.get(r['status'], r['status']))}</td>"
            f"<td>v{r['version']} · checked {html.escape(r['checked'] or '')}</td></tr>"
            for r in rows
        )
        body = (
            "<h1>Sources</h1><p>Everything the assistant can cite. Each source has a stable ID, an owner, a permission basis and a verification status.</p>"
            "<div class='table-wrap'><table><thead><tr><th>ID</th><th>Source</th><th>Owner</th><th>Status</th><th>Version</th></tr></thead>"
            f"<tbody>{items}</tbody></table></div><p><a href='/import-record'>See the import record</a></p>"
        )
        return _page("Sources", body, settings.commit)

    @app.get("/sources/{source_id}", response_class=HTMLResponse)
    def source_detail(source_id: str) -> str:
        with db_lock:
            src = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
            if src is None:
                raise HTTPException(status_code=404, detail="Unknown source")
            chunks = conn.execute("SELECT * FROM chunks WHERE source_id = ? ORDER BY ord", (source_id,)).fetchall()
            tournaments = conn.execute("SELECT * FROM tournaments WHERE source_id = ?", (source_id,)).fetchall()
            placements = conn.execute("SELECT * FROM placements WHERE source_id = ? ORDER BY rowid", (source_id,)).fetchall()
            decks = conn.execute("SELECT * FROM decks WHERE source_id = ?", (source_id,)).fetchall()
            cards = conn.execute("SELECT * FROM deck_cards WHERE source_id = ? ORDER BY deck_id, section, card_name", (source_id,)).fetchall()
            bosses = conn.execute("SELECT * FROM archetype_bosses WHERE source_id = ? ORDER BY archetype", (source_id,)).fetchall()
        e = html.escape
        parts = [
            f"<h1>{e(src['title'])}</h1>",
            "<dl class='meta'>",
            f"<dt>Source ID</dt><dd><code>{e(src['id'])}</code> (version {src['version']})</dd>",
            f"<dt>Original</dt><dd><a href='{e(src['original_url'])}'>{e(src['original_url'])}</a></dd>",
            f"<dt>Owner</dt><dd>{e(src['owner'])}</dd><dt>Permission</dt><dd>{e(src['permission'])}</dd>",
            f"<dt>Verification</dt><dd>{e(STATUS_LABEL.get(src['status'], src['status']))}</dd>",
            f"<dt>Published / checked</dt><dd>{e(src['published'] or '?')} / {e(src['checked'] or '?')}</dd>",
            f"<dt>Imported</dt><dd>{e(src['imported_at'])}</dd></dl>",
            "<h2>Stored text chunks</h2>",
        ]
        for c in chunks:
            parts.append(
                f"<section class='chunk' id='{e(c['id'].split('#')[1])}'><h3><code>{e(c['id'])}</code> · {e(c['heading'])}</h3>"
                f"<p>{e(c['text'])}</p><p class='small'>Embedding: {e(c['embed_model'] or 'none')}</p></section>"
            )
        if tournaments or placements or decks or bosses:
            parts.append("<h2>Structured records</h2>")
        for t in tournaments:
            parts.append(f"<p id='tournament-{slug(t['id'])}'><strong>{e(t['name'])}</strong>: {e(t['date_start'] or '?')} to {e(t['date_end'] or '?')}"
                         f"{' · ' + str(t['participants']) + ' participants' if t['participants'] else ''}{' · ' + e(t['date_note']) if t['date_note'] else ''}</p>")
        for p in placements:
            elements = ", ".join(f"{k} {v}" for k, v in json.loads(p["elements"] or "{}").items())
            parts.append(f"<p id='placement-{slug(p['id'])}'><strong>{e(p['placement'])}</strong>: {e(p['archetype'] or 'archetype not labeled')}"
                         f"{' · elements ' + e(elements) if elements else ''}{' · ' + e(p['note']) if p['note'] else ''}</p>")
        for d in decks:
            rows = "".join(f"<tr><td>{e(c['section'])}</td><td>{e(c['card_name'])}</td><td>{e(c['set_code'] or '')}</td><td>{c['qty']}</td></tr>" for c in cards if c["deck_id"] == d["id"])
            parts.append(f"<section id='deck-{slug(d['id'])}'><h3>Decklist: {e(d['placement'])} place ({'complete' if d['complete'] else 'partial'})</h3>"
                         f"<p><a href='{e(d['original_url'] or '')}'>Original decklist</a></p><div class='table-wrap'><table><thead><tr><th>Section</th><th>Card</th><th>Set</th><th>Qty</th></tr></thead><tbody>{rows}</tbody></table></div></section>")
        for boss in sorted({b["boss"] for b in bosses}):
            users = sorted(b["archetype"] for b in bosses if b["boss"] == boss)
            parts.append(f"<p id='boss-{slug(boss)}'><strong>{e(boss)}</strong> is played by: {e(', '.join(users))}</p>")
        for archetype in sorted({b["archetype"] for b in bosses}):
            plays = sorted(b["boss"] for b in bosses if b["archetype"] == archetype)
            parts.append(f"<p id='archetype-{slug(archetype)}'><strong>{e(archetype)}</strong> plays: {e(', '.join(plays))}</p>")
        return _page(src["title"], "".join(parts), settings.commit)

    @app.get("/import-record", response_class=HTMLResponse)
    def import_record() -> str:
        with db_lock:
            runs = conn.execute("SELECT * FROM import_runs ORDER BY id DESC").fetchall()
        rows = []
        for r in runs:
            rep = json.loads(r["report"])
            srcs = rep.get("sources", [])
            new = sum(x.get("new", 0) for x in srcs)
            changed = sum(x.get("changed", 0) for x in srcs)
            unchanged = sum(x.get("unchanged", 0) for x in srcs)
            embedded = (rep.get("embedding") or {}).get("embedded_now", 0)
            rows.append(
                f"<tr><td><a href='#run-{r['id']}'>{r['id']}</a></td><td>{html.escape(r['finished_at'] or '')}</td>"
                f"<td><code>{html.escape((r['commit_sha'] or '')[:7])}</code></td><td>{html.escape(r['corpus_version'] or '')}</td>"
                f"<td>{len(srcs)}</td><td>{new}</td><td>{changed}</td><td>{unchanged}</td><td>{embedded}</td></tr>"
            )
        table = (
            "<div class='table-wrap'><table><thead><tr><th>Run</th><th>Finished (UTC)</th><th>Commit</th><th>Corpus</th>"
            "<th>Sources</th><th>New chunks</th><th>Changed</th><th>Unchanged</th><th>Embedded</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>"
        )
        details = "".join(
            f"<details id='run-{r['id']}'{' open' if i == 0 else ''}><summary>Run {r['id']} full report</summary>"
            f"<pre>{html.escape(json.dumps(json.loads(r['report']), indent=2))}</pre></details>"
            for i, r in enumerate(runs)
        )
        intro = ("<h1>Import record</h1><p>Every import run stored in this app's database, newest first. The import runs each time "
                 "the app starts, so this list also shows that the database survives restarts and updates. A repeat import with no "
                 "data changes should show 0 new, 0 changed and 0 embedded.</p>")
        return _page("Import record", intro + table + "<h2>Full reports</h2>" + details, settings.commit)

    @app.post("/admin/import")
    def admin_import(authorization: str | None = Header(default=None)) -> dict:
        require_admin(authorization)
        with db_lock:
            return run_import(conn, settings.corpus_dir, embedder, settings.commit)

    return app


def _page(title: str, body: str, commit: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} · Elestrals Meta Assistant</title>
<style>{CSS}</style></head>
<body><a class="skip" href="#main">Skip to content</a>
<header><nav aria-label="Main"><a class="brand" href="/">Elestrals Meta Assistant</a>
<a href="/">Ask</a><a href="/sources">Sources</a><a href="/import-record">Import record</a><a href="https://xenoshin.com/projects/elestrals-rag.html">About this project</a></nav></header>
<main id="main">{body}</main>
<footer><p class="small">{FAN_NOTICE}</p>
<p class="small">Built by Peter Balasis for NJIT IS373 · source <a href="https://github.com/pb392/xenoshin-site">pb392/xenoshin-site</a> · running commit <code>{html.escape(commit[:12])}</code></p></footer>
</body></html>"""


def _ask_form(q: str) -> str:
    return f"""<h1>Ask about the Elestrals meta</h1>
<form method="get" action="/" class="ask"><label for="q">Your question</label>
<div class="row"><input id="q" name="q" type="text" maxlength="300" required value="{html.escape(q)}" placeholder="e.g. Who won the last tournament?">
<button type="submit">Ask</button></div></form>"""


def _examples() -> str:
    links = "".join(f'<li><a href="/?q={quote(x)}">{html.escape(x)}</a></li>' for x in EXAMPLES)
    return f'<details class="examples"><summary>Example questions</summary><ul>{links}</ul></details>'


def _intro() -> str:
    return """<section class="card"><h2>How it works</h2><ol>
<li>Your question is matched against the imported sources with keyword search and meaning-based (vector) search.</li>
<li>Exact facts such as card counts and which decks use a boss come from database lookups.</li>
<li>An AI model (Google Gemini) writes a short answer using only that evidence, with links to every source it used.</li>
<li>If the sources don't cover your question, it says so instead of guessing.</li></ol>
<p>The data is small on purpose: four sources, including the official 2026 Worlds results, one Premier's top 8 with the winning decklist, and the author's own meta notes. <a href="/sources">See every source</a>.</p></section>"""


def _cite_link(evidence_id: str) -> str:
    source_id, _, anchor = evidence_id.partition("#")
    return f"/sources/{quote(source_id)}#{quote(anchor)}"


def _render_answer(r: AnswerResult) -> str:
    e = html.escape
    text = e(r.answer)
    for cid in r.citations:
        text = text.replace(e(cid), f'<a href="{_cite_link(cid)}">{e(cid)}</a>')
    status_note = {
        "answered": "Answer checked: every citation matches retrieved evidence.",
        "insufficient": "The model reported that the evidence does not answer this question.",
        "withheld": "The model's answer cited no retrieved evidence, so it was withheld.",
        "no_sources": "No sources matched this question.",
        "generation_unavailable": "Answer generation is off; showing retrieved evidence only.",
        "error": "The answer service failed; showing retrieved evidence only.",
    }.get(r.status, r.status)
    warnings = "".join(f"<li>{e(w)}</li>" for w in r.warnings)
    rows = "".join(
        f"<tr><td><a href='{_cite_link(ev.id)}'><code>{e(ev.id)}</code></a></td><td>{e(ev.kind)}</td><td>{e(ev.status_label)}</td>"
        f"<td>{e(ev.text)}</td><td class='small'>{e(', '.join(f'{k} {v}' for k, v in ev.scores.items()))}</td></tr>"
        for ev in r.evidence
    )
    trace = (
        f"<details class='trace'><summary>How this answer was found (trace)</summary>"
        f"<p>Retrieval mode: {e(r.retrieval.mode if r.retrieval else '')} · model: {e(r.model or 'none')}</p>"
        f"<div class='table-wrap'><table><thead><tr><th>Evidence ID</th><th>Type</th><th>Status</th><th>Text sent to the model</th><th>Scores</th></tr></thead><tbody>{rows}</tbody></table></div>"
        f"<p class='small'>The full prompt sent to the model:</p><pre>{e(r.prompt) if r.prompt else '(no model call)'}</pre></details>"
    )
    return (
        f"<section class='card answer' aria-live='polite'><h2>Answer</h2><p class='answer-text'>{text}</p>"
        f"<p class='status status-{e(r.status)}'>{e(status_note)}</p>"
        f"<p class='small'>{e(r.coverage)}</p>"
        f"{'<ul class=small>' + warnings + '</ul>' if warnings else ''}</section>{trace}"
    )


CSS = """
:root{--bg:#0f1020;--panel:#1a1b33;--text:#ecebf7;--muted:#b8b6d6;--accent:#ffb347;--link:#8fd3ff;--ok:#7ee0a1;--warn:#ffcf70}
*{box-sizing:border-box}body{margin:0;font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--text)}
a{color:var(--link)}a:focus-visible,button:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.skip{position:absolute;left:-999px}.skip:focus{left:8px;top:8px;background:#000;padding:8px;z-index:2}
header{background:#14152b;border-bottom:1px solid #2c2d52}nav{max-width:960px;margin:auto;display:flex;flex-wrap:wrap;gap:16px;padding:12px 16px;align-items:center}
nav .brand{font-weight:700;color:var(--accent);margin-right:auto;text-decoration:none}main{max-width:960px;margin:auto;padding:16px}
footer{max-width:960px;margin:auto;padding:16px;border-top:1px solid #2c2d52}.small{font-size:.85rem;color:var(--muted)}
h1{font-size:1.7rem;margin:.6em 0}.card{background:var(--panel);border-radius:10px;padding:16px;margin:16px 0}
.ask label{display:block;font-weight:600;margin-bottom:4px}.row{display:flex;gap:8px}.row input{flex:1;min-width:0;padding:10px;border-radius:8px;border:1px solid #444;background:#0b0c18;color:var(--text);font-size:1rem}
button{padding:10px 18px;border:0;border-radius:8px;background:var(--accent);color:#1a1200;font-weight:700;font-size:1rem;cursor:pointer}
.answer-text{font-size:1.1rem}.status{font-weight:600}.status-answered{color:var(--ok)}.status-withheld,.status-error,.status-insufficient,.status-no_sources{color:var(--warn)}
.notice{background:#3a2a10;padding:10px;border-radius:8px}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:.9rem}
th,td{border:1px solid #333559;padding:6px 8px;text-align:left;vertical-align:top}pre{white-space:pre-wrap;background:#0b0c18;padding:12px;border-radius:8px;font-size:.8rem;overflow-x:auto}
code{font-size:.85em}.chunk{border-left:3px solid var(--accent);padding-left:12px;margin:12px 0}.chunk:target,section:target,p:target{background:#2a2b10}
dl.meta{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:4px 16px}dd{min-width:0;margin:0}a,code,td,dd{overflow-wrap:anywhere}@media(max-width:600px){dl.meta{grid-template-columns:1fr}dl.meta dd{margin-bottom:8px}}dl.meta dt{font-weight:600}.examples,.trace{margin:12px 0}
"""


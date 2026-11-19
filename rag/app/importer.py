"""Repeatable import: manifest -> sources, chunks (+FTS, +embeddings), tables.

Running it twice changes nothing the second time: rows are keyed by stable
IDs, structured rows for a source are replaced as a set, and a chunk is only
re-embedded when its text hash or the embedding model changes.

Run inside the container:  python -m app.importer
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from .chunking import Chunk, chunk_markdown
from .providers import Embedder, ProviderError


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_manifest(corpus_dir: Path) -> dict:
    return json.loads((corpus_dir / "manifest.json").read_text(encoding="utf-8"))


def results_to_markdown(source: dict, data: dict) -> str:
    """Readable text version of a results file, so text search can find it too."""
    lines = [f"# {source['title']}"]
    for t in data.get("tournaments", []):
        lines += ["", "## Event", "", f"{t['name']} was held on {t['date_start']} with {t.get('participants', 'an unknown number of')} participants."]
    placements = data.get("placements", [])
    if placements:
        lines += ["", "## Top 8 results", ""]
        for p in placements:
            elements = ", ".join(f"{k} {v}" for k, v in (p.get("elements") or {}).items())
            cards = ", ".join((p.get("featured_cards") or [])[:6])
            lines.append(f"The {p['placement']} deck's main-deck elements were {elements}; featured cards included {cards}.")
    for deck in data.get("decks", []):
        main = [c for c in deck["cards"] if c["section"] == "main"]
        lines += ["", f"## Winning decklist ({deck['placement']})", ""]
        lines.append(
            "The main deck ran "
            + "; ".join(f"{c['qty']} {c['name']}" for c in main)
            + "."
        )
    return "\n".join(lines) + "\n"


def _hash(*parts: str) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(part.encode())
    return h.hexdigest()


def _load_structured(corpus_dir: Path, source: dict) -> dict:
    rel = source.get("structured")
    return json.loads((corpus_dir / rel).read_text(encoding="utf-8")) if rel else {}


def _write_structured(conn: sqlite3.Connection, source: dict, data: dict) -> dict:
    sid, ver, status = source["id"], source["version"], source["status"]
    for table in ("tournaments", "placements", "decks", "archetype_bosses"):
        conn.execute(f"DELETE FROM {table} WHERE source_id = ?", (sid,))
    conn.execute("DELETE FROM deck_cards WHERE source_id = ?", (sid,))
    counts = {"tournaments": 0, "placements": 0, "decks": 0, "deck_cards": 0, "archetype_bosses": 0}
    for t in data.get("tournaments", []):
        conn.execute(
            "INSERT OR REPLACE INTO tournaments VALUES (?,?,?,?,?,?,?,?,?,?)",
            (t["id"], t["name"], json.dumps(t.get("aliases", [])), t.get("date_start"), t.get("date_end"),
             t.get("date_note"), t.get("participants"), sid, ver, status),
        )
        counts["tournaments"] += 1
    for p in data.get("placements", []):
        conn.execute(
            "INSERT INTO placements VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (p["id"], sid, ver, status, p["tournament"], p["placement"], p.get("archetype"),
             json.dumps(p.get("elements") or {}), json.dumps(p.get("featured_cards") or []),
             p.get("deck"), p.get("note")),
        )
        counts["placements"] += 1
    for d in data.get("decks", []):
        conn.execute(
            "INSERT OR REPLACE INTO decks VALUES (?,?,?,?,?,?,?,?)",
            (d["id"], d["tournament"], d["placement"], d.get("original_url"), int(bool(d.get("complete"))), sid, ver, status),
        )
        counts["decks"] += 1
        for c in d["cards"]:
            conn.execute(
                "INSERT INTO deck_cards VALUES (?,?,?,?,?,?)",
                (d["id"], c["section"], c["name"], c.get("set"), c["qty"], sid),
            )
            counts["deck_cards"] += 1
    for ab in data.get("archetype_bosses", []):
        conn.execute(
            "INSERT INTO archetype_bosses VALUES (?,?,?,?,?)", (ab["archetype"], ab["boss"], sid, ver, status)
        )
        counts["archetype_bosses"] += 1
    return counts


def run_import(conn: sqlite3.Connection, corpus_dir: Path, embedder: Embedder | None, commit: str = "unknown") -> dict:
    manifest = load_manifest(corpus_dir)
    started = _now()
    report: dict = {"corpus_version": manifest.get("corpus_version"), "sources": [], "removed_sources": []}

    planned: list[tuple[dict, dict, list[Chunk], str]] = []
    for source in manifest["sources"]:
        data = _load_structured(corpus_dir, source)
        if source["kind"] == "text":
            text = (corpus_dir / source["file"]).read_text(encoding="utf-8")
        else:
            text = results_to_markdown(source, data)
        chunks = chunk_markdown(source["id"], text)
        content_hash = _hash(text, json.dumps(data, sort_keys=True))
        planned.append((source, data, chunks, content_hash))

    # Work out which chunks need (re)embedding before touching the database.
    existing = {
        row["id"]: (row["text_hash"], row["embed_model"], row["embedding"] is not None)
        for row in conn.execute("SELECT id, text_hash, embed_model, embedding FROM chunks")
    }
    model = embedder.model if embedder else None
    to_embed = [
        c for _, _, chunks, _ in planned for c in chunks
        if not (c.id in existing and existing[c.id][0] == c.text_hash and existing[c.id][1] == model and existing[c.id][2])
    ]
    vectors: dict[str, list[float]] = {}
    embed_error = None
    if embedder and to_embed:
        try:
            for c, v in zip(to_embed, embedder.embed_documents([(c.heading, c.text) for c in to_embed])):
                vectors[c.id] = v
        except ProviderError as exc:
            embed_error = str(exc)
    report["embedding"] = {
        "model": model or "none (no API key: keyword search only)",
        "embedded_now": len(vectors),
        "error": embed_error,
    }

    with conn:
        manifest_ids = {s["id"] for s, _, _, _ in planned}
        for row in conn.execute("SELECT id FROM sources").fetchall():
            if row["id"] not in manifest_ids:
                sid = row["id"]
                for table in ("tournaments", "placements", "decks", "deck_cards", "archetype_bosses"):
                    conn.execute(f"DELETE FROM {table} WHERE source_id = ?", (sid,))
                conn.execute("DELETE FROM chunks_fts WHERE chunk_id IN (SELECT id FROM chunks WHERE source_id = ?)", (sid,))
                conn.execute("DELETE FROM chunks WHERE source_id = ?", (sid,))
                conn.execute("DELETE FROM sources WHERE id = ?", (sid,))
                report["removed_sources"].append(sid)

        for source, data, chunks, content_hash in planned:
            sid = source["id"]
            conn.execute(
                "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
                "title=excluded.title, kind=excluded.kind, original_url=excluded.original_url, owner=excluded.owner, "
                "permission=excluded.permission, status=excluded.status, version=excluded.version, "
                "published=excluded.published, checked=excluded.checked, "
                "imported_at=CASE WHEN sources.content_hash = excluded.content_hash THEN sources.imported_at ELSE excluded.imported_at END, "
                "content_hash=excluded.content_hash",
                (sid, source["title"], source["kind"], source["original_url"], source["owner"], source["permission"],
                 source["status"], source["version"], source.get("published"), source.get("checked"), content_hash, started),
            )
            stats = {"id": sid, "chunks": len(chunks), "new": 0, "changed": 0, "unchanged": 0, "removed": 0}
            keep = {c.id for c in chunks}
            for old in conn.execute("SELECT id FROM chunks WHERE source_id = ?", (sid,)).fetchall():
                if old["id"] not in keep:
                    conn.execute("DELETE FROM chunks WHERE id = ?", (old["id"],))
                    stats["removed"] += 1
            for c in chunks:
                prior = existing.get(c.id)
                if prior is None:
                    stats["new"] += 1
                elif prior[0] != c.text_hash:
                    stats["changed"] += 1
                else:
                    stats["unchanged"] += 1
                if c.id in vectors:
                    emb, emb_model = json.dumps(vectors[c.id]), model
                    conn.execute(
                        "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET ord=excluded.ord, "
                        "heading=excluded.heading, text=excluded.text, text_hash=excluded.text_hash, "
                        "embedding=excluded.embedding, embed_model=excluded.embed_model",
                        (c.id, sid, c.ord, c.heading, c.text, c.text_hash, emb, emb_model),
                    )
                elif prior is not None and prior[0] == c.text_hash:
                    conn.execute("UPDATE chunks SET ord=?, heading=? WHERE id=?", (c.ord, c.heading, c.id))
                else:
                    conn.execute(
                        "INSERT INTO chunks VALUES (?,?,?,?,?,?,NULL,NULL) ON CONFLICT(id) DO UPDATE SET ord=excluded.ord, "
                        "heading=excluded.heading, text=excluded.text, text_hash=excluded.text_hash, embedding=NULL, embed_model=NULL",
                        (c.id, sid, c.ord, c.heading, c.text, c.text_hash),
                    )
            conn.execute("DELETE FROM chunks_fts WHERE chunk_id IN (SELECT id FROM chunks WHERE source_id = ?) OR chunk_id LIKE ?", (sid, f"{sid}#%"))
            for c in chunks:
                conn.execute("INSERT INTO chunks_fts (chunk_id, heading, text) VALUES (?,?,?)", (c.id, c.heading, c.text))
            stats["structured_rows"] = _write_structured(conn, source, data)
            report["sources"].append(stats)

        report["totals"] = {
            "sources": conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
            "chunks": conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0],
            "chunks_with_embeddings": conn.execute("SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL").fetchone()[0],
            "tournaments": conn.execute("SELECT COUNT(*) FROM tournaments").fetchone()[0],
            "placements": conn.execute("SELECT COUNT(*) FROM placements").fetchone()[0],
            "deck_cards": conn.execute("SELECT COUNT(*) FROM deck_cards").fetchone()[0],
            "archetype_bosses": conn.execute("SELECT COUNT(*) FROM archetype_bosses").fetchone()[0],
        }
        conn.execute(
            "INSERT INTO import_runs (started_at, finished_at, corpus_version, commit_sha, report) VALUES (?,?,?,?,?)",
            (started, _now(), manifest.get("corpus_version"), commit, json.dumps(report)),
        )
    return report


def main() -> int:
    from .config import load_settings
    from .db import connect
    from .providers import GeminiEmbedder

    settings = load_settings()
    conn = connect(settings.db_path)
    embedder = None
    if settings.gemini_api_key:
        embedder = GeminiEmbedder(settings.gemini_api_key, settings.embed_model, settings.embed_dims, settings.gemini_base_url)
    report = run_import(conn, settings.corpus_dir, embedder, settings.commit)
    print(json.dumps(report, indent=2))
    return 0 if not report["embedding"]["error"] else 1


if __name__ == "__main__":
    sys.exit(main())

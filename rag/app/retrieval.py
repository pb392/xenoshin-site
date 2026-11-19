"""Hybrid retrieval: FTS5 keyword search + vector similarity, merged with
reciprocal rank fusion (RRF), plus structured facts from SQL.

Keyword search is the transparent baseline; vectors catch paraphrases.
Every result keeps its scores so the trace page can show why it was chosen.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field

from .facts import Evidence, structured_facts
from .providers import Embedder, ProviderError, cosine

STOPWORDS = set(
    "a an and are at be by did do does for from how i in is it its of on or the to was were what when where which who why with "
    "this that these those there their they you your me my about any can could should would".split()
)
RRF_K = 60


@dataclass
class RetrievalResult:
    question: str
    evidence: list[Evidence]
    keyword_hits: list[tuple[str, float]] = field(default_factory=list)
    vector_hits: list[tuple[str, float]] = field(default_factory=list)
    mode: str = "hybrid"
    note: str = ""


def keyword_search(conn: sqlite3.Connection, question: str, limit: int = 8) -> list[tuple[str, float]]:
    terms = [t for t in re.findall(r"[a-z0-9]+", question.lower()) if t not in STOPWORDS and len(t) > 1]
    if not terms:
        return []
    match = " OR ".join(f'"{t}"' for t in terms)
    rows = conn.execute(
        "SELECT chunk_id, bm25(chunks_fts) AS score FROM chunks_fts WHERE chunks_fts MATCH ? ORDER BY score LIMIT ?",
        (match, limit),
    ).fetchall()
    return [(r["chunk_id"], -float(r["score"])) for r in rows]  # bm25: lower is better; flip sign


def vector_search(conn: sqlite3.Connection, query_vector: list[float], model: str, limit: int = 8) -> list[tuple[str, float]]:
    scored = []
    for row in conn.execute("SELECT id, embedding FROM chunks WHERE embedding IS NOT NULL AND embed_model = ?", (model,)):
        scored.append((row["id"], cosine(query_vector, json.loads(row["embedding"]))))
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:limit]


def fuse(*rankings: list[tuple[str, float]]) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, (chunk_id, _) in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


def retrieve(conn: sqlite3.Connection, question: str, embedder: Embedder | None, top_k: int = 4) -> RetrievalResult:
    result = RetrievalResult(question=question, evidence=[])
    if conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == 0:
        result.mode, result.note = "empty", "No sources are imported."
        return result

    result.keyword_hits = keyword_search(conn, question)
    if embedder is not None:
        try:
            result.vector_hits = vector_search(conn, embedder.embed_query(question), embedder.model)
        except ProviderError as exc:
            result.mode, result.note = "keyword-only", f"Vector search unavailable: {exc}"
    else:
        result.mode, result.note = "keyword-only", "No embedding provider configured."

    keyword_scores = dict(result.keyword_hits)
    vector_scores = dict(result.vector_hits)
    fused = fuse(result.keyword_hits, result.vector_hits)[:top_k]
    for chunk_id, rrf in fused:
        row = conn.execute(
            "SELECT c.id, c.source_id, c.heading, c.text, s.status FROM chunks c JOIN sources s ON s.id = c.source_id WHERE c.id = ?",
            (chunk_id,),
        ).fetchone()
        if row is None:
            continue
        scores = {"rrf": round(rrf, 4)}
        if chunk_id in keyword_scores:
            scores["keyword_bm25"] = round(keyword_scores[chunk_id], 3)
        if chunk_id in vector_scores:
            scores["vector_cosine"] = round(vector_scores[chunk_id], 3)
        result.evidence.append(Evidence(
            id=row["id"], source_id=row["source_id"], kind="chunk", text=row["text"],
            status=row["status"], heading=row["heading"], scores=scores,
        ))
    result.evidence = structured_facts(conn, question) + result.evidence
    return result

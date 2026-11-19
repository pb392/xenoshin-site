"""Question -> retrieval -> prompt -> model -> citation check.

The model may only use the numbered evidence, must cite evidence IDs, and must
say it lacks a source when the evidence doesn't answer the question. After
generation the citations are checked against the evidence actually sent:
unknown IDs are removed, and an answer with no valid citation is withheld.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field

from .facts import Evidence, coverage_line
from .providers import Embedder, Generator, ProviderError
from .retrieval import RetrievalResult, retrieve

INSUFFICIENT = "I don't have a source for that in my imported data."

SYSTEM_PROMPT = f"""You answer questions about the competitive Elestrals trading card game meta.
Rules:
1. Use ONLY the evidence items provided. Do not use outside knowledge, even if you think you know the answer.
2. End every factual sentence with the evidence ID(s) it relies on, in square brackets, exactly as written, e.g. [S2-premier-2026-10-24#deck-d-premier-2026-10-24-1].
3. If the evidence does not answer the question, reply with exactly: {INSUFFICIENT}
4. Evidence marked "author knowledge" comes from the app author's own notes: say so (e.g. "according to the author's notes").
5. Evidence marked "unknown" means the data is missing: say it is unknown. Never turn a missing count into zero.
6. If evidence items disagree, say they disagree and cite both.
7. Answer in at most 120 words. Do not invent card text, decklists or placements."""


@dataclass
class AnswerResult:
    question: str
    answer: str
    status: str  # answered | insufficient | withheld | no_sources | generation_unavailable | error
    citations: list[str] = field(default_factory=list)
    removed_citations: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    retrieval: RetrievalResult | None = None
    coverage: str = ""
    prompt: str = ""
    model: str = ""
    warnings: list[str] = field(default_factory=list)


def build_prompt(question: str, evidence: list[Evidence], coverage: str) -> str:
    lines = ["Evidence:"]
    for n, item in enumerate(evidence, start=1):
        label = f"{item.kind}, {item.status_label}"
        heading = f" ({item.heading})" if item.heading else ""
        lines.append(f"{n}. [{item.id}] ({label}){heading}: {item.text}")
    lines += ["", f"Data coverage: {coverage}", "", f"Question: {question}"]
    return "\n".join(lines)


CITATION = re.compile(r"\[([^\[\]]{3,200})\]")


def check_citations(text: str, allowed: set[str]) -> tuple[str, list[str], list[str]]:
    valid: list[str] = []
    removed: list[str] = []

    def replace(match: re.Match) -> str:
        ids = [part.strip() for part in re.split(r"[;,]", match.group(1)) if part.strip()]
        kept = [i for i in ids if i in allowed]
        removed.extend(i for i in ids if i not in allowed)
        for i in kept:
            if i not in valid:
                valid.append(i)
        return f"[{'; '.join(kept)}]" if kept else ""

    cleaned = CITATION.sub(replace, text)
    return re.sub(r"\s+([.,;])", r"\1", cleaned).strip(), valid, removed


def is_insufficient(text: str) -> bool:
    simple = re.sub(r"[^a-z ]", "", text.lower())
    return "dont have a source for that" in simple or "do not have a source for that" in simple


def answer_question(
    conn: sqlite3.Connection,
    question: str,
    embedder: Embedder | None,
    generator: Generator | None,
    top_k: int = 4,
) -> AnswerResult:
    retrieval = retrieve(conn, question, embedder, top_k)
    coverage = coverage_line(conn)
    result = AnswerResult(
        question=question, answer="", status="", evidence=retrieval.evidence, retrieval=retrieval,
        coverage=coverage, model=getattr(generator, "model", ""),
    )
    if retrieval.note:
        result.warnings.append(retrieval.note)
    if retrieval.mode == "empty" or not retrieval.evidence:
        result.answer, result.status = INSUFFICIENT, "no_sources"
        return result

    result.prompt = build_prompt(question, retrieval.evidence, coverage)
    if generator is None:
        result.answer = "Answer generation is not configured, so only the retrieved evidence is shown below."
        result.status = "generation_unavailable"
        return result
    try:
        raw = generator.generate(SYSTEM_PROMPT, result.prompt)
    except ProviderError as exc:
        result.answer, result.status = "The answer service is unavailable right now. The retrieved evidence is shown below.", "error"
        result.warnings.append(str(exc))
        return result

    if is_insufficient(raw):
        result.answer, result.status = INSUFFICIENT, "insufficient"
        return result
    text, valid, removed = check_citations(raw, {e.id for e in retrieval.evidence})
    result.removed_citations = removed
    if removed:
        result.warnings.append(f"Removed {len(removed)} citation(s) that did not match retrieved evidence: {', '.join(removed)}")
    if not valid:
        result.answer, result.status = INSUFFICIENT, "withheld"
        result.warnings.append("The model's answer had no valid citation, so it was withheld.")
        return result
    result.answer, result.citations, result.status = text, valid, "answered"
    return result

"""Heading/paragraph chunking with stable IDs.

Each "## heading" section becomes one chunk (sections here are short).
A section longer than MAX_CHARS is split at paragraph boundaries, then at
sentence boundaries, so a chunk never cuts a sentence in half.
Chunk IDs are "<source_id>#<n>", numbered in document order, so the same
file always produces the same IDs.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

MAX_CHARS = 900


@dataclass(frozen=True)
class Chunk:
    id: str
    source_id: str
    ord: int
    heading: str
    text: str

    @property
    def text_hash(self) -> str:
        return hashlib.sha256(f"{self.heading}\n{self.text}".encode()).hexdigest()


def _split_long(text: str) -> list[str]:
    if len(text) <= MAX_CHARS:
        return [text]
    parts: list[str] = []
    current = ""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if current and len(current) + 1 + len(sentence) > MAX_CHARS:
            parts.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        parts.append(current)
    return parts


def chunk_markdown(source_id: str, markdown: str) -> list[Chunk]:
    title = ""
    sections: list[tuple[str, list[str]]] = []
    heading = ""
    paragraphs: list[str] = []
    buffer: list[str] = []

    def flush_paragraph() -> None:
        if buffer:
            paragraphs.append(" ".join(line.strip() for line in buffer).strip())
            buffer.clear()

    for line in markdown.splitlines():
        if line.startswith("# ") and not title:
            title = line[2:].strip()
            continue
        if line.startswith("## "):
            flush_paragraph()
            if paragraphs:
                sections.append((heading or title, paragraphs))
            heading, paragraphs = line[3:].strip(), []
            continue
        if not line.strip():
            flush_paragraph()
        else:
            buffer.append(line)
    flush_paragraph()
    if paragraphs:
        sections.append((heading or title, paragraphs))

    chunks: list[Chunk] = []
    for section_heading, section_paragraphs in sections:
        full_heading = f"{title} > {section_heading}" if title and section_heading != title else (title or section_heading)
        text = "\n".join(p for p in section_paragraphs if p)
        pieces = [text] if len(text) <= MAX_CHARS else [
            piece for paragraph in section_paragraphs for piece in _split_long(paragraph)
        ]
        for piece in pieces:
            n = len(chunks) + 1
            chunks.append(Chunk(f"{source_id}#{n}", source_id, n, full_heading, piece))
    return chunks

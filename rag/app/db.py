"""SQLite storage: text chunks (with FTS5 keyword index and embedding vectors)
plus small relational tables that hold the graph-shaped tournament data.

Every relationship row carries provenance: source_id, source_version and a
verification status ("externally_verified" or "author_knowledge").
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    kind TEXT NOT NULL,
    original_url TEXT NOT NULL,
    owner TEXT NOT NULL,
    permission TEXT NOT NULL,
    status TEXT NOT NULL,
    version INTEGER NOT NULL,
    published TEXT,
    checked TEXT,
    content_hash TEXT NOT NULL,
    imported_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,               -- e.g. S3-note-01#2 (stable)
    source_id TEXT NOT NULL REFERENCES sources(id),
    ord INTEGER NOT NULL,
    heading TEXT NOT NULL,
    text TEXT NOT NULL,
    text_hash TEXT NOT NULL,
    embedding TEXT,                    -- JSON array of floats
    embed_model TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(chunk_id UNINDEXED, heading, text);

CREATE TABLE IF NOT EXISTS tournaments (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    aliases TEXT NOT NULL,             -- JSON list
    date_start TEXT,
    date_end TEXT,
    date_note TEXT,
    participants INTEGER,
    source_id TEXT NOT NULL,
    source_version INTEGER NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS placements (
    id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_version INTEGER NOT NULL,
    status TEXT NOT NULL,
    tournament_id TEXT NOT NULL,
    placement TEXT NOT NULL,
    archetype TEXT,
    elements TEXT,                     -- JSON object
    featured_cards TEXT,               -- JSON list
    deck_id TEXT,
    note TEXT,
    PRIMARY KEY (source_id, id)
);

CREATE TABLE IF NOT EXISTS decks (
    id TEXT PRIMARY KEY,
    tournament_id TEXT NOT NULL,
    placement TEXT NOT NULL,
    original_url TEXT,
    complete INTEGER NOT NULL,
    source_id TEXT NOT NULL,
    source_version INTEGER NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS deck_cards (
    deck_id TEXT NOT NULL,
    section TEXT NOT NULL,
    card_name TEXT NOT NULL,
    set_code TEXT,
    qty INTEGER NOT NULL,
    source_id TEXT NOT NULL,
    PRIMARY KEY (deck_id, section, card_name, set_code)
);

CREATE TABLE IF NOT EXISTS archetype_bosses (
    archetype TEXT NOT NULL,
    boss TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_version INTEGER NOT NULL,
    status TEXT NOT NULL,
    PRIMARY KEY (archetype, boss, source_id)
);

CREATE TABLE IF NOT EXISTS import_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    corpus_version TEXT,
    commit_sha TEXT,
    report TEXT                        -- JSON
);
"""


def connect(db_path: str) -> sqlite3.Connection:
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if db_path != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    return conn

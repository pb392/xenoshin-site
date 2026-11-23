"""Structured (graph-shaped) lookups over the relational tables.

Vectors are poor at exact counts and "which X share Y" questions, so these
SQL joins turn the question into exact facts. Each fact keeps its source and
verification status so the answer can say how sure it is.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field

STATUS_LABEL = {
    "externally_verified": "externally verified",
    "author_knowledge": "author knowledge (Peter's notes)",
    "unknown": "unknown",
}

COUNT_WORDS = re.compile(r"\b(how many|copies|copy|count|number of|quantity|run|ran|play|played)\b")
WIN_WORDS = re.compile(r"\b(won|win|wins|winner|winning|champion|1st|first place|topped)\b")
RECENT_WORDS = re.compile(r"\b(last|latest|recent|newest|most recent)\b")
RESULT_WORDS = re.compile(r"\b(top ?\d+|top cut|placed|placement|placements|results|finished|standings)\b")


@dataclass
class Evidence:
    id: str
    source_id: str
    kind: str  # "chunk" or "fact"
    text: str
    status: str
    heading: str = ""
    scores: dict = field(default_factory=dict)

    @property
    def status_label(self) -> str:
        return STATUS_LABEL.get(self.status, self.status)


def norm(text: str) -> str:
    text = text.lower().replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9' ]+", " ", text)).strip()


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _contains(question: str, phrase: str) -> bool:
    phrase = norm(phrase)
    return bool(phrase) and re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", question) is not None


def _dates(row: sqlite3.Row) -> str:
    if row["date_start"] and row["date_end"] and row["date_start"] != row["date_end"]:
        return f"{row['date_start']} to {row['date_end']}"
    return row["date_start"] or "date unknown"


def mentioned_tournaments(conn: sqlite3.Connection, q: str) -> list[sqlite3.Row]:
    found = []
    for row in conn.execute("SELECT * FROM tournaments"):
        names = [row["name"], *json.loads(row["aliases"])]
        if any(_contains(q, n) for n in names):
            found.append(row)
    return found


def latest_tournament(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM tournaments ORDER BY COALESCE(date_end, date_start) DESC LIMIT 1"
    ).fetchone()


def coverage_line(conn: sqlite3.Connection) -> str:
    latest = latest_tournament(conn)
    if latest is None:
        return "No events imported yet."
    return (
        f"Latest imported event: {latest['name']} ({_dates(latest)}), from {latest['source_id']} "
        f"({STATUS_LABEL.get(latest['status'], latest['status'])}). Newer events may exist but not be imported yet."
    )


def card_names(conn: sqlite3.Connection) -> list[str]:
    return [r[0] for r in conn.execute("SELECT DISTINCT card_name FROM deck_cards")]


def _card_mentions(conn: sqlite3.Connection, q: str) -> list[str]:
    hits = []
    for name in card_names(conn):
        base = name.split(" - ")[0]
        if _contains(q, name) or (len(base) > 3 and _contains(q, base)):
            hits.append(name)
    # Prefer the most specific names ("Hestia's Hearth - Eternal Flame" over "Hestia's Hearth").
    return sorted(set(hits), key=len, reverse=True)


def card_count_facts(conn: sqlite3.Connection, q: str, tournaments: list[sqlite3.Row]) -> list[Evidence]:
    if not COUNT_WORDS.search(q):
        return []
    cards = _card_mentions(conn, q)
    facts: list[Evidence] = []
    scope = tournaments or list(conn.execute("SELECT * FROM tournaments"))
    asks_quantity = re.search(r"\b(how many|copies|copy|quantity|number of)\b", q) is not None
    if not cards and not (asks_quantity and tournaments):
        return facts
    for t in scope:
        decks = conn.execute("SELECT * FROM decks WHERE tournament_id = ?", (t["id"],)).fetchall()
        if not decks:
            if tournaments and asks_quantity:  # only report a gap for events the user named
                facts.append(Evidence(
                    id=f"{t['source_id']}#tournament-{slug(t['id'])}", source_id=t["source_id"], kind="fact",
                    status="unknown",
                    text=f"No decklist is imported for {t['name']}, so card counts for that event are unknown (not zero).",
                ))
            continue
        for deck in decks:
            for card in cards:
                rows = conn.execute(
                    "SELECT section, qty FROM deck_cards WHERE deck_id = ? AND card_name = ?", (deck["id"], card)
                ).fetchall()
                if rows:
                    parts = ", ".join(f"{r['qty']} in the {r['section']} deck" for r in rows)
                    text = f"The {deck['placement']}-place deck at {t['name']} ({_dates(t)}) ran {card}: {parts}."
                elif deck["complete"]:
                    text = f"The complete {deck['placement']}-place decklist at {t['name']} contains 0 copies of {card}."
                else:
                    continue
                facts.append(Evidence(
                    id=f"{deck['source_id']}#deck-{slug(deck['id'])}", source_id=deck["source_id"], kind="fact",
                    status=deck["status"], text=text,
                ))
    return facts


def boss_facts(conn: sqlite3.Connection, q: str) -> list[Evidence]:
    rows = conn.execute("SELECT * FROM archetype_bosses").fetchall()
    bosses = {r["boss"] for r in rows}
    archetypes = {r["archetype"] for r in rows}
    hit_bosses = {b for b in bosses if _contains(q, b) or _contains(q, b.split(" ")[0])}
    hit_archetypes = {a for a in archetypes if _contains(q, a)}
    facts: list[Evidence] = []
    for boss in sorted(hit_bosses):
        users = [r for r in rows if r["boss"] == boss]
        names = sorted({r["archetype"] for r in users})
        facts.append(Evidence(
            id=f"{users[0]['source_id']}#boss-{slug(boss)}", source_id=users[0]["source_id"], kind="fact",
            status=users[0]["status"],
            text=f"{boss} is played by {len(names)} archetype(s): {', '.join(names)}.",
        ))
    for archetype in sorted(hit_archetypes):
        plays = [r for r in rows if r["archetype"] == archetype]
        facts.append(Evidence(
            id=f"{plays[0]['source_id']}#archetype-{slug(archetype)}", source_id=plays[0]["source_id"], kind="fact",
            status=plays[0]["status"],
            text=f"{archetype} plays these bosses: {', '.join(sorted(r['boss'] for r in plays))}.",
        ))
    return facts


def _placement_text(p: sqlite3.Row, t: sqlite3.Row) -> str:
    elements = ", ".join(f"{k} {v}" for k, v in json.loads(p["elements"] or "{}").items())
    if p["archetype"]:
        what = f"{p['archetype']} ({elements})" if elements else p["archetype"]
    else:
        what = f"{elements} deck"
    note = f" Note: {p['note']}" if p["note"] else ""
    return f"{p['placement']} at {t['name']} ({_dates(t)}): {what}.{note}"


def winner_facts(conn: sqlite3.Connection, q: str, tournaments: list[sqlite3.Row]) -> list[Evidence]:
    wants_win = WIN_WORDS.search(q) is not None
    wants_recent = RECENT_WORDS.search(q) is not None
    wants_results = RESULT_WORDS.search(q) is not None
    if not (wants_win or wants_recent or (wants_results and tournaments)):
        return []
    if tournaments:
        scope = tournaments
    elif wants_recent:
        latest = latest_tournament(conn)
        scope = [latest] if latest else []
    else:
        scope = list(conn.execute("SELECT * FROM tournaments ORDER BY COALESCE(date_end, date_start) DESC"))
    facts: list[Evidence] = []
    for t in scope:
        where = "" if (wants_results and tournaments) else " AND placement = '1st'"
        rows = conn.execute(
            f"SELECT * FROM placements WHERE tournament_id = ?{where} ORDER BY rowid", (t["id"],)
        ).fetchall()
        firsts = [r for r in rows if r["placement"] == "1st"]
        if len({(r["archetype"] or r["elements"]) for r in firsts}) > 1:
            facts.append(Evidence(
                id=f"{firsts[0]['source_id']}#placement-{slug(firsts[0]['id'])}", source_id=firsts[0]["source_id"],
                kind="fact", status="unknown",
                text=f"Sources disagree about the 1st-place deck at {t['name']}: "
                + "; ".join(f"{r['source_id']} ({STATUS_LABEL.get(r['status'], r['status'])}) says {r['archetype'] or 'another deck'}" for r in firsts)
                + ". Rule: externally verified results outrank author knowledge, and both are shown.",
            ))
        for p in rows:
            facts.append(Evidence(
                id=f"{p['source_id']}#placement-{slug(p['id'])}", source_id=p["source_id"], kind="fact",
                status=p["status"], text=_placement_text(p, t),
            ))
    return facts


def structured_facts(conn: sqlite3.Connection, question: str) -> list[Evidence]:
    q = norm(question)
    tournaments = mentioned_tournaments(conn, q)
    facts = card_count_facts(conn, q, tournaments) + boss_facts(conn, q) + winner_facts(conn, q, tournaments)
    seen, unique = set(), []
    for f in facts:
        key = (f.id, f.text)
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique[:12]

"""Core pipeline checks. They use test-only hash embeddings and scripted
generators, so they prove the import/retrieval/citation logic, not the
semantic quality of the hosted Gemini models (see eval/ for hosted checks)."""

from app.answer import INSUFFICIENT, answer_question, check_citations
from app.chunking import chunk_markdown
from app.db import connect
from app.facts import coverage_line, structured_facts
from app.importer import run_import
from app.retrieval import retrieve

from conftest import CiteFirstGenerator, CountingEmbedder, FixedGenerator, add_source


def test_chunk_ids_are_stable_and_ordered():
    text = "# Title\n\n## One\n\nFirst part.\n\n## Two\n\nSecond part.\n"
    first, second = chunk_markdown("S9", text), chunk_markdown("S9", text)
    assert [c.id for c in first] == ["S9#1", "S9#2"] == [c.id for c in second]
    assert first[0].heading == "Title > One"


def test_long_sections_split_at_sentence_boundaries():
    sentence = "This sentence is about Elestrals decks. "
    chunks = chunk_markdown("S9", "# T\n\n## Long\n\n" + sentence * 60)
    assert len(chunks) > 1
    assert all(c.text.endswith(".") for c in chunks)


def test_repeat_import_creates_no_duplicates_and_embeds_nothing(loaded):
    conn, corpus, embedder = loaded
    before = embedder.document_calls
    counts = [conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("chunks", "chunks_fts", "placements", "deck_cards", "archetype_bosses")]
    report = run_import(conn, corpus, embedder)
    after = [conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("chunks", "chunks_fts", "placements", "deck_cards", "archetype_bosses")]
    assert after == counts
    assert embedder.document_calls == before
    assert report["embedding"]["embedded_now"] == 0
    assert all(s["new"] == 0 and s["changed"] == 0 for s in report["sources"])


def test_changed_text_reembeds_only_that_chunk(loaded):
    conn, corpus, embedder = loaded
    note = corpus / "text" / "S3-note-01.md"
    note.write_text(note.read_text().replace("with the winner playing Fish", "with the winner playing Fish (edited)"))
    before = embedder.document_calls
    report = run_import(conn, corpus, embedder)
    assert embedder.document_calls - before == 1
    stats = next(s for s in report["sources"] if s["id"] == "S3-note-01")
    assert stats["changed"] == 1 and stats["unchanged"] == 2


def test_boss_relationship_returns_every_archetype(loaded):
    conn, _, _ = loaded
    facts = structured_facts(conn, "Which decks run Neandersloth CoKhione?")
    text = " ".join(f.text for f in facts)
    assert "Hades Sloth" in text and "Dio Duggy" in text


def test_card_count_comes_from_the_decklist(loaded):
    conn, _, _ = loaded
    facts = structured_facts(conn, "How many copies of Gorgon's Gaze were in the October 24 Premier winning deck?")
    assert any("Gorgon's Gaze: 3 in the main deck" in f.text and f.status == "externally_verified" for f in facts)


def test_missing_decklist_is_unknown_not_zero(loaded):
    conn, _, _ = loaded
    facts = structured_facts(conn, "How many copies of Lochagon did the Columbus Open winner run?")
    gap = [f for f in facts if f.status == "unknown"]
    assert gap and "unknown (not zero)" in gap[0].text
    assert not any("0 copies" in f.text for f in facts)


def test_latest_event_and_coverage_line(loaded):
    conn, _, _ = loaded
    assert "November 21, 2026 Premier" in coverage_line(conn)
    facts = structured_facts(conn, "Who won the last tournament?")
    assert facts[0].text.startswith("1st at November 21, 2026 Premier") and facts[0].status == "externally_verified"


def test_newer_imported_event_becomes_the_latest(conn, corpus):
    add_source(corpus, {
        "id": "S2-test-newer", "title": "Test newer event", "kind": "results", "original_url": "https://example.test",
        "owner": "test", "permission": "test fixture", "status": "externally_verified", "version": 1,
    }, {
        "source_id": "S2-test-newer",
        "tournaments": [{"id": "T-TEST-2026-12-05", "name": "Test Premier", "aliases": ["test premier"], "date_start": "2026-12-05", "date_end": "2026-12-05"}],
        "placements": [{"id": "t1", "tournament": "T-TEST-2026-12-05", "placement": "1st", "archetype": "Apollo Celestleo"}],
        "decks": [],
    })
    run_import(conn, corpus, CountingEmbedder())
    assert "Test Premier" in coverage_line(conn)
    facts = structured_facts(conn, "Who won the last tournament?")
    assert "Test Premier" in facts[0].text and "Apollo Celestleo" in facts[0].text


def test_conflicting_sources_are_both_reported(conn, corpus):
    add_source(corpus, {
        "id": "S2-test-conflict", "title": "Test conflicting results", "kind": "results", "original_url": "https://example.test",
        "owner": "test", "permission": "test fixture", "status": "externally_verified", "version": 1,
    }, {
        "source_id": "S2-test-conflict", "tournaments": [],
        "placements": [{"id": "c1", "tournament": "T-COLUMBUS-OPEN-2026", "placement": "1st", "archetype": "Hades Sloth"}],
        "decks": [],
    })
    run_import(conn, corpus, CountingEmbedder())
    facts = structured_facts(conn, "Who won the Columbus Open?")
    disagreement = [f for f in facts if "disagree" in f.text]
    assert disagreement and "S3-note-01" in disagreement[0].text and "S2-test-conflict" in disagreement[0].text
    assert {"S3-note-01", "S2-test-conflict"} <= {f.source_id for f in facts}


def test_empty_corpus_refuses_without_calling_the_model():
    conn = connect(":memory:")

    class MustNotRun:
        model = "never"

        def generate(self, system, prompt):
            raise AssertionError("model should not be called")

    result = answer_question(conn, "Who won Worlds?", CountingEmbedder(), MustNotRun())
    assert result.status == "no_sources" and result.answer == INSUFFICIENT


def test_answer_keeps_only_valid_citations(loaded):
    conn, _, embedder = loaded
    result = answer_question(conn, "What archetype won the 2026 World Championship?", embedder, CiteFirstGenerator())
    assert result.status == "answered" and result.citations
    assert all(c in {e.id for e in result.evidence} for c in result.citations)


def test_invented_citations_are_removed_and_uncited_answers_withheld(loaded):
    conn, _, embedder = loaded
    result = answer_question(conn, "Who won Worlds?", embedder, FixedGenerator("Someone won [S9-invented#4]."))
    assert result.status == "withheld" and result.answer == INSUFFICIENT
    assert result.removed_citations == ["S9-invented#4"]


def test_model_refusal_is_passed_through(loaded):
    conn, _, embedder = loaded
    result = answer_question(conn, "What is the 2027 ban list?", embedder, FixedGenerator(INSUFFICIENT))
    assert result.status == "insufficient"


def test_check_citations_handles_multiple_ids():
    text, valid, removed = check_citations("Fish won [A#1; B#2, Z#9].", {"A#1", "B#2"})
    assert valid == ["A#1", "B#2"] and removed == ["Z#9"] and "[A#1; B#2]" in text


def test_retrieval_keyword_baseline_finds_the_note(loaded):
    conn, _, _ = loaded
    result = retrieve(conn, "Columbus Open winner", None)
    assert result.mode == "keyword-only"
    assert any(e.id.startswith("S3-note-01#") for e in result.evidence if e.kind == "chunk")


def test_nov21_premier_and_worlds_decklist(loaded):
    conn, _, _ = loaded
    from app.facts import structured_facts
    win = " ".join(f.text for f in structured_facts(conn, "Who won the November 21 premier?"))
    assert "Hermes Toolbox (Wind 13" in win
    worlds = " ".join(f.text for f in structured_facts(conn, "How many copies of Argo did the Worlds winner run?"))
    assert "3 in the main deck" in worlds and "2026-03-21" in worlds
    nov = " ".join(f.text for f in structured_facts(conn, "How many Gorgon's Gaze in the November 21 winning deck?"))
    assert "3 in the main deck" in nov


def test_rule_number_brackets_are_not_left_as_citations():
    from app.answer import check_citations
    text, valid, removed = check_citations("Hermes Toolbox won [S5#p1]. Player names are not stored [8].", {"S5#p1"})
    assert text == "Hermes Toolbox won [S5#p1]. Player names are not stored." and valid == ["S5#p1"] and removed == ["8"]


def test_timeout_while_reading_gemini_reply_becomes_provider_error(monkeypatch):
    import urllib.request
    from app import providers
    calls = []

    def boom(*args, **kwargs):
        calls.append(1)
        raise TimeoutError("The read operation timed out")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    monkeypatch.setattr(providers.time, "sleep", lambda s: None)
    import pytest
    with pytest.raises(providers.ProviderError):
        providers._post_json("https://example.test", "k", {}, retries=2)
    assert len(calls) == 3  # retried twice before giving up

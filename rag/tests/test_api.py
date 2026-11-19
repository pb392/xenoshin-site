"""Web layer checks (FastAPI TestClient). Skipped where FastAPI isn't installed."""

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings  # noqa: E402
from app.importer import run_import  # noqa: E402
from app.main import create_app  # noqa: E402

from conftest import CiteFirstGenerator, CountingEmbedder  # noqa: E402


@pytest.fixture
def client(conn, corpus):
    embedder = CountingEmbedder()
    run_import(conn, corpus, embedder)
    settings = Settings(db_path=":memory:", corpus_dir=corpus, gemini_api_key="", admin_token="test-admin-token",
                        commit="testcommit", per_ip_per_minute=3)
    return TestClient(create_app(settings, embedder=embedder, generator=CiteFirstGenerator(), conn=conn))


def test_health_reports_counts(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["chunks"] > 0 and body["commit"] == "testcommit"


def test_admin_import_requires_token(client):
    assert client.post("/admin/import").status_code == 401
    assert client.post("/admin/import", headers={"Authorization": "Bearer wrong"}).status_code == 403
    ok = client.post("/admin/import", headers={"Authorization": "Bearer test-admin-token"})
    assert ok.status_code == 200 and ok.json()["embedding"]["embedded_now"] == 0


def test_api_answer_has_citations_and_trace(client):
    body = client.get("/api/ask", params={"q": "What archetype won the 2026 World Championship?"}).json()
    assert body["status"] == "answered" and body["citations"]
    assert body["evidence"] and "coverage" in body


def test_answer_page_links_citations_to_sources(client):
    page = client.get("/", params={"q": "Which decks run Neandersloth CoKhione?"}).text
    assert "/sources/S3-note-02#boss-neandersloth-cokhione" in page
    assert "How this answer was found" in page and "Fan Content" in page


def test_citation_anchor_exists_on_source_page(client):
    page = client.get("/sources/S3-note-02").text
    assert "id='boss-neandersloth-cokhione'" in page
    deck = client.get("/sources/S2-premier-2026-10-24").text
    assert "id='deck-d-premier-2026-10-24-1'" in deck and "Gorgon&#x27;s Gaze" in deck


def test_rate_limit_and_length_limit(client):
    assert client.get("/api/ask", params={"q": "x" * 400}).status_code == 400
    codes = [client.get("/api/ask", params={"q": "Who won Worlds?"}).status_code for _ in range(4)]
    assert codes[:3] == [200, 200, 200] and codes[3] == 429


def test_sources_and_import_record_pages(client):
    assert "S1-worlds-2026" in client.get("/sources").text
    assert "Import record" in client.get("/import-record").text
    assert client.get("/sources/does-not-exist").status_code == 404

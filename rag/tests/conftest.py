import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.answer import INSUFFICIENT  # noqa: E402
from app.db import connect  # noqa: E402
from app.importer import run_import  # noqa: E402
from app.providers import HashEmbedder  # noqa: E402

CORPUS = ROOT / "corpus"


class CountingEmbedder(HashEmbedder):
    """TEST ONLY: hash vectors plus a count of how many texts were embedded."""

    def __init__(self):
        self.document_calls = 0

    def embed_documents(self, items):
        self.document_calls += len(items)
        return super().embed_documents(items)


class CiteFirstGenerator:
    """TEST ONLY: answers by citing the first evidence ID it was given."""

    model = "test-cite-first"

    def generate(self, system, prompt):
        first = prompt.split("[", 1)[1].split("]", 1)[0]
        return f"Test answer based on the evidence [{first}]."


class FixedGenerator:
    """TEST ONLY: always returns the given text."""

    model = "test-fixed"

    def __init__(self, text):
        self.text = text

    def generate(self, system, prompt):
        return self.text


@pytest.fixture
def corpus(tmp_path):
    target = tmp_path / "corpus"
    shutil.copytree(CORPUS, target)
    return target


@pytest.fixture
def conn():
    return connect(":memory:")


@pytest.fixture
def loaded(conn, corpus):
    embedder = CountingEmbedder()
    run_import(conn, corpus, embedder)
    return conn, corpus, embedder


def add_source(corpus: Path, source: dict, structured: dict, text: str | None = None) -> None:
    manifest = json.loads((corpus / "manifest.json").read_text())
    if text is not None:
        (corpus / "text" / f"{source['id']}.md").write_text(text)
        source["file"] = f"text/{source['id']}.md"
    (corpus / "structured" / f"{source['id']}.json").write_text(json.dumps(structured))
    source["structured"] = f"structured/{source['id']}.json"
    manifest["sources"].append(source)
    (corpus / "manifest.json").write_text(json.dumps(manifest))


__all__ = ["INSUFFICIENT", "CiteFirstGenerator", "FixedGenerator", "add_source"]

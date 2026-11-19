"""Settings read from environment variables (twelve-factor style).

Secrets such as GEMINI_API_KEY and ADMIN_TOKEN live only in the server's
.env file. They are never committed and never printed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DEFAULT_CORPUS = APP_DIR.parent / "corpus"


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    db_path: str = field(default_factory=lambda: os.environ.get("RAG_DB_PATH", "/data/rag.sqlite3"))
    corpus_dir: Path = field(default_factory=lambda: Path(os.environ.get("RAG_CORPUS_DIR", str(DEFAULT_CORPUS))))
    gemini_api_key: str = field(default_factory=lambda: os.environ.get("GEMINI_API_KEY", ""))
    gemini_base_url: str = field(
        default_factory=lambda: os.environ.get(
            "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
        )
    )
    embed_model: str = field(default_factory=lambda: os.environ.get("EMBED_MODEL", "gemini-embedding-2"))
    embed_dims: int = field(default_factory=lambda: _int("EMBED_DIMS", 768))
    gen_model: str = field(default_factory=lambda: os.environ.get("GEN_MODEL", "gemini-3.5-flash-lite"))
    admin_token: str = field(default_factory=lambda: os.environ.get("ADMIN_TOKEN", ""))
    commit: str = field(default_factory=lambda: os.environ.get("GIT_COMMIT", "unknown"))
    max_question_chars: int = field(default_factory=lambda: _int("MAX_QUESTION_CHARS", 300))
    per_ip_per_minute: int = field(default_factory=lambda: _int("RATE_PER_IP_PER_MINUTE", 8))
    global_per_day: int = field(default_factory=lambda: _int("RATE_GLOBAL_PER_DAY", 300))
    top_k: int = field(default_factory=lambda: _int("TOP_K", 4))


def load_settings() -> Settings:
    return Settings()

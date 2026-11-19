# xenoshin-site

Peter Balasis's hosted IS373 work, served from one DigitalOcean droplet behind the existing Traefik HTTPS proxy:

| Site | What | Code |
|---|---|---|
| [xenoshin.com](https://xenoshin.com) | Portfolio (static, evidence-first) | [`portfolio/`](portfolio) |
| [rag.xenoshin.com](https://rag.xenoshin.com) | Elestrals Meta Assistant (RAG app) | [`rag/`](rag) |

The research and planning record is in [pb392/is373-individual-record](https://github.com/pb392/is373-individual-record).

## Elestrals Meta Assistant: how it works

```
corpus/manifest.json ──► importer ──► SQLite (/data/rag.sqlite3, persistent volume)
  4 permitted sources         │        ├─ sources        (owner, permission, version, verification status)
  stable IDs + versions       │        ├─ chunks + FTS5  (heading/paragraph chunks, keyword index)
                              │        ├─ embeddings     (Gemini gemini-embedding-2, 768 dims, stored per chunk)
                              │        └─ tournaments · placements · decks · deck_cards · archetype_bosses
question ──► keyword (BM25) + vector (cosine) ──► reciprocal rank fusion ─┐
         └─► SQL lookups (card counts, boss→archetypes, winners, latest event) ┴─► evidence (≤ 16 items)
evidence ──► Gemini (gemini-3.5-flash-lite) with "cite or refuse" rules ──► citation check ──► answer + trace
```

* **Repeatable import:** stable chunk IDs, content hashes; re-import embeds nothing unchanged ([`importer.py`](rag/app/importer.py)). Runs on every container start; the record is at [/import-record](https://rag.xenoshin.com/import-record).
* **Provenance:** every chunk and structured row carries its source ID, version and status (`externally_verified` / `author_knowledge` / `unknown`).
* **Citation check:** citations that don't match retrieved evidence are removed; an answer with no valid citation is withheld ([`answer.py`](rag/app/answer.py)).
* **Missing evidence:** empty corpus refuses without calling the model; a missing decklist is reported as unknown, never zero; answers state the latest *imported* event.
* **Public limits:** 300-character questions, 8 questions per visitor per minute, 300 per day site-wide; import is admin-only (`POST /admin/import` with a bearer token).
* **Not stored:** card text, card art, player names.

## Checks

* `python -m pytest rag/tests`: core tests use **test-only** hash embeddings and scripted generators; they check import/retrieval/citation logic, not Gemini's quality.
* `python scripts/check_site.py`: portfolio links, anchors, one `h1`, `lang`, viewport.
* CI ([`ci.yml`](.github/workflows/ci.yml)) runs both, builds both images and smoke-tests the containers. Only after it passes does CI move the `release` branch.
* [`hosted-check.yml`](.github/workflows/hosted-check.yml) runs the evaluation questions ([`rag/eval/questions.json`](rag/eval/questions.json), expected answers written first) against the live site and commits the actual responses to [`rag/eval/hosted/`](rag/eval/hosted).

## Deployment

The droplet runs `deploy/auto-deploy.sh` every 2 minutes from cron: if `release` moved, it pulls and runs `docker compose up -d --build`. One-time setup: [`deploy/setup.sh`](deploy/setup.sh). Secrets (`GEMINI_API_KEY`, `ADMIN_TOKEN`) live only in the server's `.env` (mode 600), never in Git.

Run locally: `cd rag && pip install -r requirements.txt && RAG_DB_PATH=./local.sqlite3 GEMINI_API_KEY=... python -m app.importer && RAG_DB_PATH=./local.sqlite3 GEMINI_API_KEY=... uvicorn app.main:create_app --factory`.

---
*Unofficial Elestrals fan content, permitted under and not endorsed or approved by Elestrals. Portions of the materials used are the property of Elestrals LLC. All rights reserved by Elestrals LLC. See the [Elestrals Fan Content Policy](https://www.elestrals.com/fan-content-policy).*

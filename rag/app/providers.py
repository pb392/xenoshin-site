"""Embedding and generation providers.

GeminiEmbedder / GeminiGenerator call Google's Gemini REST API with the key
from the environment. HashEmbedder and the fake generators exist ONLY for
automated tests: they never run in the hosted app and prove nothing about
semantic quality.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import math
import re
import time
import urllib.error
import urllib.request
from typing import Protocol, Sequence


class Embedder(Protocol):
    model: str

    def embed_documents(self, items: Sequence[tuple[str, str]]) -> list[list[float]]:
        """items are (heading, text) pairs."""

    def embed_query(self, text: str) -> list[float]: ...


class Generator(Protocol):
    model: str

    def generate(self, system: str, prompt: str) -> str: ...


class ProviderError(RuntimeError):
    pass


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _post_json(url: str, api_key: str, body: dict, timeout: float = 30.0, retries: int = 2) -> dict:
    data = json.dumps(body).encode()
    for attempt in range(retries + 1):
        request = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            # Retry only rate limits and server errors; never echo the key.
            if exc.code in (429, 500, 502, 503) and attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            detail = exc.read().decode(errors="replace")[:300]
            raise ProviderError(f"Gemini API returned HTTP {exc.code}: {detail}") from None
        except urllib.error.URLError as exc:
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            raise ProviderError(f"Could not reach the Gemini API: {exc.reason}") from None
        except (TimeoutError, OSError, http.client.HTTPException, ValueError) as exc:
            # A timeout or dropped connection while reading the reply, or a reply that
            # isn't JSON. Before 2026-11-23 these escaped as HTTP 500 (hosted run 1921Z, Q4).
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            raise ProviderError(f"Gemini API reply failed: {type(exc).__name__}") from None
    raise ProviderError("Gemini API request failed")


class GeminiEmbedder:
    """gemini-embedding-2 takes the task as a text prefix; gemini-embedding-001 uses taskType."""

    def __init__(self, api_key: str, model: str, dims: int, base_url: str):
        if not api_key:
            raise ProviderError("GEMINI_API_KEY is not set")
        self.api_key, self.model, self.dims, self.base_url = api_key, model, dims, base_url.rstrip("/")

    def _request(self, text: str, task: str) -> dict:
        request: dict = {"model": f"models/{self.model}", "outputDimensionality": self.dims}
        if self.model.endswith("-001"):
            request["taskType"] = task
            request["content"] = {"parts": [{"text": text}]}
        else:
            request["content"] = {"parts": [{"text": text}]}
        return request

    def embed_documents(self, items: Sequence[tuple[str, str]]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(items), 50):
            batch = items[start : start + 50]
            requests = []
            for heading, text in batch:
                content = text if self.model.endswith("-001") else f"title: {heading} | text: {text}"
                requests.append(self._request(content, "RETRIEVAL_DOCUMENT"))
            url = f"{self.base_url}/models/{self.model}:batchEmbedContents"
            result = _post_json(url, self.api_key, {"requests": requests})
            vectors.extend(item["values"] for item in result["embeddings"])
        return vectors

    def embed_query(self, text: str) -> list[float]:
        content = text if self.model.endswith("-001") else f"task: search result | query: {text}"
        url = f"{self.base_url}/models/{self.model}:embedContent"
        result = _post_json(url, self.api_key, self._request(content, "RETRIEVAL_QUERY"))
        return result["embedding"]["values"]


class GeminiGenerator:
    def __init__(self, api_key: str, model: str, base_url: str):
        if not api_key:
            raise ProviderError("GEMINI_API_KEY is not set")
        self.api_key, self.model, self.base_url = api_key, model, base_url.rstrip("/")

    def generate(self, system: str, prompt: str) -> str:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1024},
        }
        url = f"{self.base_url}/models/{self.model}:generateContent"
        result = _post_json(url, self.api_key, body, timeout=60.0)
        try:
            parts = result["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError):
            raise ProviderError("Gemini returned no answer text") from None
        return "".join(part.get("text", "") for part in parts if not part.get("thought")).strip()


class HashEmbedder:
    """TEST ONLY: deterministic word-hash vectors. Matches shared words, not meaning."""

    model = "test-hash-64"

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * 64
        for word in re.findall(r"[a-z0-9']+", text.lower()):
            vector[int(hashlib.md5(word.encode()).hexdigest(), 16) % 64] += 1.0
        return vector

    def embed_documents(self, items: Sequence[tuple[str, str]]) -> list[list[float]]:
        return [self._vector(f"{heading} {text}") for heading, text in items]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

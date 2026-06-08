import hashlib
import math
import re

import httpx

from backend.app.core.config import settings


class EmbeddingClient:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if settings.embedding_provider == "openai-compatible":
            return self._openai_compatible_embeddings(texts)
        return [self._local_embedding(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def _openai_compatible_embeddings(self, texts: list[str]) -> list[list[float]]:
        headers = {"Content-Type": "application/json"}
        if settings.embedding_api_key:
            headers["Authorization"] = f"Bearer {settings.embedding_api_key}"
        response = httpx.post(
            f"{settings.embedding_base_url.rstrip('/')}/embeddings",
            headers=headers,
            json={"model": settings.embedding_model, "input": texts},
            timeout=settings.llm_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        return [item["embedding"] for item in sorted(payload["data"], key=lambda row: row["index"])]

    def _local_embedding(self, text: str) -> list[float]:
        vector = [0.0] * settings.embedding_dimension
        tokens = re.findall(r"[A-Za-z0-9_]+", text.lower())
        if not tokens:
            return vector
        for token in tokens:
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % settings.embedding_dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


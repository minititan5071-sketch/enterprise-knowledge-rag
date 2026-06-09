import math
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from typing import Any
from uuid import uuid5, NAMESPACE_URL

from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.rag.chunking import Chunk

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.exceptions import UnexpectedResponse
    from qdrant_client.http.models import Distance, FieldCondition, Filter, MatchValue, PointStruct
    from qdrant_client.http.models import VectorParams
except Exception:  # pragma: no cover - Qdrant is optional in local unit tests
    QdrantClient = None
    UnexpectedResponse = Exception
    Distance = FieldCondition = Filter = MatchValue = PointStruct = VectorParams = None


_MEMORY_POINTS: list[dict[str, Any]] = []
_MEMORY_WARNING_EMITTED = False

logger = get_logger(__name__)


@dataclass
class SearchHit:
    score: float
    payload: dict[str, Any]


class VectorStoreError(RuntimeError):
    pass


class QdrantCompatibilityError(VectorStoreError):
    pass


class VectorStore:
    def __init__(self) -> None:
        global _MEMORY_WARNING_EMITTED
        self.use_memory = settings.vector_store == "memory" or QdrantClient is None
        self.collection = settings.qdrant_collection
        self.client = None
        if self.use_memory and not _MEMORY_WARNING_EMITTED:
            reason = "VECTOR_STORE=memory" if settings.vector_store == "memory" else "qdrant_client_unavailable"
            logger.warning(
                "memory_vector_store_enabled",
                reason=reason,
                persistence="vectors_are_process_local_and_lost_after_backend_restart",
                action="re_ingest_documents_after_restart_or_use_qdrant_for_persistent_vectors",
            )
            _MEMORY_WARNING_EMITTED = True
        if not self.use_memory:
            self.client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)

    def upsert_chunks(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if not chunks:
            return
        if self.use_memory:
            self._memory_upsert(chunks, vectors)
            return
        self._ensure_collection()
        points = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            point_id = str(
                uuid5(
                    NAMESPACE_URL,
                    f"{chunk.metadata['document_id']}:{chunk.metadata['chunk_index']}",
                )
            )
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={**chunk.metadata, "text": chunk.text},
                )
            )
        try:
            self.client.upsert(collection_name=self.collection, points=points)
        except UnexpectedResponse as exc:
            self._raise_qdrant_unexpected_response(
                exc=exc,
                operation="upsert_points",
                endpoint=f"/collections/{self.collection}/points",
            )

    def search(self, workspace_id: str, vector: list[float], top_k: int) -> list[SearchHit]:
        if self.use_memory:
            return self._memory_search(workspace_id, vector, top_k)
        self._ensure_collection()
        query_filter = Filter(
            must=[FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id))]
        )
        try:
            if hasattr(self.client, "query_points"):
                result = self.client.query_points(
                    collection_name=self.collection,
                    query=vector,
                    query_filter=query_filter,
                    limit=top_k,
                    with_payload=True,
                )
                points = result.points
            else:  # pragma: no cover - compatibility with older qdrant-client releases
                points = self.client.search(
                    collection_name=self.collection,
                    query_vector=vector,
                    query_filter=query_filter,
                    limit=top_k,
                    with_payload=True,
                )
        except UnexpectedResponse as exc:
            self._raise_qdrant_unexpected_response(
                exc=exc,
                operation="query_points",
                endpoint=f"/collections/{self.collection}/points/query",
            )
        return [SearchHit(score=float(point.score), payload=point.payload or {}) for point in points]

    def _ensure_collection(self) -> None:
        try:
            if self.client.collection_exists(self.collection):
                return
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=settings.embedding_dimension, distance=Distance.COSINE),
            )
        except UnexpectedResponse as exc:
            self._raise_qdrant_unexpected_response(
                exc=exc,
                operation="ensure_collection",
                endpoint=f"/collections/{self.collection}",
            )

    def _raise_qdrant_unexpected_response(
        self, exc: UnexpectedResponse, operation: str, endpoint: str
    ) -> None:
        status_code = getattr(exc, "status_code", None)
        response_content = getattr(exc, "content", None)
        compatibility_hint = (
            "Qdrant server is likely incompatible with qdrant-client. "
            "For qdrant-client 1.18.x, use qdrant/qdrant:v1.18.0 or another compatible recent server. "
            "A 404 on /points/query usually means an older server such as 1.9.0 is running."
        )
        logger.error(
            "qdrant_unexpected_response",
            operation=operation,
            status_code=status_code,
            endpoint=endpoint,
            collection_name=self.collection,
            qdrant_url=settings.qdrant_url,
            qdrant_client_version=_qdrant_client_version(),
            compatibility_hint=compatibility_hint,
            response_content=_safe_response_content(response_content),
        )
        raise QdrantCompatibilityError(
            "Qdrant request failed. Check qdrant-client and Qdrant server version compatibility. "
            "For qdrant-client 1.18.x, use qdrant/qdrant:v1.18.0. "
            f"Operation={operation}, endpoint={endpoint}, status_code={status_code}."
        ) from exc

    def _memory_upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        for chunk, vector in zip(chunks, vectors, strict=True):
            point_id = str(
                uuid5(
                    NAMESPACE_URL,
                    f"{chunk.metadata['document_id']}:{chunk.metadata['chunk_index']}",
                )
            )
            _MEMORY_POINTS[:] = [point for point in _MEMORY_POINTS if point["id"] != point_id]
            _MEMORY_POINTS.append(
                {
                    "id": point_id,
                    "vector": vector,
                    "payload": {**chunk.metadata, "text": chunk.text},
                }
            )

    def _memory_search(self, workspace_id: str, vector: list[float], top_k: int) -> list[SearchHit]:
        hits: list[SearchHit] = []
        for point in _MEMORY_POINTS:
            payload = point["payload"]
            if payload.get("workspace_id") != workspace_id:
                continue
            hits.append(SearchHit(score=_cosine(vector, point["vector"]), payload=payload))
        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:top_k]


def _cosine(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(a * a for a in left)) or 1.0
    right_norm = math.sqrt(sum(b * b for b in right)) or 1.0
    return numerator / (left_norm * right_norm)


def _qdrant_client_version() -> str:
    try:
        return version("qdrant-client")
    except PackageNotFoundError:  # pragma: no cover - package missing fallback
        return "unknown"


def _safe_response_content(content: Any) -> str | None:
    if content is None:
        return None
    text = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else str(content)
    return text[:500]

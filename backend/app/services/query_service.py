import time

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.auth.rbac import ensure_workspace_role
from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.models.audit_log import AuditLog
from backend.app.models.document import Document
from backend.app.models.user import User
from backend.app.rag.embeddings import EmbeddingClient
from backend.app.rag.llm import LLMClient
from backend.app.rag.vector_store import SearchHit, VectorStore, VectorStoreError
from backend.app.schemas.query import Citation, QueryRequest, QueryResponse

logger = get_logger(__name__)


class QueryService:
    def __init__(self, db: Session):
        self.db = db
        self.embeddings = EmbeddingClient()
        self.vector_store = VectorStore()
        self.llm = LLMClient()

    def answer_question(self, payload: QueryRequest, actor: User) -> QueryResponse:
        ensure_workspace_role(self.db, actor.id, payload.workspace_id, "viewer")
        started_at = time.perf_counter()
        top_k = payload.top_k or settings.rag_top_k

        logger.info(
            "rag_query_started",
            workspace_id=payload.workspace_id,
            question=payload.question,
            top_k=top_k,
            min_score=settings.rag_min_score,
        )
        query_vector = self.embeddings.embed_query(payload.question)
        try:
            hits = self.vector_store.search(payload.workspace_id, query_vector, top_k)
        except VectorStoreError as exc:
            logger.error(
                "rag_vector_store_error",
                workspace_id=payload.workspace_id,
                question=payload.question,
                error=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        logger.info(
            "rag_chunks_retrieved",
            workspace_id=payload.workspace_id,
            question=payload.question,
            retrieved_chunks=len(hits),
            top_k=top_k,
            min_score=settings.rag_min_score,
        )
        _log_retrieved_chunks(payload.workspace_id, hits)

        if not hits:
            self._log_zero_retrieval_diagnostic(payload.workspace_id, payload.question)

        reliable_hits = [hit for hit in hits if hit.score >= settings.rag_min_score]
        if hits and not reliable_hits:
            logger.warning(
                "rag_chunks_below_min_score",
                workspace_id=payload.workspace_id,
                question=payload.question,
                retrieved_chunks=len(hits),
                min_score=settings.rag_min_score,
                top_score=max(hit.score for hit in hits),
            )

        if reliable_hits:
            logger.info(
                "rag_llm_called_with_context",
                workspace_id=payload.workspace_id,
                question=payload.question,
                context_chunks=len(reliable_hits),
            )
        else:
            logger.warning(
                "rag_refused_missing_context",
                workspace_id=payload.workspace_id,
                question=payload.question,
                retrieved_chunks=len(hits),
                min_score=settings.rag_min_score,
                reason="no_retrieved_chunks_passed_min_score",
            )

        llm_result = self.llm.generate_answer(payload.question, reliable_hits)
        citations = [_citation_from_hit(hit) for hit in reliable_hits]
        retrieved_document_ids = list(
            dict.fromkeys(citation.document_id for citation in citations if citation.document_id)
        )
        confidence = _confidence(reliable_hits)

        if not reliable_hits:
            confidence = 0.0

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        audit_log = AuditLog(
            user_id=actor.id,
            workspace_id=payload.workspace_id,
            question=payload.question,
            retrieved_document_ids=retrieved_document_ids,
            model_name=llm_result.model_name,
            latency_ms=latency_ms,
        )
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)

        return QueryResponse(
            answer=llm_result.answer,
            citations=citations,
            source_documents=list(dict.fromkeys(citation.filename for citation in citations)),
            confidence_score=confidence,
            audit_log_id=audit_log.id,
            model_name=llm_result.model_name,
        )

    def retrieval_debug(
        self, workspace_id: str, question: str, actor: User, top_k: int | None = None
    ) -> dict:
        ensure_workspace_role(self.db, actor.id, workspace_id, "admin")
        effective_top_k = top_k or settings.rag_top_k
        query_vector = self.embeddings.embed_query(question)
        try:
            hits = self.vector_store.search(workspace_id, query_vector, effective_top_k)
        except VectorStoreError as exc:
            logger.error(
                "rag_retrieval_debug_vector_store_error",
                workspace_id=workspace_id,
                question=question,
                error=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        logger.info(
            "rag_retrieval_debug",
            workspace_id=workspace_id,
            question=question,
            retrieved_chunks=len(hits),
            top_k=effective_top_k,
            min_score=settings.rag_min_score,
        )
        _log_retrieved_chunks(workspace_id, hits)
        if not hits:
            self._log_zero_retrieval_diagnostic(workspace_id, question)
        return {
            "workspace_id": workspace_id,
            "question": question,
            "top_k": effective_top_k,
            "min_score": settings.rag_min_score,
            "query_embedding": _embedding_info(query_vector),
            "retrieved_chunks": [_debug_hit(hit) for hit in hits],
            "passed_chunks": sum(1 for hit in hits if hit.score >= settings.rag_min_score),
        }

    def _log_zero_retrieval_diagnostic(self, workspace_id: str, question: str) -> None:
        rows = (
            self.db.query(
                Document.status,
                func.count(Document.id),
                func.coalesce(func.sum(Document.chunk_count), 0),
            )
            .filter(Document.workspace_id == workspace_id)
            .group_by(Document.status)
            .all()
        )
        total_documents = sum(row[1] for row in rows)
        total_chunks = sum(int(row[2] or 0) for row in rows)
        if total_documents:
            logger.warning(
                "rag_zero_chunks_with_workspace_documents",
                workspace_id=workspace_id,
                question=question,
                total_documents=total_documents,
                total_indexed_chunks=total_chunks,
                documents_by_status={row[0]: row[1] for row in rows},
                diagnostic=(
                    "documents_exist_but_vector_search_returned_zero_chunks; "
                    "check_ingestion_status_vector_store_persistence_workspace_filter_and_embedding_provider"
                ),
            )
        else:
            logger.warning(
                "rag_zero_chunks_no_workspace_documents",
                workspace_id=workspace_id,
                question=question,
                diagnostic="workspace_has_no_documents_available_for_retrieval",
            )


def _citation_from_hit(hit: SearchHit) -> Citation:
    payload = hit.payload
    return Citation(
        document_id=str(payload.get("document_id")),
        filename=str(payload.get("filename")),
        page_number=payload.get("page_number"),
        chunk_index=int(payload.get("chunk_index", 0)),
        snippet=str(payload.get("text", ""))[:700],
        score=float(hit.score),
    )


def _confidence(hits: list[SearchHit]) -> float:
    if not hits:
        return 0.0
    top_scores = [max(0.0, min(1.0, hit.score)) for hit in hits[:3]]
    return round(sum(top_scores) / len(top_scores), 3)


def _log_retrieved_chunks(workspace_id: str, hits: list[SearchHit]) -> None:
    for rank, hit in enumerate(hits, start=1):
        logger.info(
            "rag_retrieved_chunk",
            workspace_id=workspace_id,
            rank=rank,
            score=hit.score,
            passed_min_score=hit.score >= settings.rag_min_score,
            filename=hit.payload.get("filename"),
            document_id=hit.payload.get("document_id"),
            chunk_index=hit.payload.get("chunk_index"),
            page_number=hit.payload.get("page_number"),
        )


def _debug_hit(hit: SearchHit) -> dict:
    payload = hit.payload
    return {
        "document_id": payload.get("document_id"),
        "filename": payload.get("filename"),
        "page_number": payload.get("page_number"),
        "chunk_index": payload.get("chunk_index"),
        "score": hit.score,
        "passed_min_score": hit.score >= settings.rag_min_score,
        "snippet": str(payload.get("text", ""))[:700],
    }


def _embedding_info(vector: list[float]) -> dict:
    norm = sum(value * value for value in vector) ** 0.5
    non_zero_dimensions = sum(1 for value in vector if value != 0)
    return {
        "provider": settings.embedding_provider,
        "model": settings.embedding_model,
        "dimension": len(vector),
        "non_zero_dimensions": non_zero_dimensions,
        "norm": round(norm, 6),
        "preview": [round(value, 6) for value in vector[:8]],
    }

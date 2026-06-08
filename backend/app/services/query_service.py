import time

from sqlalchemy.orm import Session

from backend.app.auth.rbac import ensure_workspace_role
from backend.app.core.config import settings
from backend.app.models.audit_log import AuditLog
from backend.app.models.user import User
from backend.app.rag.embeddings import EmbeddingClient
from backend.app.rag.llm import LLMClient
from backend.app.rag.vector_store import SearchHit, VectorStore
from backend.app.schemas.query import Citation, QueryRequest, QueryResponse


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

        query_vector = self.embeddings.embed_query(payload.question)
        hits = self.vector_store.search(payload.workspace_id, query_vector, top_k)
        reliable_hits = [hit for hit in hits if hit.score >= settings.rag_min_score]
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


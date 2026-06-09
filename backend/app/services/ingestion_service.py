from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.core.logging import get_logger
from backend.app.db.session import SessionLocal
import backend.app.models  # noqa: F401
from backend.app.models.document import Document
from backend.app.rag.chunking import chunk_pages
from backend.app.rag.embeddings import EmbeddingClient
from backend.app.rag.loaders import extract_text_pages
from backend.app.rag.vector_store import VectorStore

logger = get_logger(__name__)


def ingest_document(document_id: str) -> None:
    db = SessionLocal()
    try:
        _ingest_document(db, document_id)
    finally:
        db.close()


def _ingest_document(db: Session, document_id: str) -> None:
    try:
        document = db.get(Document, document_id)
        if not document:
            logger.warning("document_not_found_for_ingestion", document_id=document_id)
            return

        document.status = "processing"
        document.error_message = None
        db.commit()

        pages = extract_text_pages(Path(document.file_path))
        chunks = chunk_pages(
            pages=pages,
            document_id=document.id,
            workspace_id=document.workspace_id,
            filename=document.filename,
        )
        vectors = EmbeddingClient().embed_texts([chunk.text for chunk in chunks])
        VectorStore().upsert_chunks(chunks, vectors)

        document.status = "completed"
        document.chunk_count = len(chunks)
        document.error_message = None
        db.commit()
        logger.info("document_ingested", document_id=document.id, chunk_count=len(chunks))
    except Exception as exc:
        db.rollback()
        _mark_document_failed(db, document_id, str(exc))
        logger.exception("document_ingestion_failed", document_id=document_id, error=str(exc))
        raise


def _mark_document_failed(db: Session, document_id: str, error_message: str) -> None:
    try:
        documents_table = Document.__table__
        result = db.execute(
            documents_table.update()
            .where(documents_table.c.id == document_id)
            .values(
                status="failed",
                error_message=error_message[:2000],
                updated_at=datetime.utcnow(),
            )
        )
        db.commit()
        if result.rowcount:
            logger.warning(
                "document_marked_failed",
                document_id=document_id,
                error_message=error_message[:500],
            )
    except Exception as mark_failed_exc:
        db.rollback()
        logger.exception(
            "document_failed_status_update_failed",
            document_id=document_id,
            error=str(mark_failed_exc),
        )

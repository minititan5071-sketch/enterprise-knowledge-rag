from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.core.logging import get_logger
from backend.app.db.session import SessionLocal
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
    document = db.get(Document, document_id)
    if not document:
        logger.warning("document_not_found_for_ingestion", document_id=document_id)
        return

    try:
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
        document = db.get(Document, document_id)
        if document:
            document.status = "failed"
            document.error_message = str(exc)[:2000]
            db.commit()
        logger.exception("document_ingestion_failed", document_id=document_id, error=str(exc))
        raise


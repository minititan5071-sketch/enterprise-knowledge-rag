import re
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.auth.rbac import ensure_workspace_role
from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.models.document import Document
from backend.app.models.user import User
from backend.app.rag.loaders import SUPPORTED_EXTENSIONS

logger = get_logger(__name__)


class DocumentService:
    def __init__(self, db: Session):
        self.db = db

    def upload_document(
        self,
        workspace_id: str,
        filename: str,
        content_type: str | None,
        content: bytes,
        actor: User,
    ) -> Document:
        ensure_workspace_role(self.db, actor.id, workspace_id, "manager")
        if len(content) > settings.max_upload_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Uploaded file exceeds maximum size",
            )

        safe_filename = _safe_filename(filename)
        suffix = Path(safe_filename).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
            )

        document_id = str(uuid4())
        workspace_dir = settings.upload_dir / workspace_id
        workspace_dir.mkdir(parents=True, exist_ok=True)
        file_path = workspace_dir / f"{document_id}_{safe_filename}"
        file_path.write_bytes(content)

        document = Document(
            id=document_id,
            workspace_id=workspace_id,
            uploaded_by_id=actor.id,
            filename=safe_filename,
            content_type=content_type,
            file_path=str(file_path),
            status="pending",
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        self._enqueue_ingestion(document.id)
        return document

    def list_documents(self, workspace_id: str, actor: User) -> list[Document]:
        ensure_workspace_role(self.db, actor.id, workspace_id, "viewer")
        return (
            self.db.query(Document)
            .filter(Document.workspace_id == workspace_id)
            .order_by(Document.created_at.desc())
            .all()
        )

    def _enqueue_ingestion(self, document_id: str) -> None:
        from backend.app.services.ingestion_service import ingest_document
        from backend.app.workers.tasks import ingest_document_task

        try:
            ingest_document_task.delay(document_id)
        except Exception as exc:
            logger.warning("failed_to_enqueue_ingestion", document_id=document_id, error=str(exc))
            if settings.environment == "development":
                ingest_document(document_id)
            else:
                document = self.db.get(Document, document_id)
                if document:
                    document.status = "queue_failed"
                    document.error_message = "Document saved, but ingestion queue is unavailable"
                    self.db.commit()
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Ingestion queue is unavailable",
                ) from exc


def _safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._")
    return cleaned or "document.txt"


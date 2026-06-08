from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user
from backend.app.auth.rbac import ensure_workspace_role
from backend.app.db.session import get_db
from backend.app.models.document import Document
from backend.app.models.user import User
from backend.app.services.query_service import QueryService

router = APIRouter(prefix="/debug", tags=["Debug"])


class RetrievalTestRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    top_k: int | None = Field(default=None, ge=1, le=50)


@router.get(
    "/workspaces/{workspace_id}/documents",
    description="Debug workspace document ingestion state. Requires workspace admin.",
)
def debug_workspace_documents(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    ensure_workspace_role(db, current_user.id, workspace_id, "admin")
    documents = (
        db.query(Document)
        .filter(Document.workspace_id == workspace_id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return {
        "workspace_id": workspace_id,
        "documents": [
            {
                "document_id": document.id,
                "filename": document.filename,
                "status": document.status,
                "number_of_chunks": document.chunk_count,
            }
            for document in documents
        ],
    }


@router.post(
    "/workspaces/{workspace_id}/retrieval-test",
    description="Debug raw retrieval results before LLM answer generation. Requires workspace admin.",
)
def debug_retrieval_test(
    workspace_id: str,
    payload: RetrievalTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return QueryService(db).retrieval_debug(
        workspace_id=workspace_id,
        question=payload.question,
        actor=current_user,
        top_k=payload.top_k,
    )

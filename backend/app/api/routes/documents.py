from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.document import DocumentRead, DocumentUploadResponse
from backend.app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    description="Upload a PDF, TXT, MD, or DOCX document for asynchronous ingestion.",
)
async def upload_document(
    workspace_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    content = await file.read()
    document = DocumentService(db).upload_document(
        workspace_id=workspace_id,
        filename=file.filename or "document",
        content_type=file.content_type,
        content=content,
        actor=current_user,
    )
    return DocumentUploadResponse(document=document, ingestion_status=document.status)


@router.get(
    "",
    response_model=list[DocumentRead],
    description="List documents in a workspace. Requires viewer role or higher.",
)
def list_documents(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DocumentRead]:
    return DocumentService(db).list_documents(workspace_id, current_user)


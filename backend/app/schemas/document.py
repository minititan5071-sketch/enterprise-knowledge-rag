from datetime import datetime

from pydantic import BaseModel


class DocumentRead(BaseModel):
    id: str
    workspace_id: str
    uploaded_by_id: str
    filename: str
    content_type: str | None = None
    status: str
    error_message: str | None = None
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    document: DocumentRead
    ingestion_status: str


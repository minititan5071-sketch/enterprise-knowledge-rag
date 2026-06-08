from datetime import datetime

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    id: str
    user_id: str
    workspace_id: str
    question: str
    retrieved_document_ids: list[str]
    model_name: str
    latency_ms: int
    created_at: datetime

    model_config = {"from_attributes": True}


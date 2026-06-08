from datetime import datetime

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    workspace_id: str
    audit_log_id: str | None = None
    question: str | None = None
    answer: str | None = None
    rating: str = Field(pattern="^(helpful|wrong|unsafe)$")
    comment: str | None = Field(default=None, max_length=2000)


class FeedbackRead(BaseModel):
    id: str
    user_id: str
    workspace_id: str
    audit_log_id: str | None = None
    question: str | None = None
    answer: str | None = None
    rating: str
    comment: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


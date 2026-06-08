from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    workspace_id: str
    question: str = Field(min_length=2, max_length=4000)
    top_k: int | None = Field(default=None, ge=1, le=20)


class Citation(BaseModel):
    document_id: str
    filename: str
    page_number: int | None = None
    chunk_index: int
    snippet: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    source_documents: list[str]
    confidence_score: float
    audit_log_id: str
    model_name: str


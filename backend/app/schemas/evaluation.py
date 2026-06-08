from datetime import datetime

from pydantic import BaseModel, Field


class GoldenQACreate(BaseModel):
    workspace_id: str
    question: str = Field(min_length=2)
    expected_answer: str | None = None
    required_facts: list[str] = Field(default_factory=list)
    required_document_ids: list[str] = Field(default_factory=list)


class EvalRunRequest(BaseModel):
    workspace_id: str


class EvaluationRunRead(BaseModel):
    id: str
    workspace_id: str
    triggered_by_id: str | None = None
    status: str
    total_questions: int
    citation_hit_rate: float
    answer_contains_required_facts: float
    retrieval_recall_at_k: float
    refusal_rate_when_context_missing: float
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class EvaluationResultRead(BaseModel):
    id: str
    run_id: str
    golden_qa_id: str
    question: str
    answer: str
    citations: list[dict]
    metrics: dict
    created_at: datetime

    model_config = {"from_attributes": True}


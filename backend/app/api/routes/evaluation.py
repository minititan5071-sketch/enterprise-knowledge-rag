from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.evaluation import (
    EvalRunRequest,
    EvaluationResultRead,
    EvaluationRunRead,
    GoldenQACreate,
)
from backend.app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/eval", tags=["Evaluation"])


@router.post(
    "/golden",
    status_code=status.HTTP_201_CREATED,
    description="Create a golden QA pair for evaluation. Requires workspace admin.",
)
def create_golden_qa(
    payload: GoldenQACreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    qa = EvaluationService(db).create_golden_qa(payload, current_user)
    return {"id": qa.id, "workspace_id": qa.workspace_id}


@router.post(
    "/run",
    response_model=EvaluationRunRead,
    description="Run batch RAG evaluation for a workspace. Requires workspace admin.",
)
def run_evaluation(
    payload: EvalRunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvaluationRunRead:
    return EvaluationService(db).run_evaluation(payload.workspace_id, current_user)


@router.get(
    "/results",
    response_model=list[EvaluationRunRead] | list[EvaluationResultRead],
    description="List evaluation runs for a workspace or detailed results for a run.",
)
def get_evaluation_results(
    workspace_id: str | None = None,
    run_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = EvaluationService(db)
    if run_id:
        return service.list_results(run_id, current_user)
    if workspace_id:
        return service.list_runs(workspace_id, current_user)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Provide either workspace_id or run_id",
    )

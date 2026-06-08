from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.feedback import FeedbackCreate, FeedbackRead
from backend.app.services.feedback_service import FeedbackService

router = APIRouter(tags=["Feedback"])


@router.post(
    "/feedback",
    response_model=FeedbackRead,
    status_code=status.HTTP_201_CREATED,
    description="Record answer feedback as helpful, wrong, or unsafe.",
)
def create_feedback(
    payload: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FeedbackRead:
    return FeedbackService(db).create_feedback(payload, current_user)


@router.get(
    "/feedback",
    response_model=list[FeedbackRead],
    description="List answer feedback for a workspace. Requires workspace admin.",
)
def list_feedback(
    workspace_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FeedbackRead]:
    return FeedbackService(db).list_feedback(workspace_id, current_user, limit)

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.query import QueryRequest, QueryResponse
from backend.app.services.query_service import QueryService

router = APIRouter(tags=["RAG Query"])


@router.post(
    "/query",
    response_model=QueryResponse,
    description="Ask a workspace-scoped question and receive a citation-grounded answer.",
)
def query(
    payload: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QueryResponse:
    return QueryService(db).answer_question(payload, current_user)


from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.audit import AuditLogRead
from backend.app.services.audit_service import AuditService

router = APIRouter(tags=["Audit Logs"])


@router.get(
    "/audit-logs",
    response_model=list[AuditLogRead],
    description="List query audit logs. Requires workspace admin role.",
)
def list_audit_logs(
    workspace_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AuditLogRead]:
    return AuditService(db).list_audit_logs(current_user, workspace_id, limit)


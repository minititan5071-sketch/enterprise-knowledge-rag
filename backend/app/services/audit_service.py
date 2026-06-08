from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.auth.rbac import ensure_workspace_role, list_workspace_ids_for_role
from backend.app.models.audit_log import AuditLog
from backend.app.models.user import User


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def list_audit_logs(
        self, actor: User, workspace_id: str | None = None, limit: int = 100
    ) -> list[AuditLog]:
        query = self.db.query(AuditLog)
        if workspace_id:
            ensure_workspace_role(self.db, actor.id, workspace_id, "admin")
            query = query.filter(AuditLog.workspace_id == workspace_id)
        else:
            admin_workspace_ids = list_workspace_ids_for_role(self.db, actor.id, "admin")
            if not admin_workspace_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access is required to view audit logs",
                )
            query = query.filter(AuditLog.workspace_id.in_(admin_workspace_ids))
        return query.order_by(AuditLog.created_at.desc()).limit(limit).all()


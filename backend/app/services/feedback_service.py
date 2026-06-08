from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.auth.rbac import ensure_workspace_role
from backend.app.models.audit_log import AuditLog
from backend.app.models.feedback import Feedback
from backend.app.models.user import User
from backend.app.schemas.feedback import FeedbackCreate


class FeedbackService:
    def __init__(self, db: Session):
        self.db = db

    def create_feedback(self, payload: FeedbackCreate, actor: User) -> Feedback:
        ensure_workspace_role(self.db, actor.id, payload.workspace_id, "viewer")
        if payload.audit_log_id:
            audit_log = self.db.get(AuditLog, payload.audit_log_id)
            if not audit_log or audit_log.workspace_id != payload.workspace_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Audit log was not found in this workspace",
                )
        feedback = Feedback(
            user_id=actor.id,
            workspace_id=payload.workspace_id,
            audit_log_id=payload.audit_log_id,
            question=payload.question,
            answer=payload.answer,
            rating=payload.rating,
            comment=payload.comment,
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    def list_feedback(self, workspace_id: str, actor: User, limit: int = 100) -> list[Feedback]:
        ensure_workspace_role(self.db, actor.id, workspace_id, "admin")
        return (
            self.db.query(Feedback)
            .filter(Feedback.workspace_id == workspace_id)
            .order_by(Feedback.created_at.desc())
            .limit(limit)
            .all()
        )

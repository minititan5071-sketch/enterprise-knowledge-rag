from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models.workspace import WorkspaceMember

ROLE_ORDER = {"viewer": 1, "manager": 2, "admin": 3}


def role_allows(actual_role: str, minimum_role: str) -> bool:
    return ROLE_ORDER.get(actual_role, 0) >= ROLE_ORDER[minimum_role]


def get_membership(db: Session, user_id: str, workspace_id: str) -> WorkspaceMember | None:
    return (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.user_id == user_id, WorkspaceMember.workspace_id == workspace_id)
        .first()
    )


def ensure_workspace_role(
    db: Session, user_id: str, workspace_id: str, minimum_role: str = "viewer"
) -> WorkspaceMember:
    membership = get_membership(db, user_id, workspace_id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this workspace",
        )
    if not role_allows(membership.role, minimum_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Workspace role '{minimum_role}' or higher is required",
        )
    return membership


def list_workspace_ids_for_role(db: Session, user_id: str, minimum_role: str) -> list[str]:
    memberships = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user_id).all()
    return [m.workspace_id for m in memberships if role_allows(m.role, minimum_role)]


from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.auth.rbac import ensure_workspace_role
from backend.app.models.user import User
from backend.app.models.workspace import Workspace, WorkspaceMember
from backend.app.schemas.workspace import WorkspaceCreate, WorkspaceMemberAdd


class WorkspaceService:
    def __init__(self, db: Session):
        self.db = db

    def create_workspace(self, payload: WorkspaceCreate, creator: User) -> Workspace:
        workspace = Workspace(
            name=payload.name,
            description=payload.description,
            created_by_id=creator.id,
        )
        self.db.add(workspace)
        self.db.flush()
        self.db.add(WorkspaceMember(workspace_id=workspace.id, user_id=creator.id, role="admin"))
        self.db.commit()
        self.db.refresh(workspace)
        return workspace

    def list_workspaces_for_user(self, user: User) -> list[tuple[Workspace, str]]:
        rows = (
            self.db.query(Workspace, WorkspaceMember.role)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .filter(WorkspaceMember.user_id == user.id)
            .order_by(Workspace.created_at.desc())
            .all()
        )
        return [(workspace, role) for workspace, role in rows]

    def add_member(
        self, workspace_id: str, payload: WorkspaceMemberAdd, actor: User
    ) -> WorkspaceMember:
        ensure_workspace_role(self.db, actor.id, workspace_id, "admin")
        user = self.db.query(User).filter(User.email == payload.email.lower()).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User with this email was not found",
            )

        existing = (
            self.db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user.id,
            )
            .first()
        )
        if existing:
            existing.role = payload.role
            member = existing
        else:
            member = WorkspaceMember(
                workspace_id=workspace_id,
                user_id=user.id,
                role=payload.role,
            )
            self.db.add(member)

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Workspace membership already exists",
            ) from exc
        self.db.refresh(member)
        return member


from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.models.workspace import WorkspaceMember
from backend.app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceMemberAdd,
    WorkspaceMemberRead,
    WorkspaceRead,
)
from backend.app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.post(
    "",
    response_model=WorkspaceRead,
    status_code=status.HTTP_201_CREATED,
    description="Create a workspace. The creator is automatically assigned the admin role.",
)
def create_workspace(
    payload: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceRead:
    workspace = WorkspaceService(db).create_workspace(payload, current_user)
    response = WorkspaceRead.model_validate(workspace)
    response.role = "admin"
    return response


@router.get(
    "",
    response_model=list[WorkspaceRead],
    description="List workspaces where the authenticated user is a member.",
)
def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WorkspaceRead]:
    rows = WorkspaceService(db).list_workspaces_for_user(current_user)
    response: list[WorkspaceRead] = []
    for workspace, role in rows:
        item = WorkspaceRead.model_validate(workspace)
        item.role = role
        response.append(item)
    return response


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberRead,
    status_code=status.HTTP_201_CREATED,
    description="Add a user to a workspace or update their role. Requires workspace admin.",
)
def add_member(
    workspace_id: str,
    payload: WorkspaceMemberAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceMemberRead:
    member = WorkspaceService(db).add_member(workspace_id, payload, current_user)
    return _member_response(member)


def _member_response(member: WorkspaceMember) -> WorkspaceMemberRead:
    return WorkspaceMemberRead(
        id=member.id,
        workspace_id=member.workspace_id,
        user_id=member.user_id,
        email=member.user.email if member.user else None,
        role=member.role,
        created_at=member.created_at,
    )


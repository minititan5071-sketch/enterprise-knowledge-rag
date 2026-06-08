from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=1000)


class WorkspaceRead(BaseModel):
    id: str
    name: str
    description: str | None = None
    created_by_id: str
    created_at: datetime
    role: str | None = None

    model_config = {"from_attributes": True}


class WorkspaceMemberAdd(BaseModel):
    email: EmailStr
    role: str = Field(pattern="^(admin|manager|viewer)$")


class WorkspaceMemberRead(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    email: EmailStr | None = None
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


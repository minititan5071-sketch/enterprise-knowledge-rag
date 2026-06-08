from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.auth import LoginRequest, Token, UserCreate, UserRead
from backend.app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    description="Register a user account with a hashed password.",
)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    return AuthService(db).register(payload)


@router.post(
    "/login",
    response_model=Token,
    description="Authenticate with email and password, returning a JWT access token.",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Token:
    return AuthService(db).login(payload.email, payload.password)


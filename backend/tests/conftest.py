import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("VECTOR_STORE", "memory")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-with-enough-length")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("OTEL_ENABLED", "false")
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "false")

from backend.app.api.deps import get_db  # noqa: E402
from backend.app.core.config import settings  # noqa: E402
from backend.app.db.base import Base  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.rag.vector_store import _MEMORY_POINTS  # noqa: E402


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    settings.upload_dir = tmp_path / "uploads"
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.vector_store = "memory"
    settings.embedding_provider = "local"
    settings.llm_provider = "local"
    settings.rag_min_score = 0.0
    settings.rag_top_k = 8
    _MEMORY_POINTS.clear()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        test_client.db_session_factory = TestingSessionLocal
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def register_user(client: TestClient, email: str, password: str = "Password123!") -> dict:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": email.split("@")[0]},
    )
    assert response.status_code == 201, response.text
    return response.json()


def login_user(client: TestClient, email: str, password: str = "Password123!") -> dict:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def auth_headers(client: TestClient, email: str, password: str = "Password123!") -> dict[str, str]:
    token = login_user(client, email, password)["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_workspace(client: TestClient, headers: dict[str, str], name: str = "Knowledge") -> dict:
    response = client.post(
        "/workspaces",
        json={"name": name, "description": "Internal knowledge"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()

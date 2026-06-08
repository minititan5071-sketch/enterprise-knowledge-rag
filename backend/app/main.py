import time

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.router import api_router
from backend.app.core.config import settings
from backend.app.core.logging import configure_logging
from backend.app.db.base import Base
from backend.app.db.session import engine
from backend.app.observability.otel import configure_tracing

configure_logging()
logger = structlog.get_logger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="Multi-tenant enterprise knowledge-base RAG API with JWT auth, RBAC, audit logs, and evaluation.",
    version="0.1.0",
    openapi_tags=[
        {"name": "Authentication", "description": "User registration and JWT login."},
        {"name": "Workspaces", "description": "Workspace and role membership management."},
        {"name": "Documents", "description": "Document upload, metadata, and ingestion lifecycle."},
        {"name": "RAG Query", "description": "Workspace-scoped retrieval and grounded answer generation."},
        {"name": "Feedback", "description": "Answer quality and safety feedback."},
        {"name": "Audit Logs", "description": "Admin-visible query audit trail."},
        {"name": "Evaluation", "description": "Golden QA and batch evaluation workflows."},
        {"name": "Health", "description": "Service health checks."},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    started_at = time.perf_counter()
    response = await call_next(request)
    latency_ms = int((time.perf_counter() - started_at) * 1000)
    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        latency_ms=latency_ms,
    )
    return response


@app.on_event("startup")
def startup() -> None:
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)


app.include_router(api_router, prefix=settings.api_v1_prefix)
configure_tracing(app)


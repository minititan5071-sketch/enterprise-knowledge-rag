from fastapi import APIRouter

from backend.app.api.routes import audit, auth, documents, evaluation, feedback, health, query
from backend.app.api.routes import workspaces

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(workspaces.router)
api_router.include_router(documents.router)
api_router.include_router(query.router)
api_router.include_router(feedback.router)
api_router.include_router(audit.router)
api_router.include_router(evaluation.router)


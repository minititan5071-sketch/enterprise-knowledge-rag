"""Central SQLAlchemy model registry.

Import this module before configuring mappers in processes that do not import
the full FastAPI app, such as Celery workers and CLI jobs.
"""

from backend.app.models.audit_log import AuditLog
from backend.app.models.document import Document
from backend.app.models.evaluation import EvaluationResult, EvaluationRun, GoldenQAPair
from backend.app.models.feedback import Feedback
from backend.app.models.user import User
from backend.app.models.workspace import Workspace, WorkspaceMember

__all__ = [
    "AuditLog",
    "Document",
    "EvaluationResult",
    "EvaluationRun",
    "Feedback",
    "GoldenQAPair",
    "User",
    "Workspace",
    "WorkspaceMember",
]

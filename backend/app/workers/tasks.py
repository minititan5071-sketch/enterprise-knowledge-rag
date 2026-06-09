from backend.app.core.celery_app import celery_app

# Ensure all SQLAlchemy mappers are registered in the Celery worker process
# before task code imports individual models through service modules.
import backend.app.models  # noqa: F401,E402

from backend.app.services.ingestion_service import ingest_document


@celery_app.task(name="documents.ingest", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def ingest_document_task(document_id: str) -> None:
    ingest_document(document_id)

from backend.app.core.celery_app import celery_app
from backend.app.services.ingestion_service import ingest_document


@celery_app.task(name="documents.ingest", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def ingest_document_task(document_id: str) -> None:
    ingest_document(document_id)


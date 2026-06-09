import subprocess
import sys

from sqlalchemy.orm import configure_mappers

from backend.app.models.document import Document
from backend.app.models.workspace import Workspace
from backend.app.services.ingestion_service import _ingest_document
from backend.tests.conftest import auth_headers, create_workspace, register_user


def test_celery_worker_import_registers_all_mappers():
    code = """
import backend.app.workers.tasks
from sqlalchemy.orm import configure_mappers
from backend.app.models.document import Document
from backend.app.models.workspace import Workspace
configure_mappers()
assert Document.workspace.property.mapper.class_ is Workspace
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=".",
        text=True,
        capture_output=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr


def test_document_workspace_relationship_resolves():
    import backend.app.models  # noqa: F401

    configure_mappers()

    assert Document.workspace.property.mapper.class_ is Workspace
    assert Workspace.documents.property.mapper.class_ is Document


def test_ingestion_failure_marks_document_failed(client, monkeypatch):
    register_user(client, "admin@example.com")
    headers = auth_headers(client, "admin@example.com")
    workspace = create_workspace(client, headers)
    monkeypatch.setattr(
        "backend.app.workers.tasks.ingest_document_task.delay",
        lambda document_id: None,
    )
    response = client.post(
        "/documents/upload",
        data={"workspace_id": workspace["id"]},
        files={"file": ("broken.txt", b"this will fail during extraction", "text/plain")},
        headers=headers,
    )
    assert response.status_code == 202, response.text
    document_id = response.json()["document"]["id"]

    def fail_extract_text_pages(path):
        raise RuntimeError("synthetic extraction failure")

    monkeypatch.setattr(
        "backend.app.services.ingestion_service.extract_text_pages",
        fail_extract_text_pages,
    )
    db = client.db_session_factory()
    try:
        try:
            _ingest_document(db, document_id)
        except RuntimeError:
            pass
        document = db.get(Document, document_id)
        assert document.status == "failed"
        assert "synthetic extraction failure" in document.error_message
    finally:
        db.close()

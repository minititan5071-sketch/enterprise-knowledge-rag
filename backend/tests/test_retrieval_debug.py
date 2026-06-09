from backend.app.services.ingestion_service import _ingest_document
from backend.tests.conftest import auth_headers, create_workspace, register_user


def _upload_and_ingest(client, headers: dict[str, str], workspace_id: str) -> dict:
    response = client.post(
        "/documents/upload",
        data={"workspace_id": workspace_id},
        files={
            "file": (
                "kyc_policy.txt",
                (
                    b"KYC onboarding requires identity document, proof of address, "
                    b"business registration certificate, and sanctions screening."
                ),
                "text/plain",
            )
        },
        headers=headers,
    )
    assert response.status_code == 202, response.text
    document = response.json()["document"]
    db = client.db_session_factory()
    try:
        _ingest_document(db, document["id"])
    finally:
        db.close()
    return document


def test_retrieval_test_returns_chunks_after_ingestion(client, monkeypatch):
    register_user(client, "admin@example.com")
    headers = auth_headers(client, "admin@example.com")
    workspace = create_workspace(client, headers)
    monkeypatch.setattr(
        "backend.app.workers.tasks.ingest_document_task.delay",
        lambda document_id: None,
    )
    _upload_and_ingest(client, headers, workspace["id"])

    documents_response = client.get(
        f"/debug/workspaces/{workspace['id']}/documents",
        headers=headers,
    )
    assert documents_response.status_code == 200, documents_response.text
    documents = documents_response.json()["documents"]
    assert documents[0]["status"] == "completed"
    assert documents[0]["number_of_chunks"] > 0

    retrieval_response = client.post(
        f"/debug/workspaces/{workspace['id']}/retrieval-test",
        json={"question": "Which documents are required for KYC onboarding?", "top_k": 8},
        headers=headers,
    )

    assert retrieval_response.status_code == 200, retrieval_response.text
    payload = retrieval_response.json()
    assert payload["query_embedding"]["dimension"] > 0
    assert payload["retrieved_chunks"]
    assert payload["passed_chunks"] > 0
    assert payload["retrieved_chunks"][0]["filename"] == "kyc_policy.txt"
    assert "identity document" in payload["retrieved_chunks"][0]["snippet"]


def test_query_pipeline_passes_retrieved_chunks_to_llm(client, monkeypatch):
    register_user(client, "admin@example.com")
    headers = auth_headers(client, "admin@example.com")
    workspace = create_workspace(client, headers)
    monkeypatch.setattr(
        "backend.app.workers.tasks.ingest_document_task.delay",
        lambda document_id: None,
    )
    _upload_and_ingest(client, headers, workspace["id"])

    captured = {}

    def fake_generate_answer(self, question, contexts):
        from backend.app.rag.llm import LLMResult

        captured["context_count"] = len(contexts)
        captured["filenames"] = [hit.payload.get("filename") for hit in contexts]
        return LLMResult(answer="KYC requires identity documents and proof of address.", model_name="test-llm")

    monkeypatch.setattr("backend.app.rag.llm.LLMClient.generate_answer", fake_generate_answer)

    response = client.post(
        "/query",
        json={"workspace_id": workspace["id"], "question": "What does KYC require?", "top_k": 8},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert captured["context_count"] > 0
    assert captured["filenames"] == ["kyc_policy.txt"]
    assert response.json()["answer"] == "KYC requires identity documents and proof of address."
    assert response.json()["citations"]


def test_query_with_documents_but_zero_retrieved_chunks_refuses(client, monkeypatch):
    register_user(client, "admin@example.com")
    headers = auth_headers(client, "admin@example.com")
    workspace = create_workspace(client, headers)
    monkeypatch.setattr(
        "backend.app.workers.tasks.ingest_document_task.delay",
        lambda document_id: None,
    )
    client.post(
        "/documents/upload",
        data={"workspace_id": workspace["id"]},
        files={"file": ("not_ingested.txt", b"Document metadata exists only.", "text/plain")},
        headers=headers,
    )

    response = client.post(
        "/query",
        json={"workspace_id": workspace["id"], "question": "What does the document say?"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["answer"].startswith("I do not know")
    assert payload["citations"] == []


def test_query_vector_store_error_returns_clean_503(client, monkeypatch):
    from backend.app.rag.vector_store import VectorStoreError

    register_user(client, "admin@example.com")
    headers = auth_headers(client, "admin@example.com")
    workspace = create_workspace(client, headers)

    def fail_search(self, workspace_id, vector, top_k):
        raise VectorStoreError("Qdrant request failed. Check qdrant-client and server versions.")

    monkeypatch.setattr("backend.app.services.query_service.VectorStore.search", fail_search)

    response = client.post(
        "/query",
        json={"workspace_id": workspace["id"], "question": "What does KYC require?"},
        headers=headers,
    )

    assert response.status_code == 503
    assert "Qdrant request failed" in response.json()["detail"]

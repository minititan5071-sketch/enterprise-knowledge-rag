from backend.tests.conftest import auth_headers, create_workspace, register_user


def test_upload_document_and_list_metadata(client, monkeypatch):
    register_user(client, "admin@example.com")
    admin_headers = auth_headers(client, "admin@example.com")
    workspace = create_workspace(client, admin_headers)
    monkeypatch.setattr(
        "backend.app.workers.tasks.ingest_document_task.delay",
        lambda document_id: None,
    )

    response = client.post(
        "/documents/upload",
        data={"workspace_id": workspace["id"]},
        files={"file": ("policy.txt", b"Security policy text", "text/plain")},
        headers=admin_headers,
    )

    assert response.status_code == 202, response.text
    payload = response.json()
    assert payload["document"]["filename"] == "policy.txt"
    assert payload["document"]["status"] == "pending"

    list_response = client.get(
        "/documents",
        params={"workspace_id": workspace["id"]},
        headers=admin_headers,
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_viewer_cannot_upload_documents(client, monkeypatch):
    register_user(client, "admin@example.com")
    register_user(client, "viewer@example.com")
    admin_headers = auth_headers(client, "admin@example.com")
    viewer_headers = auth_headers(client, "viewer@example.com")
    workspace = create_workspace(client, admin_headers)
    client.post(
        f"/workspaces/{workspace['id']}/members",
        json={"email": "viewer@example.com", "role": "viewer"},
        headers=admin_headers,
    )
    monkeypatch.setattr(
        "backend.app.workers.tasks.ingest_document_task.delay",
        lambda document_id: None,
    )

    response = client.post(
        "/documents/upload",
        data={"workspace_id": workspace["id"]},
        files={"file": ("policy.txt", b"Security policy text", "text/plain")},
        headers=viewer_headers,
    )

    assert response.status_code == 403


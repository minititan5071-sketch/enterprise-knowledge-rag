from backend.tests.conftest import auth_headers, create_workspace, register_user


def test_query_requires_workspace_membership(client):
    register_user(client, "alice@example.com")
    register_user(client, "bob@example.com")
    alice_headers = auth_headers(client, "alice@example.com")
    bob_headers = auth_headers(client, "bob@example.com")
    workspace = create_workspace(client, alice_headers, name="Alice workspace")
    create_workspace(client, bob_headers, name="Bob workspace")

    response = client.post(
        "/query",
        json={"workspace_id": workspace["id"], "question": "What is the policy?"},
        headers=bob_headers,
    )

    assert response.status_code == 403


def test_query_without_context_refuses_and_writes_audit_log(client):
    register_user(client, "admin@example.com")
    headers = auth_headers(client, "admin@example.com")
    workspace = create_workspace(client, headers)

    response = client.post(
        "/query",
        json={"workspace_id": workspace["id"], "question": "What is the policy?"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["answer"].startswith("I do not know")
    assert payload["citations"] == []
    assert payload["confidence_score"] == 0.0

    audit_response = client.get(
        "/audit-logs",
        params={"workspace_id": workspace["id"]},
        headers=headers,
    )
    assert audit_response.status_code == 200
    assert audit_response.json()[0]["question"] == "What is the policy?"


from backend.tests.conftest import auth_headers, create_workspace, register_user


def test_workspace_admin_can_add_member_and_viewer_cannot_manage_members(client):
    register_user(client, "admin@example.com")
    register_user(client, "viewer@example.com")
    admin_headers = auth_headers(client, "admin@example.com")
    viewer_headers = auth_headers(client, "viewer@example.com")
    workspace = create_workspace(client, admin_headers)

    add_response = client.post(
        f"/workspaces/{workspace['id']}/members",
        json={"email": "viewer@example.com", "role": "viewer"},
        headers=admin_headers,
    )
    assert add_response.status_code == 201, add_response.text
    assert add_response.json()["role"] == "viewer"

    forbidden_response = client.post(
        f"/workspaces/{workspace['id']}/members",
        json={"email": "viewer@example.com", "role": "manager"},
        headers=viewer_headers,
    )
    assert forbidden_response.status_code == 403


def test_workspace_listing_returns_only_memberships(client):
    register_user(client, "admin@example.com")
    register_user(client, "other@example.com")
    admin_headers = auth_headers(client, "admin@example.com")
    other_headers = auth_headers(client, "other@example.com")
    create_workspace(client, admin_headers, name="Admin workspace")

    response = client.get("/workspaces", headers=other_headers)

    assert response.status_code == 200
    assert response.json() == []


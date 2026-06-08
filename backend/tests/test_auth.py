from backend.tests.conftest import login_user, register_user


def test_register_and_login(client):
    register_user(client, "admin@example.com")

    token = login_user(client, "admin@example.com")

    assert token["token_type"] == "bearer"
    assert token["access_token"]
    assert token["user"]["email"] == "admin@example.com"


def test_duplicate_registration_is_rejected(client):
    register_user(client, "admin@example.com")

    response = client.post(
        "/auth/register",
        json={"email": "admin@example.com", "password": "Password123!"},
    )

    assert response.status_code == 409


def test_invalid_login_is_rejected(client):
    register_user(client, "admin@example.com")

    response = client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


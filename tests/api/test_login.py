from fastapi.testclient import TestClient
from bot import api

client = TestClient(api)


def test_login_success():

    client.post(
        "/signup",
        json={
            "username": "khushi",
            "email": "khushi@gmail.com",
            "password": "password123"
        }
    )

    response = client.post(
        "/login",
        json={
            "email": "khushi@gmail.com",
            "password": "password123"
        }
    )

    assert response.status_code == 200
    assert "accesstoken" in response.json()


def test_login_wrong_password():

    client.post(
        "/signup",
        json={
            "username": "abc",
            "email": "abc@gmail.com",
            "password": "password123"
        }
    )

    response = client.post(
        "/login",
        json={
            "email": "abc@gmail.com",
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401


def test_login_invalid_email():

    response = client.post(
        "/login",
        json={
            "email": "not-an-email",
            "password": "password123"
        }
    )

    assert response.status_code == 422


def test_login_nonexistent_user():

    response = client.post(
        "/login",
        json={
            "email": "nouser@gmail.com",
            "password": "password123"
        }
    )

    assert response.status_code == 401


def test_login_missing_email():

    response = client.post(
        "/login",
        json={
            "password": "password123"
        }
    )

    assert response.status_code == 422


def test_login_missing_password():

    response = client.post(
        "/login",
        json={
            "email": "khushi@gmail.com"
        }
    )

    assert response.status_code == 422
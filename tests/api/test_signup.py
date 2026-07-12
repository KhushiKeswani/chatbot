from fastapi.testclient import TestClient
from bot import api
client = TestClient(api)


def test_signup_success():
    response = client.post(
        "/signup",
        json={
            "username": "khushi",
            "email": "khushi@gmail.com",
            "password": "password123"
        }
    )

    assert response.status_code == 200


def test_signup_duplicate_email():
    client.post(
        "/signup",
        json={
            "username": "khushi",
            "email": "duplicate@gmail.com",
            "password": "password123"
        }
    )

    response = client.post(
        "/signup",
        json={
            "username": "khushi2",
            "email": "duplicate@gmail.com",
            "password": "password123"
        }
    )

    assert response.status_code == 400


def test_signup_invalid_email():
    response = client.post(
        "/signup",
        json={
            "username": "khushi",
            "email": "not-an-email",
            "password": "password123"
        }
    )

    assert response.status_code == 422


def test_signup_missing_email():
    response = client.post(
        "/signup",
        json={
            "username": "khushi",
            "password": "password123"
        }
    )

    assert response.status_code == 422


def test_signup_missing_password():
    response = client.post(
        "/signup",
        json={
            "username": "khushi",
            "email": "khushi@gmail.com"
        }
    )

    assert response.status_code == 422


def test_signup_empty_password():
    response = client.post(
        "/signup",
        json={
            "username": "khushi",
            "email": "khushi@gmail.com",
            "password": ""
        }
    )

    # Change to 400 if your backend validates empty passwords itself.
    assert response.status_code in [400, 422]


def test_signup_short_password():
    response = client.post(
        "/signup",
        json={
            "username": "khushi",
            "email": "khushi@gmail.com",
            "password": "123"
        }
    )

    # Change to 400 if your backend validates password length itself.
    assert response.status_code in [400, 422]
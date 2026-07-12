from fastapi.testclient import TestClient
from bot import api

client = TestClient(api)


def test_complete_chat_flow():
    """
    Signup
        ↓
    Login
        ↓
    Create Conversation
        ↓
    Send Chat
        ↓
    Get History
    """

    # -------------------------
    # Signup
    # -------------------------

    signup = client.post(
        "/signup",
        json={
            "username": "khushi",
            "email": "khushi@gmail.com",
            "password": "password123"
        }
    )

    assert signup.status_code == 200

    # -------------------------
    # Login
    # -------------------------

    login = client.post(
        "/login",
        json={
            "email": "khushi@gmail.com",
            "password": "password123"
        }
    )

    assert login.status_code == 200

    token = login.json()["accesstoken"]

    headers = {
        "Authorization": f"Bearer {token}"
    }

    # -------------------------
    # Create Conversation
    # -------------------------

    convo = client.post(
    "/convo",
    headers=headers
)

    assert convo.status_code == 200

    conversation_id = convo.json()["convo_id"]

    # -------------------------
    # Send Chat
    # -------------------------

    chat = client.post(
        "/chat",
        headers=headers,
        json={
            "convo_id": conversation_id,
            "message": "Hello"
        }
    )

    assert chat.status_code == 200
    assert chat.json()["response"] == "Hello from Fake Gemini"

    # -------------------------
    # History
    # -------------------------

    history = client.get(
        f"/history/{conversation_id}",
        headers=headers
    )

    assert history.status_code == 200

    data = history.json()

    assert isinstance(data, list)
    assert len(data) > 0
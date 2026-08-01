from locust import HttpUser, task, between
from locust.exception import StopUser
import uuid

class ChatUser(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self):
        email = f"user-{uuid.uuid4()}@test.com"
        password = "password123"

        signup = self.client.post("/signup", json={"email": email, "password": password})
        if signup.status_code != 200:
            raise StopUser()

        login = self.client.post("/login", json={"email": email, "password": password})
        token = login.json().get("accesstoken") if login.status_code == 200 else None
        if not token:
            raise StopUser()
        self.headers = {"Authorization": f"Bearer {token}"}

        convo = self.client.post("/convo", headers=self.headers)
        self.convo_id = convo.json().get("convo_id") if convo.status_code == 200 else None
        if not self.convo_id:
            raise StopUser()

    @task
    def send_message(self):
        self.client.post("/chat", headers=self.headers,
            json={"convo_id": self.convo_id, "message": "Hello"})
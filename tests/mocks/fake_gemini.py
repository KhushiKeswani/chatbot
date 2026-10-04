import asyncio
import random
import time
class FakeGemini:

    def chat_with_gemini(self, message: str) -> str:
        time.sleep(random.uniform(2.0, 3.0))  # simulate real Gemini latency
        return "Hello from Fake Gemini"
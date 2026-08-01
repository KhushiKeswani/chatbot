import asyncio
import random

class FakeGemini:

    def chat_with_gemini(self, message: str) -> str:
        import time
        time.sleep(random.uniform(2.0, 3.0))  # simulate real Gemini latency
        return "Hello from Fake Gemini."
from bot import api, get_gemini
from tests.mocks.fake_gemini import FakeGemini

api.dependency_overrides[get_gemini] = lambda: FakeGemini()

# run with: uvicorn load_test_app:api --port 8000
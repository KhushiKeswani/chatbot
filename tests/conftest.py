import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.pool import StaticPool

from bot import api, get_gemini
from database import Base, get_db
from tests.mocks.fake_gemini import FakeGemini

# ------------------------
# Test Database
# ------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///test_chatbot.db"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ------------------------
# Override Dependencies
# ------------------------

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


api.dependency_overrides[get_db] = override_get_db
api.dependency_overrides[get_gemini] = lambda: FakeGemini()

# ------------------------
# Fresh Database Before Every Test
# ------------------------

@pytest_asyncio.fixture(autouse=True)
async def setup_database():

    async with test_engine.begin() as conn:
        # Start every test from scratch
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

# ------------------------
# Cleanup After Entire Test Session
# ------------------------

@pytest_asyncio.fixture(scope="session", autouse=True)
async def cleanup_database():

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()

# ------------------------
# Test Client
# ------------------------

@pytest.fixture
def client():
    return TestClient(api)
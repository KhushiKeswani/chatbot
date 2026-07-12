import os
import pytest
from fastapi.testclient import TestClient
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.pool import StaticPool

from bot import api
from database import Base, get_db
from tests.mocks.fake_gemini import FakeGemini
from bot import get_gemini

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
# Override Dependency
# ------------------------

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


api.dependency_overrides[get_db] = override_get_db
api.dependency_overrides[get_db] = override_get_db
api.dependency_overrides[get_gemini] = lambda: FakeGemini()

# ------------------------
# Setup Database
# ------------------------

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()
    #if os.path.exists("test_chatbot.db"):
        #os.remove("test_chatbot.db")


# ------------------------
# Test Client
# ------------------------

@pytest_asyncio.fixture
def client():
    return TestClient(api)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path

Path("data").mkdir(exist_ok=True)
DATABASE_URL = 'sqlite+aiosqlite:///./data/chatbot.db'

# 1. Initialize DB components
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession,expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as db:
        yield db
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

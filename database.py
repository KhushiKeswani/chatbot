from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import event
from pathlib import Path

Path("data").mkdir(exist_ok=True)
DATABASE_URL = 'sqlite+aiosqlite:///./data/chatbot.db'

# 1. Initialize DB components
engine = create_async_engine(DATABASE_URL)

# Enable WAL mode so SQLite handles concurrent reads/writes better
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()

AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as db:
        yield db

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from services.llm_services import Geminiservice
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, ForeignKey, select
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

DATABASE_URL = 'sqlite+aiosqlite:///./chatbot.db'

# 1. Initialize DB components
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession)
Base = declarative_base()

# --- Database Models ---
class Message(Base):
    __tablename__ = 'message'
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String)
    conversation_id = Column(Integer, ForeignKey('conversation.id'))
    content = Column(String)
    conversation = relationship("Conversation", back_populates="messages")

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    email = Column(String)
    conversations = relationship("Conversation", back_populates="user")

class Conversation(Base):
    __tablename__ = 'conversation'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    messages = relationship("Message", back_populates="conversation")
    user = relationship("User", back_populates="conversations")

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# 2. Use modern Lifespan instead of the deprecated @api.on_event("startup")
@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs ON STARTUP
    print("Initializing Database...")
    await init_db()
    
    # This defers the heavy Gemini initialization until after the loop starts
    print("Initializing Gemini Service...")
    app.state.gemini = Geminiservice() 
    
    yield
    # Any code written here will run ON SHUTDOWN (e.g., closing connections)
    print("Shutting down...")

# Pass the lifespan context manager into FastAPI
api = FastAPI(lifespan=lifespan)

# --- Pydantic Schemas ---
class ChatRequest(BaseModel):
    convo_id: int
    message: str

class UserRequest(BaseModel):
    email: str

class ConvoRequest(BaseModel):
    user_id: int

# --- Dependencies ---
async def get_db():
    async with AsyncSessionLocal() as db:
        yield db

# Helper dependency to easily get the gemini service in endpoints
def get_gemini():
    return api.state.gemini

# --- API Endpoints ---
@api.post('/user')
async def create_user(request: UserRequest, db: AsyncSession = Depends(get_db)):
    user = User(email=request.email)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {'id': user.id, 'email': user.email}

@api.post('/convo')
async def create_convo(request: ConvoRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == request.user_id))
    user = result.scalar()
    if not user:
        raise HTTPException(status_code=404, detail='user not found')
    convo = Conversation(user_id=request.user_id)
    db.add(convo)
    await db.commit()
    await db.refresh(convo)
    return {'convo_id': convo.id}

@api.post('/chat')
async def chat(
    request: ChatRequest, 
    db: AsyncSession = Depends(get_db), 
    gemini: Geminiservice = Depends(get_gemini) # 3. Injected via Dependency
):
    result = await db.execute(select(Conversation).where(Conversation.id == request.convo_id))
    convo = result.scalar()
    if not convo:
        raise HTTPException(status_code=404, detail='convo not found')
    
    user_msg = Message(role='user', conversation_id=request.convo_id, content=request.message)
    db.add(user_msg)
    
    # NOTE: If gemini.chat_with_gemini is a blocking synchronous function, 
    # it will freeze your active server during a request. Consider looking into an async alternative!
    ai_response = gemini.chat_with_gemini(request.message)
    print('response generated')
    
    ai_msg = Message(role='assistant', conversation_id=request.convo_id, content=ai_response)
    db.add(ai_msg)
    await db.commit()
    return {'response': ai_response}

@api.get('/history/{convo_id}')
async def get_history(convo_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Message).where(Message.conversation_id == convo_id))
    messages = result.scalars().all()
    print('messages retrieved')
    return [{'role': message.role, 'content': message.content} for message in messages]


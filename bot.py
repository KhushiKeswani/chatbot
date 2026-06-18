from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from services.llm_services import Geminiservice
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, ForeignKey, select
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from utils.security import create_access_token
from utils.password import secure_pwd,verify_pwd
from utils.auth import get_current_user
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
    hashedpassword = Column(String)
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
class SignupRequest(BaseModel):
    email: str
    password: str
class LoginRequest(BaseModel):
    email: str
    password: str
# --- Dependencies ---
async def get_db():
    async with AsyncSessionLocal() as db:
        yield db

# Helper dependency to easily get the gemini service in endpoints
def get_gemini():
    return api.state.gemini

# --- API Endpoints ---
@api.post('/signup')
async def signup(request: SignupRequest,db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email==request.email))
    user = result.scalar()
    if user:
        raise HTTPException(status_code = 400, detail = 'user already exist')
    else:
        hashedpassword = secure_pwd(request.password)
        user = User(email = request.email,hashedpassword = hashedpassword)
        db.add(user)
        await db.commit()
        await db.refresh(user)
@api.post('/login')
async def login_user(request: LoginRequest,db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email==request.email))
    user = result.scalar()
    if not user:
        raise HTTPException(status_code=401,detail = 'invalid credentials')
    if not verify_pwd(request.password,user.hashedpassword):
        raise HTTPException(
        status_code=401,
        detail="invalid credentials"
    )
    token = create_access_token({'sub':user.id})
    return {'accesstoken': token , 'token_type': 'bearer'}

@api.post('/convo')
async def create_convo(current_user: User = Depends(get_current_user),db: AsyncSession = Depends(get_db)):
    convo = Conversation(user_id=current_user.id)
    db.add(convo)
    await db.commit()
    await db.refresh(convo)
    return {'convo_id': convo.id}

@api.post('/chat')
async def chat(
    request: ChatRequest, 
    db: AsyncSession = Depends(get_db), 
    gemini: Geminiservice = Depends(get_gemini),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Conversation).where(Conversation.id == request.convo_id))
    convo = result.scalar()
    if not convo:
        raise HTTPException(status_code=404, detail='convo not found')
    if convo.user_id != current_user.id:
        raise HTTPException(
        status_code=403,
        detail="not your conversation")
    user_msg = Message(role='user', conversation_id=request.convo_id, content=request.message)
    db.add(user_msg)
    ai_response = gemini.chat_with_gemini(request.message)
    print('response generated')
    
    ai_msg = Message(role='assistant', conversation_id=request.convo_id, content=ai_response)
    db.add(ai_msg)
    await db.commit()
    return {'response': ai_response}

@api.get('/history/{convo_id}')
async def get_history(convo_id: int, current_user: User=Depends(get_current_user),db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == convo_id))
    convo = result.scalar()
    if(convo.user_id!=current_user.id):
        raise HTTPException(status_code=403,detail="cannot access another person's history")
    result = await db.execute(
    select(Message).where(
        Message.conversation_id == convo_id))
    messages= result.scalars().all()
    return [{'role': message.role, 'content': message.content} for message in messages]


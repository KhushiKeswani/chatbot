from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from services.llm_services import Geminiservice
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from utils.security import create_access_token
from utils.password import secure_pwd,verify_pwd
from utils.auth import get_current_user
from repositories.user_repositories import Userrepository
from repositories.conversation_repositories import Conversationrepository
from repositories.message_repositories import Messagerepository
from models import User, Conversation,Message
from database import init_db
from database import get_db,AsyncSessionLocal

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
class SignupRequest(BaseModel):
    email: str
    password: str
class LoginRequest(BaseModel):
    email: str
    password: str


# Helper dependency to easily get the gemini service in endpoints
def get_gemini():
    return api.state.gemini

# --- API Endpoints ---
@api.post('/signup')
async def signup(request: SignupRequest,db: AsyncSession = Depends(get_db)):
    repo = Userrepository(db)
    user = await repo.get_by_email(request.email)
    if user:
        raise HTTPException(status_code = 400, detail = 'user already exist')
    else:
        hashedpassword = secure_pwd(request.password)
        user = await repo.create_user(request.email,hashedpassword)
        return {"id": user.id,"email": user.email}
@api.post('/login')
async def login_user(request: LoginRequest,db: AsyncSession = Depends(get_db)):
    repo = Userrepository(db)
    user = await repo.get_by_email(request.email)
    if not user:
        raise HTTPException(status_code=401,detail = 'invalid credentials')
    if not verify_pwd(request.password,user.hashedpassword):
        raise HTTPException(
        status_code=401,
        detail="invalid credentials"
    )
    token = create_access_token(str(user.id))
    return {'accesstoken': token , 'token_type': 'bearer'}

@api.post('/convo')
async def create_convo(current_user: User = Depends(get_current_user),db: AsyncSession = Depends(get_db)):
    repo = Conversationrepository(db)
    convo = await repo.create_convo(user_id = current_user.id)
    return {'convo_id': convo.id}

@api.post('/chat')
async def chat(
    request: ChatRequest, 
    db: AsyncSession = Depends(get_db), 
    gemini: Geminiservice = Depends(get_gemini),
    current_user: User = Depends(get_current_user)
):
    repo = Conversationrepository(db)
    msgrepo = Messagerepository(db)
    convo = await repo.get_by_id(request.convo_id)
    if not convo:
        raise HTTPException(status_code=404, detail='convo not found')
    if convo.user_id != current_user.id:
        raise HTTPException(
        status_code=403,
        detail="not your conversation")
    await msgrepo.save_message(role='user', conversation_id=request.convo_id, content=request.message)
    ai_response = gemini.chat_with_gemini(request.message)
    print('response generated')
    ai_msg = await msgrepo.save_message(role='assistant', conversation_id=request.convo_id, content=ai_response)
    return {'response': ai_response}

@api.get('/history/{convo_id}')
async def get_history(convo_id: int, current_user: User=Depends(get_current_user),db: AsyncSession = Depends(get_db)):
    repo = Conversationrepository(db)
    msgrepo = Messagerepository(db)
    convo = await repo.get_by_id(convo_id)
    if(convo.user_id!=current_user.id):
        raise HTTPException(status_code=403,detail="cannot access another person's history")
    messages = await msgrepo.get_history(convo_id=convo_id)
    return [{'role': message.role, 'content': message.content} for message in messages]


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
from database import get_db,AsyncSessionLocal,Base
from utils.logger import logger
from pydantic import EmailStr
from services.redis_service import get_cached_response,cache_response
@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs ON STARTUP
    logger.info("initializing database")
    await init_db()
    
    # This defers the heavy Gemini initialization until after the loop starts
    logger.info("Initializing Gemini Service")
    app.state.gemini = Geminiservice() 
    
    yield
    # Any code written here will run ON SHUTDOWN (e.g., closing connections)
    logger.info("Shutting down...")

# Pass the lifespan context manager into FastAPI
api = FastAPI(lifespan=lifespan)

# --- Pydantic Schemas ---
class ChatRequest(BaseModel):
    convo_id: int
    message: str
class SignupRequest(BaseModel):
    email: EmailStr
    password: str
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# Helper dependency to easily get the gemini service in endpoints
def get_gemini():
    return api.state.gemini

# --- API Endpoints ---
@api.post('/signup')
async def signup(request: SignupRequest,db: AsyncSession = Depends(get_db)):
    try:
        repo = Userrepository(db)
        user = await repo.get_by_email(request.email)
        if user:
            raise HTTPException(status_code = 400, detail = 'user already exist')
        else:
            hashedpassword = secure_pwd(request.password)
            user = await repo.create_user(request.email,hashedpassword)
            logger.info(f'new user created : user_id = {user.id}')
            return {"id": user.id,"email": user.email}
    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            f'Signup failed: {e}'
        )

        raise HTTPException(
            status_code=500,
            detail='Internal server error'
        )
@api.post('/login')
async def login_user(request: LoginRequest,db: AsyncSession = Depends(get_db)):
    try:
        repo = Userrepository(db)
        user = await repo.get_by_email(request.email)
        if not user:
            logger.warning(f"Failed login attempt for email={request.email}")
            raise HTTPException(status_code=401,detail = 'invalid credentials')
        if not verify_pwd(request.password,user.hashedpassword):
            raise HTTPException(status_code=401,detail="invalid credentials")
        token = create_access_token(str(user.id))
        return {'accesstoken': token , 'token_type': 'bearer'}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'login failed: {e}')
        raise HTTPException(status_code=500,detail = 'Internal Server Error')

@api.post('/convo')
async def create_convo(current_user: User = Depends(get_current_user),db: AsyncSession = Depends(get_db)):
    try:
        repo = Conversationrepository(db)
        convo = await repo.create_convo(user_id = current_user.id)
        logger.info(f'Created convo convo_id:{convo.id}')
        return {'convo_id': convo.id}
    except Exception as e:
        logger.error(f'conversation creation failed:{e}')
        raise HTTPException(status_code=500,detail = 'Internal Server Error')
@api.post('/chat')
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db), gemini: Geminiservice = Depends(get_gemini),current_user: User = Depends(get_current_user)):
    try:
        repo = Conversationrepository(db)
        msgrepo = Messagerepository(db)
        convo = await repo.get_by_id(request.convo_id)
        if not convo:
            raise HTTPException(status_code=404, detail='convo not found')
        if convo.user_id != current_user.id:
            raise HTTPException(status_code=403,detail="not your conversation")
        await msgrepo.save_message(role='user', conversation_id=request.convo_id, content=request.message)
        logger.info(f'chat request received,convo_id = {convo.id},user_id = {current_user.id}')
        try:
            cached = get_cached_response(request.message.strip().lower())
        except Exception:
            logger.warning("Redis unavailable")
            cached = None
        logger.info("Checking Redis cache...")
        if cached:
            logger.info("CACHE HIT")
            cached_msg = await msgrepo.save_message(role='assistant', conversation_id=request.convo_id, content=cached)
            return {'response': cached}
        logger.info("CACHE MISS")
        ai_response = gemini.chat_with_gemini(request.message)
        cache_response(request.message,ai_response)
        logger.info("Stored response in Redis")
        logger.info(f'llm response generated,convo_id = {convo.id},user_id = {current_user.id}')
        ai_msg = await msgrepo.save_message(role='assistant', conversation_id=request.convo_id, content=ai_response)
        return {'response': ai_response}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'something went wrong: {e}')
        raise HTTPException(status_code=500,detail = 'Internal Server error')

@api.get('/history/{convo_id}')
async def get_history(convo_id: int, current_user: User=Depends(get_current_user),db: AsyncSession = Depends(get_db)):
    try:
        repo = Conversationrepository(db)
        msgrepo = Messagerepository(db)
        convo = await repo.get_by_id(convo_id)
        if(convo.user_id!=current_user.id):
            raise HTTPException(status_code=403,detail="cannot access another person's history")
        messages = await msgrepo.get_history(convo_id=convo_id)
        logger.info(f'history retrieved : convo_id = {convo.id},user_id = {current_user.id}')
        return [{'role': message.role, 'content': message.content} for message in messages]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'history cannot be retrieved, try again later: {e}')
        raise HTTPException(status_code=500,detail = 'Internal Server error')


from services.llm_services import Geminiservice
gemini = Geminiservice()
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import ForeignKey
from sqlalchemy import select
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
DATABASE_URL = 'sqlite+aiosqlite:///./chatbot.db'
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(bind=engine,class_ = AsyncSession)
Base = declarative_base()
class Message(Base):
    __tablename__ = 'message'
    id = Column(Integer,primary_key = True, index = True)
    role = Column(String)
    conversation_id = Column(Integer,ForeignKey('conversation.id'))
    content = Column(String)
    conversation= relationship("Conversation", back_populates="messages")
class User(Base):
    __tablename__ = 'user'
    id = Column(Integer,primary_key = True)
    email = Column(String)
    conversations = relationship("Conversation",back_populates = "user")
class Conversation(Base):
    __tablename__ ='conversation'
    id = Column(Integer,primary_key = True)
    user_id = Column(Integer,ForeignKey('user.id'))
    messages= relationship("Message", back_populates="conversation")
    user = relationship("User",back_populates="conversations")
Base.metadata.create_all(bind=engine)
api = FastAPI()
class ChatRequest(BaseModel):
    convo_id : int
    message: str
class UserRequest(BaseModel):
    email : str
class ConvoRequest(BaseModel):
    user_id : int
async def get_db():
    async with AsyncSessionLocal as db:
        yield db
@api.post('/user')
async def create_user(request: UserRequest,db : AsyncSession = Depends(get_db)):
    user = User(email = request.email)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {'id': user.id,'email': user.email}
@api.post('/convo')
async def create_convo(request: ConvoRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == request.user_id))
    user = result.scalar()
    if not user:
        raise HTTPException(status_code = 404, detail = 'user not found')
    convo = Conversation(user_id = request.user_id)
    db.add(convo)
    await db.commit()
    await db.refresh(convo)
    return {'convo_id': convo.id}
@api.post('/chat')
def chat(request: ChatRequest, db: Session= Depends(get_db)):
    convo = db.query(Conversation).filter(Conversation.id==request.convo_id).first()
    if not convo:
        raise HTTPException(status_code = 404, detail = 'convo not found')
    User_msg = Message(role = 'user',conversation_id = request.convo_id,content = request.message)
    db.add(User_msg)
    ai_response = gemini.chat_with_gemini(request.message)
    print('response generated')
    ai_msg = Message(role = 'assistant',conversation_id = request.convo_id,content = ai_response)
    db.add(ai_msg)
    db.commit()
    return {'response': ai_response}
@api.get('/history/{convo_id}')
def get_history(convo_id: int,db:Session = Depends(get_db)):
    messages = db.query(Message).filter(Message.conversation_id == convo_id).all()
    print('messages retrieved')
    result = []
    for message in messages:
        result.append({'role':message.role, 'content' :message.content})
    return result

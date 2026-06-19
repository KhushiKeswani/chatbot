from sqlalchemy import Column, Integer, String, ForeignKey, select
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()
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
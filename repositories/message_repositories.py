from sqlalchemy import select
from models import Message

class Messagerepository:
    def __init__(self,db):
        self.db = db

    async def get_history(self,convo_id):
        result = await self.db.execute(
        select(Message).where(
        Message.conversation_id == convo_id))
        messages= result.scalars().all()
        return messages
    async def save_message(self,role,content,conversation_id):
        msg = Message(role=role,content=content,conversation_id=conversation_id)
        self.db.add(msg)
        await self.db.commit()
        return msg
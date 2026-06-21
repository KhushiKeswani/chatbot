from sqlalchemy import select
from models import Conversation

class Conversationrepository:
    def __init__(self,db):
        self.db = db
    async def get_by_id(self,convo_id):
        result = await self.db.execute(select(Conversation).where(Conversation.id == convo_id))
        convo = result.scalar()
        return convo
    async def create_convo(self,user_id):
        convo = Conversation(user_id = user_id)
        self.db.add(convo)
        await self.db.commit()
        await self.db.refresh(convo)
        return convo
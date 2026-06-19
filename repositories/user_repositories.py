from sqlalchemy import select
from models import User

class Userrepository:
    def __init__(self,db):
        self.db = db

    async def get_by_email(self,email):
        result = await self.db.execute(select(User).where(User.email==email))
        user = result.scalar()
        return user
    
    async def create_user(self,email,hashedpassword):
        user = User(email = email, hashedpassword = hashedpassword)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
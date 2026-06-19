from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from utils.security import JWTBearer, decodeJWT
from models import User
from database import get_db

async def get_current_user(
    token: str = Depends(JWTBearer()),
    db: AsyncSession = Depends(get_db)
):
    payload = decodeJWT(token)

    user_id = payload["sub"]

    result = await db.execute(
        select(User).where(User.id == int(user_id))
    )

    user = result.scalar()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="user not found"
        )

    return user
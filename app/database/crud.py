from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.models import User
from sqlalchemy.exc import IntegrityError

async def create_user(session: AsyncSession, user_id: int, username: str) -> User:
    new_user = User(user_id=user_id, username=username)
    session.add(new_user)
    try:
        await session.commit()
        return new_user
    except IntegrityError:
        await session.rollback()
        result = await session.execute(select(User).filter(User.user_id == user_id))
        return result.scalars().first()

async def get_user_by_id(session: AsyncSession, user_id: int) -> User:
    result = await session.execute(select(User).filter(User.user_id == user_id))
    return result.scalars().first()


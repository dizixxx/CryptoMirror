from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.models import User
from sqlalchemy.exc import IntegrityError
from app.database.models import Asset

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

async def upsert_asset_price(session: AsyncSession, symbol: str, name: str, price: float) -> Asset:
    result = await session.execute(select(Asset).where(Asset.symbol == symbol))
    asset = result.scalars().first()

    if asset:
        asset.prev_price = price
        asset.prev_time = datetime.utcnow()
    else:
        asset = Asset(
            symbol=symbol,
            name=name,
            prev_price=price,
            prev_time=datetime.utcnow()
        )
        session.add(asset)

    try:
        await session.commit()
        return asset
    except IntegrityError:
        await session.rollback()
        raise

from app.database.models import Asset
from sqlalchemy.future import select

async def get_asset_price(session, symbol: str):
    result = await session.execute(select(Asset).filter_by(symbol=symbol))
    asset = result.scalars().first()
    return asset


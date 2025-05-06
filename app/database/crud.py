from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.database.models import User, Balance, Trade
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

    await session.commit()
    return asset

async def get_asset_price(session, symbol: str):
    result = await session.execute(select(Asset).filter_by(symbol=symbol))
    asset = result.scalars().first()
    return asset


async def get_user_balance(session: AsyncSession, user_id: int):
    stmt = (
        select(Balance)
        .filter(Balance.user_id == user_id)
        .options(selectinload(Balance.asset))
    )
    result = await session.execute(stmt)
    balances = result.scalars().all()

    balance_info = []
    for balance in balances:
        asset_name = balance.asset.name if balance.asset else balance.symbol

        balance_info.append({
            "symbol": balance.symbol,
            "asset_name": asset_name,
            "total_amount": balance.total_amount
        })

    return balance_info

async def update_balance(session: AsyncSession, user_id: int, symbol: str, amount: float):

    asset = await session.get(Asset, symbol)
    if not asset:
        asset = Asset(
            symbol=symbol,
            name=symbol,
            prev_price=0.0,
            prev_time=datetime.utcnow()
        )
        session.add(asset)
        await session.commit()

    result = await session.execute(
        select(Balance).filter(Balance.user_id == user_id, Balance.symbol == symbol)
    )

    balance = result.scalars().first()
    if balance:
        balance.total_amount += amount
    else:
        balance = Balance(
            user_id=user_id,
            symbol=symbol,
            total_amount=amount
        )
        session.add(balance)
    await session.commit()
    return balance

async def get_asset(session: AsyncSession, symbol: str) -> Asset:
    result = await session.execute(select(Asset).filter(Asset.symbol == symbol))
    return result.scalars().first()


async def get_user_trades_history(session: AsyncSession, user_id: int, limit: int = 15):
    result = await session.execute(
        select(Trade)
        .where(Trade.user_id == user_id)
        .order_by(Trade.timestamp.desc())
        .limit(limit)
    )
    return result.scalars().all()
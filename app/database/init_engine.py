from sqlalchemy import select
from app.database.models import Base, Asset
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession

DATABASE_URL = "sqlite+aiosqlite:///./trading.db"

engine = create_async_engine(DATABASE_URL, echo=True, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_async_session():
    session = AsyncSessionLocal()
    await session.begin()
    return session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Asset))
        existing_assets = result.scalars().all()
        if not existing_assets:
            initial_assets = [
                Asset(symbol="BTCUSDT", name="Bitcoin"),
                Asset(symbol="ETHUSDT", name="Ethereum"),
                Asset(symbol="SOLUSDT", name="Solana"),
                Asset(symbol="TONUSDT", name="Toncoin"),
                Asset(symbol="BNBUSDT", name="BNB")
            ]
            session.add_all(initial_assets)
            await session.commit()

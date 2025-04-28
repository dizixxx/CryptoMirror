from datetime import datetime
from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.types import Integer, String, Float, DateTime

class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    trades: Mapped[list["Trade"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    balances: Mapped[list["Balance"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Asset(Base):
    __tablename__ = "assets"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)

    prev_price: Mapped[float] = mapped_column(Float)
    prev_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    trades: Mapped[list["Trade"]] = relationship(back_populates="asset", cascade="all, delete-orphan")
    balances: Mapped[list["Balance"]] = relationship(back_populates="asset", cascade="all, delete-orphan")


class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = (
        Index("ix_trades_user_symbol", "user_id", "symbol"),
    )

    trade_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    symbol: Mapped[str] = mapped_column(ForeignKey("assets.symbol"))
    amount: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="trades")
    asset: Mapped["Asset"] = relationship(back_populates="trades")


class Balance(Base):
    __tablename__ = "balances"
    __table_args__ = (
        Index("ix_balances_user", "user_id", "symbol"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    symbol: Mapped[str] = mapped_column(ForeignKey("assets.symbol"), primary_key=True)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)

    user: Mapped["User"] = relationship(back_populates="balances")
    asset: Mapped["Asset"] = relationship(back_populates="balances")

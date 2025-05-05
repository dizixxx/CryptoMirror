from typing import Any

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime
from sqlalchemy import select

from app.database.init_engine import AsyncSessionLocal
from app.database.models import Trade, Asset

router = Router()

user_trades_cache = {}


def format_amount(amount: float) -> str:
    if amount.is_integer():
        return f"{int(amount)}"
    return f"{amount:.8f}".rstrip('0').rstrip('.') if '.' in f"{amount:.8f}" else f"{amount}"


def format_price(price: float) -> str:
    if price >= 1000:
        return f"{price:,.2f}"
    elif price >= 1:
        return f"{price:.2f}".rstrip('0').rstrip('.') if '.' in f"{price:.2f}" else f"{price}"
    else:
        return f"{price:.8f}".rstrip('0').rstrip('.') if '.' in f"{price:.8f}" else f"{price}"


def format_percentage_change(percent: float) -> str:
    if percent > 0:
        return f"🟢 +{abs(percent):.2f}%"
    elif percent < 0:
        return f"🔴 -{abs(percent):.2f}%"
    return f"⚪️ {percent:.2f}%"


def format_trade_message(trade: Trade, current_price: float) -> str:
    price_diff = current_price - trade.price
    percent_diff = (price_diff / trade.price) * 100 if trade.price != 0 else 0

    action = "🟢 Куплено" if trade.amount > 0 else "🔴 Продано"
    amount = abs(trade.amount)

    return (
        f"{trade.symbol}: {format_amount(amount)} {action} по {format_price(trade.price)} USDT\n"
        f"   📊 Текущая цена: {format_price(current_price)} USDT "
        f"({format_price(price_diff)}, {format_percentage_change(percent_diff)})"
    )


async def get_user_trades_history(session: AsyncSessionLocal, user_id: int, limit: int = 15) -> list[Trade]:
    result = await session.execute(
        select(Trade)
        .where(Trade.user_id == user_id)
        .order_by(Trade.timestamp.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def get_trades_data(session: AsyncSessionLocal, user_id: int) -> tuple[list[Trade], dict[str, float]]:
    if user_id in user_trades_cache:
        cached_data = user_trades_cache[user_id]
        if (datetime.now() - cached_data['timestamp']).seconds < 60:
            return cached_data['trades'], cached_data['current_prices']

    trades = await get_user_trades_history(session, user_id, limit=15)

    symbols = {trade.symbol for trade in trades}
    current_prices = {}
    for symbol in symbols:
        asset = await session.get(Asset, symbol)
        current_prices[symbol] = asset.prev_price if asset else 0

    user_trades_cache[user_id] = {
        'trades': trades,
        'current_prices': current_prices,
        'timestamp': datetime.now()
    }

    return trades, current_prices


async def build_response_and_keyboard(user_id: int, page: int = 0, original_message_id: int = None) -> tuple[
                                                                                                           str, None] | \
                                                                                                       tuple[
                                                                                                           str | Any, InlineKeyboardBuilder]:
    async with AsyncSessionLocal() as session:
        try:
            trades, current_prices = await get_trades_data(session, user_id)
        except ValueError:
            trades = []
            current_prices = {}

        if not trades:
            return "📭 У вас еще нет операций", None

        pages = [trades[i:i + 5] for i in range(0, len(trades), 5)]
        if page >= len(pages):
            page = len(pages) - 1

        current_page = pages[page]

        response = (
            f"📊 <b>История операций</b> (страница {page + 1}/{len(pages)})\n"
            f"--------------------------------\n"
        )

        for trade in current_page:
            current_price = current_prices.get(trade.symbol, 0)
            response += f"\n{format_trade_message(trade, current_price)}\n"
            response += "--------------------------------"

        builder = InlineKeyboardBuilder()

        if page > 0:
            builder.add(InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"balance_page_{user_id}_{page - 1}_{original_message_id}"
            ))

        if page < len(pages) - 1:
            builder.add(InlineKeyboardButton(
                text="Вперед ➡️",
                callback_data=f"balance_page_{user_id}_{page + 1}_{original_message_id}"
            ))

        builder.adjust(2)

        builder.row(InlineKeyboardButton(
            text="❌ Закрыть",
            callback_data=f"balance_close_{user_id}_{original_message_id}"
        ))

        return response, builder


@router.message(Command('balance'))
async def cmd_balance(message: Message):
    user_id = message.from_user.id
    response, builder = await build_response_and_keyboard(
        user_id=user_id,
        original_message_id=message.message_id
    )

    if builder:
        await message.answer(response, reply_markup=builder.as_markup())
    else:
        await message.answer(response)


@router.callback_query(F.data.startswith("balance_page_"))
async def handle_balance_page(callback: CallbackQuery):
    try:
        _, _, user_id_str, page_str, original_msg_id = callback.data.split('_')
        user_id = int(user_id_str)
        page = int(page_str)
        original_message_id = int(original_msg_id)
    except ValueError:
        await callback.answer("Ошибка обработки запроса")
        return

    if callback.from_user.id != user_id:
        await callback.answer("Это не ваша история операций!")
        return

    response, builder = await build_response_and_keyboard(
        user_id=user_id,
        page=page,
        original_message_id=original_message_id
    )

    if builder:
        await callback.message.edit_text(response, reply_markup=builder.as_markup())
    else:
        await callback.message.edit_text(response)

    await callback.answer()


@router.callback_query(F.data.startswith("balance_close_"))
async def handle_balance_close(callback: CallbackQuery):
    try:
        _, _, user_id_str, original_msg_id = callback.data.split('_')
        user_id = int(user_id_str)
        original_message_id = int(original_msg_id)
    except ValueError:
        await callback.answer("Ошибка обработки запроса")
        return

    if callback.from_user.id == user_id:
        try:
            # Удаляем сообщение с историей операций
            await callback.message.delete()
            # Удаляем исходное сообщение с командой /balance
            await callback.bot.delete_message(
                chat_id=callback.message.chat.id,
                message_id=original_message_id
            )
        except Exception as e:
            print(f"Ошибка при удалении сообщений: {e}")

    await callback.answer()
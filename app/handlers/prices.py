from datetime import datetime

from aiogram import Router, F, types
from aiogram.types import Message, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.__init__ import asset
from app.services.binance import get_prices
from app.database.init_engine import AsyncSessionLocal
from app.database.crud import upsert_asset_price, get_asset_price

router = Router()


@router.message(Command('prices'))
async def cmd_prices(message: Message):
    response = 'Цены Binance на текущий момент:\n'
    async with AsyncSessionLocal() as session:
        for pair in asset:
            data = await get_prices(pair)
            price = round(float(data["price"]), 2)

            db_data = await get_asset_price(session, symbol=data["symbol"])

            if db_data:
                prev_price = db_data.prev_price
                if prev_price != 0:
                    percent_change = round(((price - prev_price) / prev_price) * 100, 2)
                    change_indicator = "📈" if percent_change >= 0 else "📉"
                    change_indicator1 = "🟢" if percent_change >= 0 else "🔴"
                    response += f"{pair}: {price}    |    ({change_indicator} {percent_change}% {change_indicator1})\n"
                else:
                    response += f"{pair}: {price}    |   (Нет данных для сравнения)\n"
            else:
                response += f"{pair}: {price}   |    (Нет данных для сравнения)\n"

            await upsert_asset_price(
                session=session,
                symbol=data["symbol"],
                name=asset[data["symbol"]],
                price=price
            )
    response += f'\n*Относительно предыдущего запроса, сделанного в {datetime.strptime(str(db_data.prev_time), "%Y-%m-%d %H:%M:%S.%f").strftime("%H:%M %d-%m")} UTC.'

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="❌ Закрыть",
        callback_data=f"delete_messages_{message.from_user.id}_{message.message_id}"
    ))

    sent_message = await message.answer(
        text=response,
        reply_markup=builder.as_markup()
    )

    builder_with_both = InlineKeyboardBuilder()
    builder_with_both.add(InlineKeyboardButton(
        text="❌ Закрыть",
        callback_data=f"delete_messages_{message.from_user.id}_{message.message_id}_{sent_message.message_id}"
    ))

    await sent_message.edit_reply_markup(reply_markup=builder_with_both.as_markup())


@router.callback_query(F.data.startswith("delete_messages_"))
async def delete_messages(callback_query: types.CallbackQuery):
    parts = callback_query.data.split("_")
    user_id = int(parts[2])
    message1_id = int(parts[3])
    message2_id = int(parts[4]) if len(parts) > 4 else None

    if callback_query.from_user.id == user_id:
        try:
            await callback_query.bot.delete_message(
                chat_id=callback_query.message.chat.id,
                message_id=message1_id
            )
            if message2_id:
                await callback_query.bot.delete_message(
                    chat_id=callback_query.message.chat.id,
                    message_id=message2_id
                )
        except Exception as e:
            print(f"Ошибка при удалении сообщений: {e}")

    await callback_query.answer()
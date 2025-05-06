import asyncio
from aiogram import Router, F, types, Bot
from aiogram.types import Message, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.__init__ import asset
from app.services.binance import get_prices
from app.services.prices_updater import PriceUpdater

router = Router()
price_updater = PriceUpdater()


async def generate_price_message(pairs: list, last_prices: dict, new_prices: dict) -> str:
    response = "🔹 Цены Binance в реальном времени:\n\n"

    for pair in pairs:
        current_price = round(new_prices.get(pair, 0), 4)
        prev_price = last_prices.get(pair)

        if prev_price is not None and prev_price != 0:
            percent_change = round(((current_price - prev_price) / prev_price) * 100, 2)
            change_indicator = "📈" if percent_change >= 0 else "📉"
            change_color = "🟢" if percent_change >= 0 else "🔴"
            response += f"{pair}: {current_price} {change_indicator} {change_color} {abs(percent_change)}%\n"
        else:
            response += f"{pair}: {current_price} (новый мониторинг)\n"

    return response


async def update_prices_task(bot: Bot, chat_id: int, message_id: int, pairs: list, user_id: int, command_message_id: int):
    while price_updater.is_running(chat_id, message_id):
        try:
            new_prices = await get_prices(pairs)
            last_prices = price_updater.get_last_prices(chat_id, message_id) or {}

            message_text = await generate_price_message(pairs, last_prices, new_prices)

            builder = InlineKeyboardBuilder()
            builder.add(InlineKeyboardButton(
                text="❌ Закрыть",
                callback_data=f"close_prices_{user_id}_{command_message_id}_{message_id}"
            ))

            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=message_text,
                reply_markup=builder.as_markup()
            )

            price_updater.update_last_prices(chat_id, message_id, new_prices)

        except Exception as e:
            print(f"Ошибка при обновлении цен: {e}")
            await asyncio.sleep(2)
            continue

        await asyncio.sleep(1)


@router.message(Command('prices'))
async def cmd_prices(message: Message, bot: Bot):
    pairs = list(asset.keys())

    try:
        initial_prices = await get_prices(pairs)
    except Exception as e:
        await message.answer(f"Ошибка при получении цен: {e}")
        return

    message_text = await generate_price_message(pairs, {}, initial_prices)

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="❌ Закрыть",
        callback_data=f"close_prices_{message.from_user.id}_{message.message_id}_PLACEHOLDER"
    ))

    sent_message = await message.answer(
        text=message_text,
        reply_markup=builder.as_markup()
    )

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="❌ Закрыть",
        callback_data=f"close_prices_{message.from_user.id}_{message.message_id}_{sent_message.message_id}"
    ))
    await bot.edit_message_reply_markup(
        chat_id=sent_message.chat.id,
        message_id=sent_message.message_id,
        reply_markup=builder.as_markup()
    )

    price_updater.add_update_task(
        chat_id=message.chat.id,
        message_id=sent_message.message_id,
        pairs=pairs
    )

    asyncio.create_task(update_prices_task(
        bot=bot,
        chat_id=message.chat.id,
        message_id=sent_message.message_id,
        pairs=pairs,
        user_id=message.from_user.id,
        command_message_id=message.message_id
    ))


@router.callback_query(F.data.startswith("close_prices_"))
async def close_prices(callback_query: types.CallbackQuery, bot: Bot):
    parts = callback_query.data.split("_")
    user_id = int(parts[2])
    command_message_id = int(parts[3])
    prices_message_id = int(parts[4])

    if callback_query.from_user.id != user_id:
        await callback_query.answer("Вы не можете закрыть этот мониторинг")
        return

    chat_id = callback_query.message.chat.id

    price_updater.stop_update_task(chat_id, prices_message_id)
    price_updater.remove_task(chat_id, prices_message_id)

    try:
        await bot.delete_message(chat_id=chat_id, message_id=command_message_id)  # Команда /prices
        await bot.delete_message(chat_id=chat_id, message_id=prices_message_id)   # Сообщение с ценами
    except Exception as e:
        print(f"Ошибка при удалении сообщений: {e}")
        await callback_query.answer("Ошибка при закрытии", show_alert=True)
        return

    await callback_query.answer()

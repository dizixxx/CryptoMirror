from aiogram import Router, types, F
from aiogram.types import Message, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

@router.message(Command('help'))
async def cmd_help(message: Message):
    response = (
        "🤖 <b>Помощь по командам</b>\n\n"
        "Все просто! Вот что я умею:\n\n"
        "🚀 <b>Основные команды:</b>\n"
        "/start - Запустить бота и получить стартовый баланс\n"
        "/help - Это окно с подсказками\n"
        "/prices - Актуальные курсы топ-5 пар\n\n"
        "💼 <b>Торговля:</b>\n"
        "/buy - Купить криптовалюту (выбрать пару → сумму → подтвердить)\n"
        "/sell - Продать актив (аналогично покупке)\n\n"
        "📊 <b>Аналитика:</b>\n"
        "/balance - Твой портфель с доходностью активов\n\n"
        "💡 <b>Как торговать?</b>\n"
        "1. Проверь цены через /prices\n"
        "2. Выбери /buy или /sell\n"
        "3. Следуй инструкциям\n"
        "4. Следи за балансом в /balance\n\n"
        "Пример: <code>BTC: 0.00146 → $68800 (+0.45%)</code>\n\n"
        "🚨 Все сделки сохраняются автоматически!"
    )

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
from aiogram import Router, F, types
from aiogram.types import Message, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.init_engine import AsyncSessionLocal
from app.database.crud import get_user_balance

router = Router()

def format_float_number(number_str: str) -> str:
    if '.' not in number_str:
        return f"{number_str}.0"
    integer_part, decimal_part = number_str.split('.', 1)

    trimmed_decimal = decimal_part.rstrip('0')
    zeros_removed = len(trimmed_decimal) < len(decimal_part)
    if not trimmed_decimal:
        return f"{integer_part}.0"
    elif zeros_removed:
        return f"{integer_part}.{trimmed_decimal}0"
    else:
        return f"{integer_part}.{trimmed_decimal}"

@router.message(Command('portfolio'))
async def cmd_prices(message: Message):
    user_id = message.from_user.id
    async with AsyncSessionLocal() as session:
        balance_info = await get_user_balance(session, user_id)

        if not balance_info:
            await message.answer("Баланс не найден!")
            return

        response = "💼 Ваш портфель:\n"
        for iter_asset in balance_info:
            if iter_asset['symbol'] != 'USDT':
                response += f"• {iter_asset['symbol']}: {float(format_float_number(str(iter_asset['total_amount'])))}\n"
            else:
                delay_ustd = f"• {iter_asset['symbol']}: {iter_asset['total_amount']:.2f}\n"
        response += f'\n💰 Ваш баланс:\n{delay_ustd}'

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
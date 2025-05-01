from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

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
                response += f"{iter_asset['symbol']}: {float(format_float_number(str(iter_asset['total_amount'])))}\n"
            else:
                delay_ustd = f"{iter_asset['symbol']}: {iter_asset['total_amount']:.2f}\n"
        response += f'\n💰 Ваш баланс:\n{delay_ustd}'

        await message.answer(response)
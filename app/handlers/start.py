from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart

from app.database.crud import get_user_by_id, create_user, update_balance
from app.database.init_engine import get_async_session

router = Router()

WELCOME_MESSAGE = f"""
<b>💰 Это бот - личный тренажёр для безопасного обучения криптотрейдингу с виртуальным балансом.</b>

Впервые у нас? Тогда обязательно ознакомьтесь 👇

<u>📌 Быстрый старт:</u>
1. Получаете стартовый капитал → /start
2. Следите за рынком → /prices
3. Совершаете сделки → /buy и /sell
4. Контролируете портфель → /balance
5. Помощь - /help

- Исходный код: https://github.com/dizixxx/CryptoMirror
- Binance: https://www.binance.com/ru/

<em>💡 Поддержка - @Dj_arbuzzzzzzz  |  Время работы: иногда :) </em>
"""

@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    async with await get_async_session() as session:
        user = await get_user_by_id(session, user_id)

        if not user:
            await create_user(session, user_id, username)
            await update_balance(session, message.from_user.id, "USDT", 100.0)

            await message.answer(
                f"<b>🚀 Добро пожаловать в <i>CryptoMirror</i>, {first_name}! Вы успешно зарегистрированы в системе.</b>\n"
                f"Ваш начальный баланс: <b>100.00 USDT</b>\n",
                parse_mode='HTML'
            )
        else:
            await message.answer(f"<b>Здравствуйте, {first_name}! Вы уже зарегистрированы, так что можете продолжать трейдинг.</b>",
                                 parse_mode='HTML')
    await message.answer(WELCOME_MESSAGE, parse_mode='HTML', disable_web_page_preview=True)
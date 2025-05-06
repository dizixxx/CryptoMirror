from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart

from app.database.crud import get_user_by_id, create_user, update_balance
from app.database.init_engine import get_async_session

router = Router()

WELCOME_MESSAGE = f"""
<b>💰 Это бот - виртуальный тренажёр для обучения криптотрейдингу с виртуальным балансом, 
созданный на основе биржи Binance.</b>

Впервые у нас? Тогда обязательно ознакомьтесь 👇

<u>📌 Доступные команды:</u>
1. Следите за рынком → /prices
2. Совершайте сделки → /buy и /sell
3. Контролируйте портфель → /balance
4. Просматривайте баланс → /portfolio
5. Помощь → /help

• Source code: https://github.com/dizixxx/CryptoMirror
• Binance: https://www.binance.com/ru/
• Powered by: https://aiogram.dev/
• Using: https://python-binance.readthedocs.io/

<em>💬 Поддержка - @Dj_arbuzzzzzzz  |  Время работы: иногда </em>
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
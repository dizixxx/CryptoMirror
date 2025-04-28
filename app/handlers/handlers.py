# /start - Старт бота с текстом, какие команды есть
# /help - хелп объяснение
# /prices - текущие цены (по 5 пар)
# /buy - Купить пару (тут сценарий, какую пару, на сколько долларов, подтвердить покупку) - с сохранением в базу
# /sell - продать пару
# /balance - тут обзор всех сделок, пример: BTC: 0.00146 куплено по 68493.22 — сейчас 68800 (+0.45%)

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command

from app.database.crud import get_user_by_id, create_user
from app.database.init_engine import get_async_session

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    async with await get_async_session() as session:
        user = await get_user_by_id(session, user_id)

        if not user:
            await create_user(session, user_id, username)
            await message.answer(f"Добро пожаловать, {first_name}! Вы успешно зарегистрированы в системе.")
        else:
            await message.answer(f"Здравствуйте, {first_name}! Вы уже зарегистрированы, так что можете продолжать трейдинг.")

@router.message(Command('help'))
async def cmd_help(message: Message):
    await message.answer('ты попросил помощь')

@router.message(Command('prices'))
async def cmd_prices(message: Message):
    await message.answer('ты хочешь узнать цены')

@router.message(Command('buy'))
async def cmd_buy(message: Message):
    await message.answer('ты хочешь купить')

@router.message(Command('balance'))
async def cmd_balance(message: Message):
    await message.answer('ты хочешь узнать баланс')

@router.message(Command('sell'))
async def cmd_sell(message: Message):
    await message.answer('ты хочешь продать')
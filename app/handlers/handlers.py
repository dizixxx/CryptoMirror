# /start - Старт бота с текстом, какие команды есть
# /help - хелп объяснение
# /prices - текущие цены (по 5 пар)
# /buy - Купить пару (тут сценарий, какую пару, на сколько долларов, подтвердить покупку) - с сохранением в базу
# /sell - продать пару
# /balance - тут обзор всех сделок, пример: BTC: 0.00146 куплено по 68493.22 — сейчас 68800 (+0.45%)

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command

router = Router()

@router.message(Command('help'))
async def cmd_help(message: Message):
    await message.answer('ты попросил помощь')
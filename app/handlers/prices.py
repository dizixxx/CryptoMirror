from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command

from app.database.crud import get_user_by_id, create_user
from app.database.init_engine import get_async_session
from app.services.binance import get_prices

router = Router()

@router.message(Command('prices'))
async def cmd_prices(message: Message):
    ans = await get_prices()
    await message.answer(f'{ans}')
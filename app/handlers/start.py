from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart

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
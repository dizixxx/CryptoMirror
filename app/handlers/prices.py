from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from app.__init__ import asset
from app.services.binance import get_prices
from app.database.init_engine import AsyncSessionLocal
from app.database.crud import upsert_asset_price, get_asset_price

router = Router()

@router.message(Command('prices'))
async def cmd_prices(message: Message):
    ans = 'Цены Binance на текущий момент:\n'
    async with AsyncSessionLocal() as session:
        for pair in asset:
            data = await get_prices(pair)
            price = round(float(data["price"]), 2)

            db_data = await get_asset_price(session, symbol=data["symbol"])

            if db_data:
                prev_price = db_data.prev_price
                if prev_price != 0:
                    percent_change = round(((price - prev_price) / prev_price) * 100, 2)
                    change_indicator = "📈" if percent_change >= 0 else "📉"
                    change_indicator1 = "🟢" if percent_change >= 0 else "🔴"
                    ans += f"{pair}: {price}    |    ({change_indicator} {percent_change}% {change_indicator1})\n"
                else:
                    ans += f"{pair}: {price}    |   (Нет данных для сравнения)\n"
            else:
                ans += f"{pair}: {price}   |    (Нет данных для сравнения)\n"

            await upsert_asset_price(
                session=session,
                symbol=data["symbol"],
                name=asset[data["symbol"]],
                price=price
            )
    ans += f'\n*Относительно предыдущего запроса, сделанного в {datetime.strptime("2025-04-28 19:46:00.734669 UTC", "%Y-%m-%d %H:%M:%S.%f UTC").strftime("%H:%M %d-%m")} UTC.'
    print(ans)

    await message.answer(f'{ans}')
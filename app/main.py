import os

from dotenv import load_dotenv
import asyncio

from aiogram import Bot, Dispatcher

from app.handlers.__init__ import routers
from app.database.init_engine import init_db
from app.services.prices_updater import PriceUpdater

load_dotenv()

async def main():
	await init_db()

	bot = Bot(token=os.getenv("BOT_TOKEN"))

	dp = Dispatcher()

	price_updater = PriceUpdater()
	price_updater.set_bot(bot)

	for router in routers:
		dp.include_router(router)

	await dp.start_polling(bot)

if __name__ == '__main__':
	try:
		asyncio.run(main())
	except KeyboardInterrupt:
		pass
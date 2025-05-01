from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

router = Router()

@router.message(Command('help'))
async def cmd_help(message: Message):
    help_text = (
        "🤖 <b>Помощь по командам</b>\n\n"
        "Все просто! Вот что я умею:\n\n"
        "🚀 <b>Основные команды:</b>\n"
        "/start - Запустить бота и получить стартовый баланс\n"
        "/help - Это окно с подсказками\n"
        "/prices - Актуальные курсы топ-5 пар\n\n"
        "💼 <b>Торговля:</b>\n"
        "/buy - Купить криптовалюту (выбрать пару → сумму → подтвердить)\n"
        "/sell - Продать актив (аналогично покупке)\n\n"
        "📊 <b>Аналитика:</b>\n"
        "/balance - Твой портфель с доходностью активов\n\n"
        "💡 <b>Как торговать?</b>\n"
        "1. Проверь цены через /prices\n"
        "2. Выбери /buy или /sell\n"
        "3. Следуй инструкциям\n"
        "4. Следи за балансом в /balance\n\n"
        "Пример: <code>BTC: 0.00146 → $68800 (+0.45%)</code>\n\n"
        "🚨 Все сделки сохраняются автоматически!"
    )

    await message.answer(help_text, parse_mode="HTML")
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.services.binance import get_prices
from app.database.init_engine import AsyncSessionLocal
from app.database.crud import get_user_balance, update_balance
from app.database.models import Trade
from app.__init__ import asset

router = Router()


def add_cancel_button(keyboard: InlineKeyboardBuilder = None) -> InlineKeyboardBuilder:
    if keyboard is None:
        keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(
        text="❌ Разорвать сделку",
        callback_data="cancel_deal"
    ))
    return keyboard


class BuyStates(StatesGroup):
    choosing_pair = State()
    entering_amount = State()
    confirming = State()


@router.message(Command("buy"))
async def cmd_buy(message: Message, state: FSMContext):
    """Начало процесса покупки - выбор пары"""
    pairs = [k for k in asset.keys() if k != "USDT"]

    builder = InlineKeyboardBuilder()
    for pair in pairs:
        builder.button(text=pair, callback_data=f"pair_{pair}")
    builder.adjust(2)
    builder = add_cancel_button(builder)

    sent_message = await message.answer(
        "🛒 Выберите торговую пару:",
        reply_markup=builder.as_markup(),
    )

    await state.update_data(bot_message_id=sent_message.message_id)
    await message.delete()
    await state.set_state(BuyStates.choosing_pair)


@router.callback_query(BuyStates.choosing_pair, F.data.startswith("pair_"))
async def pair_chosen(callback: CallbackQuery, state: FSMContext):
    """Обработка выбранной торговой пары"""
    data = await state.get_data()
    pair = callback.data.split("_")[1]

    builder = add_cancel_button()

    await callback.bot.edit_message_text(
        f"📈 Выбрана пара: {pair}\n"
        f"💵 Введите количество {pair} для покупки:",
        chat_id=callback.message.chat.id,
        message_id=data["bot_message_id"],
        reply_markup=builder.as_markup()
    )

    await state.update_data(chosen_pair=pair)
    await state.set_state(BuyStates.entering_amount)
    await callback.answer()


@router.message(BuyStates.entering_amount, F.text)
async def amount_entered(message: Message, state: FSMContext):
    """Обработка введенного количества для покупки"""
    data = await state.get_data()
    pair = data["chosen_pair"]

    await message.delete()

    try:
        asset_amount = float(message.text.replace(",", "."))
        if asset_amount <= 0:
            raise ValueError

        async with AsyncSessionLocal() as session:
            price_data = await get_prices(f"{pair}")
            price = float(price_data["price"])
            usdt_amount = asset_amount * price

            user_id = message.from_user.id
            balance_info = await get_user_balance(session, user_id)
            usdt_balance = next((b["total_amount"] for b in balance_info if b["symbol"] == "USDT"), 0)

            if usdt_balance < usdt_amount:
                builder = add_cancel_button()

                await message.bot.edit_message_text(
                    f"❌ Недостаточно USDT. Требуется: {usdt_amount:.2f}\n"
                    f"Доступно: {usdt_balance:.2f} USDT\n\n"
                    f"Введите другое количество {pair}:",
                    chat_id=message.chat.id,
                    message_id=data["bot_message_id"],
                    reply_markup=builder.as_markup()
                )
                return

            await state.update_data(
                usdt_amount=usdt_amount,
                price=price,
                asset_amount=asset_amount
            )

            builder = InlineKeyboardBuilder()
            builder.button(text="✅ Подтвердить", callback_data="confirm_yes")
            builder.button(text="✏️ Изменить", callback_data="confirm_change")
            builder = add_cancel_button(builder)
            builder.adjust(2)

            await message.bot.edit_message_text(
                f"🔄 Подтвердите сделку:\n\n"
                f"• Пара: {pair}\n"
                f"• Количество: {asset_amount:.6f} {pair}\n"
                f"• Курс: {price:.2f} USDT\n"
                f"• Сумма к списанию: {usdt_amount:.2f} USDT",
                chat_id=message.chat.id,
                message_id=data["bot_message_id"],
                reply_markup=builder.as_markup()
            )
            await state.set_state(BuyStates.confirming)

    except ValueError:
        builder = InlineKeyboardBuilder()
        builder.button(text="🔁 Повторить", callback_data="retry_amount")
        builder = add_cancel_button(builder)
        builder.adjust(2)

        await message.bot.edit_message_text(
            "❌ Некорректное количество. Введите положительное число:",
            chat_id=message.chat.id,
            message_id=data["bot_message_id"],
            reply_markup=builder.as_markup()
        )


@router.callback_query(BuyStates.entering_amount, F.data == "retry_amount")
async def retry_amount(callback: CallbackQuery, state: FSMContext):
    """Повторный ввод количества"""
    data = await state.get_data()
    pair = data.get("chosen_pair", "актива")

    builder = add_cancel_button()

    await callback.bot.edit_message_text(
        f"💵 Введите количество {pair} для покупки:",
        chat_id=callback.message.chat.id,
        message_id=data["bot_message_id"],
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(BuyStates.confirming, F.data.startswith("confirm_"))
async def handle_confirmation(callback: CallbackQuery, state: FSMContext):
    """Обработка подтверждения сделки"""
    action = callback.data.split("_")[1]
    data = await state.get_data()
    user_id = callback.from_user.id

    if action == "yes":
        async with AsyncSessionLocal() as session:
            # Обновляем баланс
            await update_balance(session, user_id, "USDT", -data["usdt_amount"])
            await update_balance(session, user_id, data["chosen_pair"], data["asset_amount"])

            # Сохраняем сделку
            trade = Trade(
                user_id=user_id,
                symbol=data["chosen_pair"],
                amount=data["asset_amount"],
                price=data["price"],
            )
            session.add(trade)
            await session.commit()

            # Формируем сообщение о успешной сделке
            success_message = (
                "✅ Сделка успешно выполнена!\n\n"
                f"▫️ Пара: {data['chosen_pair']}\n"
                f"▫️ Куплено: {data['asset_amount']:.6f} {data['chosen_pair']}\n"
                f"▫️ По курсу: {data['price']:.2f} USDT\n"
                f"▫️ Списано: {data['usdt_amount']:.2f} USDT\n\n"
                "Спасибо за использование нашего сервиса!"
            )

            await callback.bot.edit_message_text(
                success_message,
                chat_id=callback.message.chat.id,
                message_id=data["bot_message_id"],
                reply_markup=None
            )
            await state.clear()

    elif action == "change":
        # Возвращаемся к вводу количества
        builder = add_cancel_button()

        await callback.bot.edit_message_text(
            f"✏️ Введите новое количество {data['chosen_pair']}:",
            chat_id=callback.message.chat.id,
            message_id=data["bot_message_id"],
            reply_markup=builder.as_markup()
        )
        await state.set_state(BuyStates.entering_amount)
        await callback.answer("Введите новое количество")

    elif action == "no":
        # Сообщение об отмене
        await callback.bot.edit_message_text(
            "❌ Сделка отменена\n\n"
            "Вы можете начать новую сделку командой /buy",
            chat_id=callback.message.chat.id,
            message_id=data["bot_message_id"],
            reply_markup=None
        )
        await state.clear()
        await callback.answer("Сделка отменена")


@router.callback_query(F.data == "cancel_deal")
async def handle_cancel_deal(callback: CallbackQuery, state: FSMContext):
    """Обработка отмены сделки"""
    data = await state.get_data()

    await callback.bot.edit_message_text(
        "❌ Сделка прервана\n\n"
        "Для начала новой сделки используйте /buy",
        chat_id=callback.message.chat.id,
        message_id=data["bot_message_id"],
        reply_markup=None
    )

    await state.clear()
    await callback.answer("Сделка отменена")
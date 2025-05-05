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

router = Router()


def add_cancel_button(keyboard: InlineKeyboardBuilder = None) -> InlineKeyboardBuilder:
    if keyboard is None:
        keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(
        text="❌ Разорвать сделку",
        callback_data="cancel_deal"
    ))
    return keyboard


class SellStates(StatesGroup):
    choosing_asset = State()
    entering_amount = State()
    confirming = State()


@router.message(Command("sell"))
async def cmd_sell(message: Message, state: FSMContext):
    """Начало процесса продажи - выбор актива"""
    user_id = message.from_user.id
    async with AsyncSessionLocal() as session:
        balance_info = await get_user_balance(session, user_id)
        assets = [b["symbol"] for b in balance_info if b["symbol"] != "USDT" and b["total_amount"] > 0]

    if not assets:
        await message.answer("❌ У вас нет активов для продажи.")
        return

    builder = InlineKeyboardBuilder()
    for asset in assets:
        builder.button(text=asset, callback_data=f"asset_{asset}")
    builder.adjust(2)
    builder = add_cancel_button(builder)

    sent_message = await message.answer(
        "💱 Выберите актив для продажи:",
        reply_markup=builder.as_markup(),
    )

    await state.update_data(bot_message_id=sent_message.message_id)
    await message.delete()
    await state.set_state(SellStates.choosing_asset)


@router.callback_query(SellStates.choosing_asset, F.data.startswith("asset_"))
async def asset_chosen(callback: CallbackQuery, state: FSMContext):
    """Обработка выбранного актива для продажи"""
    data = await state.get_data()
    asset = callback.data.split("_")[1]

    user_id = callback.from_user.id
    async with AsyncSessionLocal() as session:
        balance_info = await get_user_balance(session, user_id)
        available = next((b["total_amount"] for b in balance_info if b["symbol"] == asset), 0.0)

    builder = add_cancel_button()

    await callback.bot.edit_message_text(
        f"💰 Выбран актив: {asset}\n"
        f"💳 Доступно: {available:.6f} {asset}\n\n"
        f"🔢 Введите количество {asset} для продажи:",
        chat_id=callback.message.chat.id,
        message_id=data["bot_message_id"],
        reply_markup=builder.as_markup()
    )

    await state.update_data(chosen_asset=asset, available_amount=available)
    await state.set_state(SellStates.entering_amount)
    await callback.answer()


@router.message(SellStates.entering_amount, F.text)
async def amount_entered(message: Message, state: FSMContext):
    """Обработка введенного количества для продажи"""
    data = await state.get_data()
    asset = data["chosen_asset"]
    available = data["available_amount"]

    await message.delete()

    try:
        asset_amount = float(message.text.replace(",", "."))
        if asset_amount <= 0:
            raise ValueError

        if asset_amount > available:
            builder = add_cancel_button()

            await message.bot.edit_message_text(
                f"❌ Недостаточно {asset}. Доступно: {available:.6f}\n\n"
                f"Введите другое количество {asset}:",
                chat_id=message.chat.id,
                message_id=data["bot_message_id"],
                reply_markup=builder.as_markup()
            )
            return

        async with AsyncSessionLocal() as session:
            price_data = await get_prices(f"{asset}")
            price = float(price_data["price"])
            usdt_amount = asset_amount * price

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
                f"🔄 Подтвердите продажу:\n\n"
                f"• Актив: {asset}\n"
                f"• Количество: {asset_amount:.6f} {asset}\n"
                f"• Курс: {price:.2f} USDT\n"
                f"• Сумма к зачислению: {usdt_amount:.2f} USDT",
                chat_id=message.chat.id,
                message_id=data["bot_message_id"],
                reply_markup=builder.as_markup()
            )
            await state.set_state(SellStates.confirming)

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


@router.callback_query(SellStates.entering_amount, F.data == "retry_amount")
async def retry_amount(callback: CallbackQuery, state: FSMContext):
    """Повторный ввод количества"""
    data = await state.get_data()
    asset = data.get("chosen_asset", "актива")

    builder = add_cancel_button()

    await callback.bot.edit_message_text(
        f"🔢 Введите количество {asset} для продажи:",
        chat_id=callback.message.chat.id,
        message_id=data["bot_message_id"],
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(SellStates.confirming, F.data.startswith("confirm_"))
async def handle_confirmation(callback: CallbackQuery, state: FSMContext):
    """Обработка подтверждения продажи"""
    action = callback.data.split("_")[1]
    data = await state.get_data()
    user_id = callback.from_user.id

    if action == "yes":
        async with AsyncSessionLocal() as session:
            # Обновляем баланс
            await update_balance(session, user_id, data["chosen_asset"], -data["asset_amount"])
            await update_balance(session, user_id, "USDT", data["usdt_amount"])

            # Сохраняем сделку
            trade = Trade(
                user_id=user_id,
                symbol=data["chosen_asset"],
                amount=-data["asset_amount"],
                price=data["price"],
            )
            session.add(trade)
            await session.commit()

            # Формируем сообщение о успешной сделке
            success_message = (
                "✅ Продажа успешно выполнена!\n\n"
                f"▫️ Актив: {data['chosen_asset']}\n"
                f"▫️ Продано: {data['asset_amount']:.6f} {data['chosen_asset']}\n"
                f"▫️ По курсу: {data['price']:.2f} USDT\n"
                f"▫️ Зачислено: {data['usdt_amount']:.2f} USDT\n\n"
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
        builder = add_cancel_button()

        await callback.bot.edit_message_text(
            f"✏️ Введите новое количество {data['chosen_asset']}:",
            chat_id=callback.message.chat.id,
            message_id=data["bot_message_id"],
            reply_markup=builder.as_markup()
        )
        await state.set_state(SellStates.entering_amount)
        await callback.answer("Введите новое количество")


@router.callback_query(F.data == "cancel_deal")
async def handle_cancel_deal(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    await callback.bot.edit_message_text(
        "❌ Сделка прервана\n\n"
        "Для начала новой сделки используйте /sell",
        chat_id=callback.message.chat.id,
        message_id=data["bot_message_id"],
        reply_markup=None
    )

    await state.clear()
    await callback.answer("Сделка отменена")
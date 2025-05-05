from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
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

class BuyStates(StatesGroup):
    choosing_pair = State()
    entering_amount = State()
    confirming = State()

@router.message(Command("buy"))
async def cmd_buy(message: Message, state: FSMContext):
    pairs = [k for k in asset.keys() if k != "USDT"]

    builder = InlineKeyboardBuilder()
    for pair in pairs:
        builder.button(text=pair, callback_data=f"pair_{pair}")
    builder.adjust(2)

    await message.answer(
        "🛒 Выберите торговую пару:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(BuyStates.choosing_pair)


@router.callback_query(BuyStates.choosing_pair, F.data.startswith("pair_"))
async def pair_chosen(callback: CallbackQuery, state: FSMContext):
    pair = callback.data.split("_")[1]
    await state.update_data(chosen_pair=pair)

    await callback.message.edit_text(
        f"📈 Выбрана пара: {pair}\n"
        f"💵 Введите количество {pair} для покупки:"
    )
    await state.set_state(BuyStates.entering_amount)

@router.message(BuyStates.entering_amount, F.text)
async def amount_entered(message: Message, state: FSMContext):
    try:
        asset_amount = float(message.text.replace(",", "."))
        if asset_amount <= 0:
            raise ValueError
    except ValueError:
        builder = InlineKeyboardBuilder()
        builder.button(text="🔁 Повторить ввод", callback_data="retry_amount")
        builder.button(text="❌ Отменить", callback_data="confirm_no")
        builder.adjust(2)

        await message.answer(
            "❌ Некорректное количество. Введите положительное число.\n\n"
            "Вы можете повторить ввод или отменить сделку:",
            reply_markup=builder.as_markup()
        )
        return

    data = await state.get_data()
    pair = data["chosen_pair"]

    async with AsyncSessionLocal() as session:
        price_data = await get_prices(f"{pair}")
        price = float(price_data["price"])

        usdt_amount = asset_amount * price

        user_id = message.from_user.id
        balance_info = await get_user_balance(session, user_id)
        usdt_balance = next((b["total_amount"] for b in balance_info if b["symbol"] == "USDT"), 0)

        if usdt_balance < usdt_amount:
            await message.answer(
                f"❌ Недостаточно USDT. Требуется: {usdt_amount:.2f}\n"
                f"Доступно: {usdt_balance:.2f} USDT"
            )
            await state.clear()
            return

        await state.update_data(
            usdt_amount=usdt_amount,
            price=price,
            asset_amount=asset_amount
        )

        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Подтвердить", callback_data="confirm_yes")
        builder.button(text="✏️ Изменить количество", callback_data="confirm_change")
        builder.button(text="❌ Отменить", callback_data="confirm_no")
        builder.adjust(2)

        await message.answer(
            f"🔄 Подтвердите сделку:\n\n"
            f"• Пара: {pair}\n"
            f"• Количество: {asset_amount:.6f} {pair}\n"
            f"• Курс: {price:.2f} USDT/{pair}\n"
            f"• Сумма к списанию: {usdt_amount:.2f} USDT",
            reply_markup=builder.as_markup()
        )
        await state.set_state(BuyStates.confirming)


@router.callback_query(BuyStates.entering_amount, F.data == "retry_amount")
async def retry_amount(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pair = data.get("chosen_pair", "актива")
    await callback.message.edit_text(f"💵 Введите количество {pair} для покупки:")


@router.callback_query(BuyStates.confirming, F.data.startswith("confirm_"))
async def handle_confirmation(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[1]
    data = await state.get_data()
    user_id = callback.from_user.id

    if action == "yes":
        async with AsyncSessionLocal() as session:
            # Обновляем баланс USDT и актива
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

            await callback.message.edit_text(
                f"✅ Успешно куплено:\n"
                f"• Количество: {data['asset_amount']:.6f} {data['chosen_pair']}\n"
                f"• Списано: {data['usdt_amount']:.2f} USDT\n"
                f"• Курс: {data['price']:.2f} USDT/{data['chosen_pair']}"
            )
            await state.clear()

    elif action == "change":
        await callback.message.edit_text(f"💵 Введите новое количество {data['chosen_pair']}:")
        await state.set_state(BuyStates.entering_amount)

    elif action == "no":
        await callback.message.edit_text("❌ Сделка отменена")
        await state.clear()

@router.message(BuyStates.confirming)
async def incorrect_confirmation(message: Message):
    await message.answer("⚠️ Пожалуйста, используйте кнопки для подтверждения сделки")
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

router = Router()


class SellStates(StatesGroup):
    choosing_asset = State()
    entering_amount = State()
    confirming = State()


def format_float(value: float) -> str:
    return "{:.8f}".format(value).rstrip('0').rstrip('.') if '.' in str(value) else str(value)


@router.message(Command("sell"))
async def cmd_sell(message: Message, state: FSMContext):
    user_id = message.from_user.id
    async with AsyncSessionLocal() as session:
        balance_info = await get_user_balance(session, user_id)
        assets = [b["symbol"] for b in balance_info if b["symbol"] != "USDT" and b["total_amount"] > 0]

    if not assets:
        await message.answer("❌ У вас нет активов для продажи.")
        return

    builder = InlineKeyboardBuilder()
    for asset in assets:
        builder.button(text=asset, callback_data=f"sell_{asset}")
    builder.adjust(2)

    await message.answer(
        "💱 Выберите актив, который хотите продать за USDT:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(SellStates.choosing_asset)


@router.callback_query(SellStates.choosing_asset, F.data.startswith("sell_"))
async def asset_chosen(callback: CallbackQuery, state: FSMContext):
    asset = callback.data.split("_")[1]
    await state.update_data(chosen_asset=asset)

    user_id = callback.from_user.id
    async with AsyncSessionLocal() as session:
        balance_info = await get_user_balance(session, user_id)
        available = next(
            (b["total_amount"]
             for b in balance_info
             if b["symbol"] == asset),
            0.0
        )

    await callback.message.edit_text(
        f"💰 Выбран актив: {asset}\n"
        f"🔢 Введите количество {asset} для продажи:\n"
        f"💳 Доступно для продажи: {format_float(available)} {asset}"
    )
    await state.set_state(SellStates.entering_amount)



@router.message(SellStates.entering_amount, F.text)
async def amount_entered(message: Message, state: FSMContext):
    try:
        input_amount = message.text.replace(",", ".")
        asset_amount = round(float(input_amount), 8)

        if asset_amount <= 0:
            raise ValueError
    except ValueError:
        builder = InlineKeyboardBuilder()
        builder.button(text="🔁 Повторить ввод", callback_data="retry_amount")
        builder.button(text="❌ Отменить", callback_data="confirm_no")
        builder.adjust(2)

        await message.answer(
            "❌ Некорректное количество. Введите положительное число.",
            reply_markup=builder.as_markup()
        )
        return

    data = await state.get_data()
    asset = data["chosen_asset"]

    async with AsyncSessionLocal() as session:
        balance_info = await get_user_balance(session, message.from_user.id)
        available = next(
            (b["total_amount"]
             for b in balance_info
             if b["symbol"] == asset),
            0.0
        )

        if asset_amount > available:
            await message.answer(
                f"❌ Недостаточно {asset}. Доступно: {format_float(available)} {asset}"
            )
            await state.clear()
            return

        price_data = await get_prices(f"{asset}")
        price = round(float(price_data["price"]), 8)
        usdt_amount = round(asset_amount * price, 2)

        await state.update_data(
            asset_amount=asset_amount,
            usdt_amount=usdt_amount,
            price=price
        )

        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Подтвердить", callback_data="confirm_yes")
        builder.button(text="✏️ Изменить количество", callback_data="confirm_change")
        builder.button(text="❌ Отменить", callback_data="confirm_no")
        builder.adjust(2)

        await message.answer(
            f"🔄 Подтвердите продажу:\n\n"
            f"• Актив: {asset}\n"
            f"• Количество: {format_float(asset_amount)} {asset}\n"
            f"• Курс: {format_float(price)} USDT/{asset}\n"
            f"• Вы получите: {usdt_amount:.2f} USDT",
            reply_markup=builder.as_markup()
        )
        await state.set_state(SellStates.confirming)


@router.callback_query(SellStates.entering_amount, F.data == "retry_amount")
async def retry_amount(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    asset = data.get("chosen_asset", "актива")
    await callback.message.edit_text(f"🔢 Введите количество {asset} для продажи:")


@router.callback_query(SellStates.confirming, F.data.startswith("confirm_"))
async def handle_confirmation(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[1]
    data = await state.get_data()
    user_id = callback.from_user.id

    if action == "yes":
        async with AsyncSessionLocal() as session:
            await update_balance(session, user_id, data["chosen_asset"], -data["asset_amount"])
            await update_balance(session, user_id, "USDT", data["usdt_amount"])

            trade = Trade(
                user_id=user_id,
                symbol=data["chosen_asset"],
                amount=-data["asset_amount"],
                price=data["price"]
            )
            session.add(trade)
            await session.commit()

        await callback.message.edit_text(
            f"✅ Продажа выполнена:\n"
            f"• Продано: {format_float(data['asset_amount'])} {data['chosen_asset']}\n"
            f"• Получено: {data['usdt_amount']:.2f} USDT\n"
            f"• Курс: {format_float(data['price'])} USDT/{data['chosen_asset']}"
        )
        await state.clear()

    elif action == "change":
        await callback.message.edit_text(f"🔢 Введите новое количество {data['chosen_asset']} для продажи:")
        await state.set_state(SellStates.entering_amount)

    elif action == "no":
        await callback.message.edit_text("❌ Сделка отменена.")
        await state.clear()


@router.message(SellStates.confirming)
async def incorrect_confirmation(message: Message):
    await message.answer("⚠️ Пожалуйста, используйте кнопки для подтверждения сделки.")
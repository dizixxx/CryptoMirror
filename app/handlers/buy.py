from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.services.binance import get_prices
from app.database.init_engine import AsyncSessionLocal
from app.database.crud import get_user_balance, update_balance
from app.database.models import Trade
from app.__init__ import asset

router = Router()

#
# class BuyStates(StatesGroup):
#     choosing_pair = State()
#     entering_amount = State()
#     confirming = State()
#
#
# async def edit_or_resend(bot, chat_id, state, new_text, reply_markup=None):
#     data = await state.get_data()
#     message_id = data.get('buy_message_id')
#
#     try:
#         if message_id:
#             try:
#                 await bot.edit_message_text(
#                     chat_id=chat_id,
#                     message_id=message_id,
#                     text=new_text,
#                     reply_markup=reply_markup
#                 )
#                 return message_id
#             except Exception:
#                 pass
#
#     except KeyError:
#         pass
#
#     new_msg = await bot.send_message(chat_id, new_text, reply_markup=reply_markup)
#     await state.update_data(buy_message_id=new_msg.message_id)
#     return new_msg.message_id
#
#
# @router.message(Command("buy"))
# async def cmd_buy(message: types.Message, state: FSMContext):
#     await state.clear()
#     await state.set_state(BuyStates.choosing_pair)
#
#     pairs = [k for k in asset.keys() if k != "USDT"]
#     builder = InlineKeyboardBuilder()
#
#     for pair in pairs:
#         builder.button(text=pair, callback_data=f"buy_pair_{pair}")
#     builder.adjust(2)
#
#     await edit_or_resend(
#         message.bot,
#         message.chat.id,
#         state,
#         "🛒 Выберите торговую пару:",
#         builder.as_markup()
#     )
#     await message.delete()
#
#
# @router.callback_query(F.data.startswith("buy_pair_"))
# async def pair_chosen(callback: types.CallbackQuery, state: FSMContext):
#     pair = callback.data.split("_")[2]
#     await state.update_data(chosen_pair=pair)
#     await state.set_state(BuyStates.entering_amount)
#
#     await edit_or_resend(
#         callback.bot,
#         callback.message.chat.id,
#         state,
#         f"📈 Выбрана пара: {pair}\n💵 Введите количество {pair} для покупки:",
#         None
#     )
#     await callback.answer()
#
#
# @router.message(BuyStates.entering_amount, F.text)
# async def amount_entered(message: types.Message, state: FSMContext):
#     data = await state.get_data()
#     pair = data["chosen_pair"]
#
#     try:
#         asset_amount = float(message.text.replace(",", "."))
#         if asset_amount <= 0:
#             raise ValueError
#     except ValueError:
#         builder = InlineKeyboardBuilder()
#         builder.button(text="🔁 Повторить", callback_data="buy_retry")
#         builder.button(text="❌ Отменить", callback_data="buy_cancel")
#         builder.adjust(2)
#
#         await edit_or_resend(
#             message.bot,
#             message.chat.id,
#             state,
#             "❌ Некорректное количество. Введите положительное число.",
#             builder.as_markup()
#         )
#         await message.delete()
#         return
#
#     async with AsyncSessionLocal() as session:
#         price_data = await get_prices(f"{pair}")
#         price = float(price_data["price"])
#         usdt_amount = asset_amount * price
#
#         balance_info = await get_user_balance(session, message.from_user.id)
#         usdt_balance = next((b["total_amount"] for b in balance_info if b["symbol"] == "USDT"), 0)
#
#         if usdt_balance < usdt_amount:
#             await edit_or_resend(
#                 message.bot,
#                 message.chat.id,
#                 state,
#                 f"❌ Недостаточно USDT. Нужно: {usdt_amount:.2f}\nДоступно: {usdt_balance:.2f}",
#                 None
#             )
#             await state.clear()
#             await message.delete()
#             return
#
#         await state.update_data(
#             usdt_amount=usdt_amount,
#             price=price,
#             asset_amount=asset_amount
#         )
#
#     builder = InlineKeyboardBuilder()
#     builder.button(text="✅ Подтвердить", callback_data="buy_confirm")
#     builder.button(text="✏️ Изменить", callback_data="buy_retry")
#     builder.button(text="❌ Отменить", callback_data="buy_cancel")
#     builder.adjust(2)
#
#     text = (
#         f"🔄 Подтвердите покупку:\n\n"
#         f"• Пара: {pair}\n"
#         f"• Количество: {asset_amount:.6f}\n"
#         f"• Цена: {price:.2f} USDT\n"
#         f"• Итого: {usdt_amount:.2f} USDT"
#     )
#
#     await edit_or_resend(
#         message.bot,
#         message.chat.id,
#         state,
#         text,
#         builder.as_markup()
#     )
#     await message.delete()
#
#
# @router.callback_query(F.data == "buy_retry")
# async def retry_amount(callback: types.CallbackQuery, state: FSMContext):
#     data = await state.get_data()
#     await edit_or_resend(
#         callback.bot,
#         callback.message.chat.id,
#         state,
#         f"💵 Введите новое количество {data['chosen_pair']}:",
#         None
#     )
#     await callback.answer()
#
#
# @router.callback_query(F.data == "buy_cancel")
# async def cancel_buy(callback: types.CallbackQuery, state: FSMContext):
#     await state.clear()
#     await edit_or_resend(
#         callback.bot,
#         callback.message.chat.id,
#         state,
#         "❌ Покупка отменена",
#         None
#     )
#     await callback.answer()
#
#
# @router.callback_query(F.data == "buy_confirm")
# async def confirm_buy(callback: types.CallbackQuery, state: FSMContext):
#     data = await state.get_data()
#
#     async with AsyncSessionLocal() as session:
#         await update_balance(session, callback.from_user.id, "USDT", -data["usdt_amount"])
#         await update_balance(session, callback.from_user.id, data["chosen_pair"], data["asset_amount"])
#
#         trade = Trade(
#             user_id=callback.from_user.id,
#             symbol=data["chosen_pair"],
#             amount=data["asset_amount"],
#             price=data["price"],
#         )
#         session.add(trade)
#         await session.commit()
#
#     await edit_or_resend(
#         callback.bot,
#         callback.message.chat.id,
#         state,
#         f"✅ Успешно куплено {data['asset_amount']:.6f} {data['chosen_pair']} за {data['usdt_amount']:.2f} USDT",
#         None
#     )
#     await state.clear()
#     await callback.answer()
#
#
# @router.message()
# async def handle_other_messages(message: types.Message, state: FSMContext):
#     """Перехватывает все сообщения во время процесса покупки"""
#     current_state = await state.get_state()
#     if current_state in BuyStates.__all_states__:
#         await message.delete()
#         msg = await message.answer("⚠️ Завершите текущую покупку или используйте /cancel")
#         await msg.delete(delay=3)
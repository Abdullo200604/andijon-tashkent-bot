import asyncio
import re
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import ORDER_TIMEOUT
from database import (
    get_user, create_order, get_all_active_taxi_ids,
    expire_order, get_order, add_discount_balance, get_client_orders
)
from keyboards import client_menu, cancel_keyboard, order_keyboard, location_keyboard, passengers_keyboard, cabinet_keyboard, back_to_cabinet
from states import OrderForm, DiscountCalcForm
from utils import is_valid_time, is_valid_location_name

router = Router()

# Aktiv buyurtmalar: {order_id: {taxi_id: message_id}}
active_order_messages: dict[int, dict[int, int]] = {}


@router.message(F.text == "🚖 Taksi chaqirish")
async def start_order(message: Message, state: FSMContext):
    """Buyurtma berish bosqichi — qayerdan"""
    user = await get_user(message.from_user.id)
    if not user or user["role"] != "client":
        return

    await state.set_state(OrderForm.from_loc)
    await message.answer(
        "📍 Qayerdan ketasiz?\n\n(Misol: Andijon, Asaka, Namangan...)",
        reply_markup=cancel_keyboard()
    )


@router.message(OrderForm.from_loc)
async def order_from(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=client_menu())
        return

    if not is_valid_location_name(message.text):
        await message.answer("❌ Noto'g'ri nom. Iltimos, joylashuv nomini to'g'ri kiriting.")
        return

    await state.update_data(from_loc=message.text)
    await state.set_state(OrderForm.to_loc)
    await message.answer("📍 Qayerga ketasiz?\n\n(Misol: Toshkent, Chirchiq...)", reply_markup=cancel_keyboard())


@router.message(OrderForm.to_loc)
async def order_to(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=client_menu())
        return

    if not is_valid_location_name(message.text):
        await message.answer("❌ Noto'g'ri nom. Iltimos, joylashuv nomini to'g'ri kiriting.")
        return

    await state.update_data(to_loc=message.text)
    await state.set_state(OrderForm.location) 
    await message.answer(
        "📍 Turgan joyingizni (lakatsiya) yuboring:\n\n"
        "Bu manzil faqat haydovchi buyurtmani qabul qilganidan so'ng unga ko'rinadi.",
        reply_markup=location_keyboard()
    )


@router.message(OrderForm.location, F.location | (F.text == "❌ Bekor qilish"))
async def order_location(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=client_menu())
        return

    if not message.location:
        await message.answer("❌ Iltimos, pastdagi tugma orqali lakatsiyangizni yuboring.")
        return

    await state.update_data(lat=message.location.latitude, lon=message.location.longitude)
    await state.set_state(OrderForm.order_time)
    await message.answer("🕒 Qaysi vaqtda ketasiz?\n\n(Misol: 14:00, Hozir...)", reply_markup=cancel_keyboard())


@router.message(OrderForm.order_time)
async def order_time(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=client_menu())
        return

    if not is_valid_time(message.text):
        await message.answer("❌ Noto'g'ri vaqt formati. (Misol: 12:00 yoki 'Hozir')")
        return

    await state.update_data(order_time=message.text)
    await state.set_state(OrderForm.price)
    await message.answer("💰 Narx bo'yicha taklifingiz?\n\n(Misol: 200 000)", reply_markup=cancel_keyboard())


@router.message(OrderForm.price)
async def order_price(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=client_menu())
        return

    await state.update_data(price=message.text)
    await state.set_state(OrderForm.passengers)
    await message.answer("👥 Necha kishi ketasiz?", reply_markup=passengers_keyboard())


@router.message(OrderForm.passengers)
async def order_passengers(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=client_menu())
        return

    data = await state.get_data()
    await state.clear()

    user = await get_user(message.from_user.id)
    if not user or not user["phone"]:
        await message.answer("❌ Telefon raqamingiz topilmadi, qayta /start bosing.")
        return

    order_id = await create_order(
        message.from_user.id, data["from_loc"], data["to_loc"],
        data["order_time"], data["price"], user["phone"],
        data.get("lat"), data.get("lon"), message.text
    )

    await message.answer("✅ Buyurtmangiz yuborildi! Taxi haydovchilar xabardor qilindi.\n⏱ 5 daqiqa ichida javob keladi...", reply_markup=client_menu())

    taxi_ids = await get_all_active_taxi_ids()
    order_text = (
        f"🆕 <b>Yangi buyurtma #{order_id}</b>\n\n"
        f"👤 Yo'lovchilar: {message.text}\n"
        f"📍 <b>{data['from_loc']}</b> → <b>{data['to_loc']}</b>\n"
        f"🕒 {data['order_time']}\n"
        f"💰 {data['price']}\n"
        f"📞 {user['phone']}"
    )

    sent_messages: dict[int, int] = {}
    for taxi_id in taxi_ids:
        try:
            sent = await bot.send_message(taxi_id, order_text, parse_mode="HTML", reply_markup=order_keyboard(order_id))
            sent_messages[taxi_id] = sent.message_id
        except: pass

    active_order_messages[order_id] = sent_messages
    asyncio.create_task(_order_timeout(bot, order_id, message.from_user.id))


async def _order_timeout(bot: Bot, order_id: int, client_id: int):
    await asyncio.sleep(ORDER_TIMEOUT)
    order = await get_order(order_id)
    if order and order["status"] == "pending":
        await expire_order(order_id)
        try:
            await bot.send_message(client_id, "❌ Uzr, hozircha bo'sh taxi topilmadi.\nIltimos, keyinroq urinib ko'ring. 🙏")
        except: pass

        if order_id in active_order_messages:
            for taxi_id, msg_id in active_order_messages[order_id].items():
                try: await bot.edit_message_text("⌛ Buyurtma vaqti o'tdi.", chat_id=taxi_id, message_id=msg_id)
                except: pass
            del active_order_messages[order_id]


# ─── KABINET VA TARIX ─────────────────────────────────────────────────────────

@router.message(F.text == "👤 Kabinet")
async def client_cabinet(message: Message):
    user = await get_user(message.from_user.id)
    if not user or user["role"] != "client": return
    
    text = (
        f"👤 <b>Mijoz kabineti</b>\n\n"
        f"Ism: {user['full_name']}\n"
        f"Telefon: {user['phone']}\n"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=cabinet_keyboard("client"))


@router.callback_query(F.data == "cabinet")
async def client_cabinet_cb(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    text = (
        f"👤 <b>Mijoz kabineti</b>\n\n"
        f"Ism: {user['full_name']}\n"
        f"Telefon: {user['phone']}\n"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=cabinet_keyboard("client"))


@router.callback_query(F.data == "history")
async def client_history(call: CallbackQuery):
    orders = await get_client_orders(call.from_user.id)
    if not orders:
        await call.answer("Buyurtmalar tarixi topilmadi.")
        return

    text = "📜 <b>Oxirgi 20 ta buyurtmangiz:</b>\n"
    for o in orders:
        status = "✅" if o["status"] == "taken" else "❌" if o["status"] == "expired" else "⏳"
        text += f"{status} {o['from_loc']} ➔ {o['to_loc']} | {o['price']} so'm\n"
    
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=back_to_cabinet())


# ─── CHEGIRMA HISOB-KITOBI ────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("disc_price:"))
async def start_discount_calc(call: CallbackQuery, state: FSMContext):
    _, percent, taxi_id = call.data.split(":")
    await state.update_data(discount_percent=int(percent), discount_taxi_id=int(taxi_id))
    await state.set_state(DiscountCalcForm.waiting_price)
    await call.message.edit_text(
        f"🎉 <b>Tabriklaymiz!</b> Sizda <b>{percent}% chegirma</b> mavjud! 🎁\n\n"
        f"Iltimos, haydovchi bilan kelishgan <b>aniq narxni</b> kiriting (raqamlarda):",
        parse_mode="HTML"
    )
    await call.answer()


@router.message(DiscountCalcForm.waiting_price)
async def process_discount_price(message: Message, state: FSMContext, bot: Bot):
    digits = re.sub(r'\D', '', message.text)
    if not digits:
        await message.answer("❌ Iltimos, raqamlarda kiriting:")
        return
        
    actual_price = int(digits)
    data = await state.get_data()
    percent = data.get("discount_percent", 0)
    taxi_id = data.get("discount_taxi_id")
    await state.clear()
    
    discount_amount = int(actual_price * percent / 100)
    final_price = actual_price - discount_amount
    
    await message.answer(f"🎉 Sizning {percent}% chegirmangiz {discount_amount:,} so'm bo'ldi!\n\nHaydovchiga faqat {final_price:,} so'm to'laysiz.", reply_markup=client_menu())
    
    if taxi_id:
        await add_discount_balance(taxi_id, discount_amount)
        try:
            await bot.send_message(taxi_id, f"🎁 <b>Bonus qo'shildi!</b>\n\nMijozga qilingan {percent}% chegirma sababli hisobingizga <b>{discount_amount:,} so'm</b> bonus qo'shildi!", parse_mode="HTML")
        except: pass

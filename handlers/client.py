import asyncio
import re
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import ORDER_TIMEOUT, REBROADCAST_LIMIT
from database import (
    get_user, create_order, get_all_active_taxi_ids,
    expire_order, get_order, add_discount_balance, get_client_orders,
    log_analytics, increment_rebroadcast_count, get_order_by_idempotency_key,
    cancel_order_db
)
from keyboards import (
    client_menu, cancel_keyboard, order_keyboard, location_keyboard, 
    passengers_keyboard, cabinet_keyboard, back_to_cabinet,
    gender_keyboard, cancel_reason_keyboard, passenger_order_actions
)
from states import OrderForm, DiscountCalcForm, CancelForm
from utils import is_valid_time, is_valid_location_name
import json
from datetime import datetime

router = Router()

# Aktiv buyurtmalar: {order_id: {taxi_id: message_id}}
active_order_messages: dict[int, dict[int, int]] = {}


@router.message(F.text == "🚖 Taksi chaqirish")
async def start_order(message: Message, state: FSMContext):
    """Buyurtma berish bosqichi — qayerdan"""
    user = await get_user(message.from_user.id)
    from config import ADMIN_ID
    if message.from_user.id != ADMIN_ID:
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
    await state.set_state(OrderForm.gender)
    await message.answer("👤 Jinsingizni tanlang:", reply_markup=gender_keyboard())


@router.message(OrderForm.gender)
async def order_gender(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=client_menu())
        return

    if message.text not in ["👨 Erkak", "👩 Ayol", "🧑 Boshqa"]:
        await message.answer("❌ Iltimos, tugmalardan birini tanlang.")
        return

    await state.update_data(gender=message.text)
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
async def order_passengers(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=client_menu())
        return

    await state.update_data(passengers=message.text)
    await state.set_state(OrderForm.contact_phone)
    
    user = await get_user(message.from_user.id)
    reg_phone = user["phone"] if user else ""
    
    from keyboards import contact_phone_keyboard
    await message.answer(
        f"📞 <b>Bog'lanish uchun raqamni kiriting:</b>\n\n"
        f"Agar hozirgi raqamingiz (<code>{reg_phone}</code>) aktiv bo'lsa, pastdagi tugmani bosing:",
        parse_mode="HTML",
        reply_markup=contact_phone_keyboard(reg_phone)
    )


@router.message(OrderForm.contact_phone)
async def order_contact_phone(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=client_menu())
        return

    contact_phone = message.text
    if message.contact:
        contact_phone = message.contact.phone_number
    
    data = await state.get_data()
    # Idempotency key: user_id + locations + time + passengers + current_hour
    # Bu orqali 1 soat ichida bir xil buyurtmani 2 marta yuborishni oldini olamiz
    idempotency_raw = f"{message.from_user.id}:{data['from_loc']}:{data['to_loc']}:{data['passengers']}:{datetime.now().strftime('%Y-%m-%d-%H')}"
    
    user = await get_user(message.from_user.id)
    if not user or not user["phone"]:
        await message.answer("❌ Telefon raqamingiz topilmadi, qayta /start bosing.")
        return

    # Avval mavjudligini tekshiramiz (Double click protection)
    existing_order = await get_order_by_idempotency_key(idempotency_raw)
    if existing_order:
        await state.clear()
        await message.answer("⚠️ Bu buyurtma allaqachon yuborilgan.", reply_markup=client_menu())
        return

    order_id = await create_order(
        message.from_user.id, data["from_loc"], data["to_loc"],
        data["order_time"], data["price"], user["phone"],
        data.get("lat"), data.get("lon"), data["passengers"],
        data["gender"], contact_phone, idempotency_raw
    )
    
    await state.clear()
    await log_analytics("order_created", message.from_user.id, order_id)

    await message.answer(
        f"✅ Buyurtmangiz yuborildi! (ID: #{order_id})\nTaxi haydovchilar xabardor qilindi.\n⏱ {ORDER_TIMEOUT} daqiqa ichida javob keladi...", 
        reply_markup=passenger_order_actions(order_id)
    )

    await broadcast_order(bot, order_id)


async def broadcast_order(bot: Bot, order_id: int):
    """Buyurtmani barcha faol haydovchilarga yuborish"""
    order = await get_order(order_id)
    if not order or order["status"] != "pending":
        return

    taxi_ids = await get_all_active_taxi_ids()
    username = f"@{order['username']}" if order.get('username') else "—" # Fix: fetch user separately if needed
    
    # User ma'lumotlarini qayta olish (username uchun)
    client = await get_user(order["client_id"])
    username = f"@{client['username']}" if client and client["username"] else "—"
    
    order_text = (
        f"🆕 <b>Yangi buyurtma #{order_id}</b>\n\n"
        f"👤 Telegram: {username}\n"
        f"👤 Jins: {order['gender']}\n"
        f"👥 Yo'lovchilar: {order['passengers']}\n"
        f"📍 <b>{order['from_loc']}</b> → <b>{order['to_loc']}</b>\n"
        f"🕒 {order['order_time']}\n"
        f"💰 {order['price']}\n"
        f"📞 Tel: {order['contact_phone'] or order['phone']}"
    )

    sent_messages: dict[int, int] = {}
    tasks = []
    for taxi_id in taxi_ids:
        tasks.append(bot.send_message(taxi_id, order_text, parse_mode="HTML", reply_markup=order_keyboard(order_id)))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for i, res in enumerate(results):
        if isinstance(res, Message):
            sent_messages[taxi_ids[i]] = res.message_id

    active_order_messages[order_id] = sent_messages
    await log_analytics("order_broadcasted", None, order_id, {"count": len(sent_messages)})
    asyncio.create_task(_order_timeout(bot, order_id, order["client_id"]))


async def _order_timeout(bot: Bot, order_id: int, client_id: int):
    await asyncio.sleep(ORDER_TIMEOUT)
    order = await get_order(order_id)
    if order and order["status"] == "pending":
        if order["rebroadcast_count"] < REBROADCAST_LIMIT:
            await increment_rebroadcast_count(order_id)
            try:
                await bot.send_message(client_id, "🔍 Xaydovchi topilmadi — qayta qidirilyapti...")
            except: pass
            await broadcast_order(bot, order_id)
            await log_analytics("order_rebroadcasted", None, order_id)
        else:
            await expire_order(order_id)
            try:
                await bot.send_message(client_id, "❌ Uzr, bo'sh taxi topilmadi.\nIltimos, keyinroq urinib ko'ring. 🙏", reply_markup=client_menu())
            except: pass

            if order_id in active_order_messages:
                for taxi_id, msg_id in active_order_messages[order_id].items():
                    try: await bot.edit_message_text("⌛ Buyurtma vaqti o'tdi.", chat_id=taxi_id, message_id=msg_id)
                    except: pass
                del active_order_messages[order_id]


# ─── KABINET VA TARIX ───────────────────────────────────────────────────────── (Handlers moved to start.py)



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


# ─── BEKOR QILISH ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cancel_order:"))
async def start_client_cancel(call: CallbackQuery, state: FSMContext):
    order_id = int(call.data.split(":")[1])
    await state.update_data(cancel_order_id=order_id)
    await state.set_state(CancelForm.reason_choice)
    await call.message.answer("📦 Buyurtmani bekor qilish sababini tanlang:", reply_markup=cancel_reason_keyboard("client"))
    await call.answer()


@router.callback_query(CancelForm.reason_choice, F.data.startswith("cancel_res:"))
async def process_client_cancel_reason(call: CallbackQuery, state: FSMContext, bot: Bot):
    reason_key = call.data.split(":")[1]
    data = await state.get_data()
    order_id = data.get("cancel_order_id")
    
    if reason_key == "other":
        await state.set_state(CancelForm.reason_text)
        await call.message.answer("📝 Iltimos, bekor qilish sababini yozing:")
        await call.answer()
        return

    reason_map = {"plans": "Rejalar o'zgardi", "gender": "Jins mos emas", "car": "Mashina mos emas"}
    reason = reason_map.get(reason_key, "Boshqa")
    await finalize_cancellation(call.message, state, bot, order_id, "client", reason)
    await call.answer("Bekor qilindi.")


@router.message(CancelForm.reason_text)
async def process_client_cancel_text(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    order_id = data.get("cancel_order_id")
    await finalize_cancellation(message, state, bot, order_id, "client", message.text)


async def finalize_cancellation(message, state, bot, order_id, role, reason):
    from database import log_cancellation, cancel_order_db
    user_id = message.chat.id
    
    await cancel_order_db(order_id, role, reason)
    await log_cancellation(user_id, role, order_id, reason)
    await log_analytics(f"{role}_cancel", user_id, order_id, {"reason": reason})
    
    await state.clear()
    await bot.send_message(user_id, f"✅ Buyurtma bekor qilindi. Sabab: {reason}", reply_markup=client_menu())
    
    # Haydovchilarga xabar berish
    if order_id in active_order_messages:
        for taxi_id, msg_id in active_order_messages[order_id].items():
            try:
                await bot.edit_message_text(f"❌ Buyurtma #{order_id} mijoz tomonidan bekor qilindi.", chat_id=taxi_id, message_id=msg_id)
            except: pass
        del active_order_messages[order_id]

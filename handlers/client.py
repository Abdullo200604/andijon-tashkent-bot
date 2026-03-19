import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import ORDER_TIMEOUT
from database import (
    get_user, create_order, get_all_active_taxi_ids,
    expire_order, get_order
)
from keyboards import client_menu, cancel_keyboard, order_keyboard, location_keyboard
from states import OrderForm
from utils import is_valid_phone, is_valid_time, is_valid_location_name

router = Router()

# Aktiv buyurtmalar: {order_id: {taxi_id: message_id}}
active_order_messages: dict[int, dict[int, int]] = {}


@router.message(F.text == "🚖 Taksi chaqirish")
async def start_order(message: Message, state: FSMContext):
    """Buyurtma berish bosqichi — qayerdan"""
    user = await get_user(message.from_user.id)
    if not user or user["role"] != "client":
        await message.answer("❌ Bu buyruq faqat mijozlar uchun.")
        return

    await state.set_state(OrderForm.from_loc)
    await message.answer(
        "📍 Qayerdan ketasiz?\n\n"
        "(Misol: Andijon, Asaka, Namangan...)",
        reply_markup=cancel_keyboard()
    )


@router.message(OrderForm.from_loc)
async def order_from(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Buyurtma bekor qilindi.", reply_markup=client_menu())
        return

    if not is_valid_location_name(message.text):
        await message.answer("❌ Noto'g'ri nom. Iltimos, joylashuv nomini to'g'ri kiriting (masalan: Andijon).")
        return

    await state.update_data(from_loc=message.text)
    await state.set_state(OrderForm.to_loc)
    await message.answer(
        "📍 Qayerga ketasiz?\n\n"
        "(Misol: Toshkent, Chirchiq...)",
        reply_markup=cancel_keyboard()
    )


@router.message(OrderForm.to_loc)
async def order_to(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Buyurtma bekor qilindi.", reply_markup=client_menu())
        return

    if not is_valid_location_name(message.text):
        await message.answer("❌ Noto'g'ri nom. Iltimos, joylashuv nomini to'g'ri kiriting (masalan: Toshkent).")
        return

    await state.update_data(to_loc=message.text)
    await state.set_state(OrderForm.location) # Endi lakatsiya so'raymiz
    await message.answer(
        "📍 Turgan joyingizni (lakatsiya) yuboring:\n\n"
        "Bu manzil faqat haydovchi buyurtmani qabul qilganidan so'ng unga ko'rinadi.",
        reply_markup=location_keyboard()
    )


@router.message(OrderForm.location, F.location | (F.text == "❌ Bekor qilish"))
async def order_location(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Buyurtma bekor qilindi.", reply_markup=client_menu())
        return

    if not message.location:
        await message.answer("❌ Iltimos, pastdagi tugma orqali lakatsiyangizni yuboring.")
        return

    await state.update_data(
        lat=message.location.latitude,
        lon=message.location.longitude
    )
    await state.set_state(OrderForm.order_time)
    await message.answer(
        "🕒 Qaysi vaqtda ketasiz?\n\n"
        "(Misol: 14:00, Hozir...)",
        reply_markup=cancel_keyboard()
    )


@router.message(OrderForm.order_time)
async def order_time(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Buyurtma bekor qilindi.", reply_markup=client_menu())
        return

    if not is_valid_time(message.text):
        await message.answer("❌ Noto'g'ri vaqt formati. Iltimos, HH:MM formatida yoki 'Hozir' deb yozing.")
        return

    await state.update_data(order_time=message.text)
    await state.set_state(OrderForm.price)
    await message.answer(
        "💰 Narx bo'yicha taklifingiz?\n\n"
        "(Misol: 120 000, Kelishamiz...)",
        reply_markup=cancel_keyboard()
    )


@router.message(OrderForm.price)
async def order_price(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Buyurtma bekor qilindi.", reply_markup=client_menu())
        return

    await state.update_data(price=message.text)
    await state.set_state(OrderForm.phone)
    await message.answer(
        "📞 Telefon raqamingiz?\n\n"
        "(Misol: +998901234567)",
        reply_markup=cancel_keyboard()
    )


@router.message(OrderForm.phone)
async def order_phone(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Buyurtma bekor qilindi.", reply_markup=client_menu())
        return

    if not is_valid_phone(message.text):
        await message.answer("❌ Noto'g'ri telefon raqami. Iltimos, +998XXXXXXXXX formatida kiriting.")
        return

    data = await state.get_data()
    await state.clear()

    from_loc = data["from_loc"]
    to_loc = data["to_loc"]
    lat = data.get("lat")
    lon = data.get("lon")
    order_time = data["order_time"]
    price = data["price"]
    phone = message.text
    client_id = message.from_user.id

    # Buyurtmani bazaga yozish
    order_id = await create_order(client_id, from_loc, to_loc, order_time, price, phone, lat, lon)

    await message.answer(
        "✅ Buyurtmangiz yuborildi! Taxi haydovchilar xabardor qilindi.\n"
        "⏱ 5 daqiqa ichida javob keladi...",
        reply_markup=client_menu()
    )

    # Barcha aktiv taxi haydovchilarga yuborish
    taxi_ids = await get_all_active_taxi_ids()

    order_text = (
        f"🆕 <b>Yangi buyurtma #{order_id}</b>\n\n"
        f"📍 <b>{from_loc}</b> → <b>{to_loc}</b>\n"
        f"🕒 {order_time}\n"
        f"💰 {price}\n"
        f"📞 {phone}"
    )

    sent_messages: dict[int, int] = {}
    for taxi_id in taxi_ids:
        try:
            sent = await bot.send_message(
                taxi_id,
                order_text,
                parse_mode="HTML",
                reply_markup=order_keyboard(order_id)
            )
            sent_messages[taxi_id] = sent.message_id
        except Exception:
            pass  # Bot bloklanganlar o'tkazib yuboriladi

    active_order_messages[order_id] = sent_messages

    # 5 daqiqadan keyin avtomatik yopiladi
    asyncio.create_task(_order_timeout(bot, order_id, client_id))


async def _order_timeout(bot: Bot, order_id: int, client_id: int):
    """5 daqiqadan keyin buyurtma yopilishi"""
    await asyncio.sleep(ORDER_TIMEOUT)

    order = await get_order(order_id)
    if order and order["status"] == "pending":
        await expire_order(order_id)

        # Mijozga xabar
        try:
            await bot.send_message(
                client_id,
                "❌ Uzr, hozircha bo'sh taxi topilmadi.\n"
                "Iltimos, keyinroq urinib ko'ring. 🙏"
            )
        except Exception:
            pass

        # Taxi xabarlarini yangilash
        if order_id in active_order_messages:
            for taxi_id, msg_id in active_order_messages[order_id].items():
                try:
                    await bot.edit_message_text(
                        "⌛ Buyurtma vaqti o'tdi.",
                        chat_id=taxi_id,
                        message_id=msg_id
                    )
                except Exception:
                    pass
            del active_order_messages[order_id]

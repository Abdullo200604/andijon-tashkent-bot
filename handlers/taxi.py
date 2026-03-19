from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import GROUP_ID
from database import get_user, get_active_subscription
from keyboards import taxi_menu, cancel_keyboard, subscription_keyboard, tariff_keyboard
from states import TaxiAnnounceForm
from utils import is_valid_phone, is_valid_time, is_valid_location_name

router = Router()


def _taxi_only(user) -> bool:
    return user and user["role"] == "taxi"


# ─── E'LON BERISH ─────────────────────────────────────────────────────────────

@router.message(F.text == "📢 Эълон бериш")
async def announce_start(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not _taxi_only(user):
        await message.answer("❌ Bu bo'lim faqat taxi haydovchilar uchun.")
        return

    # Obuna tekshiruvi
    sub = await get_active_subscription(message.from_user.id)
    if not sub:
        await message.answer(
            "❌ E'lon berish uchun faol obuna kerak!\n\n"
            "💳 Obuna sotib olish uchun: <b>Obuna</b> tugmasini bosing.",
            parse_mode="HTML"
        )
        return

    await state.set_state(TaxiAnnounceForm.direction)
    await message.answer(
        "📍 Yo'nalishni kiriting:\n\n"
        "(Misol: Andijon → Toshkent)",
        reply_markup=cancel_keyboard()
    )


@router.message(TaxiAnnounceForm.direction)
async def announce_direction(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=taxi_menu())
        return

    if not is_valid_location_name(message.text):
        await message.answer("❌ Noto'g'ri nom. Iltimos, yo'nalishni to'g'ri kiriting (masalan: Andijon → Toshkent).")
        return

    await state.update_data(direction=message.text)
    await state.set_state(TaxiAnnounceForm.ann_time)
    await message.answer(
        "🕒 Jo'nab ketish vaqtini kiriting:\n\n"
        "(Misol: 14:00)",
        reply_markup=cancel_keyboard()
    )


@router.message(TaxiAnnounceForm.ann_time)
async def announce_time(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=taxi_menu())
        return

    await state.update_data(ann_time=message.text)
    await state.set_state(TaxiAnnounceForm.ann_phone)
    await message.answer(
        "📞 Telefon raqamingizni kiriting:\n\n"
        "(Misol: +998901234567)",
        reply_markup=cancel_keyboard()
    )


@router.message(TaxiAnnounceForm.ann_phone)
async def announce_phone(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=taxi_menu())
        return

    data = await state.get_data()
    await state.clear()

    direction = data["direction"]
    ann_time = data["ann_time"]
    phone = message.text
    taxi_name = message.from_user.full_name
    username = f"@{message.from_user.username}" if message.from_user.username else "—"

    text = (
        f"🚕 <b>Yangi taxi</b>\n\n"
        f"📍 {direction}\n"
        f"🕒 {ann_time}\n"
        f"📞 {phone}\n"
        f"👤 {taxi_name} ({username})"
    )

    # Guruhga yuborish
    try:
        await bot.send_message(GROUP_ID, text, parse_mode="HTML")
        await message.answer(
            "✅ E'loningiz guruhga muvaffaqiyatli yuborildi!",
            reply_markup=taxi_menu()
        )
    except Exception as e:
        await message.answer(
            f"❌ Xato yuz berdi: {e}\n\n"
            "Iltimos, admin bilan bog'laning.",
            reply_markup=taxi_menu()
        )


# ─── OBUNA KO'RISH ────────────────────────────────────────────────────────────

@router.message(F.text == "💳 Обуна")
async def show_subscription(message: Message):
    user = await get_user(message.from_user.id)
    if not _taxi_only(user):
        await message.answer("❌ Bu bo'lim faqat taxi haydovchilar uchun.")
        return

    sub = await get_active_subscription(message.from_user.id)

    if sub:
        from datetime import datetime
        start = datetime.fromisoformat(sub["start_date"]).strftime("%d.%m.%Y")
        end = datetime.fromisoformat(sub["end_date"]).strftime("%d.%m.%Y")

        await message.answer(
            f"✅ <b>Obuna aktiv</b>\n\n"
            f"📅 Boshlangan: {start}\n"
            f"📅 Tugash: {end}\n"
            f"📦 Tarif: {sub['tariff']}",
            parse_mode="HTML",
            reply_markup=subscription_keyboard()
        )
    else:
        await message.answer(
            "❌ <b>Faol obuna topilmadi.</b>\n\n"
            "Tarif tanlash uchun pastdagi tugmani bosing:",
            parse_mode="HTML",
            reply_markup=tariff_keyboard()
        )


@router.callback_query(F.data == "extend_subscription")
async def extend_sub(call: CallbackQuery):
    await call.message.edit_text(
        "🔄 Tarif tanlang:",
        reply_markup=tariff_keyboard()
    )
    await call.answer()


@router.callback_query(F.data == "back_to_taxi")
async def back_to_taxi_cb(call: CallbackQuery):
    await call.message.delete()
    await call.answer()

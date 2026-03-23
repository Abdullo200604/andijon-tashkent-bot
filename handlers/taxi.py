from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import GROUP_ID
from database import get_user, get_active_subscription, get_taxi_orders
from keyboards import taxi_menu, cancel_keyboard, subscription_keyboard, tariff_keyboard, cabinet_keyboard, back_to_cabinet
from states import TaxiAnnounceForm
from utils import is_valid_location_name

router = Router()


def _taxi_only(user) -> bool:
    return user and user["role"] == "taxi"


# ─── E'LON BERISH ─────────────────────────────────────────────────────────────

@router.message(F.text == "📢 Эълон бериш")
async def announce_start(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not _taxi_only(user):
        return

    # Obuna tekshiruvi
    sub = await get_active_subscription(message.from_user.id)
    if not sub:
        await message.answer(
            "❌ <b>E'lon berish uchun faol obuna kerak!</b>\n\n"
            "💳 Obuna sotib olish uchun: <b>Kabinet</b> bo'limiga o'ting.",
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
async def announce_time(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=taxi_menu())
        return

    data = await state.get_data()
    await state.clear()
    
    user = await get_user(message.from_user.id)
    phone = user.get("phone", "Noma'lum")

    direction = data["direction"]
    ann_time = message.text
    taxi_name = message.from_user.full_name
    username = f"@{message.from_user.username}" if message.from_user.username else "—"

    text = (
        f"🚕 <b>Yangi taxi</b>\n\n"
        f"📍 {direction}\n"
        f"🕒 {ann_time}\n"
        f"📞 {phone}\n"
        f"👤 {taxi_name} ({username})"
    )

    try:
        await bot.send_message(GROUP_ID, text, parse_mode="HTML")
        await message.answer("✅ E'loningiz guruhga muvaffaqiyatli yuborildi!", reply_markup=taxi_menu())
    except Exception as e:
        await message.answer(f"❌ Xato yuz berdi: {e}", reply_markup=taxi_menu())


# ─── KABINET ──────────────────────────────────────────────────────────────────

@router.message(F.text == "👤 Kabinet")
async def taxi_cabinet(message: Message):
    user = await get_user(message.from_user.id)
    if not _taxi_only(user): return

    sub = await get_active_subscription(message.from_user.id)
    sub_text = "❌ Faol emas"
    if sub:
        from datetime import datetime
        end = datetime.fromisoformat(sub["end_date"]).strftime("%d.%m.%Y")
        sub_text = f"✅ Faol (Tugash: {end})"

    text = (
        f"👤 <b>Haydovchi kabineti</b>\n\n"
        f"💰 Asosiy balans: {user.get('balance', 0):,} so'm\n"
        f"🎁 Bonus balans: {user.get('discount_balance', 0):,} so'm\n"
        f"📅 Obuna holati: {sub_text}\n"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=cabinet_keyboard("taxi"))


@router.callback_query(F.data == "cabinet")
async def taxi_cabinet_cb(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    sub = await get_active_subscription(call.from_user.id)
    sub_text = "❌ Faol emas"
    if sub:
        from datetime import datetime
        end = datetime.fromisoformat(sub["end_date"]).strftime("%d.%m.%Y")
        sub_text = f"✅ Faol (Tugash: {end})"

    text = (
        f"👤 <b>Haydovchi kabineti</b>\n\n"
        f"💰 Asosiy balans: {user.get('balance', 0):,} so'm\n"
        f"🎁 Bonus balans: {user.get('discount_balance', 0):,} so'm\n"
        f"📅 Obuna holati: {sub_text}\n"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=cabinet_keyboard("taxi"))


@router.callback_query(F.data == "subscription")
async def taxi_sub_menu(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    kb = await tariff_keyboard(user.get("discount_balance", 0))
    await call.message.edit_text("💳 <b>Obunani rasmiylashtirish yoki balansni to'ldirish:</b>\n\nTarif tanlang:", parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "history")
async def taxi_history(call: CallbackQuery):
    orders = await get_taxi_orders(call.from_user.id)
    if not orders:
        await call.answer("Olingan buyurtmalar topilmadi.")
        return

    text = "📜 <b>Oxirgi 20 ta buyurtmangiz:</b>\n"
    for o in orders:
        text += f"• {o['from_loc']} ➔ {o['to_loc']} | {o['price']} so'm\n"
    
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=back_to_cabinet())


@router.callback_query(F.data == "back_to_taxi")
async def back_to_taxi_cb(call: CallbackQuery):
    await call.message.delete()
    await call.answer()


@router.message(F.text == "🚪 Чиқиш")
async def exit_taxi(message: Message, state: FSMContext):
    from keyboards import role_keyboard
    await message.answer("Bosh menyuga qaytildi.", reply_markup=role_keyboard())
    await state.clear()

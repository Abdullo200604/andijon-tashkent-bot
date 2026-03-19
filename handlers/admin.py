from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from config import ADMIN_ID, TARIFFS
from database import (
    get_payment, update_payment_status, add_subscription, get_user,
    count_users_by_role, count_active_subscriptions, count_payments, count_orders
)

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ─── STATISTIKA ───────────────────────────────────────────────────────────────

@router.message(Command("stats"))
async def admin_stats(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Bu buyruq faqat admin uchun.")
        return

    clients = await count_users_by_role("client")
    taxis = await count_users_by_role("taxi")
    active_subs = await count_active_subscriptions()
    payments = await count_payments()
    orders = await count_orders()

    await message.answer(
        f"📊 <b>Bot statistikasi</b>\n\n"
        f"👤 Mijozlar: <b>{clients}</b>\n"
        f"🚕 Taxi haydovchilar: <b>{taxis}</b>\n"
        f"✅ Faol obunalar: <b>{active_subs}</b>\n"
        f"💳 Tasdiqlangan to'lovlar: <b>{payments}</b>\n"
        f"📦 Jami buyurtmalar: <b>{orders}</b>",
        parse_mode="HTML"
    )


# ─── TO'LOV TASDIQLASH ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("approve:"))
async def approve_payment(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id):
        await call.answer("❌ Ruxsatsiz!", show_alert=True)
        return

    payment_id = int(call.data.split(":")[1])
    payment = await get_payment(payment_id)

    if not payment:
        await call.answer("❌ To'lov topilmadi.", show_alert=True)
        return

    if payment["status"] != "pending":
        await call.answer("⚠️ Bu to'lov allaqachon ko'rib chiqilgan.", show_alert=True)
        return

    # To'lov tasdiqlash
    await update_payment_status(payment_id, "approved")

    # Obuna qo'shish
    tariff = TARIFFS.get(payment["tariff"])
    if tariff:
        await add_subscription(payment["user_id"], tariff["name"], tariff["days"])

    # Taxiga xabar
    try:
        from datetime import datetime, timedelta
        end_date = (datetime.now() + timedelta(days=tariff["days"])).strftime("%d.%m.%Y")
        await bot.send_message(
            payment["user_id"],
            f"✅ <b>Obunangiz faollashtirildi!</b>\n\n"
            f"📦 Tarif: {tariff['name']}\n"
            f"📅 Tugash sanasi: {end_date}\n\n"
            f"Endi buyurtma qabul qila olasiz! 🚕",
            parse_mode="HTML"
        )
    except Exception:
        pass

    # Admin xabarini yangilash
    await call.message.edit_text(
        call.message.text + "\n\n✅ <b>TASDIQLANGAN</b>",
        parse_mode="HTML"
    )
    await call.answer("✅ To'lov tasdiqlandi!")


@router.callback_query(F.data.startswith("reject:"))
async def reject_payment(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id):
        await call.answer("❌ Ruxsatsiz!", show_alert=True)
        return

    payment_id = int(call.data.split(":")[1])
    payment = await get_payment(payment_id)

    if not payment:
        await call.answer("❌ To'lov topilmadi.", show_alert=True)
        return

    if payment["status"] != "pending":
        await call.answer("⚠️ Bu to'lov allaqachon ko'rib chiqilgan.", show_alert=True)
        return

    await update_payment_status(payment_id, "rejected")

    # Taxiga xabar
    try:
        await bot.send_message(
            payment["user_id"],
            "❌ <b>To'lovingiz tasdiqlanmadi.</b>\n\n"
            "Sabab: To'lov topilmadi yoki noto'g'ri miqdor.\n\n"
            "Iltimos, qayta urinib ko'ring yoki admin bilan bog'laning.",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await call.message.edit_text(
        call.message.text + "\n\n❌ <b>RAD ETILGAN</b>",
        parse_mode="HTML"
    )
    await call.answer("❌ To'lov rad etildi.")


# ─── ADMIN PANELI ─────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Ruxsatsiz!")
        return

    await message.answer(
        "👑 <b>Admin paneli</b>\n\n"
        "/stats — Statistika\n"
        "/admin — Ushbu menyu\n\n"
        "To'lovlar avtomatik kelib tushadi — tasdiqlash uchun tugmalarni bosing.",
        parse_mode="HTML"
    )

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID
from database import (
    get_payment, update_payment_status, add_subscription, get_user,
    count_users_by_role, count_active_subscriptions, count_payments, count_orders,
    deduct_discount_balance, update_balance, get_tariffs, update_tariff,
    get_all_users, get_all_orders, get_stats_by_period, get_user_by_search, delete_subscription
)
from keyboards import admin_panel_keyboard, admin_payment_keyboard, admin_stats_keyboard, back_to_admin
from states import AdminState

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "👑 <b>Bosh admin paneli</b>\n\n"
        "Quyidagi bo'limlardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=admin_panel_keyboard()
    )


# ─── STATISTIKA ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_stats")
async def admin_stats_menu_callback(call: CallbackQuery):
    await call.message.edit_text(
        "📊 <b>Statistika bo'limi</b>\n\nDavrni tanlang:",
        parse_mode="HTML",
        reply_markup=admin_stats_keyboard()
    )
    await call.answer()


@router.callback_query(F.data.startswith("stats_"))
async def admin_stats_detail_callback(call: CallbackQuery):
    days = int(call.data.split("_")[1])
    stats = await get_stats_by_period(days)
    
    period_text = "Bugungi" if days == 1 else "Haftalik" if days == 7 else "Oylik"
    
    text = (
        f"📊 <b>{period_text} statistika</b> ({days} kun):\n\n"
        f"👤 Yangi foydalanuvchilar: <b>{stats['new_users']}</b>\n"
        f"📦 Yangi buyurtmalar: <b>{stats['new_orders']}</b>\n"
        f"💳 Tasdiqlangan to'lovlar: <b>{stats['payment_count']}</b>\n"
        f"💰 Umumiy tushum: <b>{stats['payment_sum']:,} so'm</b>"
    )
    
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_stats_keyboard())
    await call.answer()


# ─── BUYURTMALAR ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_orders")
async def admin_orders_list(call: CallbackQuery):
    orders = await get_all_orders(limit=15)
    if not orders:
        await call.answer("Buyurtmalar hali yo'q.")
        return

    text = "📦 <b>Oxirgi 15 ta buyurtma:</b>\n\n"
    for o in orders:
        status_icon = "✅" if o["status"] == "taken" else "⏳"
        text += f"{status_icon} #{o['id']} | {o['from_loc']} ➔ {o['to_loc']} | {o['price']} so'm\n"

    await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_panel_keyboard())
    await call.answer()


# ─── FOYDALANUVCHILARNI BOSHQARISH ──────────────────────────────────────────

@router.callback_query(F.data == "admin_users")
async def admin_users_menu(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.waiting_user_id)
    await call.message.edit_text(
        "🔍 Foydalanuvchini topish uchun uning <b>Telegram ID</b> sini yoki <b>Username</b> ini yozing (+ @ belgisi bilan):",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_cancel")]])
    )
    await call.answer()


@router.message(AdminState.waiting_user_id)
async def admin_find_user(message: Message, state: FSMContext):
    search = message.text.strip()
    user = await get_user_by_search(search)
    
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi. Qayta urinib ko'ring (ID yoki @username):")
        return

    user_dict = dict(user)
    await state.update_data(target_user_id=user_dict["telegram_id"])
    
    text = (
        f"👤 <b>Foydalanuvchi ma'lumoti</b>\n\n"
        f"ID: <code>{user_dict['telegram_id']}</code>\n"
        f"Ism: {user_dict['full_name']}\n"
        f"Username: @{user_dict['username'] if user_dict['username'] else '—'}\n"
        f"Telefon: {user_dict['phone']}\n"
        f"Rol: {user_dict['role']}\n"
        f"Asosiy Balans: {user_dict.get('balance', 0):,} so'm\n"
        f"Bonus Balans: {user_dict.get('discount_balance', 0):,} so'm\n"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Balansni o'zgartirish", callback_data="admin_edit_balance")],
        [InlineKeyboardButton(text="➕ 1 kunlik obuna", callback_data=f"admin_add_sub:1")],
        [InlineKeyboardButton(text="➕ 30 kunlik obuna", callback_data=f"admin_add_sub:30")],
        [InlineKeyboardButton(text="❌ Obunani o'chirish", callback_data="admin_del_sub")],
        [InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin_cancel")],
    ])
    
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "admin_edit_balance")
async def admin_pre_edit_balance(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.waiting_balance_amount)
    await call.message.answer("Summani yozing (masalan, 50000 qo'shish uchun <code>50000</code>, ayirish uchun <code>-10000</code>):", parse_mode="HTML")
    await call.answer()


@router.message(AdminState.waiting_balance_amount)
async def admin_apply_balance(message: Message, state: FSMContext):
    if not message.text.replace("-", "").isdigit():
        await message.answer("❌ Faqat raqam kiriting.")
        return
    
    amount = int(message.text)
    data = await state.get_data()
    target_id = data.get("target_user_id")
    
    await update_balance(target_id, amount)
    await message.answer(f"✅ Balans {amount:,} so'mga o'zgartirildi.", reply_markup=admin_panel_keyboard())
    await state.clear()


@router.callback_query(F.data.startswith("admin_add_sub:"))
async def admin_add_sub_manual(call: CallbackQuery, state: FSMContext):
    days = int(call.data.split(":")[1])
    data = await state.get_data()
    target_id = data.get("target_user_id")
    
    await add_subscription(target_id, f"Manual {days} kun", days)
    await call.message.answer(f"✅ Foydalanuvchiga {days} kunlik obuna berildi.")
    await call.answer()


@router.callback_query(F.data == "admin_del_sub")
async def admin_del_sub_handler(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    target_id = data.get("target_user_id")
    await delete_subscription(target_id)
    await call.message.answer("✅ Obuna o'chirildi (expired holatiga o'tkazildi).")
    await call.answer()


# ─── TARIFLARNI BOSHQARISH ──────────────────────────────────────────────

@router.callback_query(F.data == "admin_tariffs")
async def admin_tariffs_list(call: CallbackQuery):
    tariffs = await get_tariffs()
    text = "⚙️ <b>Tariflar narxini o'zgartirish:</b>\n\n"
    kb_btns = []
    for t in tariffs:
        text += f"• {t['name']}: {t['price']:,} so'm\n"
        kb_btns.append([InlineKeyboardButton(text=f"✏️ {t['name']} ni tahrirlash", callback_data=f"edit_t:{t['key']}")])
    
    kb_btns.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_cancel")])
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_btns))


@router.callback_query(F.data.startswith("edit_t:"))
async def admin_edit_tariff_start(call: CallbackQuery, state: FSMContext):
    key = call.data.split(":")[1]
    await state.update_data(edit_tariff_key=key)
    await state.set_state(AdminState.waiting_tariff_price)
    await call.message.answer(f"Ushbu tarif uchun yangi narxni kiriting (faqat raqam):")
    await call.answer()


@router.message(AdminState.waiting_tariff_price)
async def admin_apply_tariff_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Faqat raqam kiriting.")
        return
    
    price = int(message.text)
    data = await state.get_data()
    key = data.get("edit_tariff_key")
    
    tariffs = await get_tariffs()
    t = next((t for t in tariffs if t["key"] == key), None)
    if t:
        await update_tariff(key, price, t["days"])
        await message.answer(f"✅ {t['name']} narxi {price:,} so'mga o'zgartirildi.", reply_markup=admin_panel_keyboard())
    
    await state.clear()


# ─── TO'LOVLARNI TASDIQLASH (CALLBACKS FROM SUBSCRIPTION) ──────────────────

@router.callback_query(F.data.startswith("approve:"))
async def approve_payment_handler(call: CallbackQuery, bot: Bot):
    parts = call.data.split(":")
    payment_id = int(parts[1])
    used_discount = int(parts[2]) if len(parts) > 2 else 0
    
    payment = await get_payment(payment_id)
    if not payment or payment["status"] != "pending":
        await call.answer("⚠️ Bu to'lov ko'rib chiqilgan yoki topilmadi.", show_alert=True)
        return

    await update_payment_status(payment_id, "approved")
    
    if used_discount > 0:
        await deduct_discount_balance(payment["user_id"], used_discount)

    tariffs = await get_tariffs()
    t = next((t for t in tariffs if t["key"] == payment["tariff"]), None)
    if t:
        await add_subscription(payment["user_id"], t["name"], t["days"])
        # Taxiga xabar
        try:
            await bot.send_message(
                payment["user_id"],
                f"✅ <b>To'lovingiz tasdiqlandi!</b>\n\n📦 Tarif: {t['name']}\nEndi e'lon berishingiz mumkin! 🚕",
                parse_mode="HTML"
            )
        except: pass

    await call.message.edit_text(call.message.text + "\n\n✅ <b>TASDIQLANGAN (ID: " + str(payment_id) + ")</b>")
    await call.answer("Tasdiqlandi!")


@router.callback_query(F.data.startswith("reject:"))
async def reject_payment_handler(call: CallbackQuery, bot: Bot):
    payment_id = int(call.data.split(":")[1])
    payment = await get_payment(payment_id)
    if payment:
        await update_payment_status(payment_id, "rejected")
        try:
            await bot.send_message(payment["user_id"], "❌ To'lovingiz rad etildi.")
        except: pass
    await call.message.edit_text(call.message.text + "\n\n❌ <b>RAD ETILDI</b>")
    await call.answer("Rad etildi.")


@router.callback_query(F.data == "admin_cancel")
async def admin_cancel_handler(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Bosh admin paneli", reply_markup=admin_panel_keyboard())
    await call.answer()

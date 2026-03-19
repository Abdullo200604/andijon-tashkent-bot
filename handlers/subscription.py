from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, LabeledPrice, PreCheckoutQuery, Message

from config import TARIFFS, CARD_NUMBER, CARD_NAME, ADMIN_ID, CLICK_TOKEN
from database import get_user, create_payment, get_active_subscription, add_subscription, update_payment_status
from keyboards import payment_confirm_keyboard, tariff_keyboard, subscription_keyboard

router = Router()


@router.callback_query(F.data.startswith("tariff:"))
async def tariff_selected(call: CallbackQuery):
    """Tarif tanlandi — to'lov usulini tanlash"""
    tariff_key = call.data.split(":")[1]
    tariff = TARIFFS.get(tariff_key)

    if not tariff:
        await call.answer("❌ Noto'g'ri tarif.", show_alert=True)
        return

    text = (
        f"📦 <b>Siz tanladingiz: {tariff['name']}</b>\n"
        f"💰 Narxi: {tariff['price']:,} so'm\n\n"
        f"To'lov usulini tanlang:"
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 CLICK (Avtomatik)", callback_data=f"pay_click:{tariff_key}")],
        [InlineKeyboardButton(text="🏦 Karta orqali (Manual)", callback_data=f"pay_manual:{tariff_key}")],
        [InlineKeyboardButton(text="🔙 Орқа", callback_data="back_to_tariff")],
    ])

    await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await call.answer()


@router.callback_query(F.data.startswith("pay_click:"))
async def pay_click(call: CallbackQuery, bot: Bot):
    """Click orqali hisob (Invoice) yuborish"""
    tariff_key = call.data.split(":")[1]
    tariff = TARIFFS.get(tariff_key)

    if not CLICK_TOKEN:
        await call.answer("❌ Click to'lov tizimi vaqtinchalik ishlamayapti.", show_alert=True)
        return

    await bot.send_invoice(
        chat_id=call.from_user.id,
        title=f"Obuna: {tariff['name']}",
        description=f"Taxi Bot uchun {tariff['name']}lik obuna",
        payload=f"sub_{tariff_key}",
        provider_token=CLICK_TOKEN,
        currency="UZS",
        prices=[
            LabeledPrice(label=tariff['name'], amount=tariff['price'] * 100)  # Tiynlarda
        ],
        start_parameter="taxi_subscription",
    )
    await call.answer()


@router.callback_query(F.data.startswith("pay_manual:"))
async def pay_manual(call: CallbackQuery):
    """Manual to'lov (karta orqali) ko'rsatmalari"""
    tariff_key = call.data.split(":")[1]
    tariff = TARIFFS.get(tariff_key)

    payment_id = await create_payment(call.from_user.id, tariff_key, tariff["price"])

    text = (
        f"🏦 <b>Karta orqali to'lov (Manual)</b>\n\n"
        f"📦 Tarif: {tariff['name']}\n"
        f"💰 Summa: {tariff['price']:,} so'm\n\n"
        f"💳 Karta raqami: <code>{CARD_NUMBER}</code>\n"
        f"👤 Ism: <b>{CARD_NAME}</b>\n\n"
        f"❗ To'lovdan so'ng <b>\"To'lov qildim\"</b> tugmasini bosing."
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ To'lov qildim", callback_data=f"payment_done:{payment_id}")],
        [InlineKeyboardButton(text="🔙 Орқа", callback_data="back_to_tariff")],
    ])

    await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await call.answer()


# ─── TO'LOV HANDLERLARI (INVOICE) ─────────────────────────────────────────────

@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    """To'lovdan oldingi tekshiruv"""
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message):
    """Muvaffaqiyatli to'lovdan keyin obunani faollashtirish"""
    payment = message.successful_payment
    payload = payment.invoice_payload  # "sub_1_month"

    tariff_key = payload.replace("sub_", "")
    tariff = TARIFFS.get(tariff_key)

    if tariff:
        # Obunani qo'shish
        await add_subscription(message.from_user.id, tariff["name"], tariff["days"])

        from datetime import datetime, timedelta
        end_date = (datetime.now() + timedelta(days=tariff["days"])).strftime("%d.%m.%Y")

        await message.answer(
            f"💰 <b>To'lov qabul qilindi!</b>\n\n"
            f"✅ Obunangiz faollashtirildi.\n"
            f"📅 Tugash sanasi: {end_date}\n\n"
            f"Tabriklaymiz! Endi buyurtmalar bilan ishlashingiz mumkin. 🚕",
            parse_mode="HTML"
        )

        # Adminni ham xabardor qilish
        # (Ixtiyoriy: admin panelga ham yozish mumkin)


@router.callback_query(F.data.startswith("payment_done:"))
async def payment_done(call: CallbackQuery, bot: Bot):
    """Foydalanuvchi to'lov qildim dedi — adminga xabar"""
    payment_id = int(call.data.split(":")[1])

    from database import get_payment
    payment = await get_payment(payment_id)
    if not payment:
        await call.answer("❌ To'lov topilmadi.", show_alert=True)
        return

    tariff = TARIFFS.get(payment["tariff"], {})
    user = await get_user(call.from_user.id)
    username = f"@{user['username']}" if user and user["username"] else "—"

    from keyboards import admin_payment_keyboard
    text = (
        f"💳 <b>Yangi to'lov so'rovi</b>\n\n"
        f"👤 Foydalanuvchi: {call.from_user.full_name}\n"
        f"📱 Username: {username}\n"
        f"🆔 ID: <code>{call.from_user.id}</code>\n\n"
        f"📦 Tarif: {tariff.get('name', payment['tariff'])}\n"
        f"💰 Summa: {payment['amount']:,} so'm"
    )

    try:
        await bot.send_message(
            ADMIN_ID,
            text,
            parse_mode="HTML",
            reply_markup=admin_payment_keyboard(payment_id)
        )
    except Exception as e:
        await call.message.edit_text(
            f"❌ Admin bilan bog'lanishda xato: {e}\n"
            "Iltimos, to'lov chekini adminga yuboring."
        )
        return

    await call.message.edit_text(
        "✅ <b>So'rovingiz adminga yuborildi!</b>\n\n"
        "⏳ Admin tasdiqlashidan so'ng obunangiz faollashadi.\n"
        "Odatda 5-30 daqiqa ichida tasdiqlanadi.",
        parse_mode="HTML"
    )
    await call.answer("✅ So'rov yuborildi!")


@router.callback_query(F.data == "back_to_tariff")
async def back_to_tariff(call: CallbackQuery):
    await call.message.edit_text(
        "💳 Tarif tanlang:",
        reply_markup=tariff_keyboard()
    )
    await call.answer()

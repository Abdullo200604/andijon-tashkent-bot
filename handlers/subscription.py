from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, LabeledPrice, PreCheckoutQuery, Message

from config import TARIFFS, CARD_NUMBER, CARD_NAME, ADMIN_ID, CLICK_TOKEN
from database import get_user, create_payment, get_active_subscription, add_subscription, update_payment_status
from keyboards import payment_confirm_keyboard, tariff_keyboard, subscription_keyboard

router = Router()


@router.callback_query(F.data.startswith("tariff:"))
async def tariff_selected(call: CallbackQuery):
    """Tarif tanlandi — manual to'lov (karta orqali) ko'rsatmalari"""
    tariff_key = call.data.split(":")[1]
    tariff = TARIFFS.get(tariff_key)

    if not tariff:
        await call.answer("❌ Noto'g'ri tarif.", show_alert=True)
        return

    user = await get_user(call.from_user.id)
    discount_balance = user.get("discount_balance", 0)

    text = (
        f"📦 <b>Siz tanladingiz: {tariff['name']}</b>\n"
        f"💰 Asosiy narxi: {tariff['price']:,} so'm\n"
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard_buttons = []

    if discount_balance > 0:
        amount_to_pay = max(0, tariff["price"] - discount_balance)
        text += (
            f"🎁 <b>Sizning chegirma bonusingiz:</b> {discount_balance:,} so'm\n"
            f"✅ <b>Chegirma bilan to'lashingiz kerak:</b> {amount_to_pay:,} so'm\n\n"
        )
        keyboard_buttons.append([InlineKeyboardButton(text=f"🎁 Chegirma orqali to'ladim ({amount_to_pay:,})", callback_data=f"pay_disc:{tariff_key}")])
        keyboard_buttons.append([InlineKeyboardButton(text=f"💳 To'liq narxda to'ladim ({tariff['price']:,})", callback_data=f"pay_full:{tariff_key}")])
    else:
        text += "\n"
        keyboard_buttons.append([InlineKeyboardButton(text="✅ To'lov qildim", callback_data=f"pay_full:{tariff_key}")])

    text += (
        f"💳 Karta raqami: <code>{CARD_NUMBER}</code>\n"
        f"👤 Ism: <b>{CARD_NAME}</b>\n\n"
        f"❗ To'lovdan so'ng tegishli tugmani bosing va to'lov chekini (skrinshot) adminga yuboring."
    )

    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Орқа", callback_data="back_to_tariff")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await call.answer()


@router.callback_query(F.data.startswith("pay_full:") | F.data.startswith("pay_disc:"))
async def payment_done(call: CallbackQuery, bot: Bot):
    """Foydalanuvchi to'lov qildim dedi — adminga xabar va to'lovni bazaga qo'shish"""
    action, tariff_key = call.data.split(":")
    tariff = TARIFFS.get(tariff_key)
    if not tariff:
        await call.answer("❌ Xatolik.", show_alert=True)
        return

    user = await get_user(call.from_user.id)
    discount_balance = user.get("discount_balance", 0)

    amount = tariff["price"]
    used_discount = 0

    if action == "pay_disc" and discount_balance > 0:
        used_discount = min(discount_balance, amount)
        amount = max(0, amount - discount_balance)
        # We don't deduct immediately, admin must approve first.
        # But we need a way to store how much discount was requested.
        # We can store negative amount in db or similar. 
        # Actually, let's just deduct it when approved.

    # Save payment to DB
    payment_id = await create_payment(call.from_user.id, tariff_key, amount)

    # Admin xabari
    username = f"@{user['username']}" if user and user.get("username") else "—"
    from keyboards import admin_payment_keyboard
    
    discount_text = f"\n🎁 Ishlatilgan chegirma: {used_discount:,} so'm" if used_discount > 0 else ""

    text = (
        f"💳 <b>Yangi to'lov so'rovi</b>\n\n"
        f"👤 Foydalanuvchi: {call.from_user.full_name}\n"
        f"📱 Username: {username}\n"
        f"📞 Telefon: {user.get('phone', '—')}\n"
        f"🆔 ID: <code>{call.from_user.id}</code>\n\n"
        f"📦 Tarif: {tariff['name']}\n"
        f"💰 Kutilayotgan summa: {amount:,} so'm{discount_text}\n\n"
        f"❗ <i>Eslatma: Tasdiqlansa, agar chegirma ishlatilgan bo'lsa, balansdan yechiladi.</i>"
    )

    try:
        await bot.send_message(
            ADMIN_ID,
            text,
            parse_mode="HTML",
            # We pass action so admin knows if disc was used
            reply_markup=admin_payment_keyboard(payment_id, used_discount)
        )
    except Exception as e:
        await call.message.edit_text(
            f"❌ Admin bilan bog'lanishda xato.\n"
            "Iltimos, to'lov chekini bevosita adminga yuboring."
        )
        return

    await call.message.edit_text(
        "✅ <b>So'rovingiz adminga yuborildi!</b>\n\n"
        "⏳ Admin tasdiqlashidan so'ng obunangiz faollashadi.\n"
        "Odatda 5-30 daqiqa ichida tasdiqlanadi.",
        parse_mode="HTML"
    )
    await call.answer("✅ So'rov yuborildi!")    text = (
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

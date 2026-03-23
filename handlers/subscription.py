from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, LabeledPrice, PreCheckoutQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import CARD_NUMBER, CARD_NAME, ADMIN_ID
from database import get_user, create_payment, get_tariffs, update_payment_status, add_subscription, update_balance, deduct_discount_balance
from keyboards import tariff_keyboard

router = Router()


@router.callback_query(F.data.startswith("tariff:"))
async def tariff_selected(call: CallbackQuery):
    """Tarif tanlandi — manual to'lov (karta orqali) ko'rsatmalari"""
    tariff_key = call.data.split(":")[1]
    tariffs = await get_tariffs()
    tariff = next((t for t in tariffs if t["key"] == tariff_key), None)

    if not tariff:
        await call.answer("❌ Noto'g'ri tarif.", show_alert=True)
        return

    user = await get_user(call.from_user.id)
    user_dict = dict(user)
    discount_balance = user_dict.get("discount_balance", 0)
    balance = user_dict.get("balance", 0)

    text = (
        f"📦 <b>Siz tanladingiz: {tariff['name']}</b>\n"
        f"💰 Asosiy narxi: {tariff['price']:,} so'm\n\n"
        f"👤 Sizning balansingiz: {balance:,} so'm\n"
        f"🎁 Sizning bonusingiz: {discount_balance:,} so'm\n\n"
    )

    keyboard_buttons = []
    
    # 1. Balansdan to'lash (agar yetsa)
    total_available = balance + discount_balance
    if total_available >= tariff["price"]:
        keyboard_buttons.append([InlineKeyboardButton(text="💎 Balansdan darhol sotib olish", callback_data=f"buy_balance:{tariff_key}")])
    
    # 2. Karta orqali to'lov variantlari
    if discount_balance > 0:
        amount_to_pay = max(0, tariff["price"] - discount_balance)
        text += (
            f"✅ <b>Bonusingizni chegirib to'lashingiz kerak:</b> {amount_to_pay:,} so'm\n"
        )
        keyboard_buttons.append([InlineKeyboardButton(text=f"🎁 Chegirma orqali to'ladim ({amount_to_pay:,} so'm)", callback_data=f"pay_disc:{tariff_key}")])
        keyboard_buttons.append([InlineKeyboardButton(text=f"💳 To'liq narxda to'ladim ({tariff['price']:,} so'm)", callback_data=f"pay_full:{tariff_key}")])
    else:
        keyboard_buttons.append([InlineKeyboardButton(text="✅ To'lov qildim (Chekni yuborish)", callback_data=f"pay_full:{tariff_key}")])

    text += (
        f"\n💳 Karta raqami: <code>{CARD_NUMBER}</code>\n"
        f"👤 Ism: <b>{CARD_NAME}</b>\n\n"
        f"❗ To'lovdan so'ng tegishli tugmani bosing va to'lov chekini (skrinshot) adminga yuboring."
    )

    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_tariff")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await call.answer()


@router.callback_query(F.data.startswith("pay_full:") | F.data.startswith("pay_disc:"))
async def payment_request(call: CallbackQuery, bot: Bot):
    """Foydalanuvchi to'lov qildim dedi — adminga xabar va to'lovni bazaga qo'shish"""
    action, tariff_key = call.data.split(":")
    tariffs = await get_tariffs()
    tariff = next((t for t in tariffs if t["key"] == tariff_key), None)
    
    if not tariff:
        await call.answer("❌ Xatolik.", show_alert=True)
        return

    user = await get_user(call.from_user.id)
    discount_balance = dict(user).get("discount_balance", 0)

    amount = tariff["price"]
    used_discount = 0

    if action == "pay_disc" and discount_balance > 0:
        used_discount = min(discount_balance, amount)
        amount = max(0, amount - used_discount)

    # Save payment to DB
    payment_id = await create_payment(call.from_user.id, tariff_key, amount)

    # Admin xabari
    username = f"@{user_dict.get('username')}" if user_dict.get("username") else "—"
    from keyboards import admin_payment_keyboard
    
    discount_text = f"\n🎁 Ishlatilgan chegirma: {used_discount:,} so'm" if used_discount > 0 else ""

    text = (
        f"💳 <b>Yangi to'lov so'rovi</b>\n\n"
        f"👤 Foydalanuvchi: {call.from_user.full_name}\n"
        f"📱 Username: {username}\n"
        f"📞 Telefon: {user_dict.get('phone', '—')}\n"
        f"🆔 ID: <code>{call.from_user.id}</code>\n\n"
        f"📦 Tarif: {tariff['name']}\n"
        f"💰 Kutilayotgan summa: {amount:,} so'm{discount_text}\n\n"
        f"❗ <i>Eslatma: Tasdiqlansa, agar bonus ishlatilgan bo'lsa, avtomatik yechiladi.</i>"
    )

    try:
        await bot.send_message(
            ADMIN_ID,
            text,
            parse_mode="HTML",
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
    await call.answer("✅ So'rov yuborildi!")


@router.callback_query(F.data.startswith("buy_balance:"))
async def buy_with_balance(call: CallbackQuery):
    """Balans orqali sotib olish (Admin aralashuvisiz)"""
    tariff_key = call.data.split(":")[1]
    tariffs = await get_tariffs()
    tariff = next((t for t in tariffs if t["key"] == tariff_key), None)
    
    if not tariff:
        return
    
    user = await get_user(call.from_user.id)
    user_dict = dict(user)
    balance = user_dict.get("balance", 0)
    discount_balance = user_dict.get("discount_balance", 0)
    
    price = tariff["price"]
    
    if (balance + discount_balance) < price:
        await call.answer("❌ Balans yetarli emas.", show_alert=True)
        return
    
    # Avval bonusdan yechamiz
    used_discount = min(discount_balance, price)
    remaining_price = price - used_discount
    
    if used_discount > 0:
        await deduct_discount_balance(call.from_user.id, used_discount)
    
    if remaining_price > 0:
        await update_balance(call.from_user.id, -remaining_price)
        
    await add_subscription(call.from_user.id, tariff_key, tariff["days"])
    
    await call.message.edit_text(
        f"🎉 <b>Tabriklaymiz!</b>\n\n"
        f"Sizning <b>{tariff['name']}</b> obunangiz muvaffaqiyatli faollashtirildi!\n"
        f"Endi bemalol e'lon berishingiz mumkin.",
        parse_mode="HTML"
    )
    await call.answer("✅ Obuna faollashdi!")


@router.callback_query(F.data == "back_to_tariff")
async def back_to_tariff(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    kb = await tariff_keyboard(dict(user).get("discount_balance", 0))
    await call.message.edit_text(
        "💳 Tarif tanlang:",
        reply_markup=kb
    )
    await call.answer()

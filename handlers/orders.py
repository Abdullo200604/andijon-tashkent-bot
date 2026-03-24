from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import random
import logging

from database import get_user, get_order, take_order, get_active_subscription
from keyboards import order_taken_keyboard
from handlers.client import active_order_messages

router = Router()


@router.callback_query(F.data.startswith("take:"))
async def take_order_cb(call: CallbackQuery, bot: Bot):
    """Taxi buyurtmani qabul qiladi — faqat birinchi bosgan oladi"""
    order_id = int(call.data.split(":")[1])
    taxi_id = call.from_user.id

    # Faqat faol obunali taxilar olsin
    sub = await get_active_subscription(taxi_id)
    if not sub:
        await call.answer(
            "❌ Sizning obunangiz faol emas! 💳 Obuna bo'lish uchun Kabinet bo'limini ko'ring.",
            show_alert=True
        )
        return

    # Atomik olish — birinchi bosgan oladi
    success = await take_order(order_id, taxi_id)

    if not success:
        await call.answer("⛔ Kechirasiz, bu buyurtmani boshqa haydovchi oldi!", show_alert=True)
        try:
            await call.message.edit_reply_markup(reply_markup=order_taken_keyboard())
        except: pass
        return

    # Taxi ma'lumotlari
    taxi_user = await get_user(taxi_id)
    taxi_name = taxi_user["full_name"] if taxi_user else "Taxi"
    taxi_username = f"@{taxi_user['username']}" if taxi_user and taxi_user["username"] else "—"

    # Buyurtma ma'lumotlari
    order = await get_order(order_id)
    if not order:
        await call.answer("❌ Buyurtma topilmadi.")
        return

    # Mijozga taxi ma'lumotlarini yuborish
    try:
        await bot.send_message(
            order["client_id"],
            f"✅ <b>Taxi topildi!</b>\n\n"
            f"🚕 Haydovchi: {taxi_name}\n"
            f"📱 Telegram: {taxi_username}\n\n"
            f"👤 Yo'lovchilar: {order['passengers']}\n"
            f"📍 Marshrut: {order['from_loc']} → {order['to_loc']}\n"
            f"🕒 Vaqt: {order['order_time']}\n"
            f"💰 Narx: {order['price']}",
            parse_mode="HTML"
        )
        
        # CHEGIRMA MANTIG'I (Milestone-based)
        milestones = [1, 100, 1000, 10000, 100000, 1000000]
        if order_id in milestones:

            rand = random.randint(1, 100)
            if rand <= 70:
                discount_percent = random.randint(1, 5)
            elif rand <= 90:
                discount_percent = random.randint(5, 7)
            else:
                discount_percent = random.randint(7, 10)
                
            markup = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="📝 Kelishilgan narxni yozish", 
                    callback_data=f"disc_price:{discount_percent}:{taxi_id}"
                )
            ]])
            
            await bot.send_message(
                order["client_id"],
                f"🎉 <b>TABRIKLAYMIZ!</b>\n\nSiz botimizdagi <b>{order_id}-buyurtma</b> egasisiz! 🏆\n\n"
                f"Shu sababli sizga <b>{discount_percent}% chegirma</b> taqdim etiladi! 🎁\n\n"
                f"Haydovchi bilan yakuniy narxni kelishganingizdan so'ng, "
                f"pastdagi tugmani bosib narxni kiriting va biz chegirmangizni hisoblab beramiz.",
                reply_markup=markup,
                parse_mode="HTML"
            )
    except Exception as e:
        logging.error(f"Error in taxi-to-client notice: {e}")

    # Mijoz ma'lumotlari (username uchun)
    client_user = await get_user(order["client_id"])
    client_username = f"@{client_user['username']}" if client_user and client_user["username"] else "—"
    
    # Lokatsiya linki
    loc_link = ""
    if order.get("latitude") and order.get("longitude"):
        loc_link = f"\n📍 <a href='https://www.google.com/maps?q={order['latitude']},{order['longitude']}'>Xaritada ko'rish</a>"

    # Haydovchiga mijoz raqamini va lakatsiyasini yuborish
    await call.message.edit_text(
        f"✅ <b>Buyurtma sizniki!</b>\n\n"
        f"📞 Tel: {order['contact_phone'] or order['phone']}\n"
        f"👤 Telegram: {client_username}\n"
        f"👥 Yo'lovchilar: {order['passengers']}\n"
        f"📍 {order['from_loc']} → {order['to_loc']}{loc_link}\n\n"
        f"Mijoz bilan bog'laning.",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

    if order.get("latitude") and order.get("longitude"):
        try:
            await bot.send_location(taxi_id, latitude=order["latitude"], longitude=order["longitude"])
        except: pass
        
    await call.answer("✅ Buyurtma biriktirildi!")

    # Boshqa taxilarga xabar berish — buyurtma olindi
    if order_id in active_order_messages:
        for other_taxi_id, msg_id in active_order_messages[order_id].items():
            if other_taxi_id != taxi_id:
                try:
                    await bot.edit_message_text(f"⛔ Buyurtma #{order_id} olingan.", chat_id=other_taxi_id, message_id=msg_id)
                except: pass
        del active_order_messages[order_id]


@router.callback_query(F.data.startswith("decline:"))
async def decline_order_cb(call: CallbackQuery):
    await call.message.delete()
    await call.answer("❌ Buyurtma rad etildi.")


@router.callback_query(F.data == "already_taken")
async def already_taken_cb(call: CallbackQuery):
    await call.answer("⛔ Bu buyurtma allaqachon olingan.", show_alert=True)

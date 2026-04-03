from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import random
import logging

from database import (
    get_user, get_order, take_order, get_active_subscription,
    get_driver_location, log_analytics, reset_order_to_pending,
    cancel_order_db, log_cancellation
)
from keyboards import order_taken_keyboard, driver_order_actions, cancel_reason_keyboard, client_menu
from config import DRIVER_LOCATION_MAX_AGE
from states import CancelForm
from aiogram.fsm.context import FSMContext

router = Router()

# Aktiv buyurtmalar xabarlari (client.py dagi dict ga havola)
from handlers.client import active_order_messages


@router.callback_query(F.data.startswith("take:"))
async def take_order_cb(call: CallbackQuery, bot: Bot):
    """Taxi buyurtmani qabul qiladi — faqat birinchi bosgan oladi"""
    order_id = int(call.data.split(":")[1])
    taxi_id = call.from_user.id

    # Haydovchi lokatsiyasini tekshirish
    loc = await get_driver_location(taxi_id)
    if not loc or loc["age_sec"] > DRIVER_LOCATION_MAX_AGE:
        await call.answer("❌ Joylashuv yuborilmadi — qabul qilib bo'lmadi", show_alert=True)
        await log_analytics("driver_accept_fail_location", taxi_id, order_id)
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
    loc_link = f"\n📍 <a href='https://www.google.com/maps?q={order['latitude']},{order['longitude']}'>Xaritada ko'rish</a>" if order.get("latitude") and order.get("longitude") else ""

    # Haydovchiga mijoz raqamini va lakatsiyasini yuborish
    await call.message.edit_text(
        f"✅ <b>Buyurtma sizniki!</b>\n\n"
        f"📞 Tel: {order['contact_phone'] or order['phone']}\n"
        f"👤 Telegram: {client_username}\n"
        f"👤 Jins: {order['gender']}\n"
        f"👥 Yo'lovchilar: {order['passengers']}\n"
        f"📍 {order['from_loc']} → {order['to_loc']}{loc_link}\n\n"
        f"Mijoz bilan bog'laning.",
        parse_mode="HTML",
        reply_markup=driver_order_actions(order_id),
        disable_web_page_preview=True
    )

    if order.get("latitude") and order.get("longitude"):
        try:
            await bot.send_location(taxi_id, latitude=order["latitude"], longitude=order["longitude"])
        except: pass
        
    await call.answer("✅ Buyurtma biriktirildi!")
    await log_analytics("order_assigned", taxi_id, order_id)

    # Boshqa taxilarga xabar berish — buyurtma olindi
    if order_id in active_order_messages:
        for other_taxi_id, msg_id in active_order_messages[order_id].items():
            if other_taxi_id != taxi_id:
                try:
                    await bot.edit_message_text(f"⛔ Buyurtma #{order_id} olingan.", chat_id=other_taxi_id, message_id=msg_id)
                except: pass
        del active_order_messages[order_id]


@router.callback_query(F.data.startswith("driver_cancel:"))
async def driver_cancel_order(call: CallbackQuery, state: FSMContext):
    order_id = int(call.data.split(":")[1])
    await state.update_data(cancel_order_id=order_id)
    await state.set_state(CancelForm.reason_choice)
    await call.message.answer("📦 Safarni bekor qilish sababini tanlang:", reply_markup=cancel_reason_keyboard("taxi"))
    await call.answer()


@router.callback_query(CancelForm.reason_choice, F.data.startswith("cancel_res:"))
async def process_driver_cancel_reason(call: CallbackQuery, state: FSMContext, bot: Bot):
    reason_key = call.data.split(":")[1]
    data = await state.get_data()
    order_id = data.get("cancel_order_id")
    
    if reason_key == "other":
        await state.set_state(CancelForm.reason_text)
        await call.message.answer("📝 Iltimos, bekor qilish sababini yozing:")
        await call.answer()
        return

    reason_map = {"traffic": "Yo'l yopiq/Tirbandlik", "time": "Vaqt mos emas", "no_answer": "Mijoz javob bermadi"}
    reason = reason_map.get(reason_key, "Boshqa")
    await finalize_driver_cancellation(call.message, state, bot, order_id, reason)
    await call.answer("Bekor qilindi.")


@router.message(CancelForm.reason_text)
async def process_driver_cancel_text(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    order_id = data.get("cancel_order_id")
    await finalize_driver_cancellation(message, state, bot, order_id, message.text)


async def finalize_driver_cancellation(message, state, bot, order_id, reason):
    from database import log_cancellation, cancel_order_db, reset_order_to_pending, get_order
    from handlers.client import broadcast_order
    
    user_id = message.chat.id
    order = await get_order(order_id)
    
    await cancel_order_db(order_id, "driver", reason) # Log old state
    await log_cancellation(user_id, "taxi", order_id, reason)
    await log_analytics("driver_cancel", user_id, order_id, {"reason": reason})
    
    # Qayta pending qilib broadcast qilish
    await reset_order_to_pending(order_id)
    await log_analytics("order_rebroadcasted", None, order_id, {"reason_by_driver": reason})
    
    await state.clear()
    await bot.send_message(user_id, f"✅ Safar bekor qilindi va qayta qidiruvga berildi.", reply_markup=client_menu())
    
    # Mijozga xabar berish
    if order:
        try:
            await bot.send_message(order["client_id"], "🚕 Haydovchi safaringizni bekor qildi. Qayta haydovchi qidirilmoqda...")
        except: pass

    # Qayta barcha haydovchilarga yuborish
    await broadcast_order(bot, order_id)


@router.callback_query(F.data.startswith("decline:"))
async def decline_order_cb(call: CallbackQuery):
    await call.message.delete()
    await call.answer("❌ Buyurtma rad etildi.")


@router.callback_query(F.data == "already_taken")
async def already_taken_cb(call: CallbackQuery):
    await call.answer("⛔ Bu buyurtma allaqachon olingan.", show_alert=True)

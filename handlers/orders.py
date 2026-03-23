from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

from database import get_user, get_order, take_order
from keyboards import order_taken_keyboard, client_menu
from handlers.client import active_order_messages

router = Router()


@router.callback_query(F.data.startswith("take:"))
async def take_order_cb(call: CallbackQuery, bot: Bot):
    """Taxi buyurtmani qabul qiladi — faqat birinchi bosgan oladi"""
    order_id = int(call.data.split(":")[1])
    taxi_id = call.from_user.id

    # Faqat faol obunali taxilar olsin
    from database import get_active_subscription
    sub = await get_active_subscription(taxi_id)
    if not sub:
        await call.answer(
            "❌ Sizning obunangiz faol emas! 💳 Obuna bo'lish uchun menyuni oching.",
            show_alert=True
        )
        return

    # Atomik olish — birinchi bosgan oladi
    success = await take_order(order_id, taxi_id)

    if not success:
        await call.answer("⛔ Kechirasiz, bu buyurtmani boshqa haydovchi oldi!", show_alert=True)
        try:
            await call.message.edit_reply_markup(reply_markup=order_taken_keyboard())
        except Exception:
            pass
        return

    # Taxi ma'lumotlari
    taxi_user = await get_user(taxi_id)
    taxi_name = taxi_user["full_name"] if taxi_user else "Taxi"
    taxi_username = f"@{taxi_user['username']}" if taxi_user and taxi_user["username"] else "—"

    # Buyurtma ma'lumotlari
    order = await get_order(order_id)

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
        
        # CHEGIRMA MANTIG'I (Milestone)
        import random
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        milestones = [1, 100, 1000, 10000, 100000, 1000000]
        if order_id in milestones:
            rand = random.randint(1, 100)
            if rand <= 70:
                discount_percent = random.randint(1, 5)
            elif rand <= 90:
                discount_percent = random.randint(6, 7)
            else:
                discount_percent = random.randint(8, 10)
                
            markup = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="📝 Kelishilgan narxni yozish", 
                    callback_data=f"disc_price:{discount_percent}:{taxi_id}"
                )
            ]])
            
            await bot.send_message(
                order["client_id"],
                f"🎉 <b>Tabriklaymiz!</b> Siz bizning botimizda {order_id}-buyurtma egasisiz!\n\n"
                f"Shu sababli sizga <b>{discount_percent}% chegirma</b> taqdim etiladi! 🎁\n\n"
                f"Haydovchi bilan yakuniy narxni kelishganingizdan so'ng, "
                f"pastdagi tugmani bosib narxni kiriting va biz sizga chegirmangizni hisoblab beramiz.",
                reply_markup=markup,
                parse_mode="HTML"
            )
    except Exception:
        pass

    # Haydovchiga mijoz raqamini va lakatsiyasini yuborish
    await call.message.edit_text(
        f"✅ <b>Buyurtma sizniki!</b>\n\n"
        f"📞 Mijoz: {order['phone']}\n"
        f"👤 Yo'lovchilar: {order['passengers']}\n"
        f"📍 {order['from_loc']} → {order['to_loc']}\n\n"
        f"Mijoz bilan bog'laning.",
        parse_mode="HTML"
    )


    # Agar lakatsiya (koordinatalar) bo'lsa, uni ham yuborish
    if order.get("latitude") and order.get("longitude"):
        await call.message.answer_location(
            latitude=order["latitude"],
            longitude=order["longitude"]
        )
    await call.answer("✅ Buyurtma sizga biriktirildi!")

    # Boshqa taxilarga xabar berish — buyurtma olindi
    if order_id in active_order_messages:
        for other_taxi_id, msg_id in active_order_messages[order_id].items():
            if other_taxi_id == taxi_id:
                continue
            try:
                await bot.edit_message_text(
                    f"⛔ Buyurtma #{order_id} boshqa haydovchi tomonidan olindi.",
                    chat_id=other_taxi_id,
                    message_id=msg_id
                )
            except Exception:
                pass
        del active_order_messages[order_id]


@router.callback_query(F.data.startswith("decline:"))
async def decline_order_cb(call: CallbackQuery):
    """Taxi buyurtmani rad etadi — faqat o'zidan o'chadi"""
    await call.message.delete()
    await call.answer("❌ Buyurtma rad etildi.")


@router.callback_query(F.data == "already_taken")
async def already_taken_cb(call: CallbackQuery):
    await call.answer("⛔ Bu buyurtma allaqachon olingan.", show_alert=True)

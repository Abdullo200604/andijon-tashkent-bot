from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import get_user, upsert_user, save_user_phone
from keyboards import role_keyboard, client_menu, taxi_menu, phone_request_keyboard
from states import RegisterForm

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Bot boshlash — ro'yxatdan o'tish yoki rol tanlash"""
    await state.clear()
    user = await get_user(message.from_user.id)

    # Ildiz xatolikni oldini olish uchun: agar user bazada bo'lsa-yu, phone bo'lmasa -> ro'yxatdan o'tish
    user_dict = dict(user) if user else {}
    if not user or not user_dict.get("phone"):
        await state.set_state(RegisterForm.phone)
        await message.answer(
            "👋 Assalomu alaykum!\n\n"
            "Botdan foydalanish uchun, iltimos, telefon raqamingizni yuboring:",
            reply_markup=phone_request_keyboard()
        )
        return

    # Agar phone bo'lsa-yu, roli bo'lmasa -> rol tanlash
    if not user_dict.get("role"):
        await message.answer(
            "Iltimos, rolingizni tanlang:",
            reply_markup=role_keyboard()
        )
        return

    # Agar hammasi joyida bo'lsa -> menyu
    if user_dict["role"] == "client":
        await message.answer(
            "👋 Xush kelibsiz, Mijoz!\n\n"
            "Taksi chaqirish uchun tugmani bosing:",
            reply_markup=client_menu()
        )
    elif user_dict["role"] == "taxi":
        await message.answer(
            "🚕 Taxi paneliga xush kelibsiz!",
            reply_markup=taxi_menu()
        )

@router.message(RegisterForm.phone, F.contact)
async def process_phone(message: Message, state: FSMContext):
    """Raqam qabul qilish"""
    phone = message.contact.phone_number
    await save_user_phone(
        telegram_id=message.from_user.id,
        phone=phone,
        username=message.from_user.username or "",
        full_name=message.from_user.full_name or ""
    )
    await state.clear()
    await message.answer(
        "Raqamingiz muvaffaqiyatli saqlandi! ✅\n\n"
        "Iltimos, rolingizni tanlang:",
        reply_markup=role_keyboard()
    )

@router.message(RegisterForm.phone)
async def process_phone_invalid(message: Message):
    """Noto'g'ri raqam formati (kerak bo'lsa)"""
    await message.answer(
        "❌ Iltimos, pastdagi tugmani bosish orqali raqamingizni yuboring.",
        reply_markup=phone_request_keyboard()
    )



@router.message(F.text == "👤 Клиент")
async def choose_client(message: Message, state: FSMContext):
    """Mijoz rolini tanlash"""
    await state.clear()
    await upsert_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username or "",
        full_name=message.from_user.full_name or "",
        role="client"
    )
    await message.answer(
        "✅ Siz 👤 Mijoz sifatida ro'yxatdan o'tdingiz!\n\n"
        "Taksi chaqirish uchun tugmani bosing:",
        reply_markup=client_menu()
    )


@router.message(F.text == "🚕 Такси")
async def choose_taxi(message: Message, state: FSMContext):
    """Taxi rolini tanlash"""
    await state.clear()
    await upsert_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username or "",
        full_name=message.from_user.full_name or "",
        role="taxi"
    )
    await message.answer(
        "🚕 Taxi paneliga xush kelibsiz!\n\n"
        "⚠️ Eslatma: Buyurtma olish uchun faol obuna kerak.",
        reply_markup=taxi_menu()
    )


# ─── KABINET ──────────────────────────────────────────────────────────────────

@router.message(F.text == "👤 Kabinet")
async def unified_cabinet(message: Message):
    """Mijoz va Haydovchi uchun umumiy kabinet handler"""
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Iltimos, avval ro'yxatdan o'ting: /start")
        return

    from config import ADMIN_ID
    from keyboards import cabinet_keyboard
    
    user_dict = dict(user) if user else {}
    if user_dict.get("role") == "taxi" or message.from_user.id == ADMIN_ID:
        # Taxi kabineti
        from database import get_active_subscription
        sub = await get_active_subscription(message.from_user.id)
        sub_text = "❌ Faol emas"
        if sub:
            from datetime import datetime
            end = datetime.fromisoformat(sub["end_date"]).strftime("%d.%m.%Y")
            sub_text = f"✅ Faol (Tugash: {end})"

        text = (
            f"👤 <b>Haydovchi kabineti</b>\n\n"
            f"💰 Asosiy balans: {user_dict.get('balance', 0):,} so'm\n"
            f"🎁 Bonus balans: {user_dict.get('discount_balance', 0):,} so'm\n"
            f"📅 Obuna holati: {sub_text}\n"
        )
        await message.answer(text, parse_mode="HTML", reply_markup=cabinet_keyboard("taxi"))
    
    elif user_dict.get("role") == "client":
        # Mijoz kabineti
        text = (
            f"👤 <b>Mijoz kabineti</b>\n\n"
            f"Ism: {user_dict.get('full_name', '—')}\n"
            f"Telefon: {user_dict.get('phone', '—')}\n"
        )
        await message.answer(text, parse_mode="HTML", reply_markup=cabinet_keyboard("client"))


@router.message(F.text == "🚪 Чиқиш")
async def logout(message: Message, state: FSMContext):
    """Chiqish — rolni qayta tanlash"""
    await state.clear()
    await upsert_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username or "",
        full_name=message.from_user.full_name or "",
        role=None
    )
    await message.answer(
        "👋 Chiqildi. Rollardan birini tanlang:",
        reply_markup=role_keyboard()
    )

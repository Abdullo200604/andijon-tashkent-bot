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

    if user and user.get("phone"):
        if user.get("role") == "client":
            await message.answer(
                "👋 Xush kelibsiz, Mijoz!\n\n"
                "Taksi chaqirish uchun tugmani bosing:",
                reply_markup=client_menu()
            )
        elif user.get("role") == "taxi":
            await message.answer(
                "🚕 Taxi paneliga xush kelibsiz!",
                reply_markup=taxi_menu()
            )
        else:
            await message.answer(
                "Iltimos, rolingizni tanlang:",
                reply_markup=role_keyboard()
            )
    else:
        await state.set_state(RegisterForm.phone)
        await message.answer(
            "👋 Assalomu alaykum!\n\n"
            "Botdan foydalanish uchun, iltimos, telefon raqamingizni yuboring:",
            reply_markup=phone_request_keyboard()
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
        "👋 Chiqildi. Qayta boshlash uchun /start bosing.",
        reply_markup=role_keyboard()
    )

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import get_user, upsert_user
from keyboards import role_keyboard, client_menu, taxi_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Bot boshlash — rol tanlash"""
    await state.clear()
    user = await get_user(message.from_user.id)

    if user and user["role"]:
        # Rol tanlangan bo'lsa, menyuni ko'rsat
        if user["role"] == "client":
            await message.answer(
                "👋 Xush kelibsiz, Mijoz!\n\n"
                "Taksi chaqirish uchun tugmani bosing:",
                reply_markup=client_menu()
            )
        elif user["role"] == "taxi":
            await message.answer(
                "🚕 Taxi paneliga xush kelibsiz!",
                reply_markup=taxi_menu()
            )
    else:
        await message.answer(
            "👋 Assalomu alaykum!\n\n"
            "Iltimos, rolingizni tanlang:",
            reply_markup=role_keyboard()
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

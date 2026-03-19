from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from config import TARIFFS


# ─── ASOSIY MENYULAR ──────────────────────────────────────────────────────────

def role_keyboard() -> ReplyKeyboardMarkup:
    """Rol tanlash tugmalari"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Клиент"), KeyboardButton(text="🚕 Такси")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def client_menu() -> ReplyKeyboardMarkup:
    """Mijoz asosiy menyusi"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚖 Taksi chaqirish")],
        ],
        resize_keyboard=True,
    )


def taxi_menu() -> ReplyKeyboardMarkup:
    """Taxi asosiy menyusi"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 Эълон бериш")],
            [KeyboardButton(text="💳 Обуна")],
            [KeyboardButton(text="🚪 Чиқиш")],
        ],
        resize_keyboard=True,
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    """Bekor qilish tugmasi"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


# ─── OBUNA ────────────────────────────────────────────────────────────────────

def tariff_keyboard() -> InlineKeyboardMarkup:
    """Tarif tanlash"""
    buttons = []
    for key, t in TARIFFS.items():
        buttons.append([InlineKeyboardButton(
            text=t["label"], callback_data=f"tariff:{key}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Орқа", callback_data="back_to_taxi")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def payment_confirm_keyboard() -> InlineKeyboardMarkup:
    """To'lov qildim tugmasi"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ To'lov qildim", callback_data="payment_done")],
        [InlineKeyboardButton(text="🔙 Орқа", callback_data="back_to_tariff")],
    ])


def subscription_keyboard() -> InlineKeyboardMarkup:
    """Obuna ko'rish menyusi"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обунани узайтириш", callback_data="extend_subscription")],
        [InlineKeyboardButton(text="🔙 Орқа", callback_data="back_to_taxi")],
    ])


# ─── ADMIN TO'LOV ─────────────────────────────────────────────────────────────

def admin_payment_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    """Admin uchun tasdiqlash/rad etish tugmalari"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Tasdiqlash", callback_data=f"approve:{payment_id}"
            ),
            InlineKeyboardButton(
                text="❌ Rad etish", callback_data=f"reject:{payment_id}"
            ),
        ]
    ])


# ─── BUYURTMA ─────────────────────────────────────────────────────────────────

def order_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Taxi uchun buyurtmani qabul qilish / rad etish"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Олиш", callback_data=f"take:{order_id}"
            ),
            InlineKeyboardButton(
                text="❌ Бекор қилиш", callback_data=f"decline:{order_id}"
            ),
        ]
    ])


def order_taken_keyboard() -> InlineKeyboardMarkup:
    """Buyurtma olinganida boshqa haydovchilarga ko'rsatiladigan klaviatura"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⛔ Buyurtma allaqachon olindi", callback_data="already_taken")]
    ])

def location_keyboard() -> ReplyKeyboardMarkup:
    """Lakatsiya yuborish tugmasi"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Manzilni yuborish", request_location=True)],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True
    )

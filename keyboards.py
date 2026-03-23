from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from database import get_tariffs


# ─── ASOSIY MENYULAR ──────────────────────────────────────────────────────────

def phone_request_keyboard() -> ReplyKeyboardMarkup:
    """Telefon raqam yuborish tugmasi"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


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
            [KeyboardButton(text="👤 Kabinet")],
        ],
        resize_keyboard=True,
    )


def taxi_menu() -> ReplyKeyboardMarkup:
    """Taxi asosiy menyusi"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 Эълон бериш")],
            [KeyboardButton(text="👤 Kabinet")],
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

async def tariff_keyboard(discount_balance: int = 0) -> InlineKeyboardMarkup:
    """Tarif tanlash"""
    tariffs_db = await get_tariffs()
    buttons = []
    for t in tariffs_db:
        buttons.append([InlineKeyboardButton(
            text=t["name"], callback_data=f"tariff:{t['key']}"
        )])

    
    if discount_balance > 0:
        buttons.append([InlineKeyboardButton(
            text=f"🎁 Chegirmadan foydalanish ({discount_balance} so'm)", 
            callback_data="use_discount"
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


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Admin asosiy paneli"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📦 Buyurtmalar", callback_data="admin_orders")],
        [InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin_users")],
        [InlineKeyboardButton(text="⚙️ Tariflar", callback_data="admin_tariffs")],
    ])


def admin_payment_keyboard(payment_id: int, used_discount: int = 0) -> InlineKeyboardMarkup:
    """Admin uchun tasdiqlash/rad etish tugmalari"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Tasdiqlash", callback_data=f"approve:{payment_id}:{used_discount}"
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


def passengers_keyboard() -> ReplyKeyboardMarkup:
    """Yo'lovchilar sonini tanlash tugmalari"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1 kishi"), KeyboardButton(text="2 kishi")],
            [KeyboardButton(text="3 kishi"), KeyboardButton(text="4 kishi")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def cabinet_keyboard(role: str) -> InlineKeyboardMarkup:
    """Kabinet menyusi"""
    buttons = [
        [InlineKeyboardButton(text="📜 Buyurtmalar tarixi", callback_data="history")],
    ]
    if role == "taxi":
        buttons.insert(0, [InlineKeyboardButton(text="💳 Obuna / Balans", callback_data="subscription")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_cabinet() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="cabinet")]
    ])


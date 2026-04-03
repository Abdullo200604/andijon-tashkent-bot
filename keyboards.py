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
        name = t["name"]
        if t["days"] >= 30:
            mo_price = int(t["price"] / (t["days"] / 30))
            if t["days"] > 30:
                name = f"{name} (~{mo_price:,}/oy)"
        
        buttons.append([InlineKeyboardButton(
            text=name, callback_data=f"tariff:{t['key']}"
        )])

    if discount_balance > 0:
        buttons.append([InlineKeyboardButton(
            text=f"🎁 Bonusingizni ishlatish ({discount_balance:,} so'm)", 
            callback_data="use_discount"
        )])
        
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_taxi")])
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


def admin_stats_keyboard() -> InlineKeyboardMarkup:
    """Statistika davrini tanlash"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Bugun (24s)", callback_data="stats_1")],
        [InlineKeyboardButton(text="🗓 Shu hafta (7 kun)", callback_data="stats_7")],
        [InlineKeyboardButton(text="📅 Shu oy (30 kun)", callback_data="stats_30")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_cancel")],
    ])


def gender_keyboard() -> ReplyKeyboardMarkup:
    """Jins tanlash tugmalari"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨 Erkak"), KeyboardButton(text="👩 Ayol")],
            [KeyboardButton(text="🧑 Boshqa")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def cancel_reason_keyboard(role: str) -> InlineKeyboardMarkup:
    """Bekor qilish sabablari"""
    reasons = []
    if role == "client":
        reasons = [
            ("Rejalar o'zgardi", "plans"),
            ("Jins mos emas", "gender"),
            ("Mashina mos emas", "car"),
            ("Boshqa", "other")
        ]
    else: # driver
        reasons = [
            ("Yo'l yopiq / Tirbandlik", "traffic"),
            ("Vaqt mos emas", "time"),
            ("Mijoz javob bermadi", "no_answer"),
            ("Boshqa", "other")
        ]
    
    btns = [[InlineKeyboardButton(text=r[0], callback_data=f"cancel_res:{r[1]}")] for r in reasons]
    return InlineKeyboardMarkup(inline_keyboard=btns)


def contact_phone_keyboard(phone):
    kb = [
        [KeyboardButton(text=f"{phone}", request_contact=True)],
        [KeyboardButton(text="❌ Bekor qilish")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def back_to_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_cancel")]
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
            InlineKeyboardButton(text="✅ Қабул қиламан", callback_data=f"take:{order_id}"),
            InlineKeyboardButton(text="❌ Рад этиш", callback_data=f"decline:{order_id}"),
        ]
    ])


def passenger_order_actions(order_id: int) -> InlineKeyboardMarkup:
    """Mijoz uchun buyurtma amallari (bekor qilish)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel_order:{order_id}")]
    ])


def driver_order_actions(order_id: int) -> InlineKeyboardMarkup:
    """Qabul qilingan buyurtmani haydovchi bekor qilishi uchun"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Safarni bekor qilish", callback_data=f"driver_cancel:{order_id}")]
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

def location_keyboard() -> ReplyKeyboardMarkup:
    """Lakatsiya yuborish tugmasi"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Manzilni yuborish", request_location=True)],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True
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



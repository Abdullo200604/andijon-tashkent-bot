import os
from dotenv import load_dotenv

load_dotenv()

# Bot sozlamalari
BOT_TOKEN_1 = os.getenv("BOT_TOKEN_1")
BOT_TOKEN_2 = os.getenv("BOT_TOKEN_2")
CLICK_TOKEN = os.getenv("CLICK_TOKEN")

ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
GROUP_ID = int(os.getenv("GROUP_ID", 0))

# Karta ma'lumotlari
CARD_NUMBER = os.getenv("CARD_NUMBER", "8600 0000 0000 0000")
CARD_NAME = os.getenv("CARD_NAME", "ABDULLOH ARSLONOV")

# Obuna tariflari: {nomi: (narxi, kunlar soni, tavsif)}
TARIFFS = {
    "1_month": {
        "name": "1 oy",
        "price": 99_000,
        "days": 30,
        "label": "1 oy — 99 000 so'm",
    },
    "3_month": {
        "name": "3 oy",
        "price": 249_000,
        "days": 90,
        "label": "3 oy — 249 000 so'm 🔥",
    },
    "6_month": {
        "name": "6 oy",
        "price": 449_000,
        "days": 180,
        "label": "6 oy — 449 000 so'm 🔥",
    },
    "1_year": {
        "name": "1 yil",
        "price": 799_000,
        "days": 365,
        "label": "1 yil — 799 000 so'm 🔥",
    },
}

# Buyurtma kutish vaqti (soniyada)
ORDER_TIMEOUT = 30           # 30 soniya timeout
REBROADCAST_LIMIT = 2        # Necha marta qayta yuborish
DRIVER_LOCATION_MAX_AGE = 60 # Soniya — haydovchi lokatsiyasi eskirgan deb hisoblanishi uchun

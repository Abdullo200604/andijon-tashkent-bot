from aiogram.fsm.state import State, StatesGroup


class OrderForm(StatesGroup):
    """Mijoz buyurtma berish bosqichlari"""
    from_loc = State()    # Qayerdan
    to_loc = State()      # Qayerga
    location = State()  # Yangi: Geolokatsiya
    order_time = State()  # Vaqt
    price = State()       # Narx
    phone = State()       # Telefon


class TaxiAnnounceForm(StatesGroup):
    """Taxi e'lon berish bosqichlari"""
    direction = State()   # Yo'nalish (masalan Andijon → Toshkent)
    ann_time = State()    # Vaqt
    ann_phone = State()   # Telefon


class PaymentForm(StatesGroup):
    """To'lov tasdiqlash bosqichi"""
    waiting_confirm = State()  # Admin tasdiqlashini kutish

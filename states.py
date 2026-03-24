from aiogram.fsm.state import State, StatesGroup

class RegisterForm(StatesGroup):
    """Ro'yxatdan o'tish (telefon raqam)"""
    phone = State()

class OrderForm(StatesGroup):
    """Mijoz buyurtma berish bosqichlari"""
    from_loc = State()    # Qayerdan
    to_loc = State()      # Qayerga
    location = State()    # Geolokatsiya
    order_time = State()  # Vaqt
    price = State()       # Narx
    passengers = State()  # Yo'lovchilar soni
    contact_phone = State()


class TaxiAnnounceForm(StatesGroup):
    """Taxi e'lon berish bosqichlari"""
    direction = State()   # Yo'nalish
    ann_time = State()    # Vaqt


class PaymentForm(StatesGroup):
    """To'lov tasdiqlash bosqichi"""
    waiting_confirm = State()
    waiting_proof = State()  # Rasm (screenshot) kutish
    waiting_amount = State() # To'langan summani kutish


class DiscountCalcForm(StatesGroup):
    """Olingan buyurtma uchun chegirma hisoblash bosqichi"""
    waiting_price = State()  # Mijoz kiritgan real narxni kutish


class AdminState(StatesGroup):
    """Admin boshqaruv bosqichlari"""
    waiting_user_id = State()
    waiting_balance_amount = State()
    waiting_tariff_price = State()


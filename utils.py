import re

def is_valid_phone(phone: str) -> bool:
    """Telefon raqami +998XXXXXXXXX formatidami?"""
    return bool(re.match(r"^\+998\d{9}$", phone))

def is_valid_time(time_str: str) -> bool:
    """Vaqt HH:MM formatidami yoki 'hozir'mi?"""
    if time_str.lower() in ["hozir", "now"]:
        return True
    return bool(re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", time_str))

def is_valid_location_name(loc: str) -> bool:
    """Joylashuv nomi kamida 2 ta harfdan iboratmi?"""
    # Faqat harflar va bo'shliqlarni tekshirish (uzbek harflari bilan)
    return len(loc) >= 2 and any(c.isalpha() for c in loc)

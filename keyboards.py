from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_keyboard(is_admin=False):
    if is_admin:
        buttons = [
            [KeyboardButton(text="👨‍💼 Admin Panel")]
        ]
    else:
        buttons = [
            [KeyboardButton(text="📝 Test ishlash")],
            [KeyboardButton(text="🔍 Boshqa sinf testlari")],
            [KeyboardButton(text="📊 Reyting")],
            [KeyboardButton(text="🏠 Bosh menyu")]
        ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def admin_panel_keyboard():
    buttons = [
        [KeyboardButton(text="➕ Fan qo'shish")],
        [KeyboardButton(text="📋 Test qo'shish")],
        [KeyboardButton(text="✏️ Testni tahrirlash")],   # ← YANGI TUGMA
        [KeyboardButton(text="🗑 Test o'chirish")],
        [KeyboardButton(text="📊 Reyting ko'rish")],
        [KeyboardButton(text="🔙 Orqaga")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def class_selection_keyboard(classes):
    buttons = []
    for cls in classes:
        buttons.append([KeyboardButton(text=cls['name'])])
    buttons.append([KeyboardButton(text="🔙 Orqaga")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def back_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Orqaga")]], resize_keyboard=True)


# ================= YANGI: Savol tahrirlash klaviaturalari =================

def question_edit_fields_keyboard():
    """Savolning qaysi maydonini tahrirlashni tanlash."""
    buttons = [
        [KeyboardButton(text="📝 Savol matni")],
        [KeyboardButton(text="🖼 Rasm")],              # ← YANGI
        [KeyboardButton(text="🅰️ A varianti")],
        [KeyboardButton(text="🅱️ B varianti")],
        [KeyboardButton(text="©️ C varianti")],
        [KeyboardButton(text="🅳 D varianti")],
        [KeyboardButton(text="✅ To'g'ri javob")],
        [KeyboardButton(text="📋 Savol turi")],
        [KeyboardButton(text="🔙 Orqaga")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def image_actions_keyboard():
    """Rasm bilan amallar."""
    buttons = [
        [KeyboardButton(text="🖼 Yangi rasm yuklash")],
        [KeyboardButton(text="🗑 Rasmni o'chirish")],
        [KeyboardButton(text="🔙 Orqaga")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def question_type_keyboard():
    """Savol turini tanlash (closed/open)."""
    buttons = [
        [KeyboardButton(text="closed")],
        [KeyboardButton(text="open")],
        [KeyboardButton(text="🔙 Orqaga")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def tests_selection_keyboard(tests):
    """Testlar ro'yxatidan tanlash."""
    buttons = []
    for t in tests:
        buttons.append([KeyboardButton(text=t['name'])])
    buttons.append([KeyboardButton(text="🔙 Orqaga")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def subjects_selection_keyboard(subjects):
    """Fanlar ro'yxatidan tanlash."""
    buttons = []
    for s in subjects:
        buttons.append([KeyboardButton(text=s['name'])])
    buttons.append([KeyboardButton(text="🔙 Orqaga")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# ================= REYTING TOZALASH =================

def rating_actions_keyboard():
    """Reyting ko'rsatilgandan keyingi amallar."""
    buttons = [
        [KeyboardButton(text="🗑 Reytingni tozalash")],
        [KeyboardButton(text="🔙 Orqaga")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def rating_clear_confirm_keyboard():
    """Reytingni tozalashni tasdiqlash."""
    buttons = [
        [KeyboardButton(text="✅ Ha, tozalash")],
        [KeyboardButton(text="❌ Yo'q, bekor qilish")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
from aiogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    ReplyKeyboardMarkup, 
    KeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# --- 1. LANGUAGE SELECTION ---
def lang_selection() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇸 English", callback_data="lang_EN")
    builder.button(text="🇪🇹 አማርኛ", callback_data="lang_AM")
    builder.adjust(2)
    return builder.as_markup()

# --- 2. GENDER SELECTION ---
def gender_markup(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if lang == "AM":
        builder.button(text="ወንድ 👨", callback_data="gender_male")
        builder.button(text="ሴት 👩", callback_data="gender_female")
    else:
        builder.button(text="Male 👨", callback_data="gender_male")
        builder.button(text="Female 👩", callback_data="gender_female")
    builder.adjust(2)
    return builder.as_markup()

# --- 3. PHONE SHARING (REPLY KEYBOARD) ---
# This is "Ultra-Premium" because it reduces typing errors.
def phone_markup(lang: str) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    text = "📲 ስልክ ቁጥር አጋራ" if lang == "AM" else "📲 Share Phone Number"
    builder.row(KeyboardButton(text=text, request_contact=True))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

# --- 4. LEGAL & HEALTH AGREEMENT ---
def legal_markup(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    text = "✅ አዎ፣ ተስማምቻለሁ" if lang == "AM" else "✅ I Agree & Continue"
    builder.button(text=text, callback_data="agree")
    return builder.as_markup()

# --- 5. ADMIN DASHBOARD (Quick View) ---
def admin_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⏳ Pending Payments", callback_data="admin_pending"),
        InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats")
    )
    builder.row(
        InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast")
    )
    return builder.as_markup()


from aiogram.utils.keyboard import InlineKeyboardBuilder

LEGAL_TEXTS = {
    "EN": {
        "rule_1": "10. Competition Rules & Refund Policy\nI understand that the 1000 ETB fee is non-refundable for any reason. I also agree to undergo a medical checkup if I win the grand prize.",
        "rule_2": "11. Health Confirmation\nI confirm that I have no heart, respiratory, bone, or joint issues, and I am not medically prohibited from intense exercise.",
        "rule_3": "12. Liability Waiver\nI take full responsibility for my health during this challenge and will not hold the organizers liable for any injuries or health issues.",
        "btn_rule_1": "I agree to the rules",
        "btn_rule_2": "I am healthy & fit",
        "btn_rule_3": "I take full responsibility",
        "btn_continue": "Confirm & Continue ➔",
        "instruction": "⚠️ <b>Please click all 3 buttons below to check them (⭕ → ✅).</b> Once all are checked, the continue button will appear.",
    },
    "AM": {
        "rule_1": "10. የውድድሩ ህግ እና ደንብ ስምምነት\nአንዴ ከተመዘገቡ በኋላ በምንም ምክንያት የከፈሉት 900 ብር ተመላሽ እንደማይሆን እና አሸናፊ ከሆኑ የህክምና ምርመራ እንደሚያደርጉ ተስማምቻለሁ።",
        "rule_2": "11. አጠቃላይ የጤና ሁኔታ\nምንም አይነት የልብ፣ የመተንፈሻ አካል፣ የአጥንት ወይም የመገጣጠሚያ ህመም እንደሌለብኝ እና ስፖርት ለመስራት በሀኪም እንዳልተከለከልኩ አረጋግጣለሁ።",
        "rule_3": "12. ኃላፊነትን በራስ ስለመውሰድ\nበዚህ ውድድር ምክንያት ለሚደርስብኝ ማንኛውም የጤና እክል አዘጋጆቹን ተጠያቂ እንደማላደርግ እና ሙሉ ኃላፊነቱን እራሴ እወስዳለሁ።",
        "btn_rule_1": "አንብቤ ተስማምቻለሁ",
        "btn_rule_2": "ጤነኛ ነኝ/በሀኪም አልተከለከልኩም",
        "btn_rule_3": "አንብቤ ሙሉ ኃላፊነት እወስዳለሁ",
        "btn_continue": "አረጋግጥና ቀጥል ➔",
        "instruction": "⚠️ <b>እባክዎ ለመቀጠል ሦስቱንም ምርጫዎች ይጫኑ (⭕ ወደ ✅ ይቀየራሉ)።</b> ሦስቱንም ሲያጠናቅቁ 'ቀጥል' የሚል ምርጫ ይመጣልዎታል።",
    }
}

def legal_keyboard(lang: str, checks: list):
    builder = InlineKeyboardBuilder()
    texts = LEGAL_TEXTS[lang]
    
    # Checkmarks: ✅ if in checks list, else ⭕
    c1 = "✅" if 1 in checks else "⭕"
    c2 = "✅" if 2 in checks else "⭕"
    c3 = "✅" if 3 in checks else "⭕"
    
    builder.button(text=f"{c1} {texts['btn_rule_1']}", callback_data="legal_1")
    builder.button(text=f"{c2} {texts['btn_rule_2']}", callback_data="legal_2")
    builder.button(text=f"{c3} {texts['btn_rule_3']}", callback_data="legal_3")
    
    # Only show the "Continue" button if all 3 are checked
    if len(checks) == 3:
        builder.button(text=texts['btn_continue'], callback_data="legal_finalize")
    
    builder.adjust(1)
    return builder.as_markup()


from aiogram.utils.keyboard import InlineKeyboardBuilder

def admin_verify_keyboard(user_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Approve", callback_data=f"approve_{user_id}")
    builder.button(text="❌ Reject", callback_data=f"reject_{user_id}")
    builder.adjust(2)
    return builder.as_markup()
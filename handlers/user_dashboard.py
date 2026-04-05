from aiogram import Router, F, types
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from database.db import Database
from config import settings
import logging
from utils.localization import get_member_card
logger = logging.getLogger(__name__)


router = Router(name="user_dashboard")


# --- 2. MAIN DASHBOARD KEYBOARD ---
def get_main_dashboard(lang: str):
    builder = ReplyKeyboardBuilder()
    if lang == "EN":
        builder.row(types.KeyboardButton(text="👤 My Profile"), types.KeyboardButton(text="📢 Groups & Channel"))
        builder.row(types.KeyboardButton(text="❓ Help & Rules"), types.KeyboardButton(text="⚙️ Settings"))
    else:
        builder.row(types.KeyboardButton(text="👤 መገለጫዬ"), types.KeyboardButton(text="📢 ግሩፕ እና ቻናል"))
        builder.row(types.KeyboardButton(text="❓ እርዳታና ደንቦች"), types.KeyboardButton(text="⚙️ ማስተካከያ"))

    return builder.as_markup(resize_keyboard=True, input_field_placeholder="Select a command...")

# --- 3. PROFILE HANDLER ---
@router.message(F.text.in_({"👤 My Profile", "👤 መገለጫዬ"}))
async def show_profile(message: types.Message, db: Database):
    user = await db.get_user(message.from_user.id)
    if not user: return
    
    card_text = get_member_card(
        lang=user['language'],
        user_id=user['telegram_id'],
        name=user['full_name'],
        registration_step=user['registration_step']
    )
    await message.answer(card_text, parse_mode="HTML")

# --- 4. DETAILED HELP & RULES ---
from aiogram.filters import Command

# --- 4. DETAILED HELP & RULES (ሁለቱንም /help እና Button የሚሰማ) ---
@router.message(Command("help"))
@router.message(F.text.in_({"❓ Help & Rules", "❓ እርዳታና ደንቦች"}))
async def help_rules_view(message: types.Message, db: Database):
    user = await db.get_user(message.from_user.id)
    if not user:
        return await message.answer("Please /start first.")
        
    lang = user.get('language', 'EN')
    
    if lang == "EN":
        text = (
            "🏆 <b>8-WEEK TRANSFORMATION CHALLENGE</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📅 <b>START DATE:</b> The competition officially begins on <b>April 19, 2026 (Dagmawi Tensae 11/07/2018 E.C.)</b>.\n"
            "Use this time to prepare your kitchen and mindset!\n\n"
            "💰 <b>THE PRIZE POOL:</b>\n"
            "🥇 1st Place: 100,000 ETB\n"
            "🥈 2nd Place: 50,000 ETB\n\n"
            "📋 <b>HOW TO COMPETE:</b>\n"
            # "1️⃣ <b>Sunday Check-ins:</b> You must submit your weight and photos every Sunday via the 📸 button.\n"
            "1️⃣  <b>The Blueprint:</b> Follow the workout and meal plans sent to the private channel daily.\n"
            "2️⃣ <b>Integrity:</b> Any sign of photo manipulation results in instant disqualification.\n\n"
            "🛠 <b>SUPPORT:</b> Contact @EWCSupportbot for technical issues."
        )
    else:
        text = (
            "🏆 <b>የ8-ሳምንት የለውጥ ውድድር</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📅 <b>የመጀመሪያ ቀን፦</b> ውድድሩ በይፋ የሚጀምረው በ<b>ሚያዝያ 11/2018 ዓ.ም (ዳግማዊ ትንሳኤ)</b> ነው።\n"
            "እስከዚያው ዝግጅትዎን ያጠናቅቁ!\n\n"
            "💰 <b>የሽልማት ማህደር፦</b>\n"
            "🥇 1ኛ ደረጃ፦ 100,000 ብር\n"
            "🥈 2ኛ ደረጃ፦ 50,000 ብር\n\n"
            "📋 <b>መመሪያዎች፦</b>\n"
            # "1️⃣ <b>የእሁድ ክትትል፦</b> በየሳምንቱ እሁድ በ 📸 ቁልፍ በኩል ፎቶና ክብደትዎን መላክ ግዴታ ነው።\n"
            "1️⃣  <b>መመሪያ፦</b> በዝግ ቻናሉ የሚለቀቁትን የምግብና የስልጠና መመሪያዎች በትክክል ይከተሉ።\n"
            "2️⃣ <b>ታማኝነት፦</b> ማንኛውም የፎቶ ማጭበርበር ከውድድሩ ወዲያውኑ ያስወጣል።\n\n"
            "🛠 <b>ድጋፍ፦</b> ለቴክኒክ ችግሮች @EWCSupportbot ን ያነጋግሩ።"
        )
    await message.answer(text, parse_mode="HTML")
    
    
# --- 5. SETTINGS & CHANNEL LINK ---
# --- SETTINGS VIEW (The Trigger) ---
@router.message(F.text.in_({"⚙️ Settings", "⚙️ ማስተካከያ"}))
async def settings_view(message: types.Message, db: Database):
    user = await db.get_user(message.from_user.id)
    lang = user.get('language', 'EN')
    
    builder = InlineKeyboardBuilder()
    # If current is EN, offer AM. If current is AM, offer EN.
    new_lang = "AM" if lang == "EN" else "EN"
    
    btn_text = "Switch to Amharic 🇪🇹" if lang == "EN" else "ወደ እንግሊዝኛ ቀይር 🇺🇸"
    builder.button(text=btn_text, callback_data=f"switch_lang_{new_lang}")
    
    text = "<b>Settings</b> ⚙️" if lang == "EN" else "<b>ማስተካከያ</b> ⚙️"
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")


# --- LANGUAGE SWITCH HANDLER (The Logic) ---
@router.callback_query(F.data.startswith("switch_lang_"))
async def process_language_switch(callback: types.CallbackQuery, db: Database):
    # 1. Extract the new language from callback data
    new_lang = callback.data.split("_")[-1] # "AM" or "EN"
    
    # 2. Update the Database
    await db.update_user(callback.from_user.id, language=new_lang)
    
    # 3. Prepare Confirmation Text
    if new_lang == "AM":
        confirm_text = "✅ ቋንቋው ወደ አማርኛ ተቀይሯል።"
    else:
        confirm_text = "✅ Language switched to English."
        
    # 4. CRITICAL: Update the Reply Keyboard (Main Menu)
    # We send a new message with the updated keyboard so the user sees the change
    
    
    await callback.message.answer(
        confirm_text,
        reply_markup=get_main_dashboard(new_lang) 
    )
    
    # 5. Clean up: Delete the settings inline message and answer callback
    await callback.message.delete()
    await callback.answer()

@router.message(F.text.in_({"📅 Daily Blueprint", "📅 የዕለት መመሪያ"}))
async def daily_blueprint(message: types.Message, db: Database):
    user = await db.get_user(message.from_user.id)
    lang = user['language']
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📢 Open Private Arena" if lang == "EN" else "📢 ወደ ዝግ መድረኩ ግባ", url=settings.CHALLENGE_CHANNEL_INVITE_LINK))
    text = "🔗 The transformation roadmap is waiting in the Arena." if lang == "EN" else "🔗 የለውጥ መመሪያው በዝግ መድረኩ ተቀምጧል።"
    await message.answer(text, reply_markup=builder.as_markup())
    
# --- THE GROUPS & CHANNEL HANDLER ---
@router.message(F.text.in_({"📢 Groups & Channel", "📢 ግሩፕ እና ቻናል"}))
async def community_links_handler(message: types.Message, db: Database):
    user = await db.get_user(message.from_user.id)
    if not user:
        return
    
    lang = user.get('language', 'EN')
    full_name = user.get('full_name', 'Challenger')

    # 1. Generate fresh "Join Request" links specifically for this user
    try:
        group_invite = await message.bot.create_chat_invite_link(
            chat_id=settings.CHALLENGE_GROUP_ID,
            name=f"Community Tab: {full_name}",
            creates_join_request=True # This forces the ChatJoinRequest event
        )
        group_url = group_invite.invite_link
        
        channel_invite = await message.bot.create_chat_invite_link(
            chat_id=settings.CHALLENGE_CHANNEL_ID,
            name=f"Community Tab: {full_name}",
            creates_join_request=True
        )
        channel_url = channel_invite.invite_link
    except Exception as e:
        logger.error(f"Failed to create invite links: {e}")
        # Fallback to static links if creation fails
        group_url = settings.CHALLENGE_GROUP_INVITE_LINK
        channel_url = settings.CHALLENGE_CHANNEL_INVITE_LINK

    # 2. Build the UI
    builder = InlineKeyboardBuilder()
    
    if lang == "EN":
        msg_text = (
            "🚀 <b>THE TRANSFORMATION HUBS</b>\n\n"
            "Access your exclusive community and daily plans below:"
        )
        builder.row(types.InlineKeyboardButton(text="💬 Join Group Chat", url=group_url))
        builder.row(types.InlineKeyboardButton(text="📅 Join Channel", url=channel_url))
    else:
        msg_text = (
            "🚀 <b>የመረጃ መድረኮች</b>\n\n"
            "ከታች ያሉትን ሊንኮች በመጠቀም መመሪያዎችን እና ውይይቶችን ያግኙ፦"
        )
        builder.row(types.InlineKeyboardButton(text="💪 ግሩፑን ይቀላቀሉ", url=group_url))
        builder.row(types.InlineKeyboardButton(text="📢 ቻናሉን ይቀላቀሉ", url=channel_url))

    await message.answer(
        msg_text, 
        reply_markup=builder.as_markup(), 
        parse_mode="HTML"
    )
    



from aiogram.filters import StateFilter, Command
from aiogram import Router, F, types, Bot

# 1. Update the decorator with Filters
@router.message(
    StateFilter(None),           # ONLY catch if the user is NOT in an active FSM state
    ~Command("start"),           # EXCLUDE the /start command
    F.text                       # ONLY catch Text (ignores photos/files)
)
async def forward_random_signals(message: types.Message, bot: Bot, db: Database):
    """
    Forwards random text to Admin ONLY if the user is idling.
    """
    # 1. Get user data safely
    user = await db.get_user(message.from_user.id)
    # Default to 'EN' if user doesn't exist in DB yet
    lang = (user.get('language') if user else 'EN').upper()
    
    # 2. Premium Admin Notification (Clean UI)
    admin_id = 1131741322
    user_info = (
        f"👤 <b>User:</b> {message.from_user.full_name}\n"
        f"🆔 <b>ID:</b> <code>{message.from_user.id}</code>\n"
        f"🔗 <b>Username:</b> @{message.from_user.username or 'None'}"
    )
    
    await bot.send_message(admin_id, f"<b>📩 Random Signal:*</b>\n\n{user_info}\n\n<b>Content:</b>")
    await message.forward(admin_id)

    # 3. Personalized Response based on Language
    if lang == "AM":
        reply_text = (
            "ተጨማሪ ጥያቄ ወይም እርዳታ ካስፈለገዎት\n"
            "ፈጣን ምላሽ ለማግኘት እዚ ላይ ያዋሩን፦ <b>@EWCSupportBot 😊</b>"
        )
    else:
        reply_text = (
            "If you have any specific questions or issues,\n "
            "please contact our support team here: <b>@EWCSupportBot 😊</b>"
        )

    await message.answer(reply_text)

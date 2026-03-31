from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from database.db import Database
from handlers.user_dashboard import get_main_dashboard
from utils.localization import get_text, get_member_card
import logging
from datetime import datetime, timezone
logger = logging.getLogger(__name__)
from aiogram.fsm.state import State, StatesGroup
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from database.db import Database
from utils.localization import get_member_card
import asyncio
from config import settings


router = Router(name="admin")


class AdminStates(StatesGroup):
    waiting_for_rejection_reason = State()

# --- 1. HANDLE APPROVAL ---
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import timedelta
# --- 1. HANDLE APPROVAL ---
@router.callback_query(F.data.startswith("approve_"))
async def approve_user(callback: types.CallbackQuery, db: Database):
    user_id = int(callback.data.split("_")[-1]) 
    
    user = await db.get_user(user_id)
    if not user:
        return await callback.answer("❌ User not found.", show_alert=True)
    
    lang = user.get('language', 'EN')
    full_name = user.get('full_name', 'Participant')

    # 1. Update Database
    await db.update_user(user_id, registration_step='verified', is_paid=True)

    # 2. Update Admin UI
    try:
        await callback.message.edit_text(
            f"{callback.message.text}\n\n✅ <b>APPROVED BY:</b> @{callback.from_user.username}",
            parse_mode="HTML",
            reply_markup=None 
        )
    except Exception:
        pass

    # 3. Handle Invite Links
    try:
        group_invite = await callback.bot.create_chat_invite_link(
            chat_id=settings.CHALLENGE_GROUP_ID,
            name=f"Group Access: {full_name}",
            creates_join_request=True
        )
        group_url = group_invite.invite_link
    except Exception as e:
        group_url = settings.CHALLENGE_GROUP_INVITE_LINK

    try:
        channel_invite = await callback.bot.create_chat_invite_link(
            chat_id=settings.CHALLENGE_CHANNEL_ID,
            name=f"Channel Access: {full_name}",
            creates_join_request=True
        )
        channel_url = channel_invite.invite_link
    except Exception as e:
        channel_url = settings.CHALLENGE_CHANNEL_ID

    user_card = get_member_card(lang, user_id, full_name, registration_step='verified')

    # 4. Prepare Bilingual Notification (STICKING TO YOUR EXACT TEXT)
    if lang == "EN":
        congrats_text = (
            f"🚀 <b>CONGRATULATIONS {full_name.upper()}!</b>\n\n"
            f"Your registration is <b>VERIFIED</b>. You are officially in!\n\n"
            f"{user_card}\n\n"
            f"📍 <b>YOUR NEXT STEPS:</b>\n"
            f"1️⃣ <b>The Group:</b> Join the community chat.\n"
            f"🔗 {group_url}\n\n"
            f"2️⃣ <b>The Channel:</b> Get your workout/meal plans here.\n"
            f"🔗 {channel_url}\n\n"
            f"<i>Click the buttons below to request access!</i>"
        )
        btn_group, btn_channel = "💪 JOIN THE GROUP", "📢 JOIN THE CHANNEL"
        link_header = "🔗 <b>ACCESS LINKS:</b>"
    else:
        congrats_text = (
            f"🚀 <b>እንኳን ደስ አለዎት {full_name.upper()}!</b>\n\n"
            f"ምዝገባዎ በተሳካ ሁኔታ <b>ተረጋግጧል</b>። አሁን በይፋ ተመዝግበዋል!\n\n"
            f"{user_card}\n\n"
            f"📍 <b>ቀጣይ ደረጃዎች፦</b>\n"
            f"1️⃣ <b>ግሩፑ፦</b> የልምምድ ጓደኞችዎን ለማግኘት ግሩፑን ይቀላቀሉ።\n"
            f"🔗 {group_url}\n\n"
            f"2️⃣ <b>ቻናሉ፦</b> የየቀኑን የፊትነስ እና የምግብ ምክሮችን እዚህ ያገኛሉ።\n"
            f"🔗 {channel_url}\n\n"
            f"<i>ከታች ያሉትን በተኖች በመጫን መግቢያ ይጠይቁ!</i>"
        )
        btn_group, btn_channel = "💪 ግሩፑን ይቀላቀሉ", "📢 ቻናሉን ይቀላቀሉ"
        link_header = "🔗 <b>የመግቢያ ሊንኮች፦</b>"

    # 5. Build Inline Keyboard (Links)
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text=btn_group, url=group_url))
    builder.row(types.InlineKeyboardButton(text=btn_channel, url=channel_url))
    
    # 6. Send to User
    try:
        # FIRST MESSAGE: Congrats + Member Card + UNLOCK MAIN MENU
        await callback.bot.send_message(
            chat_id=user_id, 
            text=congrats_text, 
            parse_mode="HTML",
            reply_markup=get_main_dashboard(lang) # This shows the Profile/Help buttons
        )
        
        # SECOND MESSAGE: The actual clickable Link Buttons
        await callback.bot.send_message(
            chat_id=user_id,
            text=link_header,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        
        await callback.answer("Verified! Instructions sent.", show_alert=False)
        
    except Exception as e:
        # Log the actual error to see why it failed (don't just assume block)
        logging.error(f"Failed to notify user {user_id}: {e}")
        await callback.answer("Error sending message. Check logs.", show_alert=True)
# --- 2. HANDLE REJECTION CLICK ---
@router.callback_query(F.data.startswith("reject_"))
async def start_rejection_process(callback: types.CallbackQuery, state: FSMContext):
    # FIX: Use [-1] to get the last part of the string (the ID)
    parts = callback.data.split("_")
    user_id = int(parts[-1]) 
    
    # Save the target user_id and the message_id so we can edit it later
    await state.update_data(reject_target_id=user_id, admin_msg_id=callback.message.message_id)
    
    await callback.message.answer(
        "📝 <b>CUSTOM REJECTION REASON:</b>\n"
        "Please type the reason for rejection. I will forward it to the user.",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_rejection_reason)
    await callback.answer()
# --- 3. CAPTURE REASON & NOTIFY USER ---
@router.message(AdminStates.waiting_for_rejection_reason)
async def finalize_rejection(message: types.Message, state: FSMContext, db: Database):
    reason = message.text
    data = await state.get_data()
    user_id = data['reject_target_id']
    admin_msg_id = data['admin_msg_id']
    
    user = await db.get_user(user_id)
    lang = user.get('language', 'EN') if user else 'EN'

    # 1. Update DB to reflect rejection
    await db.update_user(user_id, registration_step='rejected')

    # 2. Update Admin UI (Edit original registration card)
    try:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=admin_msg_id,
            text=f"❌ <b>REJECTED BY:</b> @{message.from_user.username}\n<b>REASON:</b> {reason}",
            parse_mode="HTML"
        )
    except Exception:
        pass 

    # 3. Create the "Self-Healing" Button for the User
    retry_builder = InlineKeyboardBuilder()
    retry_text = "🔄 Re-upload Everything / ድጋሚ ይላኩ" if lang == "EN" else "🔄 ሁሉንም ድጋሚ ይላኩ"
    # We use a specific callback data that we will handle in onboarding.py
    retry_builder.row(types.InlineKeyboardButton(text=retry_text, callback_data="retry_registration"))

    # 4. Notify the User
    fail_header = "❌ <b>Registration Update</b>" if lang == "EN" else "❌ <b>የምዝገባ ሁኔታ</b>"
    
    if lang == "EN":
        fail_body = (
            f"Your application was not approved for the following reason:\n\n"
            f"👉 <b>{reason}</b>\n\n"
            "Please click the button below to re-upload your photos and ID correctly."
        )
    else:
        fail_body = (
            f"ምዝገባዎ በሚከተለው ምክንያት ተቀባይነት አላገኘም፦\n\n"
            f"👉 <b>{reason}</b>\n\n"
            "እባክዎን ከታች ያለውን በተን በመጫን ፎቶዎችን እና መታወቂያዎን በድጋሚ ይላኩ።"
        )

    try:
        await message.bot.send_message(
            chat_id=user_id, 
            text=f"{fail_header}\n\n{fail_body}", 
            parse_mode="HTML",
            reply_markup=retry_builder.as_markup()
        )
        await message.answer(f"✅ Rejection sent to user {user_id}.")
    except Exception as e:
        logger.error(f"Failed to notify user {user_id}: {e}")
        await message.answer("⚠️ Could not message user.")

    await state.clear()


class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_search = State()
    waiting_for_rejection_reason = State()

# --- 1. KEYBOARDS ---
def admin_reply_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="📊 Stats Summary"))
    builder.row(types.KeyboardButton(text="⏳ Pending Applications"), types.KeyboardButton(text="🔍 Search User"))
    return builder.as_markup(resize_keyboard=True)

def quick_reject_keyboard(user_id):
    builder = InlineKeyboardBuilder()
    # Quick buttons to avoid typing
    builder.row(types.InlineKeyboardButton(text="📸 Blurry Photos", callback_data=f"qrej_{user_id}_blurry"))
    builder.row(types.InlineKeyboardButton(text="🧾 No Receipt", callback_data=f"qrej_{user_id}_receipt"))
    builder.row(types.InlineKeyboardButton(text="🪪 ID Mismatch", callback_data=f"qrej_{user_id}_id"))
    builder.row(types.InlineKeyboardButton(text="✍️ Custom Reason", callback_data=f"reject_{user_id}"))
    builder.row(types.InlineKeyboardButton(text="⬅️ Back", callback_data="admin_refresh"))
    return builder.as_markup()
# --- 2. RELATIVE TIME HELPER ---
def get_relative_time(dt):
    # Make 'now' aware of UTC so it matches Telegram's dt
    now = datetime.now(timezone.utc) 
    
    diff = now - dt
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return f"{int(seconds)}s ago"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    else:
        return f"{int(seconds // 3600)}h ago"
    

def admin_refresh_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Refresh Data", callback_data="admin_stats_refresh")
    return builder.as_markup()

# --- 3. THE UNIFIED SUMMARY HANDLER ---
@router.message(Command("admin"))
@router.message(F.text == "📊 Stats Summary")
async def admin_cmd(message: types.Message, db: Database):
    stats = await db.get_system_stats()
    now = datetime.now()
    # In your summary builder
    from datetime import timedelta

    # For display purposes (UTC + 3)
    ethiopia_time = datetime.now(timezone.utc) + timedelta(hours=3)
    time_str = ethiopia_time.strftime("%H:%M:%S")
    
    text = (
        "🛠 <b>ADMIN CONTROL PANEL</b> ⚡️\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📊 <b>LIVE CHALLENGE SUMMARY</b>\n\n"
        f"👥 Total Leads: <b>{stats['total']}</b>\n"
        f"✅ Verified: <b>{stats['verified']}</b>\n"
        f"⏳ Pending: <b>{stats['pending']}</b>\n"
        f"💰 Revenue: <b>{stats['revenue']:,} ETB</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🕒 <i>Last Updated: {time_str} (Just now)</i>\n\n"
        "<i>Use the menu below to manage the challenge.</i>"
    )
    
    # We send ONE message with the stats AND the inline button attached
    await message.answer(
        text,
        reply_markup=admin_refresh_kb(), 
        parse_mode="HTML"
    )
    
    # We also send/ensure the Reply Keyboard is active
    # If this was triggered by /admin, it will pop up the reply menu
    if message.text == "/admin":
        await message.answer("Admin Menu Active 🛠", reply_markup=admin_reply_menu())

# --- 4. THE REFRESH CALLBACK (Edits the existing card) ---
@router.callback_query(F.data == "admin_stats_refresh")
async def refresh_stats_callback(callback: types.CallbackQuery, db: Database):
    stats = await db.get_system_stats()
    
    # Calculating relative time from the message's original creation date
    orig_time = callback.message.date
    relative_str = get_relative_time(orig_time)
    
    now_time_str = datetime.now().strftime("%H:%M:%S")
    
    text = (
        "🛠 <b>ADMIN CONTROL PANEL</b> ⚡️\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📊 <b>LIVE CHALLENGE SUMMARY</b>\n\n"
        f"👥 Total Leads: <b>{stats['total']}</b>\n"
        f"✅ Verified: <b>{stats['verified']}</b>\n"
        f"⏳ Pending: <b>{stats['pending']}</b>\n"
        f"💰 Revenue: <b>{stats['revenue']:,} ETB</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🕒 <i>Last Refreshed: {now_time_str}</i>\n"
        f"⏳ <i>Original Post: {relative_str}</i>\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    
    try:
        # Edit the same message with updated stats and the same button
        await callback.message.edit_text(
            text, 
            reply_markup=admin_refresh_kb(), 
            parse_mode="HTML"
        )
        await callback.answer("Stats Updated! 🔄")
    except Exception:
        # If stats haven't changed, Telegram throws an error on edit_text
        await callback.answer("No new data yet.")
        
# --- 4. SEARCH & CONSISTENT CARD ---
@router.message(F.text == "🔍 Search User")
async def start_search(message: types.Message, state: FSMContext):
    await message.answer("🔍 Enter Name or Phone Number to search:")
    await state.set_state(AdminStates.waiting_for_search)

@router.message(AdminStates.waiting_for_search)
async def perform_search(message: types.Message, state: FSMContext, db: Database):
    results = await db.search_users(message.text)
    
    if not results:
        return await message.answer("❌ <b>No user found.</b> Check the spelling or phone number.", parse_mode="HTML")

    await message.answer(f"🔎 <b>Found {len(results)} matching participants:</b>", parse_mode="HTML")

    for user in results:
        # 1. Pull data from the current user object in the loop
        u_id = user['telegram_id']
        u_name = user.get('full_name', 'N/A').upper()
        u_lang = user.get('language', 'EN')
        u_step = user.get('registration_step', 'pending')
        
        is_verified = u_step == 'verified'
        status_icon = "✅ VERIFIED" if is_verified else "⏳ PENDING"
        
        # 2. Base Admin Card
        card = (
            f"👤 <b>PARTICIPANT CARD</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"📝 <b>NAME:</b> {u_name}\n"
            f"📞 <b>PHONE:</b> <code>{user.get('phone_number', 'N/A')}</code>\n"
            f"⚖️ <b>DATA:</b> {user.get('age')}y | {user.get('current_weight_kg')}kg | {user.get('gender')}\n"
            f"📡 <b>STATUS:</b> {status_icon}\n"
            f"━━━━━━━━━━━━━━"
        )
        
        # 3. If verified, append the actual Digital Member Card
        if is_verified:
            # We call your preferred sync function here
            digital_card = get_member_card(u_lang, u_id, u_name, registration_step='verified')
            card += f"\n\n{digital_card}"

        # 4. Dynamic Buttons
        builder = InlineKeyboardBuilder()
        builder.button(text="🔍 Full Profile", callback_data=f"view_prof_{u_id}")

        if not is_verified:
            builder.button(text="✅ Approve", callback_data=f"approve_{u_id}")
            builder.button(text="❌ Reject", callback_data=f"reject_options_{u_id}")
            builder.adjust(1, 2) 
        else:
            # Maybe add a "Revoke" or "Message User" button for verified users?
            builder.adjust(1)

        await message.answer(
            card, 
            reply_markup=builder.as_markup(), 
            parse_mode="HTML"
        )
    
    await state.clear()
    
# --- 5. QUICK REJECT LOGIC ---
@router.callback_query(F.data.startswith("reject_options_"))
async def show_quick_reject(callback: types.CallbackQuery):
    user_id = callback.data.split("_")[2]
    await callback.message.edit_reply_markup(reply_markup=quick_reject_keyboard(user_id))

@router.callback_query(F.data.startswith("qrej_"))
async def handle_quick_reject(callback: types.CallbackQuery, db: Database):
    parts = callback.data.split("_")
    user_id, reason_key = int(parts[1]), parts[2]
    
    reasons = {
        "blurry": "Your photos are blurry. Please retake them clearly.",
        "receipt": "The payment receipt is missing or invalid.",
        "id": "The Fayda ID provided does not match your registration name."
    }
    reason = reasons.get(reason_key, "Invalid data provided.")
    
    # Update DB & Notify User (Re-using your existing rejection logic)
    await db.update_user(user_id, registration_step='rejected')
    
    try:
        await callback.bot.send_message(
            chat_id=user_id, 
            text=f"❌ <b>Update:</b> {reason}\n\nPlease try again.", 
            parse_mode="HTML"
        )
        await callback.message.edit_text(f"❌ Rejected for: {reason_key.upper()}")
    except Exception:
        await callback.answer("User blocked bot.", show_alert=True)
        



# --- PENDING QUEUE: THE GRACEFUL TRIAGE ---

@router.message(F.text == "⏳ Pending Applications")
async def show_pending_queue(message: types.Message, db: Database):
    pending_users = await db.get_pending_users()
    
    if not pending_users:
        return await message.answer(
            "✨ <b>Inbox Zero!</b>\nAll participants have been processed. Take a break!",
            parse_mode="HTML"
        )

    count = len(pending_users)
    await message.answer(f"📂 <b>Reviewing {count} Pending Applications:</b>", parse_mode="HTML")

    # We show the first 5 to avoid flooding, or just the most recent
    for user in pending_users[:5]: 
        # Using the same consistent card format
        card = (
            f"⏳ <b>PENDING REVIEW</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"👤 <b>NAME:</b> {user['full_name'].upper()}\n"
            f"📞 <b>PHONE:</b> <code>{user['phone_number']}</code>\n"
            f"⚖️ <b>DATA:</b> {user['age']}y | {user['current_weight_kg']}kg\n"
            f"📅 <b>APPLIED:</b> {get_relative_time(user['created_at'])}\n"
            f"━━━━━━━━━━━━━━\n"
            f"<i>Check the Admin Group for their 5-photo evidence.</i>"
        )
        
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Approve", callback_data=f"approve_{user['telegram_id']}")
        builder.button(text="❌ Reject", callback_data=f"reject_options_{user['telegram_id']}")
        # Direct link to their profile if you have a search feature
        builder.row(types.InlineKeyboardButton(text="🔍 Full Profile", callback_data=f"view_prof_{user['telegram_id']}"))
        
        await message.answer(card, reply_markup=builder.as_markup(), parse_mode="HTML")

    if count > 5:
        await message.answer(f"<i>...and {count - 5} more. Clear these first!</i>")



from aiogram.utils.media_group import MediaGroupBuilder
@router.callback_query(F.data.startswith("view_prof_"))
async def view_full_profile(callback: types.CallbackQuery, db: Database):
    user_id = int(callback.data.split("_")[2])
    user = await db.get_user(user_id)
    
    if not user:
        return await callback.answer("❌ User not found.", show_alert=True)

    # 1. Fetch Payment separately
    query = "SELECT proof_file_id FROM payments WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1"
    payment_row = await db._pool.fetchrow(query, user_id)
    payment_photo = payment_row['proof_file_id'] if payment_row else None

    # 2. Build the Dossier Text
    profile_text = (
        f"📋 <b>FULL PROFILE: {user['full_name'].upper()}</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"🆔 Telegram ID: <code>{user['telegram_id']}</code>\n"
        f"📞 Phone: <code>{user.get('phone_number', 'N/A')}</code>\n"
        f"⚖️ Stats: {user['age']}y | {user['current_weight_kg']}kg | {user['gender']}\n"
        f"🌐 Language: {user['language']}\n"
        f"━━━━━━━━━━━━━━\n"
        f"✅ Terms: {'Yes' if user['accepted_terms'] else 'No'}\n"
        f"🏥 Health: {'Yes' if user['has_health_clearance'] else 'No'}\n"
        f"━━━━━━━━━━━━━━"
    )

    # 3. Construct the 5-Photo Album
    album = MediaGroupBuilder(caption=profile_text)
    photo_count = 0
    
    # Explicit list of all 5 possible evidence photos
    proof_keys = [
        'photo_front_file_id', 
        'photo_side_file_id', 
        'photo_rear_file_id', 
        'fayda_file_id' # <--- Fixed: Explicitly checking Fayda ID
    ]

    for key in proof_keys:
        if user.get(key):
            album.add_photo(media=user[key])
            photo_count += 1
    
    # Adding the Payment Receipt from the payments table
    if payment_photo:
        album.add_photo(media=payment_photo)
        photo_count += 1

    try:
        if photo_count > 0:
            # Send the album (The profile_text is the caption of the FIRST photo)
            await callback.message.answer_media_group(media=album.build())
        else:
            # If no photos exist, send text only
            await callback.message.answer(profile_text, parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"Album send fail for {user_id}: {e}")
        # Final fallback to just the text
        await callback.message.answer(profile_text + "\n\n⚠️ <i>Photos failed to load.</i>", parse_mode="HTML")

    # 4. Final Decision Buttons (Sent at the bottom)
    if user['registration_step'] != 'verified':
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Approve", callback_data=f"approve_{user_id}")
        builder.button(text="❌ Reject", callback_data=f"reject_options_{user_id}")
        await callback.message.answer(f"<b>Verify {user['full_name']}:</b>", 
                                    reply_markup=builder.as_markup(), 
                                    parse_mode="HTML")
    
    await callback.answer()
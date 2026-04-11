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
    
    # 1. FETCH FULL CONTEXT (Added 'id' to the SELECT)
    user = await db.get_user(user_id)
    
    # CRITICAL FIX: Include 'id' here so it exists in the payment object
    payment = await db._pool.fetchrow(
        "SELECT id, status FROM payments WHERE user_id = $1 AND status = 'pending' ORDER BY created_at DESC LIMIT 1", 
        user_id
    )

    if not user:
        return await callback.answer("❌ User not found.", show_alert=True)

    # 🛑 THE SAFETY CHECK
    if not payment:
        return await callback.answer(
            "⚠️ Cannot Approve: No pending payment found for this user.", 
            show_alert=True
        )

    lang = user.get('language', 'EN')
    full_name = user.get('full_name', 'Participant')

    # 2. Update Database (Atomic Move)
    # Set 'is_paid' to True and move the step to 'verified'
    await db.update_user(user_id, registration_step='verified', is_paid=True)
    
    # Audit trail: who processed this and which specific payment ID
    admin_identity = callback.from_user.username or callback.from_user.full_name
    pay_id = payment['id'] # This will now work without KeyError
    
    await db._pool.execute(
        "UPDATE payments SET status = 'approved', processed_by = $1, processed_at = NOW() WHERE id = $2",
        admin_identity, pay_id
    )

    # 3. Update Admin UI (Visual Confirmation)
    try:
        await callback.message.edit_caption(
            caption=f"{callback.message.caption}\n\n✅ <b>APPROVED BY:</b> @{admin_identity}",
            parse_mode="HTML",
            reply_markup=None # Kill buttons to prevent double-click
        )
    except Exception:
        pass

    # 4. Handle Invite Links (The "Golden Ticket")
    # Using your existing logic to generate dynamic invite links
    try:
        group_invite = await callback.bot.create_chat_invite_link(
            chat_id=settings.CHALLENGE_GROUP_ID,
            name=f"Access: {full_name}",
            member_limit=1 # Single use for extra security
        )
        group_url = group_invite.invite_link
    except Exception:
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
    # Row 1: The Heavy Hitters
    builder.row(
        types.KeyboardButton(text="📊 Stats"),
        types.KeyboardButton(text="⏳ Pending"), 
    )
    # Row 2: Management
    builder.row(
        types.KeyboardButton(text="📢 Broadcast"),
        types.KeyboardButton(text="🔍 Search User")
    )
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
from datetime import datetime, timezone, timedelta

@router.message(F.text == "📊 Stats")
@router.message(Command("admin"))
async def admin_cmd(message: types.Message, db: Database):
    stats = await db.get_funnel_stats()
    
    # Ethiopia Time (UTC+3)
    eth_time = datetime.now(timezone.utc) + timedelta(hours=3)
    time_str = eth_time.strftime("%H:%M:%S")

    # Visual Funnel Builder
    # We use emojis to create a "Progress Bar" feel
    text = (
        "🛠 <b>ADMIN CONTROL PANEL</b> ⚡️\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📈 <b>REGISTRATION FUNNEL</b>\n\n"
        
        f"👣 <b>Step 1: Interest</b>\n"
        f"├ Start: <code>{stats['start']}</code>\n"
        f"└ Contacted: <code>{stats['phone']}</code>\n\n"
        
        f"⚖️ <b>Step 2: Profile Prep</b>\n"
        f"├ Bio/Weight: <code>{stats['gender'] + stats['age'] + stats['weight']}</code>\n"
        f"└ Legal Agreed: <code>{stats['legal']}</code>\n\n"
        
        f"💰 <b>Step 3: The Money Gate</b>\n"
        f"└ <b>Awaiting Payment: <code>{stats['payment']}</code></b> ⚠️\n\n"
        
        f"📸 <b>Step 4: The Photo Gap</b>\n"
        f"└ <b>Paid but missing Photos: <code>{stats['photo']}</code></b> 🚨\n\n"
        
        "🏆 <b>FINAL RESULTS</b>\n"
        f"├ ✅ Verified: <b>{stats['verified']}</b>\n"
        f"├ ⏳ Reviewing: <b>{stats['pending']}</b>\n"
        f"└ ❌ Rejected: <b>{stats['rejected']}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>REVENUE: {stats['revenue']:,} ETB</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🕒 <i>Last Update: {time_str}</i>"
    )

    await message.answer(
        text,
        reply_markup=admin_refresh_kb(), # Your inline refresh button
        parse_mode="HTML"
    )
    
    await message.answer("Admin Menu Active 🛠", reply_markup=admin_reply_menu())

# --- 4. THE REFRESH CALLBACK (Edits the existing card) ---
@router.callback_query(F.data == "admin_stats_refresh")
async def refresh_stats_callback(callback: types.CallbackQuery, db: Database):
    # 1. Fetch the NEW funnel stats
    stats = await db.get_funnel_stats()
    
    # 2. Sync Timezones (UTC+3 for Ethiopia)
    eth_time = datetime.now(timezone.utc) + timedelta(hours=3)
    now_time_str = eth_time.strftime("%H:%M:%S")
    
    # 3. Rebuild the EXACT funnel UI
    text = (
        "🛠 <b>ADMIN CONTROL PANEL</b> ⚡️\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📈 <b>REGISTRATION FUNNEL (LIVE)</b>\n\n"
        
        f"👣 <b>Step 1: Interest</b>\n"
        f"├ Start: <code>{stats['start']}</code>\n"
        f"└ Contacted: <code>{stats['phone']}</code>\n\n"
        
        f"⚖️ <b>Step 2: Profile Prep</b>\n"
        f"├ Bio/Weight: <code>{stats['gender'] + stats['age'] + stats['weight']}</code>\n"
        f"└ Legal Agreed: <code>{stats['legal']}</code>\n\n"
        
        f"💰 <b>Step 3: The Money Gate</b>\n"
        f"└ <b>Awaiting Payment: <code>{stats['payment']}</code></b> ⚠️\n\n"
        
        f"📸 <b>Step 4: The Photo Gap</b>\n"
        f"└ <b>Paid but missing Photos: <code>{stats['photo']}</code></b> 🚨\n\n"
        
        "🏆 <b>FINAL RESULTS</b>\n"
        f"├ ✅ Verified: <b>{stats['verified']}</b>\n"
        f"├ ⏳ Reviewing: <b>{stats['pending']}</b>\n"
        f"└ ❌ Rejected: <b>{stats['rejected']}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>REVENUE: {stats['revenue']:,} ETB</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🕒 <i>Last Refreshed: {now_time_str}</i>"
    )
    
    try:
        await callback.message.edit_text(
            text, 
            reply_markup=admin_refresh_kb(), 
            parse_mode="HTML"
        )
        await callback.answer("Stats Updated! 🔄")
    except Exception:
        # This triggers if stats are exactly the same (Telegram doesn't allow 'editing' to identical text)
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


@router.message(F.text == "⏳ Pending")
async def show_pending_menu(message: types.Message):
    await message.answer(
        "📂 <b>PENDING MANAGEMENT</b>\n"
        "Choose a category to review:",
        reply_markup=pending_management_menu(),
        parse_mode="HTML"
    )
    
@router.message(F.text == "💰 P. Payments")
async def show_pending_payments(message: types.Message, db: Database):
    # Fetch payments where status is 'pending'
    query = """
        SELECT p.*, u.full_name, u.phone_number, u.telegram_id as user_id
        FROM payments p 
        JOIN users u ON p.user_id = u.telegram_id 
        WHERE p.status = 'pending'
        ORDER BY p.created_at ASC
    """
    pending_pays = await db._pool.fetch(query)

    if not pending_pays:
        return await message.answer("✅ <b>All payments verified!</b>", parse_mode="HTML")

    await message.answer(f"💳 <b>{len(pending_pays)} Unverified Receipts:</b>", parse_mode="HTML")

    for pay in pending_pays[:5]:
        user_id = pay['user_id']
        
        # --- LIVE TELEGRAM FETCH FOR CLICKABLE LINK ---
        try:
            chat = await message.bot.get_chat(user_id)
            username = chat.username
            # If they have a @username, use it. If not, use the tg:// link (God Mode)
            user_link = f"@{username}" if username else f'<a href="tg://user?id={user_id}">Direct Link</a>'
        except Exception:
            # Fallback if the bot can't fetch the chat info
            user_link = "<i>(Private/Hidden)</i>"

        pay_card = (
            f"💰 <b>RECEIPT REVIEW</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"👤 <b>USER:</b> {pay['full_name'].upper()}\n"
            f"🆔 <b>USERNAME:</b> {user_link}\n"
            f"📞 <b>PHONE:</b> <code>{pay['phone_number']}</code>\n"
            f"💵 <b>AMOUNT:</b> {pay['amount']} ETB\n"
            f"📅 <b>SENT:</b> {pay['created_at'].strftime('%Y-%m-%d %H:%M')}\n"
            f"━━━━━━━━━━━━━━"
        )
        
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Mark Paid", callback_data=f"pay_approve_{pay['id']}")
        builder.button(text="❌ Bad Receipt", callback_data=f"pay_reject_{pay['id']}")
        builder.row(types.InlineKeyboardButton(text="🔍 View Application", callback_data=f"view_prof_{user_id}"))

        # Safety check for the photo before sending
        photo_id = pay['proof_file_id']
        try:
            if photo_id:
                await message.answer_photo(
                    photo=photo_id,
                    caption=pay_card,
                    reply_markup=builder.as_markup(),
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    pay_card + "\n⚠️ <i>Receipt photo missing!</i>",
                    reply_markup=builder.as_markup(),
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Failed to send payment card for {user_id}: {e}")
            
            
@router.callback_query(F.data.startswith("pay_reject_"))
async def reject_payment(callback: types.CallbackQuery, db: Database):
    payment_id = int(callback.data.replace("pay_reject_", ""))
    
    # 1. Fetch user info
    query_user = "SELECT user_id FROM payments WHERE id = $1"
    payment_data = await db._pool.fetchrow(query_user, payment_id)
    
    if not payment_data:
        return await callback.answer("❌ Record not found.")

    user_id = payment_data['user_id']
    
    # FIX 1: In a callback handler, use callback.from_user (not message.from_user)
    admin_identity = callback.from_user.username or callback.from_user.full_name
    
    # 2. Update DB status to 'rejected'
    # FIX 2: Variable name must be payment_id (lowercase 'i')
    await db._pool.execute(
        """
        UPDATE payments 
        SET status = 'rejected', processed_by = $1, processed_at = NOW() 
        WHERE id = $2
        """,
        admin_identity, payment_id
    )
    
    # Update registration step so /start or 'Resume' works correctly
    await db.update_user(user_id, registration_step='rejected')

    # 3. Notify the User (Bilingual)
    user = await db.get_user(user_id)
    lang = user.get('language', 'EN')
    
    if lang == "EN":
        rejection_text = (
            "❌ <b>Payment Not Verified</b>\n\n"
            "Your receipt was rejected. This usually happens if the screenshot is blurry, "
            "incorrect, or already used. Please try again with a clear receipt."
        )
    else:
        rejection_text = (
            "❌ <b>ክፍያዎ አልተረጋገጠም</b>\n\n"
            "የላኩት ደረሰኝ ተቀባይነት አላገኘም። ምናልባት ደረሰኙ ግልጽ ካልሆነ ወይም የተሳሳተ ከሆነ ሊሆን ይችላል። "
            "እባክዎን ትክክለኛውን ደረሰኝ በድጋሚ ይላኩ።"
        )

    retry_kb = InlineKeyboardBuilder()
    retry_kb.button(text="🔄 Try Again / ድጋሚ ሞክር", callback_data="resume_reg")

    try:
        await callback.bot.send_message(
            user_id, 
            rejection_text, 
            reply_markup=retry_kb.as_markup(), 
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Could not notify user {user_id} of rejection: {e}")

    # 4. Update Admin UI
    # We remove the buttons and add the admin's name for accountability
    try:
        await callback.message.edit_caption(
            caption=f"{callback.message.caption}\n\n🔴 <b>REJECTED BY:</b> @{admin_identity}",
            parse_mode="HTML",
            reply_markup=None # Removes the buttons so no one clicks again
        )
    except Exception:
        pass
        
    await callback.answer("Entry Rejected ❌")

@router.message(F.text == "🔙 Back")
async def back_to_admin_main(message: types.Message, db: Database):
    """
    Returns the admin to the main dashboard and restores 
    the original Admin Reply Keyboard.
    """
    # 1. We reuse the admin_cmd logic to show the fresh funnel
    await admin_cmd(message, db)
    
    # 2. Optionally, send a small confirmation toast/alert
    # (The main admin_cmd already sends the reply_markup=admin_reply_menu())
@router.callback_query(F.data.startswith("pay_approve_"))
async def approve_payment_only(callback: types.CallbackQuery, db: Database):
    # 1. Extract and ID Check
    pay_id = int(callback.data.split("_")[2])
    admin_identity = callback.from_user.username or callback.from_user.full_name
    
    # 2. Check current status to prevent "Double Processing"
    status = await db._pool.fetchval("SELECT status FROM payments WHERE id = $1", pay_id)
    if status == 'approved':
        return await callback.answer("✅ Already approved!")

    # 3. Atomic Update (Payments + Users)
    # Added 'processed_by' to the query for the Audit Log
    query = """
        WITH updated_pay AS (
            UPDATE payments 
            SET status = 'approved', 
                processed_at = CURRENT_TIMESTAMP,
                processed_by = $2
            WHERE id = $1 AND status = 'pending'
            RETURNING user_id
        )
        UPDATE users 
        SET is_paid = TRUE 
        WHERE telegram_id = (SELECT user_id FROM updated_pay)
        RETURNING full_name;
    """
    user_name = await db._pool.fetchval(query, pay_id, admin_identity)

    if not user_name:
        # This triggers if the payment status was changed by another admin 
        # between the 'fetchval' and the 'UPDATE'
        return await callback.answer("❌ Payment already processed by another admin.")

    # 4. Update Admin UI
    await callback.message.edit_caption(
        caption=f"{callback.message.caption}\n\n✅ <b>APPROVED BY:</b> @{admin_identity}",
        parse_mode="HTML",
        reply_markup=None # Clean UI: buttons disappear instantly
    )
    
    await callback.answer(f"Payment for {user_name} verified!")

@router.message(F.text == "📂 P. Applications")
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


from aiogram.utils.keyboard import ReplyKeyboardBuilder
def pending_management_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📂 P. Applications")
    builder.button(text="💰 P. Payments")
    builder.button(text="📜 All Trans.")  # New Log Button
    builder.button(text="🔙 Back")
    builder.adjust(2, 2) # Rows of 2, 2
    return builder.as_markup(resize_keyboard=True)

from math import ceil
from aiogram.types import InputMediaPhoto
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder

@router.message(F.text == "📜 All Trans.")
async def show_all_transactions(message: types.Message, db: Database, page: int = 1):
    # OFFSET logic for "1 Card at a Time" (The Premium approach)
    limit = 1
    offset = (page - 1) * limit

    # 1. FETCH DATA (Joined User + Payment + Proof Image)
    query = """
        SELECT p.id, p.status, p.processed_by, p.processed_at, 
               u.full_name, p.amount, p.proof_file_id, u.telegram_id
        FROM payments p
        JOIN users u ON p.user_id = u.telegram_id
        ORDER BY p.created_at DESC
        LIMIT $1 OFFSET $2
    """
    count_query = "SELECT COUNT(*) FROM payments"
    
    row = await db._pool.fetchrow(query, limit, offset)
    total_count = await db._pool.fetchval(count_query) or 0

    if not row:
        return await message.answer("<b>× ARCHIVE_EMPTY // NO_RECORDS_FOUND</b>")

    # 2. 2030 CINEMATIC CAPTION
    # Status styling for instant recognition
    status_map = {
        'approved': "🟢 VERIFIED_SUCCESS",
        'rejected': "🔴 DECLINED_VOID",
        'pending':  "🟡 IN_REVIEW"
    }
    status_label = status_map.get(row['status'], "⚪ UNKNOWN")
    
    caption = (
        f"<b>── TRANSACTION_RECORD ──</b>\n"
        f"👤 <b>CLIENT:</b> {row['full_name'].upper()}\n"
        f"🆔 <b>TG_ID:</b> <code>{row['telegram_id']}</code>\n"
        f"💰 <b>VALUE:</b> <code>{row['amount']} ETB</code>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📑 <b>STATUS:</b> {status_label}\n"
        f"🕒 <b>DATE:</b> {row['processed_at'].strftime('%Y/%m/%d %H:%M') if row['processed_at'] else 'PENDING'}\n"
        f"👨‍💻 <b>ADMIN:</b> {row['processed_by'] or 'AUTO_SYSTEM'}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"<code>LOG_ENTRY: {page} // TOTAL_ENTRIES: {total_count}</code>"
    )

    # 3. DYNAMIC NAVIGATION
    builder = InlineKeyboardBuilder()
    
    # Navigation Row (Arrow Emojis + Modern Text)
    nav_row = []
    if page > 1:
        nav_row.append(types.InlineKeyboardButton(text="« PREV", callback_data=f"alltrans_p_{page-1}"))
    if page < total_count:
        nav_row.append(types.InlineKeyboardButton(text="NEXT »", callback_data=f"alltrans_p_{page+1}"))
    
    if nav_row:
        builder.row(*nav_row)

    # 4. EXECUTION (The UI Switcher)
    try:
        # If message comes from a callback (Next/Prev), we swap the media
        if message.from_user.is_bot:
            await message.edit_media(
                media=InputMediaPhoto(
                    media=row['proof_file_id'], 
                    caption=caption, 
                    parse_mode="HTML"
                ),
                reply_markup=builder.as_markup()
            )
        else:
            # If it's a fresh text command, send new photo
            await message.answer_photo(
                photo=row['proof_file_id'],
                caption=caption,
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await message.answer("🔄 Record current.")
        else:
            logging.error(f"UI Update Failed: {e}")

# 5. THE CALLBACK ROUTER
@router.callback_query(F.data.startswith("alltrans_p_"))
async def paginate_transactions(callback: types.CallbackQuery, db: Database):
    page = int(callback.data.split("_")[-1])
    await show_all_transactions(callback.message, db, page=page)
    await callback.answer()
    
    
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
    


class BroadcastStates(StatesGroup):
    selecting_target = State()
    writing_msg = State()
    confirming = State()

# --- STEP 1: TRIGGER & TARGET SELECTION ---
@router.message(F.text == "📢 Broadcast") # Restricted to Admin in your middleware/filter
async def start_broadcast(message: types.Message, state: FSMContext):
    await state.clear()
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="✅ Verified Only", callback_data="target_verified"))
    kb.row(types.InlineKeyboardButton(text="❌ Unverified Leads", callback_data="target_unverified"))
    kb.row(types.InlineKeyboardButton(text="🌐 Everyone (All)", callback_data="target_all"))
    kb.row(types.InlineKeyboardButton(text="🚫 Cancel", callback_data="cancel_broadcast"))
    
    await message.answer(
        "🎯 <b>BROADCAST ENGINE</b>\n\nSelect the target audience for this transmission:",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await state.set_state(BroadcastStates.selecting_target)

# --- STEP 2: SHOW STATS & ASK FOR CONTENT ---
@router.callback_query(BroadcastStates.selecting_target, F.data.startswith("target_"))
async def select_target(callback: types.CallbackQuery, state: FSMContext, db: Database):
    target = callback.data.split("_")[1]
    
    # Get count from DB (You'll need to implement this method in your DB class)
    count = await db.get_user_count_by_status(target) 
    
    await state.update_data(target=target, count=count)
    
    await callback.message.edit_text(
        f"👥 <b>Target:</b> {target.upper()}\n"
        f"📊 <b>Reach:</b> {count} users\n\n"
        "Please send the message content now.\n"
        "<i>Supports HTML: <b>bold</b>, <i>italic</i>, <a href='...'>links</a>.</i>",
        parse_mode="HTML"
    )
    await state.set_state(BroadcastStates.writing_msg)

# --- STEP 3: THE PREVIEW GATEWAY ---
@router.message(BroadcastStates.writing_msg)
async def preview_broadcast(message: types.Message, state: FSMContext):
    content = message.text
    data = await state.get_data()
    
    await state.update_data(message_text=content)
    
    confirm_kb = InlineKeyboardBuilder()
    confirm_kb.row(types.InlineKeyboardButton(text="🚀 CONFIRM & SEND", callback_data="confirm_broadcast"))
    confirm_kb.row(types.InlineKeyboardButton(text="✍️ Edit Message", callback_data=f"target_{data['target']}"))
    
    # We show the admin EXACTLY how it will look
    await message.answer("🧪 <b>PREVIEW:</b>")
    await message.answer(content, parse_mode="HTML")
    await message.answer(
        f"────────────────────\n"
        f"⚠️ <b>Ready to send to {data['count']} users?</b>",
        reply_markup=confirm_kb.as_markup(),
        parse_mode="HTML"
    )
    await state.set_state(BroadcastStates.confirming)

# --- STEP 4: DISPATCH ---
@router.callback_query(BroadcastStates.confirming, F.data == "confirm_broadcast")
async def dispatch_broadcast(callback: types.CallbackQuery, state: FSMContext, db: Database):
    data = await state.get_data()
    users = await db.get_users_for_broadcast(data['target']) # Returns list of user_ids
    
    await callback.message.edit_text(f"🚀 Dispatching to {len(users)} users... please wait.")
    
    success = 0
    blocked = 0
    
    for user_id in users:
        try:
            await callback.bot.send_message(user_id, data['message_text'], parse_mode="HTML")
            success += 1
            await asyncio.sleep(0.05) # Prevent Flood Limit
        except Exception:
            blocked += 1
            
    await callback.message.answer(
        f"🏁 <b>BROADCAST COMPLETE</b>\n\n"
        f"✅ Delivered: {success}\n"
        f"🚫 Blocked/Failed: {blocked}",
        reply_markup=admin_reply_menu(),
        parse_mode="HTML"
    )
    await state.clear()
import logging
import asyncio
from aiogram.utils.media_group import MediaGroupBuilder
from config import settings
from keyboards import inline as kb
from aiogram import Router, types
from utils.localization import get_member_card

# Initialize logger for this module
logger = logging.getLogger(__name__)
router = Router(name="tasks")
from aiogram.utils.media_group import MediaGroupBuilder
import logging

logger = logging.getLogger(__name__)
import logging
from aiogram.utils.media_group import MediaGroupBuilder
from config import settings
from utils.localization import get_member_card

logger = logging.getLogger(__name__)

async def send_to_admin_group(bot, user_id: int, data: dict, payment_photo: str):
    """
    Handles background delivery of registration data to Admins and the User.
    Optimized for high-reliability and clean Admin UI.
    """
    admin_group_id = settings.ADMIN_NEW_USER_LOG_ID 
    lang = data.get('language', 'EN')
    full_name = data.get('full_name', 'Participant')
    
    # Generate ID for display
    member_no = f"EW1-2026-{str(user_id)[-4:]}"

    # --- 1. USER NOTIFICATION (Instant Feedback) ---
    try:
        user_card_text = get_member_card(
            lang, 
            user_id, 
            full_name, 
            registration_step='verification_pending'
        )
        
        await bot.send_message(
            chat_id=user_id,
            text=user_card_text,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"❌ User Card Notify Fail {user_id}: {e}")

    # --- 2. ADMIN DOSSIER (The Full Gallery) ---
    try:
        # Build a cleaner, more 'Surgical' Admin Caption
        admin_caption = (
            f"🔔 <b>NEW CHALLENGE APPLICATION</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>NAME:</b> {full_name.upper()}\n"
            f"🔢 <b>CODE:</b> <code>{member_no}</code>\n"
            f"📞 <b>PHONE:</b> <code>{data.get('phone_number', 'N/A')}</code>\n"
            f"⚖️ <b>WEIGHT:</b> {data.get('current_weight_kg')}kg | <b>AGE:</b> {data.get('age')}\n"
            f"────────────────────\n"
            f"✅ <b>Terms:</b> {'Yes' if data.get('accepted_terms') else 'No'}\n"
            f"🏥 <b>Health:</b> {'Yes' if data.get('has_health_clearance') else 'No'}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🖼 <i>5 Photos: Front | Side | Rear | ID | Receipt</i>"
        )

        album = MediaGroupBuilder(caption=admin_caption)
        
        # We use a list to make adding photos safer/cleaner
        photos = [
            data['photo_front_file_id'],
            data['photo_side_file_id'],
            data['photo_rear_file_id'],
            data['fayda_file_id'],
            payment_photo
        ]

        for photo in photos:
            album.add_photo(media=photo)

        # Send the Media Group
        # Senior Tip: We store the returned message list to use the first ID for the reply
        messages = await bot.send_media_group(chat_id=admin_group_id, media=album.build())

        # --- 3. DECISION BUTTONS ---
        # We reply to the FIRST photo of the album. 
        # This keeps the 'Approve' buttons physically attached to the photos.
        decision_text = (
            f"📋 <b>Review Required:</b> {full_name}\n"
            f"<i>Action will notify the user immediately.</i>"
        )
        
        await bot.send_message(
            chat_id=admin_group_id,
            text=decision_text,
            reply_to_message_id=messages[0].message_id,
            reply_markup=kb.admin_verify_keyboard(user_id), # Ensure this helper exists
            parse_mode="HTML"
        )
        
        logger.info(f"✅ Full Dossier sent to Admin for User {user_id}")

    except Exception as e:
        # If the MediaGroup fails, we send a 'Panic' text so the Admin knows someone applied
        logger.error(f"🚨 CRITICAL: Admin Gallery Fail for {user_id}: {e}")
        error_report = (
            f"🚨 <b>GALLERY FAILED TO LOAD</b>\n"
            f"User {full_name} ({user_id}) submitted but photos couldn't bundle.\n"
            f"Please check the Database/Logs."
        )
        await bot.send_message(chat_id=admin_group_id, text=error_report)
async def notify_new_lead(bot, user_id: int, data: dict):
    """
    Notifies the Leads Group with a LIVE fetched clickable Telegram username/ID.
    This fires the moment they agree to terms but BEFORE they pay.
    """
    lead_group_id = settings.ADMIN_NEW_LEAD_LOG_ID
    full_name = data.get('full_name', 'Unknown')
    
    # --- LIVE TELEGRAM FETCH (The Elite Way) ---
    try:
        chat = await bot.get_chat(user_id)
        username = chat.username
        # Use @username if it exists, otherwise the 'God Mode' ID link
        user_link = f"@{username}" if username else f'<a href="tg://user?id={user_id}">Direct Link</a>'
    except Exception as e:
        logger.warning(f"Could not fetch live chat for Lead {user_id}: {e}")
        user_link = "<i>(Private/Hidden)</i>"
    
    # Mapping Logic for Yes/No
    terms_status = "✅ YES" if data.get('accepted_terms') else "❌ NO"
    health_status = "✅ YES" if data.get('has_health_clearance') else "❌ NO"

    lead_caption = (
        f"🎯 <b>NEW HOT LEAD (PRE-PAYMENT)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>NAME:</b> {full_name.upper()}\n"
        f"🆔 <b>USER:</b> {user_link}\n"
        f"📞 <b>PHONE:</b> <code>{data.get('phone_number', 'N/A')}</code>\n"
        f"⚖️ <b>WEIGHT:</b> {data.get('current_weight_kg')}kg | <b>AGE:</b> {data.get('age')}\n"
        f"────────────────────\n"
        f"📜 <b>Terms:</b> {terms_status}\n"
        f"🏥 <b>Health:</b> {health_status}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Status: Viewing Payment Instructions...</i>"
    )

    try:
        await bot.send_message(
            chat_id=lead_group_id, 
            text=lead_caption, 
            parse_mode="HTML",
            disable_web_page_preview=True # Keeps the group clean
        )
        logger.info(f"✅ Lead Alert sent for {user_id}")
    except Exception as e:
        logger.error(f"❌ Lead Notify Fail: {e}")


async def notify_payment_submitted(bot, user_id: int, data: dict, proof_photo: str):
    """
    STARK ALERT: Fetches live Telegram data to ensure the Admin 
    always has a fresh, clickable link to the user.
    """
    admin_group_id = settings.ADMIN_NEW_USER_LOG_ID 
    full_name = data.get('full_name', 'Unknown')
    
    # --- LIVE TELEGRAM FETCH ---
    try:
        chat = await bot.get_chat(user_id)
        username = chat.username
        user_link = f"@{username}" if username else f'<a href="tg://user?id={user_id}">Direct Link</a>'
    except Exception as e:
        logger.warning(f"Could not fetch live chat for {user_id}: {e}")
        user_link = "<i>(Hidden/Private)</i>"

    # --- CAPTION DESIGN ---
    caption = (
        f"💰 <b>NEW PAYMENT SUBMITTED</b> 💳\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>NAME:</b> {full_name.upper()}\n"
        f"🆔 <b>USER:</b> {user_link}\n"
        f"📞 <b>PHONE:</b> <code>{data.get('phone_number', 'N/A')}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ <b>STATUS:</b> Awaiting Finance Review\n"
        f"📸 <b>NEXT STEP:</b> User is now taking body photos.\n\n"
        f"<i>Check the 'Pending Payments' dashboard to verify.</i>"
    )

    try:
        await bot.send_photo(
            chat_id=admin_group_id,
            photo=proof_photo,
            caption=caption,
            parse_mode="HTML"
        )
        logger.info(f"✅ Live Payment Alert sent for {user_id}")
    except Exception as e:
        logger.error(f"❌ Payment Alert Fail for {user_id}: {e}")
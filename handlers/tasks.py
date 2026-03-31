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
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
async def send_to_admin_group(bot, user_id: int, data: dict, payment_photo: str):
    """
    Handles background delivery of registration data to Admins and the User.
    Updated for 5-photo validation and dynamic card status.
    """
    admin_group_id = settings.ADMIN_NEW_USER_LOG_ID 
    lang = data.get('language', 'EN')
    full_name = data.get('full_name', 'Participant')
    
    # Generate the Code (Used for display only here)
    member_no = f"EW1-2026-{str(user_id)[-4:]}"

    # --- 1. USER NOTIFICATION (Digital Card) ---
    try:
        # Pass 'verification_pending' since they just finished the process
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
        logger.error(f"User Card Notify Fail {user_id}: {e}")

    # --- 2. ADMIN NOTIFICATION (The Full Gallery) ---
    try:
        admin_caption = (
            f"🔔 <b>NEW CHALLENGE APPLICATION</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Name:</b> {full_name}\n"
            f"🔢 <b>CODE:</b> <code>{member_no}</code>\n"
            f"📞 <b>Phone:</b> <code>{data.get('phone_number', 'N/A')}</code>\n"
            f"⚖️ <b>Weight:</b> {data.get('current_weight_kg')}kg | <b>Age:</b> {data.get('age')}\n"
            f"✅ Terms: {'Yes' if data.get('accepted_terms') else 'No'}\n"
            f"🏥 Health Clear: {'Yes' if data.get('has_health_clearance') else 'No'}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🖼 <i>Check all 5 photos below (3 Body, 1 ID, 1 Payment)</i>"
        )

        album = MediaGroupBuilder(caption=admin_caption)
        
        # Adding the 5 Proofs in order
        album.add_photo(media=data['photo_front_file_id'])
        album.add_photo(media=data['photo_side_file_id'])
        album.add_photo(media=data['photo_rear_file_id'])
        album.add_photo(media=data['fayda_file_id'])
        album.add_photo(media=payment_photo)

        # Send the media group
        messages = await bot.send_media_group(chat_id=admin_group_id, media=album.build())

        # --- 3. DECISION BUTTONS ---
        # Reply to the first photo of the album to keep the chat organized
        await bot.send_message(
            chat_id=admin_group_id,
            text=f"Review required for <b>{full_name}</b>:",
            reply_to_message_id=messages[0].message_id,
            reply_markup=kb.admin_verify_keyboard(user_id),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"ADMIN NOTIFY ERROR for user {user_id}: {e}")
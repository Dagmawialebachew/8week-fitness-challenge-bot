import asyncio
import logging
from aiogram import Router, types, F
from aiogram.types import ChatJoinRequest
from database.db import Database
from config import settings
from aiogram.enums import ContentType

router = Router(name="group")
logger = logging.getLogger(__name__)

def get_stealth_name(full_name: str) -> str:
    """Converts 'Dagmawi Tewodros' to 'Dagmawi T.' for privacy."""
    parts = full_name.split()
    if len(parts) > 1:
        return f"{parts[0].capitalize()} {parts[1][0].upper()}."
    return full_name.capitalize()


# --- THE SERVICE MESSAGE CLEANER ---
# @router.message(F.content_type.in_({ContentType.NEW_CHAT_MEMBERS, ContentType.LEFT_CHAT_MEMBER}))
# async def clean_service_messages(message: types.Message):
#     """
#     Instantly deletes 'User joined' and 'User left' system messages 
#     to keep the group professional and clean.
#     """
#     try:
#         await message.delete()
#     except Exception as e:
#         logger.error(f"Failed to delete service message: {e}")
        
        
@router.chat_join_request()
async def handle_join_request(update: ChatJoinRequest, db: Database):
    user_id = update.from_user.id
    chat_id = update.chat.id 
    
    # Identify IDs
    target_group_id = int(settings.CHALLENGE_GROUP_ID)
    target_channel_id = int(settings.CHALLENGE_CHANNEL_ID)

    # 1. Determine Target
    is_group = chat_id == target_group_id
    is_channel = chat_id == target_channel_id

    # If it's neither, ignore it completely
    if not (is_group or is_channel):
        return

    # 2. Check Database for Status
    user = await db.get_user(user_id)
    lang = user.get('language', 'EN') if user else 'EN'
    is_verified = user and user.get('is_paid') and user.get('registration_step') == 'verified'
    
    if is_verified:
        try:
            # --- ACCESS GRANTED (Group & Channel) ---
            await update.approve()
            
            # 3. ONLY run the extra Welcome/DM logic if they are joining the GROUP
            if is_group:
                stealth_name = get_stealth_name(user.get('full_name', 'Challenger'))
                
                # Localized DM
                if lang == "EN":
                    success_dm = (
                        "🎊 <b>ACCESS GRANTED!</b>\n\n"
                        "The system verified your membership. You are now officially in.\n\n"
                        "📍 <b>WHERE IS THE GROUP?</b>\n"
                        "• Check your <b>Chat List</b> for the '8-Week Fitness Challenge' group.\n"
                        "• Or simply <b>click the 'Join' button</b> in the message above.\n\n"
                        "💪 <i>Go introduce yourself, we start soon!</i>"
                    )
                else:
                    success_dm = (
                        "🎊 <b>መግቢያ ተፈቅዶልዎታል!</b>\n\n"
                        "ሲስተሙ አባልነትዎን አረጋግጧል። አሁን በይፋ ተቀላቅለዋል።\n\n"
                        "📍 <b>ግሩፑን የት ያገኙታል?</b>\n"
                        "• የቴሌግራም <b>Chat List</b> ውስጥ '8-Week Fitness Challenge' የሚለውን ይፈልጉ።\n"
                        "• ወይም ከላይ የላክንልዎትን <b>'Join' የሚለውን በተን</b> ይጫኑ።\n\n"
                        "💪 <i>ወደ ግሩፑ በመግባት እራስዎን ያስተዋውቁ፤ በቅርቡ እንጀምራለን!</i>"
                    )
                
                await update.bot.send_message(chat_id=user_id, text=success_dm, parse_mode="HTML")
                
                # Public Group Welcome
                welcome_text = (
                    f"🚀 <b>አዲስ ተሳታፊ ተቀላቅሏል!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"እንኳን ደህና መጣህ/ሽ <b>{stealth_name}</b>!\n"
                    f"Member ID: <code>#EW1-{str(user_id)[-4:]}</code>\n"
                    f"━━━━━━━━━━━━━━━━━━"
                )
                welcome_msg = await update.bot.send_message(chat_id=chat_id, text=welcome_text, parse_mode="HTML")

                # Auto-Cleanup
                await asyncio.sleep(60)
                try:
                    await update.bot.delete_message(chat_id=chat_id, message_id=welcome_msg.message_id)
                except:
                    pass 

            logger.info(f"✅ Approved {user_id} for {'Group' if is_group else 'Channel'}")
            
        except Exception as e:
            logger.error(f"Approval error for {user_id}: {e}")
    
    else:
        # --- ACCESS DENIED ---
        try:
            await update.decline()
            
            # 4. ONLY send the "Decline" DM if they were trying to join the GROUP
            # Channel declines will be silent (nothing happens for the user)
            if is_group:
                if lang == "EN":
                    reject_msg = (
                        "⚠️ <b>ACCESS DENIED</b>\n\n"
                        "Your payment hasn't been verified yet. Please wait for the bot confirmation."
                    )
                else:
                    reject_msg = (
                        "⚠️ <b>መግቢያ አልተፈቀደም</b>\n\n"
                        "ክፍያዎ ገና አልተረጋገጠም። እባክዎን የቦቱን ማረጋገጫ መልእክት ይጠብቁ።"
                    )
                await update.bot.send_message(chat_id=user_id, text=reject_msg, parse_mode="HTML")
                
        except Exception as e:
            logger.error(f"Decline error for {user_id}: {e}")
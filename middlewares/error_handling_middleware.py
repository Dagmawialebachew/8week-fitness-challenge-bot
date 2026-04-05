import logging
import traceback
from typing import Any, Dict
from aiogram import Router, types
from aiogram.types import ErrorEvent, BufferedInputFile
from config import settings

router = Router()
@router.error()
async def global_error_handler(event: ErrorEvent, **data): # Capture middleware data via **data
    # 1. Log to console for local debugging
    logging.exception(f"Engine Exception: {event.exception}")

    # 2. Extract Bot and Update
    # In Aiogram 3, the bot is usually in the middleware data
    bot = data.get("bot") 
    update = event.update
    
    # 3. Robust User/Context Extraction
    user = None
    if update.message:
        user = update.message.from_user
    elif update.callback_query:
        user = update.callback_query.from_user
    
    user_id = user.id if user else 0
    username = f"@{user.username}" if user and user.username else "Unknown"

    # 4. Notify Admin Group
    if settings.ADMIN_ERROR_LOG_ID and bot:
        try:
            # Get the full traceback
            tb_list = traceback.format_exception(None, event.exception, event.exception.__traceback__)
            tb_text = "".join(tb_list)
            
            # Create a buffered file for the traceback
            log_file = BufferedInputFile(tb_text.encode(), filename=f"error_{user_id}.txt")
            
            caption = (
                f"🚨 <b>CHALLENGE ENGINE ERROR</b>\n"
                f"————————————————————\n"
                f"👤 <b>User:</b> {username} (<code>{user_id}</code>)\n"
                f"⚠️ <b>Exception:</b> <code>{type(event.exception).__name__}</code>\n"
                f"📝 <b>Brief:</b> <code>{str(event.exception)[:100]}</code>"
            )
            
            # Use the bot instance from the data to send the document
            await bot.send_document(
                chat_id=settings.ADMIN_ERROR_LOG_ID,
                document=log_file,
                caption=caption,
                parse_mode="HTML"
            )
        except Exception as log_err:
            # This shows up in your terminal if the admin send fails
            logging.error(f"CRITICAL: Failed to send error to admin group: {log_err}")

    # 5. User Recovery Logic
    try:
        # Get language from user data or fallback to 'EN'
        lang = data.get("language", "EN")
        error_msg = (
            "⚠️ <b>System Update</b>\n\nWe are experiencing heavy traffic. Please wait a moment."
            if lang == "EN" else
            "⚠️ <b>ሲስተም ማሻሻያ</b>\n\nከፍተኛ የተጠቃሚ ቁጥር ስላለ እባክዎን ከጥቂት ደቂቃ በኋላ እንደገና ይሞክሩ።"
        )
        
        if update.message:
            await update.message.answer(error_msg, parse_mode="HTML")
        elif update.callback_query:
            await update.callback_query.message.answer(error_msg, parse_mode="HTML")
            await update.callback_query.answer()
    except Exception:
        pass 

    return True
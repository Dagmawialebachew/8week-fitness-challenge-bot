import logging
import traceback
from typing import Any, Dict
from aiogram import Router, types
from aiogram.types import ErrorEvent, BufferedInputFile
from config import settings

router = Router(name="error_handler")

@router.error()
async def global_error_handler(event: ErrorEvent): # Removed 'data' from arguments
    # 1. Log to console
    logging.exception(f"Engine Exception: {event.exception}")

    # 2. Context Extraction
    # Access 'data' via the event object instead of a positional argument
    data = event.data 
    bot = event.bot # ErrorEvent has direct access to the bot
    
    # Robust user extraction
    user = None
    if event.update.message:
        user = event.update.message.from_user
    elif event.update.callback_query:
        user = event.update.callback_query.from_user
    
    user_id = user.id if user else 0
    username = f"@{user.username}" if user and user.username else "Unknown"

    # 3. Notify Admin Group with Technical Details
    if settings.ADMIN_ERROR_LOG_ID:
        try:
            # Important: format_exception returns the actual traceback of the error that triggered the handler
            tb_text = "".join(traceback.format_exception(None, event.exception, event.exception.__traceback__))
            log_file = BufferedInputFile(tb_text.encode(), filename=f"error_8week_{user_id}.txt")
            
            caption = (
                f"🚨 <b>CHALLENGE ENGINE ERROR</b>\n"
                f"————————————————————\n"
                f"👤 <b>User:</b> {username} (<code>{user_id}</code>)\n"
                f"⚠️ <b>Exception:</b> <code>{type(event.exception).__name__}</code>\n"
                f"📝 <b>Brief:</b> <code>{str(event.exception)[:100]}</code>"
            )
            
            await bot.send_document(
                chat_id=settings.ADMIN_ERROR_LOG_ID,
                document=log_file,
                caption=caption,
                parse_mode="HTML"
            )
        except Exception as log_err:
            logging.error(f"Failed to log error to Admin: {log_err}")

    # 4. Graceful User Recovery
    try:
        # Pull language from the injected middleware data
        lang = data.get("language", "EN")
        error_msg = (
            "⚠️ <b>System Update</b>\n\nWe are experiencing heavy traffic. Please wait a moment and try again."
            if lang == "EN" else
            "⚠️ <b>ሲስተም ማሻሻያ</b>\n\nከፍተኛ የተጠቃሚ ቁጥር ስላለ እባክዎን ከጥቂት ደቂቃ በኋላ እንደገና ይሞክሩ።"
        )
        
        if event.update.message:
            await event.update.message.answer(error_msg, parse_mode="HTML")
        elif event.update.callback_query:
            # Using answer() on callback_query.message to avoid "query is too old" errors
            await event.update.callback_query.message.answer(error_msg, parse_mode="HTML")
            # Also answer the callback so the loading spinner stops
            await event.update.callback_query.answer()
    except Exception:
        pass 

    return True # Prevents the error from propagating further
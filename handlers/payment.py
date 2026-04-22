# import asyncio
# import logging
# from aiogram import Router, F, types, Bot
# from aiogram.fsm.context import FSMContext
# from database.db import Database
# from utils.localization import get_text
# from config import settings
# import html

# router = Router(name="payment")
# logger = logging.getLogger(__name__)


# # --- ADMIN NOTIFICATION LOGIC ---
# async def notify_admin_payment(bot: Bot, user_id: int, full_name: str, username: str, photo_id: str, fayda_id: str):
#     """
#     Sends a high-detail verification card to the Admin group.
#     Includes the Receipt AND the Fayda ID for side-by-side verification.
#     """
#     admin_id = settings.ADMIN_IDS[0] # Primary Admin
#     safe_name = html.escape(full_name)
#     safe_username = f"@{html.escape(username)}" if username else "No Username"

#     caption = (
#         "💳 <b>NEW PAYMENT SUBMITTED</b>\n"
#         "————————————————————\n"
#         f"👤 <b>User:</b> {safe_name}\n"
#         f"🔗 <b>Username:</b> {safe_username}\n"
#         f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
#         "————————————————————\n"
#         "👇 <b>RECEIPT BELOW</b>"
#     )

#     try:
#         # 1. Send the Receipt Photo
#         await bot.send_photo(admin_id, photo=photo_id, caption=caption, parse_mode="HTML")
        
#         # 2. Send the Fayda ID Photo for identity cross-check
#         await bot.send_photo(
#             admin_id, 
#             photo=fayda_id, 
#             caption=f"🪪 <b>FAYDA ID:</b> {safe_name}\n<i>Verify this matches the receipt name.</i>",
#             parse_mode="HTML"
#         )
#     except Exception as e:
#         logger.error(f"Failed to notify admin: {e}")

# # --- PAYMENT HANDLER (Capturing the Receipt) ---
# # This is triggered by the final state in onboarding.py
# @router.message(F.photo, flags={"long_operation": "upload_photo"})
# async def handle_payment_screenshot(message: types.Message, state: FSMContext, db: Database, bot: Bot):
#     """
#     The 'Grand Finale' of the onboarding. Captures the receipt, 
#     syncs all data to DB, and alerts the admin.
#     """
#     current_state = await state.get_state()
    
#     # Ensure this only triggers if they are actually in the payment step
#     if "payment_upload" not in str(current_state):
#         return

#     data = await state.get_data()
#     lang = data.get("language", "EN")
#     photo_id = message.photo[-1].file_id
#     fayda_id = data.get("fayda_file_id")

#     # 1. Update Database: Finalize User Registration
#     await db.update_user(
#         message.from_user.id,
#         full_name=data.get('full_name'),
#         gender=data.get('gender'),
#         age=data.get('age'),
#         current_weight_kg=data.get('current_weight_kg'),
#         phone_number=data.get('phone'),
#         fayda_file_id=fayda_id,
#         registration_step='pending_verification'
#     )

#     # 2. Update Database: Create Payment Entry
#     await db.submit_payment(
#         user_id=message.from_user.id,
#         proof_file_id=photo_id,
#         amount=1000.00 # Fixed contest fee
#     )

#     # 3. Notify Admin Team for Manual Approval
#     await notify_admin_payment(
#         bot=bot,
#         user_id=message.from_user.id,
#         full_name=data.get('full_name'),
#         username=message.from_user.username,
#         photo_id=photo_id,
#         fayda_id=fayda_id
#     )

#     # 4. Success Message to User
#     await message.answer(get_text(lang, "payment_received"), parse_mode="HTML")
    
#     # 5. Clear State - Process Complete
#     await state.clear()

# # --- FALLBACK FOR RANDOM TEXT ---
# @router.message()
# async def handle_random_input(message: types.Message, state: FSMContext, db: Database):
#     """
#     If a user sends random text during the payment phase instead of a photo.
#     """
#     current_state = await state.get_state()
#     if current_state is None:
#         return

#     data = await state.get_data()
#     lang = data.get("language", "EN")
    
#     if "payment_upload" in str(current_state):
#         await message.answer(
#             "⚠️ <b>Action Required</b>\n\n" + get_text(lang, "ask_payment"),
#             parse_mode="HTML"
#         )
        

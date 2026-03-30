from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import Database
from handlers.tasks import send_to_admin_group
from utils.localization import LEGAL_TEXTS, get_text
from keyboards import inline as kb
from config import settings as Config
from aiogram.utils.media_group import MediaGroupBuilder # New Import for Gallery


router = Router(name="onboarding")


class ChallengeStates(StatesGroup):
    language = State()
    full_name = State()
    phone = State()        # Lead capture early
    gender = State()
    age = State()          # Split Step 1
    weight = State()       # Split Step 2
    legal = State()
    before_photo_front = State() 
    before_photo_side = State()  
    before_photo_rear = State()
    fayda_upload = State()
    payment_upload = State()

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext, db: Database):
    await state.clear()
    user = await db.get_user(message.from_user.id)
    
    if user and user.get('is_paid'):
        lang = user.get('language', 'EN')
        msg = (
            "<b>WELCOME BACK CHAMPION!</b> 🏆\n\n"
            "Your profile is locked in. Get ready for the transformation of a lifetime."
            if lang == "EN" else
            "<b>እንኳን ደህና መጡ ሻምፒዮን!</b> 🏆\n\n"
            "ምዝገባዎ ተጠናቋል። ለህይወት ለውጥዎ ዝግጁ ይሁኑ።"
        )
        return await message.answer(msg)

    # Clean Language Selection
    await message.answer(
        "<b>CHOOSE YOUR LANGUAGE / ቋንቋ ይምረጡ</b> 🌐", 
        reply_markup=kb.lang_selection()
    )
    await state.set_state(ChallengeStates.language)
    

import asyncio
from aiogram.enums import ChatAction
@router.callback_query(ChallengeStates.language)
async def process_lang(callback: types.CallbackQuery, state: FSMContext, db: Database):
    lang = callback.data.replace("lang_", "").upper()
    await state.update_data(language=lang)
    
    # Update DB with language and initial state
    await db.update_user(
        callback.from_user.id, 
        language=lang, 
        username=callback.from_user.username
    )
    
    # 1. Logic for Welcome Text and Step 1 Text
    if lang == "EN":
        welcome_text = (
            "<b>WELCOME TO THE 8-WEEK TRANSFORMATION!</b> 🔥🏆\n\n"
            "<b>ይቀንሱ፣ ይሸለሙ! — Lose Weight, Get Rewarded!</b>\n\n"
            "This is a results-driven journey to change your physique and win a share of <b>200,000 ETB</b> in total prizes:\n\n"
            "🥇 <b>1st Place: 100,000 ETB</b>\n"
            "🥈 <b>2nd Place: 50,000 ETB</b>\n\n"
            "📅 <b>Duration:</b> 8 Weeks\n"
            "💰 <b>Entry Fee:</b> 1000 ETB (Limited Spots)\n"
            "⚠️ <b>Requirement:</b> Valid Fayda ID & 'Before' Photo proof"
        )
        step_text = (
            "📍 <b>Step 1/9 — Identity</b>\n"
            "▰▱▱▱▱▱\n\n"
            "To get started, what is your <b>Full Name</b>?\n"
            "<i>Example: Solomon Ayele</i>"
        )
    else:
        welcome_text = (
            "<b>እንኳን ወደ 8-ሳምንት የለውጥ ጉዞ በደህና መጡ!</b> 🔥🏆\n\n"
            "<b>ይቀንሱ፣ ይሸለሙ! — አጠቃላይ የ200,000 ብር ሽልማት!</b>\n\n"
            "ጤናዎን እየቀየሩ ከሚከተሉት አሸናፊዎች አንዱ መሆን ይችላሉ፦\n\n"
            "🥇 <b>1ኛ ደረጃ፦ 100,000 ብር</b>\n"
            "🥈 <b>2ኛ ደረጃ፦ 50,000 ብር</b>\n\n"
            "📅 <b>ቆይታ፦</b> 8 ሳምንታት\n"
            "💰 <b>የመመዝገቢያ ዋጋ፦</b> 1000 ብር\n"
            "⚠️ <b>መስፈርት፦</b> የታደሰ የፋይዳ መለያ እና 'የመጀመሪያ ቀን' ፎቶ"
        )
        step_text = (
            "📍 <b>ምዕራፍ 1/9 — መለያ</b>\n"
            "▰▱▱▱▱▱\n\n"
            "ለመጀመር፣ <b>ሙሉ ስምዎን</b> ያስገቡ፦\n"
            "<i>ምሳሌ፦ ሰለሞን አየለ</i>"
        )

    # 1. Edit the first message to show the Prize Details (Instant)
    await callback.message.edit_text(welcome_text)
    
    # 2. Add the "Premium Pause"
    # Show "typing..." in the top bar for 1.5 seconds
    await callback.bot.send_chat_action(
        chat_id=callback.message.chat.id,
        action=ChatAction.TYPING
    )
    await asyncio.sleep(1.5) 

    # 3. Send Step 1 as a separate bubble
    await callback.message.answer(step_text)

    # 4. Finalize state
    await state.set_state(ChallengeStates.full_name)
    
@router.message(ChallengeStates.full_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    lang = (await state.get_data())['language']
    
    await message.answer(get_text(lang, "ask_phone"), reply_markup=kb.phone_markup(lang))
    await state.set_state(ChallengeStates.phone)
from aiogram.types import ReplyKeyboardRemove # 1. IMPORTANT: Add this import

@router.message(ChallengeStates.phone)
async def process_phone(message: types.Message, state: FSMContext):
    lang = (await state.get_data())['language']

    if message.contact:
        # ✅ Correct flow: user clicked "Share My Number"
        phone = message.contact.phone_number
        await state.update_data(phone_number=phone)

        # 2. THE FIX: 
        # We send the "ask_gender" message and explicitly tell the bot 
        # to REMOVE the reply keyboard (the phone button).
        # Since gender_markup is an INLINE keyboard (buttons on the bubble), 
        # it won't conflict with ReplyKeyboardRemove.
        
        await message.answer("✅✅", reply_markup=ReplyKeyboardRemove())
        await message.answer(
            get_text(lang, "ask_gender"),
            reply_markup=kb.gender_markup(lang) # This is Inline
        )
        
        # If your gender_markup is Inline, but the phone button is STILL there,
        # you have to send a tiny "dummy" message to force the removal:

        await state.set_state(ChallengeStates.gender)
    else:
        # ❌ Wrong flow: user typed text instead of sharing contact
        await message.answer(
            get_text(lang, "error_phone"),
            reply_markup=kb.phone_markup(lang)
        )

@router.callback_query(ChallengeStates.gender)
async def process_gender(callback: types.CallbackQuery, state: FSMContext):
    gender = callback.data.replace("gender_", "")
    await state.update_data(gender=gender)
    
    lang = (await state.get_data())['language']
    await callback.message.edit_text(get_text(lang, "ask_age"))
    await state.set_state(ChallengeStates.age)

@router.message(ChallengeStates.age)
async def process_age(message: types.Message, state: FSMContext):
    lang = (await state.get_data())['language']
    
    if not message.text.isdigit():
        return await message.answer(get_text(lang, "error_age"))
        
    await state.update_data(age=int(message.text))
    await message.answer(get_text(lang, "ask_weight"))
    await state.set_state(ChallengeStates.weight)
    
@router.message(ChallengeStates.weight)
async def process_weight(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('language', 'EN')
    
    try:
        # Sanitizing input
        clean_weight = message.text.lower().replace("kg", "").replace("ኪሎ", "").strip()
        weight_val = float(clean_weight)
        
        # Initialize empty legal checks
        await state.update_data(current_weight_kg=weight_val, legal_checks=[])
        header = "📍 <b>Step 6/9 — Legal & Health Agreement</b> ✅" if lang == "EN" else "📍 <b>ምዕራፍ 6/9 — የጤና እና የደንብ ስምምነት</b> ✅"
        
        # Build the localized prompt
        legal_prompt = (
            f"{header}\n"           
            f"▰▰▰▰▰▱\n\n"
            f"<i>{LEGAL_TEXTS[lang]['rule_1']}</i>\n\n"
            f"<i>{LEGAL_TEXTS[lang]['rule_2']}</i>\n\n"
            f"<i>{LEGAL_TEXTS[lang]['rule_3']}</i>\n\n"
            f"────────────────────\n"
            f"{LEGAL_TEXTS[lang]['instruction']}" # <--- The CTA is here
        )
        
        await message.answer(
            legal_prompt, 
            reply_markup=kb.legal_keyboard(lang, []),
            parse_mode="HTML"
        )
        await state.set_state(ChallengeStates.legal)
        
    except ValueError:
        await message.answer(get_text(lang, "error_weight"))
# 1. LEGAL TOGGLE & TRANSITION
# 1. FINALIZING LEGAL -> START PHOTOS
@router.callback_query(ChallengeStates.legal, F.data.startswith("legal_"))
async def handle_legal_toggles(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    checks = data.get("legal_checks", [])
    lang = data['language']
    
    if callback.data == "legal_finalize":
        # Delete the rules message to clean up the UI before starting upload
        await callback.message.delete()
        
        # Send Reference Gallery
        album = MediaGroupBuilder(caption=get_text(lang, "photo_gallery_intro"))
        album.add_photo(media=Config.BEFORE_EXAMPLE_ID) 
        album.add_photo(media=Config.BEFORE_SIDE_ID)    
        album.add_photo(media=Config.BEFORE_REAR_ID)    
        
        await callback.message.answer_media_group(media=album.build())
        
        # Send fresh instruction
        await callback.message.answer(get_text(lang, "ask_photo_front"), parse_mode="HTML")
        await state.set_state(ChallengeStates.before_photo_front)
        return

    # ... (Toggle Logic stays the same)
    rule_num = int(callback.data.split("_")[1])
    if rule_num in checks: checks.remove(rule_num)
    else: checks.append(rule_num)
    
    await state.update_data(legal_checks=checks)
    try:
        await callback.message.edit_reply_markup(reply_markup=kb.legal_keyboard(lang, checks))
    except Exception:
        await callback.answer()

# 2.1 HANDLE FRONT PHOTO
@router.message(ChallengeStates.before_photo_front, F.photo)
async def process_front_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data['language']
    
    # Save Photo (No deletion)
    await state.update_data(photo_front_file_id=message.photo[-1].file_id)
    
    # Respond with a NEW message (Confirmation + Next Step)
    # If the localization key doesn't exist, we provide a fallback string here
    next_text = get_text(lang, "ask_photo_side") or "✅ Front photo received! Now, please send the **SIDE** view."
    await message.answer(next_text, parse_mode="HTML")
    
    await state.set_state(ChallengeStates.before_photo_side)

# 2.2 HANDLE SIDE PHOTO
@router.message(ChallengeStates.before_photo_side, F.photo)
async def process_side_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data['language']
    
    # Save Photo (No deletion)
    await state.update_data(photo_side_file_id=message.photo[-1].file_id)
    
    # Respond with a NEW message
    next_text = get_text(lang, "ask_photo_rear") or "✅ Side photo received! Finally, please send the **REAR** (back) view."
    await message.answer(next_text, parse_mode="HTML")
    
    await state.set_state(ChallengeStates.before_photo_rear)

# 2.3 HANDLE REAR PHOTO -> TRANSITION TO FAYDA
@router.message(ChallengeStates.before_photo_rear, F.photo)
async def process_rear_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data['language']
    
    # Save Photo (No deletion)
    await state.update_data(photo_rear_file_id=message.photo[-1].file_id)
    
    # Final confirmation of photos
    confirm_text = get_text(lang, "before_photo_received") or "✅ All photos saved! We are almost done."
    await message.answer(confirm_text)
    
    # PROCEED TO FAYDA ID
    fayda_text = get_text(lang, "ask_fayda") or "Please upload your Fayda ID (National ID) to verify your entry."
    await message.answer_photo(
        photo=Config.FAYDA_EXAMPLE_ID,
        caption=fayda_text
    )
    await state.set_state(ChallengeStates.fayda_upload)
# 3. FAYDA ID HANDLER
@router.message(ChallengeStates.fayda_upload, F.photo)
async def process_fayda(message: types.Message, state: FSMContext):
    # Save the user's actual ID photo
    await state.update_data(fayda_file_id=message.photo[-1].file_id)
    lang = (await state.get_data())['language']
    
    await message.answer(get_text(lang, "fayda_received"))
    
    # SEND PAYMENT INSTRUCTIONS (Text Only)
    await message.answer(get_text(lang, "ask_payment"))
    await state.set_state(ChallengeStates.payment_upload)
import asyncio
from aiogram.utils.media_group import MediaGroupBuilder


@router.message(ChallengeStates.payment_upload, F.photo)
async def handle_registration_finish(message: types.Message, state: FSMContext, db: Database):
    payment_photo = message.photo[-1].file_id
    await state.update_data(accepted_terms=True, has_health_clearance=True)
    data = await state.get_data()
    lang = data['language']
    
    # 1. Update Database (Reflecting new photo structure)
    await db.update_user(
        message.from_user.id,
        full_name=data['full_name'],
        gender=data['gender'],
        age=data['age'],
        current_weight_kg=data['current_weight_kg'],
        phone_number=data['phone_number'],
        # New split photo IDs
        fayda_file_id = data['fayda_file_id'],
        photo_front_file_id=data['photo_front_file_id'],
        photo_side_file_id=data['photo_side_file_id'],
        photo_rear_file_id=data['photo_rear_file_id'],
        # Health & Terms
        has_health_clearance=True,
        accepted_terms=True,
        registration_step='verification_pending'
    )
    
    await db.submit_payment(message.from_user.id, payment_photo)
    
    # 2. Inform User (Immediate Feedback)
    await message.answer(get_text(lang, "payment_received"))
    
    # 3. Trigger Background Task for Admin & Member ID
    # Note: send_to_admin_group task must also be updated to expect 3 photos
    asyncio.create_task(send_to_admin_group(message.bot, message.from_user.id, data, payment_photo))
    
    await state.clear()
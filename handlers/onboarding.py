from aiogram import Router, F, types
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import Database
from handlers.tasks import send_to_admin_group
from handlers.user_dashboard import get_main_dashboard
from utils.localization import LEGAL_TEXTS, get_member_card, get_text
from keyboards import inline as kb
from config import settings as Config
from aiogram.utils.media_group import MediaGroupBuilder # New Import for Gallery
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


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
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    # --- 1. HANDLE PAID / VERIFIED / REJECTED ---
    if user and user.get('registration_step') in ['verification_pending', 'verified', 'rejected']:
        lang = user.get('language', 'EN')
        step = user.get('registration_step')
        
        # Generate the Digital Card text you provided
        card_text = get_member_card(
            lang=lang, 
            user_id=user_id, 
            name=user.get('full_name', 'Challenger'),
            registration_step=step
        )
        
        if step == 'verified':
            # --- 10/10 SENIOR MOVE: Show Card + Your Persistent Dashboard ---
            await message.answer(card_text, parse_mode="HTML") # The Card
            return await message.answer(
                "🏆 <b>DASHBOARD UNLOCKED</b>" if lang == "EN" else "🏆 <b>ዳሽቦርድ ተከፍቷል</b>",
                reply_markup=get_main_dashboard(lang) # Your Reply Keyboard
            )

        elif step == 'rejected':
            # Inline button for Re-applying
            retry_kb = InlineKeyboardBuilder()
            btn = "🔄 Re-apply / ድጋሚ ይሞክሩ" if lang == "EN" else "🔄 ድጋሚ ይሞክሩ"
            retry_kb.row(types.InlineKeyboardButton(text=btn, callback_data="retry_registration"))
            return await message.answer(card_text, reply_markup=retry_kb.as_markup(), parse_mode="HTML")

        else:
            # Verification Pending: Let them refresh
            refresh_kb = InlineKeyboardBuilder()
            btn = "🔄 Refresh Status / አድስ" if lang == "EN" else "🔄 አድስ"
            refresh_kb.row(types.InlineKeyboardButton(text=btn, callback_data="refresh_status"))
            return await message.answer(card_text, reply_markup=refresh_kb.as_markup(), parse_mode="HTML")

    # --- 2. THE RESUME GATEWAY (Intermediate Progress) ---
    partial_steps = ['full_name', 'phone', 'gender', 'age', 'weight', 'legal', 'photo_front']
    if user and user.get('registration_step') in partial_steps:
        # (Resume logic we brainstormed earlier goes here...)
        pass

    # --- 3. NEW START ---
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
# 2.1 HANDLE FRONT PHOTO
@router.message(ChallengeStates.before_photo_front, F.photo)
async def process_front_photo(message: types.Message, state: FSMContext, db: Database):
    data = await state.get_data()
    lang = data['language']

    # --- GALLERY GUARD (Localized) ---
    if message.media_group_id:
        error_msg = "⚠️ Please send photos <b>one by one</b>, not as a gallery." if lang == "EN" \
                    else "⚠️ እባክዎን ፎቶዎቹን <b>አንዱን ከላኩ በኋላ ቀጣዩን</b> ይላኩ (በአንድ ላይ አይላኩ)።"
        return await message.answer(error_msg, parse_mode="HTML")

    # Save to FSM
    await state.update_data(photo_front_file_id=message.photo[-1].file_id)
    
    # 10/10 Save Point: Sync DB so "Resume" works
    await db.update_user(message.from_user.id, registration_step='photo_side')
    
    # Success Message
    next_text = get_text(lang, "ask_photo_side")
    await message.answer(f"✅ {next_text}", parse_mode="HTML")
    await state.set_state(ChallengeStates.before_photo_side)

# 2.2 HANDLE SIDE PHOTO
@router.message(ChallengeStates.before_photo_side, F.photo)
async def process_side_photo(message: types.Message, state: FSMContext, db: Database):
    data = await state.get_data()
    lang = data['language']

    # --- GALLERY GUARD ---
    if message.media_group_id:
        error_msg = "⚠️ Please send photos one by one." if lang == "EN" else "⚠️ እባክዎን ፎቶዎቹን একে একে ይላኩ።"
        return await message.answer(error_msg)

    await state.update_data(photo_side_file_id=message.photo[-1].file_id)
    
    # Save Point
    await db.update_user(message.from_user.id, registration_step='photo_rear')
    
    next_text = get_text(lang, "ask_photo_rear")
    await message.answer(f"✅ {next_text}", parse_mode="HTML")
    await state.set_state(ChallengeStates.before_photo_rear)

# 2.3 HANDLE REAR PHOTO -> TRANSITION TO FAYDA
@router.message(ChallengeStates.before_photo_rear, F.photo)
async def process_rear_photo(message: types.Message, state: FSMContext, db: Database):
    data = await state.get_data()
    lang = data['language']

    if message.media_group_id:
        return await message.answer("⚠️ Send photos one by one.")

    await state.update_data(photo_rear_file_id=message.photo[-1].file_id)
    
    # Save Point
    await db.update_user(message.from_user.id, registration_step='fayda')
    
    await message.answer(get_text(lang, "before_photo_received"))
    
    # Show Fayda Example
    fayda_prompt = get_text(lang, "ask_fayda")
    await message.answer_photo(
        photo=Config.FAYDA_EXAMPLE_ID,
        caption=fayda_prompt
    )
    await state.set_state(ChallengeStates.fayda_upload)

# 3. FAYDA ID HANDLER
@router.message(ChallengeStates.fayda_upload, F.photo)
async def process_fayda(message: types.Message, state: FSMContext, db: Database):
    if message.media_group_id:
        return await message.answer("⚠️ Please send your ID separately.")

    await state.update_data(fayda_file_id=message.photo[-1].file_id)
    lang = (await state.get_data())['language']
    
    # Save Point: They are now ready for Payment
    await db.update_user(message.from_user.id, registration_step='payment')
    
    await message.answer(get_text(lang, "fayda_received"))
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
    
    
    
#For rejection Purpose

@router.callback_query(F.data == "retry_registration")
async def process_retry_registration(callback: types.CallbackQuery, state: FSMContext, db: Database):
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    lang = user.get('language', 'EN') if user else 'EN'

    # 1. Wipe old file IDs from the Database to ensure a clean slate
    await db.update_user(
        user_id,
        photo_front_file_id=None,
        photo_side_file_id=None,
        photo_rear_file_id=None,
        fayda_file_id=None,
        registration_step='re-uploading'
    )

    # 2. Reset FSM State to the first photo step
    await state.set_state(ChallengeStates.before_photo_front)

    # 3. Inform the user and show the Gallery again
    instruction = (
        "<b>RE-UPLOAD STARTED</b> 🔄\n\n"
        "Please follow the examples below and send your <b>FRONT VIEW</b> photo."
        if lang == "EN" else
        "<b>የፎቶ መላክ ሂደት ተጀምሯል</b> 🔄\n\n"
        "እባክዎን ከታች ያለውን ምሳሌ በመከተል <b>የፊት ለፊት</b> ፎቶዎን ይላኩ።"
    )

    # Show the reference photos again so they know what "good" looks like
    album = MediaGroupBuilder(caption=get_text(lang, "photo_gallery_intro"))
    album.add_photo(media=Config.BEFORE_EXAMPLE_ID) 
    album.add_photo(media=Config.BEFORE_SIDE_ID)    
    album.add_photo(media=Config.BEFORE_REAR_ID)    
    
    await callback.message.answer_media_group(media=album.build())
    await callback.message.answer(instruction, parse_mode="HTML")
    await callback.answer()
    
    


@router.callback_query(F.data == "resume_reg")
async def resume_registration(callback: types.CallbackQuery, state: FSMContext, db: Database):
    user = await db.get_user(callback.from_user.id)
    step = user.get('registration_step')
    lang = user.get('language', 'EN')
    
    # 1. Map DB strings to ChallengeStates
    # This acts like a 'Save Point' in a video game
    state_mapping = {
        'full_name': ChallengeStates.full_name,
        'phone': ChallengeStates.phone,
        'gender': ChallengeStates.gender,
        'age': ChallengeStates.age,
        'weight': ChallengeStates.weight,
        'legal': ChallengeStates.legal,
        'photo_front': ChallengeStates.before_photo_front,
        'photo_side': ChallengeStates.before_photo_side,
        'photo_rear': ChallengeStates.before_photo_rear,
        'fayda': ChallengeStates.fayda_upload,
        'payment': ChallengeStates.payment_upload
    }

    target_state = state_mapping.get(step, ChallengeStates.full_name)
    
    # 2. Sync FSM with Database data
    # We load what they already did into the FSM memory so the final step has it
    await state.update_data(
        language=lang,
        full_name=user.get('full_name'),
        phone_number=user.get('phone_number'),
        gender=user.get('gender'),
        age=user.get('age'),
        current_weight_kg=user.get('current_weight_kg')
    )

    # 3. Move them to the state
    await state.set_state(target_state)

    # 4. Trigger the prompt for that state
    # Example: If they stopped at weight, ask for weight again
    prompts = {
        'photo_front': get_text(lang, "ask_photo_front"),
        'photo_side': get_text(lang, "ask_photo_side"),
        'fayda': get_text(lang, "ask_fayda"),
        'payment': get_text(lang, "ask_payment")
    }
    
    prompt_text = prompts.get(step, "Please continue where you left off.")
    await callback.message.answer(f"✅ <b>RESUMED</b>\n\n{prompt_text}", parse_mode="HTML")
    await callback.answer()
    

@router.message(
    StateFilter(
        ChallengeStates.before_photo_front, 
        ChallengeStates.before_photo_side, 
        ChallengeStates.before_photo_rear,
        ChallengeStates.fayda_upload,
        ChallengeStates.payment_upload
    ),
    ~F.photo
)
async def handle_wrong_photo_format(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('language', 'EN')
    
    error_text = (
        "❌ <b>Invalid format!</b>\nPlease send a <b>PHOTO</b> (not a file or text)."
        if lang == "EN" else
        "❌ <b>የተሳሳተ አላላክ!</b>\nእባክዎን <b>ፎቶ</b> ብቻ ይላኩ (ፋይል ወይም ጽሁፍ አይቀበልም)።"
    )
    await message.answer(error_text, parse_mode="HTML")
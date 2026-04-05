from aiogram import Router, F, types
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import Database
from handlers.tasks import notify_new_lead, send_to_admin_group
from handlers.user_dashboard import get_main_dashboard
from utils.localization import LEGAL_TEXTS, get_member_card, get_payment_text, get_text
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
    payment_upload = State()
    fayda_upload = State()
    before_photo_front = State() 
    before_photo_side = State()  
    before_photo_rear = State()

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
async def process_name(message: types.Message, state: FSMContext, db:Database):
    await state.update_data(full_name=message.text)
    await db.update_user(message.from_user.id, full_name=message.text, registration_step='phone')
    lang = (await state.get_data())['language']
    
    await message.answer(get_text(lang, "ask_phone"), parse_mode="HTML")
    await state.set_state(ChallengeStates.phone)
from aiogram.types import ReplyKeyboardRemove # 1. IMPORTANT: Add this import
import re

@router.message(ChallengeStates.phone)
async def process_phone(message: types.Message, state: FSMContext, db: Database):
    lang = (await state.get_data())['language']
    user_input = message.text.strip() if message.text else ""

    # 1. THE REGEX: Matches '09' or '07' followed by 8 digits (Total 10)
    # Example: 0960306801
    is_valid = re.fullmatch(r"^(09|07)\d{8}$", user_input)

    if is_valid:
        # ✅ SUCCESS: Valid Ethiopian format
        await state.update_data(phone_number=user_input)
        
        # SILENT SAVE: Capture the lead immediately
        await db.update_user(
            message.from_user.id, 
            phone_number=user_input, 
            registration_step='gender'
        )

        # Remove any old reply keyboards and move to Gender
        await message.answer("✅", reply_markup=types.ReplyKeyboardRemove())
        await message.answer(
            get_text(lang, "ask_gender"),
            reply_markup=kb.gender_markup(lang)
        )
        await state.set_state(ChallengeStates.gender)

    else:
        # ❌ ERROR: Wrong format or typed text
        error_msg = (
            "❌ <b>Invalid Format!</b>\nPlease enter your number exactly like: <code>0960306801</code>"
            if lang == "EN" else
            "❌ <b>የተሳሳተ ቁጥር!</b>\nእባክዎን በዚህ መልኩ ያስገቡ፦ <code>0960306801</code>"
        )
        await message.answer(error_msg, parse_mode="HTML")

@router.callback_query(ChallengeStates.gender)
async def process_gender(callback: types.CallbackQuery, state: FSMContext, db: Database):
    gender = callback.data.replace("gender_", "")
    await state.update_data(gender=gender)
    
    await db.update_user(callback.from_user.id, gender=gender, registration_step='age')
    
    lang = (await state.get_data())['language']
    await callback.message.edit_text(get_text(lang, "ask_age"))
    await state.set_state(ChallengeStates.age)
    
@router.message(ChallengeStates.age)
async def process_age(message: types.Message, state: FSMContext, db: Database):
    lang = (await state.get_data())['language']
    
    if not message.text.isdigit():
        return await message.answer(get_text(lang, "error_age"))
        
    age_val = int(message.text)
    await state.update_data(age=age_val)
    
    # SILENT SAVE 4
    await db.update_user(message.from_user.id, age=age_val, registration_step='weight')
    
    await message.answer(get_text(lang, "ask_weight"))
    await state.set_state(ChallengeStates.weight)
    
@router.message(ChallengeStates.weight)
async def process_weight(message: types.Message, state: FSMContext, db: Database):
    data = await state.get_data()
    lang = data.get('language', 'EN')
    
    try:
        # Sanitizing input
        clean_weight = message.text.lower().replace("kg", "").replace("ኪሎ", "").strip()
        weight_val = float(clean_weight)
        
        # Initialize empty legal checks
        await state.update_data(current_weight_kg=weight_val, legal_checks=[])
        await db.update_user(message.from_user.id, current_weight_kg=weight_val, registration_step='legal')
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
        
@router.callback_query(ChallengeStates.legal, F.data.startswith("legal_"))
async def handle_legal_toggles(callback: types.CallbackQuery, state: FSMContext, db: Database):
    data = await state.get_data()
    checks = data.get("legal_checks", []) # This is a list like [1, 2]
    lang = data.get('language', 'EN')
    
    # --- 1. HANDLE FINALIZE (The "Submit" Button) ---
    if callback.data == "legal_finalize":
        # Check if all 3 checkboxes are clicked
        if len(checks) < 3:
            error_msg = (
                "⚠️ Please accept all terms to continue." 
                if lang == "EN" else 
                "⚠️ እባክዎን ለመቀጠል ሁሉንም ደንቦች ይቀበሉ።"
            )
            return await callback.answer(error_msg, show_alert=True)

        # SUCCESS: User agreed to everything
        await callback.message.delete()
        
        # A. Update FSM with explicit booleans for the Admin Notification
        await state.update_data(
            accepted_terms=True,      # Correct column name
    has_health_clearance=True,  # Correct column name
            legal_status="✅ AGREED"
        )
        
        # B. Persistent Save to Database
        await db.update_user(
            callback.from_user.id, 
            registration_step='payment',
            accepted_terms=True,      # Correct column name
    has_health_clearance=True  # Correct column name
        )
        
        updated_data = await state.get_data()

        # 3. Fire the Lead Notification (Non-blocking)
        asyncio.create_task(notify_new_lead(callback.bot, callback.from_user.id, updated_data))
        
        # C. Move to Payment
        payment_instruction = get_payment_text(lang) 
        await callback.message.answer(payment_instruction, parse_mode="HTML")
        await state.set_state(ChallengeStates.payment_upload)
        return await callback.answer()

    # --- 2. HANDLE TOGGLES (The Checkbox Buttons) ---
    try:
        rule_num = int(callback.data.split("_")[1])
        
        if rule_num in checks:
            checks.remove(rule_num)
        else:
            checks.append(rule_num)
        
        # Save the updated list of checked IDs to FSM
        await state.update_data(legal_checks=checks)
        
        # Refresh the keyboard to show the new "✅" marks
        await callback.message.edit_reply_markup(
            reply_markup=kb.legal_keyboard(lang, checks)
        )
        await callback.answer() # Keep it silent/smooth
        
    except Exception:
        # Prevents crashing if the user double-clicks too fast 
        # or if the keyboard is already in the requested state
        await callback.answer()
        
    

@router.message(ChallengeStates.payment_upload, F.photo)
async def process_payment(message: types.Message, state: FSMContext, db: Database):
    payment_photo = message.photo[-1].file_id
    await state.update_data(payment_file_id=payment_photo)
    
    # Save payment to DB immediately
    await db.submit_payment(message.from_user.id, payment_photo)
    await db.update_user(message.from_user.id, registration_step='fayda')
    
    lang = (await state.get_data())['language']
    await message.answer(get_text(lang, "payment_received"))
    
    # 3. Ask for Fayda ID
    await message.answer_photo(
        photo=Config.FAYDA_EXAMPLE_ID,
        caption=get_text(lang, "ask_fayda")
    )
    await state.set_state(ChallengeStates.fayda_upload)
    


@router.message(ChallengeStates.fayda_upload, F.photo)
async def process_fayda(message: types.Message, state: FSMContext, db: Database):
    fayda_id = message.photo[-1].file_id
    await state.update_data(fayda_file_id=fayda_id)
    
    await db.update_user(message.from_user.id, registration_step='photo_front')
    
    lang = (await state.get_data())['language']
    await message.answer(get_text(lang, "fayda_received"))
    
    # Show Reference Gallery for the 3 photos
    album = MediaGroupBuilder(caption=get_text(lang, "photo_gallery_intro"))
    album.add_photo(media=Config.BEFORE_EXAMPLE_ID) 
    album.add_photo(media=Config.BEFORE_SIDE_ID)    
    album.add_photo(media=Config.BEFORE_REAR_ID)    
    
    await message.answer_media_group(media=album.build())
    await message.answer(get_text(lang, "ask_photo_front"), parse_mode="HTML")
    await state.set_state(ChallengeStates.before_photo_front)
    
    

@router.message(ChallengeStates.before_photo_front, F.photo)
async def process_front_photo(message: types.Message, state: FSMContext, db: Database):
    await state.update_data(photo_front_file_id=message.photo[-1].file_id)
    await db.update_user(message.from_user.id, registration_step='photo_side')
    
    lang = (await state.get_data())['language']
    await message.answer(f"✅ {get_text(lang, 'ask_photo_side')}", parse_mode="HTML")
    await state.set_state(ChallengeStates.before_photo_side)

@router.message(ChallengeStates.before_photo_side, F.photo)
async def process_side_photo(message: types.Message, state: FSMContext, db: Database):
    await state.update_data(photo_side_file_id=message.photo[-1].file_id)
    await db.update_user(message.from_user.id, registration_step='photo_rear')
    
    lang = (await state.get_data())['language']
    await message.answer(f"✅ {get_text(lang, 'ask_photo_rear')}", parse_mode="HTML")
    await state.set_state(ChallengeStates.before_photo_rear)
    

@router.message(ChallengeStates.before_photo_rear, F.photo)
async def handle_registration_finish(message: types.Message, state: FSMContext, db: Database):
    await state.update_data(photo_rear_file_id=message.photo[-1].file_id)
    data = await state.get_data()
    lang = data['language']
    
    # 1. Final Database Update
    await db.update_user(
        message.from_user.id,
        photo_front_file_id=data['photo_front_file_id'],
        photo_side_file_id=data['photo_side_file_id'],
        photo_rear_file_id=data['photo_rear_file_id'],
        fayda_file_id=data['fayda_file_id'],
        registration_step='verification_pending'
    )
    
    # 2. Inform User
    await message.answer(get_text(lang, "before_photo_received"))
    
    final_msg = (
                   "🚀 <b>CONGRATULATIONS!</b>\n\n"
            "Your registration is sent. I will check your receipt and photos now. "
            "I will add you to our private group very soon. <b>Get ready to win!</b>"
        if lang == "EN" else
          "🚀 <b>እንኳን ደስ አለዎት!</b>\n\n"
            "ምዝገባዎ ተልኳል። መረጃዎን አረጋግጬ በቅርቡ በግል ግሩፓችን ውስጥ እጨምርዎታለሁ። "
            "<b>ለማሸነፍ ዝግጁ ይሁኑ!</b>"

    )
    await message.answer(final_msg, parse_mode="HTML")
    
    # 3. Notify Admins
    asyncio.create_task(send_to_admin_group(message.bot, message.from_user.id, data, data['payment_file_id']))
    
    await state.clear()
    
#For rejection Purpose
@router.callback_query(F.data == "resume_reg")
async def resume_registration(callback: types.CallbackQuery, state: FSMContext, db: Database):
    user = await db.get_user(callback.from_user.id)
    step = user.get('registration_step')
    lang = user.get('language', 'EN')
    
    # 1. Map DB strings to the NEW order of states
    state_mapping = {
        'full_name': ChallengeStates.full_name,
        'phone': ChallengeStates.phone,
        'gender': ChallengeStates.gender,
        'age': ChallengeStates.age,
        'weight': ChallengeStates.weight,
        'legal': ChallengeStates.legal,
        'payment': ChallengeStates.payment_upload, # Changed order
        'fayda': ChallengeStates.fayda_upload,     # Changed order
        'photo_front': ChallengeStates.before_photo_front,
        'photo_side': ChallengeStates.before_photo_side,
        'photo_rear': ChallengeStates.before_photo_rear,
    }

    target_state = state_mapping.get(step, ChallengeStates.full_name)
    
    # 2. Re-hydrate FSM memory from DB
    await state.update_data(
        language=lang,
        full_name=user.get('full_name'),
        phone_number=user.get('phone_number'),
        gender=user.get('gender'),
        age=user.get('age'),
        current_weight_kg=user.get('current_weight_kg')
    )

    await state.set_state(target_state)

    # 3. Dynamic Prompts based on new flow
    prompts = {
        'payment': get_payment_text(lang),
        'fayda': get_text(lang, "ask_fayda"),
        'photo_front': get_text(lang, "ask_photo_front"),
        'photo_side': get_text(lang, "ask_photo_side"),
        'photo_rear': get_text(lang, "ask_photo_rear")
    }
    
    # Fallback if step isn't in prompts
    instruction = prompts.get(step, get_text(lang, "ask_full_name") if step == 'full_name' else "Please continue...")
    
    await callback.message.answer(f"✅ <b>RESUMED / ቀጥል</b>\n\n{instruction}", parse_mode="HTML")
    await callback.answer()
    


@router.callback_query(F.data == "retry_registration")
async def process_retry_registration(callback: types.CallbackQuery, state: FSMContext, db: Database):
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    lang = user.get('language', 'EN') if user else 'EN'

    # 1. Wipe ONLY physique photos. Keep Payment & Fayda ID.
    await db.update_user(
        user_id,
        photo_front_file_id=None,
        photo_side_file_id=None,
        photo_rear_file_id=None,
        registration_step='photo_front' # Set them back to photos
    )

    # 2. Set FSM back to the first photo
    await state.set_state(ChallengeStates.before_photo_front)
    await state.update_data(language=lang)

    # 3. Instruction & Reference Gallery
    instruction = (
        "<b>RE-UPLOAD STARTED</b> 🔄\n\n"
        "Your payment was verified, but your photos were rejected. Please follow the examples below and send your <b>FRONT VIEW</b> photo."
        if lang == "EN" else
        "<b>የፎቶ መላክ ሂደት ተጀምሯል</b> 🔄\n\n"
        "ክፍያዎ ተረጋግጧል፤ ነገር ግን የላኩት ፎቶ ተቀባይነት አላገኘም። እባክዎን ከታች ያለውን ምሳሌ በመከተል <b>የፊት ለፊት</b> ፎቶዎን ይላኩ።"
    )

    album = MediaGroupBuilder(caption=get_text(lang, "photo_gallery_intro"))
    album.add_photo(media=Config.BEFORE_EXAMPLE_ID) 
    album.add_photo(media=Config.BEFORE_SIDE_ID)    
    album.add_photo(media=Config.BEFORE_REAR_ID)    
    
    await callback.message.answer_media_group(media=album.build())
    await callback.message.answer(instruction, parse_mode="HTML")
    await callback.answer()
    


@router.message(
    StateFilter(
        ChallengeStates.before_photo_front, 
        ChallengeStates.before_photo_side, 
        ChallengeStates.before_photo_rear,
        ChallengeStates.fayda_upload,
        ChallengeStates.payment_upload
    )
)
async def handle_photo_inputs(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('language', 'EN')

    # A. Check if it's a photo
    if not message.photo:
        error_text = (
            "❌ <b>Invalid format!</b>\nPlease send a <b>PHOTO</b> (not a file or text)."
            if lang == "EN" else
            "❌ <b>የተሳሳተ አላላክ!</b>\nእባክዎን <b>ፎቶ</b> ብቻ ይላኩ (ፋይል ወይም ጽሁፍ አይቀበልም)።"
        )
        return await message.answer(error_text, parse_mode="HTML")

    # B. Check if they sent a gallery (Batch)
    if message.media_group_id:
        error_batch = (
            "⚠️ Please send photos <b>one by one</b>, not as a group."
            if lang == "EN" else
            "⚠️ እባክዎን ፎቶዎቹን <b>አንዱን ከላኩ በኋላ ቀጣዩን</b> ይላኩ (በአንድ ላይ አይላኩ)።"
        )
        return await message.answer(error_batch, parse_mode="HTML")

   
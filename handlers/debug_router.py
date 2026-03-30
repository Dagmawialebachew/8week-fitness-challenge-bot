from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import Database
from utils.localization import LEGAL_TEXTS, get_text
from keyboards import inline as kb
from config import settings as Config


router = Router(name="debug_router")


@router.message(F.photo)
async def get_photo_id(message: types.Message):
    # This will print to your terminal directly
    file_id = message.photo[-1].file_id
    print(f"\n📸 CAPTURED FILE ID: {file_id}\n") 

    response = (
        f"✅ *High-Res File ID Captured:*\n\n"
        f"`{file_id}`\n\n"
        f"Copy this into your .env"
    )
    await message.reply(response, parse_mode="Markdown")
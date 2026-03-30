from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import settings
from database.db import Database

# --- THE ELITE FIX ---
# By setting ParseMode.HTML here, every message sent by this 'bot' 
# instance will automatically convert <b>, <i>, and <a> tags.
bot = Bot(
    token=settings.BOT_TOKEN, 
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()
db = Database(dsn=settings.DATABASE_URL)
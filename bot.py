import asyncio
import logging
import os
import sys

from aiohttp import web
import aiohttp_cors

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import settings
from app_context import bot, dp, db
# from middlewares.language import LanguageMiddleware
from middlewares.throttling_middleware import ThrottlingMiddleware

# Import your admin API route setup
# from api.api import setup_admin_routes

# 1. LOGGING CONFIGURATION (Cinematic/Clean)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

# Include all handlers (onboarding, payment, etc.)
dp["db"] = db


from handlers import all_routers
for r in all_routers:
    dp.include_router(r)

# Error handling MUST be included last to catch unhandled exceptions in the chain

dp.message.middleware(ThrottlingMiddleware(message_interval=0.8))
dp.callback_query.middleware(ThrottlingMiddleware(message_interval=0.5))


from middlewares.error_handling_middleware import router as error_router
dp.include_router(error_router)

# 3. DYNAMIC BILINGUAL COMMANDS
async def set_commands(bot: Bot, admin_ids: list[int]):
    """Sets the menu commands for users (Default) and Admins (Specific Scope)."""
    
    # User Commands (Global)
    user_commands = [
        BotCommand(command="start", description="🚀 Start / ጀምር"),
        BotCommand(command="help", description="❓ Help / እርዳታ"),
    ]
    
    # Admin Commands (Visible only to ADMIN_IDS)
    admin_commands = user_commands + [
        BotCommand(command="admin", description="🔐 Dashboard"),
    ]

    try:
        # Set default for everyone
        await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())
        
        # Set specific commands for each admin
        for admin_id in admin_ids:
            try:
                await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
            except Exception as e:
                logging.warning(f"Could not set admin commands for {admin_id}: {e}")
                
    except Exception as e:
        logging.exception("Failed to set bot commands: %s", e)

# 4. LIFECYCLE HOOKS
async def on_startup(bot: Bot):
    logging.info("🔥 [ELITE 8] Engine Ignited. Initializing systems...")
    await db.connect()
    await db.setup()  # Auto-migrates the new schema we built
    await set_commands(bot, settings.ADMIN_IDS)

    if os.getenv("WEBHOOK_BASE_URL"):
        webhook_url = f"{settings.WEBHOOK_BASE_URL}/webhook"
        await bot.set_webhook(webhook_url, drop_pending_updates=True)
        logging.info(f"🌐 Webhook Active: {webhook_url}")

async def on_shutdown(bot: Bot):
    logging.info("🛑 [ELITE 8] Safe shutdown initiated...")
    await db.disconnect()
    await bot.session.close()

# 5. AIOHTTP APP FACTORY (Admin Dashboard Backend)
async def create_app() -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app["db"] = db

    # Health Check for Render/Railway/DigitalOcean uptime monitoring
    app.router.add_get("/health", lambda _: web.json_response({"status": "optimal"}))

    # Register Telegram Webhook
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path="/webhook")

    # Setup Dashboard Routes
    # setup_admin_routes(app)

    # CORS Setup for the Admin Frontend
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        ),
    })

    for route in list(app.router.routes()):
        if not isinstance(route.resource, web.StaticResource):
            cors.add(route)

    # Aiogram App Integration
    setup_application(app, dp, bot=bot)
    app.on_startup.append(lambda _: on_startup(bot))
    # Using on_cleanup for graceful termination
    app.on_cleanup.append(lambda _: on_shutdown(bot))
    
    return app

# 6. RUN MODES
async def start_polling():
    await on_startup(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        await on_shutdown(bot)

if __name__ == "__main__":
    if "--polling" in sys.argv:
        logging.info("🔌 Starting in POLLING mode (Local Dev)...")
        asyncio.run(start_polling())
    else:
        port = int(os.getenv("PORT", "8080"))
        logging.info(f"🌐 Starting in WEBHOOK mode on port {port}...")
        web.run_app(create_app(), host="0.0.0.0", port=port)
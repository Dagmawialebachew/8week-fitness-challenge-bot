import time
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from typing import Callable, Dict, Any, Awaitable

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, message_interval: float = 0.8, callback_interval: float = 0.5) -> None:
        super().__init__()
        self.message_interval = message_interval
        self.callback_interval = callback_interval
        self.users: dict[str, float] = {}
        
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        if not user or user.is_bot:
            return await handler(event, data)

        user_id = user.id
        now = time.time()
        
        is_callback = isinstance(event, CallbackQuery)
        event_key = f"{'cb' if is_callback else 'msg'}_{user_id}"
        limit = self.callback_interval if is_callback else self.message_interval

        last_time = self.users.get(event_key, 0.0)
        if (now - last_time) < limit:
            if is_callback:
                # Get language from FSM or DB data if available
                lang = data.get("language", "EN")
                alert = "⚡️ Easy! Processing..." if lang == "EN" else "⚡️ ቀስ ይበሉ! እየሰራን ነው..."
                try:
                    await event.answer(alert, show_alert=False)
                except:
                    pass
            return None 

        self.users[event_key] = now
        
        # Cleanup to prevent memory leaks
        if len(self.users) > 2000:
            self.users = {k: v for k, v in self.users.items() if (now - v) < 60}

        return await handler(event, data)
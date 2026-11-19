from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class AccessMiddleware(BaseMiddleware):
    """Faqat ro'yxatdagi foydalanuvchilar (ega va u qo'shganlar) botdan foydalanadi."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        db = data["db"]
        if user is None or not await db.is_allowed(user.id):
            if isinstance(event, Message):
                await event.answer(
                    f"Bu yopiq bot. Sizning ID: <code>{user.id if user else '?'}</code>\n"
                    "Egasi sizni qo'shishi kerak."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer("Ruxsat yo'q", show_alert=True)
            return None
        row = await db.get_user(user.id)
        data["role"] = row["role"]
        data["user_name"] = row["name"] or user.first_name or ""
        return await handler(event, data)

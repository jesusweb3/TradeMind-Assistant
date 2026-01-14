"""
Middleware — промежуточные обработчики.
"""

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from config import config
from utils.logger import get_logger

logger = get_logger(__name__)


class AccessMiddleware(BaseMiddleware):
    """
    Middleware для проверки доступа пользователей.
    Если user_id не в ALLOWED_USER_IDS — сообщение игнорируется.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Получаем user_id в зависимости от типа события
        user_id = None
        
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
        
        # Если не удалось получить user_id — игнорируем
        if user_id is None:
            return None
        
        # Проверяем доступ
        if user_id not in config.ALLOWED_USER_IDS:
            logger.warning(f"Доступ запрещён для user_id={user_id}")
            return None  # Просто игнорируем, не отвечаем
        
        # Пользователь разрешён — передаём дальше
        return await handler(event, data)

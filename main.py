"""
TradeMind Assistant — Telegram-бот для ведения дневника трейдера.

Точка входа приложения.
"""

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import config
from bot.handlers import router
from bot.middlewares import AccessMiddleware
from utils.logger import get_logger

# Инициализируем логгер
logger = get_logger(__name__)


async def main() -> None:
    """Запуск бота."""
    # Проверяем конфигурацию
    config.validate()
    
    logger.info(f"Разрешённые пользователи: {config.ALLOWED_USER_IDS}")
    
    # Инициализируем бота с настройками по умолчанию
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    
    # Создаём диспетчер
    dp = Dispatcher()
    
    # Подключаем middleware для проверки доступа
    dp.message.middleware(AccessMiddleware())
    dp.callback_query.middleware(AccessMiddleware())
    
    # Подключаем роутеры (обработчики)
    dp.include_router(router)
    
    # Запуск
    logger.info("Бот запущен...")
    
    try:
        # Удаляем вебхуки и запускаем polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        logger.info("Бот остановлен...")
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

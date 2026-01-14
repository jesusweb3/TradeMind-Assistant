"""
Конфигурация приложения.
Загружает переменные окружения из .env файла.
"""

import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()


def parse_user_ids(value: str) -> set[int]:
    """Парсит список ID пользователей из строки."""
    if not value:
        return set()
    
    ids = set()
    for item in value.split(","):
        item = item.strip()
        if item.isdigit():
            ids.add(int(item))
    return ids


class Config:
    """Основная конфигурация бота."""
    
    # Telegram
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # Разрешённые пользователи (через запятую)
    ALLOWED_USER_IDS: set[int] = parse_user_ids(os.getenv("ALLOWED_USER_IDS", ""))
    
    # OpenRouter
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    
    # Google
    GOOGLE_SHEET_ID: str = os.getenv("GOOGLE_SHEET_ID", "")
    GOOGLE_SERVICE_ACCOUNT_FILE: str = os.getenv(
        "GOOGLE_SERVICE_ACCOUNT_FILE", 
        "service-account.json"
    )
    
    @classmethod
    def validate(cls) -> bool:
        """Проверяет, что обязательные переменные заданы."""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не задан! Проверьте .env файл.")
        if not cls.ALLOWED_USER_IDS:
            raise ValueError("ALLOWED_USER_IDS не задан! Укажите хотя бы свой Telegram ID.")
        return True


# Создаём экземпляр конфигурации
config = Config()

"""
Обработка текста через LLM (OpenRouter).
Извлечение структурированных данных о сделке.
"""

import json
import re
from dataclasses import dataclass
from typing import Optional

import requests

from utils.config import config
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TradeInfo:
    """Информация о сделке, извлечённая из текста."""
    asset: str          # Актив, например "BTC/USDT"
    scenario: str       # Сценарий, например "ЛП", "Пробой"
    date: str           # Дата, например "03.10.2025"
    raw_text: str       # Исходный текст


SYSTEM_PROMPT = """Ты помощник криптовалютного трейдера. Твоя задача — извлечь из текста информацию о сделке.

Извлеки:
1. Актив (тикер) — формат: BTC/USDT, ETH/USDT и т.д.
2. Сценарий — тип входа: ЛП, ЛПП, Пробой, Ретест, или другое
3. Дата — формат: DD.MM.YYYY

Если информация не указана явно, попробуй определить из контекста.
Если дата не указана, используй "не указана".

Ответь ТОЛЬКО валидным JSON без markdown:
{"asset": "BTC/USDT", "scenario": "ЛП", "date": "03.10.2025"}"""


def extract_trade_info(text: str) -> Optional[TradeInfo]:
    """
    Извлекает информацию о сделке из текста через LLM.
    
    Args:
        text: Текст описания сделки (от пользователя)
    
    Returns:
        TradeInfo с извлечёнными данными или None при ошибке
    """
    if not config.OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY не задан")
        return None
    
    logger.info(f"Отправка в LLM: {text[:100]}...")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": config.LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Извлеки данные из этого описания сделки:\n\n{text}"}
        ],
        "temperature": 0,
        "max_tokens": 200
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Ошибка OpenRouter: {response.status_code} - {response.text}")
            return None
        
        answer = response.json()['choices'][0]['message']['content']
        logger.info(f"Ответ LLM: {answer}")
        
        # Парсим JSON из ответа
        data = _parse_json_response(answer)
        
        if data:
            return TradeInfo(
                asset=data.get("asset", "Не указан"),
                scenario=data.get("scenario", "Не указан"),
                date=data.get("date", "Не указана"),
                raw_text=text
            )
        
        return None
        
    except requests.RequestException as e:
        logger.error(f"Ошибка запроса к OpenRouter: {e}")
        return None
    except (KeyError, json.JSONDecodeError) as e:
        logger.error(f"Ошибка парсинга ответа: {e}")
        return None


def _parse_json_response(text: str) -> Optional[dict]:
    """Извлекает JSON из ответа LLM."""
    # Пробуем напрямую
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Ищем JSON в тексте
    json_match = re.search(r'\{[^{}]+\}', text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    logger.warning(f"Не удалось распарсить JSON: {text}")
    return None

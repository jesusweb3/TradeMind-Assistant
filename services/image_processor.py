"""
Обработка изображений — склейка скриншотов в коллаж.
"""

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TradeHeader:
    """Данные для заголовка коллажа."""
    asset: str       # "BTC/USDT"
    scenario: str    # "ЛП"
    date: str        # "03.10.2025"


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Получает шрифт нужного размера."""
    # Пробуем загрузить системные шрифты
    font_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    
    for font_path in font_paths:
        if Path(font_path).exists():
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue
    
    # Fallback на встроенный шрифт
    return ImageFont.load_default()


def create_vertical_collage(images: list[bytes]) -> bytes:
    """
    Создаёт вертикальный коллаж из списка изображений (без заголовка).
    
    Args:
        images: Список изображений в виде байтов (bytes)
    
    Returns:
        Готовый коллаж в формате JPEG (bytes)
    """
    if not images:
        raise ValueError("Список изображений пуст")
    
    pil_images = _load_images(images)
    collage = _stitch_images(pil_images)
    
    return _save_to_bytes(collage)


def create_collage_with_header(
    images: list[bytes],
    header: TradeHeader
) -> bytes:
    """
    Создаёт коллаж с заголовком (информация о сделке сверху).
    
    Args:
        images: Список изображений в виде байтов
        header: Данные для заголовка (актив, сценарий, дата)
    
    Returns:
        Готовый коллаж с заголовком в формате JPEG (bytes)
    """
    if not images:
        raise ValueError("Список изображений пуст")
    
    # Создаём базовый коллаж
    pil_images = _load_images(images)
    base_collage = _stitch_images(pil_images)
    
    # Добавляем заголовок
    final_collage = _add_header(base_collage, header)
    
    return _save_to_bytes(final_collage)


def _load_images(images: list[bytes]) -> list[Image.Image]:
    """Загружает и конвертирует изображения."""
    pil_images: list[Image.Image] = []
    
    for i, img_bytes in enumerate(images):
        try:
            img = Image.open(io.BytesIO(img_bytes))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            pil_images.append(img)
            logger.info(f"Изображение #{i+1}: {img.size[0]}x{img.size[1]}")
        except Exception as e:
            logger.error(f"Ошибка открытия изображения #{i+1}: {e}")
            raise
    
    return pil_images


def _stitch_images(pil_images: list[Image.Image]) -> Image.Image:
    """Склеивает изображения вертикально."""
    max_width = max(img.size[0] for img in pil_images)
    total_height = sum(img.size[1] for img in pil_images)
    
    logger.info(f"Склейка: {max_width}x{total_height} из {len(pil_images)} изображений")
    
    # Белый фон
    collage = Image.new("RGB", (max_width, total_height), (255, 255, 255))
    
    y_offset = 0
    for i, img in enumerate(pil_images):
        x_offset = (max_width - img.size[0]) // 2
        collage.paste(img, (x_offset, y_offset))
        y_offset += img.size[1]
    
    return collage


def _add_header(collage: Image.Image, header: TradeHeader) -> Image.Image:
    """Добавляет заголовок с информацией о сделке."""
    collage_width, collage_height = collage.size
    
    # Размеры заголовка (две строки с увеличенным отступом)
    header_height = 110
    padding = 30
    
    # Создаём новый холст: header + collage
    new_height = collage_height + header_height
    final = Image.new("RGB", (collage_width, new_height), (18, 18, 24))  # Тёмный фон
    
    # Вставляем коллаж ниже заголовка
    final.paste(collage, (0, header_height))
    
    # Рисуем заголовок
    draw = ImageDraw.Draw(final)
    
    # Шрифты (увеличены)
    font_title = _get_font(36)
    font_label = _get_font(24)
    font_value = _get_font(26)
    
    # === СТРОКА 1: Заголовок по центру ===
    title_text = f"Сделка {header.asset}"
    title_bbox = draw.textbbox((0, 0), title_text, font=font_title)
    title_width = title_bbox[2] - title_bbox[0]
    
    draw.text(
        ((collage_width - title_width) // 2, 12),
        title_text,
        font=font_title,
        fill=(255, 255, 255)
    )
    
    # === СТРОКА 2: Сценарий (лейбл) | Значение | Дата ===
    row2_y = 65  # Увеличен отступ от первой строки
    
    # Левая часть: "Сценарий"
    draw.text(
        (padding, row2_y),
        "Сценарий",
        font=font_label,
        fill=(255, 255, 255)  # Белый
    )
    
    # Центр: значение сценария (в плашке)
    scenario_text = header.scenario
    scenario_bbox = draw.textbbox((0, 0), scenario_text, font=font_value)
    scenario_width = scenario_bbox[2] - scenario_bbox[0]
    scenario_height = scenario_bbox[3] - scenario_bbox[1]
    
    box_padding = 20
    box_width = scenario_width + box_padding * 2
    box_height = scenario_height + 16
    box_x = (collage_width - box_width) // 2
    box_y = row2_y - 5
    
    # Плашка
    draw.rounded_rectangle(
        [box_x, box_y, box_x + box_width, box_y + box_height],
        radius=8,
        fill=(45, 45, 55)
    )
    
    # Текст сценария
    draw.text(
        (box_x + box_padding, row2_y),
        scenario_text,
        font=font_value,
        fill=(255, 255, 255)
    )
    
    # Правая часть: Дата
    date_text = f"Дата {header.date}"
    date_bbox = draw.textbbox((0, 0), date_text, font=font_label)
    date_width = date_bbox[2] - date_bbox[0]
    
    draw.text(
        (collage_width - date_width - padding, row2_y),
        date_text,
        font=font_label,
        fill=(255, 255, 255)  # Белый
    )
    
    logger.info(f"Добавлен заголовок: {header.asset} | {header.scenario} | {header.date}")
    
    return final


def _save_to_bytes(image: Image.Image) -> bytes:
    """Сохраняет изображение в байты JPEG."""
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=95)
    output.seek(0)
    
    result_bytes = output.getvalue()
    logger.info(f"Коллаж сохранён: {len(result_bytes) / 1024:.1f} KB")
    
    return result_bytes

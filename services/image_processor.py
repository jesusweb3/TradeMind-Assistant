"""
Обработка изображений — склейка скриншотов в коллаж.
"""

import io
from pathlib import Path

from PIL import Image

from utils.logger import get_logger

logger = get_logger(__name__)


def create_vertical_collage(images: list[bytes]) -> bytes:
    """
    Создаёт вертикальный коллаж из списка изображений.
    
    Args:
        images: Список изображений в виде байтов (bytes)
    
    Returns:
        Готовый коллаж в формате PNG (bytes)
    """
    if not images:
        raise ValueError("Список изображений пуст")
    
    # Открываем все изображения
    pil_images: list[Image.Image] = []
    for i, img_bytes in enumerate(images):
        try:
            img = Image.open(io.BytesIO(img_bytes))
            # Конвертируем в RGB если нужно (для PNG с прозрачностью)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            pil_images.append(img)
            logger.info(f"Изображение #{i+1}: {img.size[0]}x{img.size[1]}")
        except Exception as e:
            logger.error(f"Ошибка открытия изображения #{i+1}: {e}")
            raise
    
    # Вычисляем размеры коллажа
    # Ширина = максимальная ширина среди всех изображений
    # Высота = сумма высот всех изображений
    max_width = max(img.size[0] for img in pil_images)
    total_height = sum(img.size[1] for img in pil_images)
    
    logger.info(f"Создаём коллаж: {max_width}x{total_height} из {len(pil_images)} изображений")
    
    # Создаём канвас для коллажа (белый фон)
    collage = Image.new("RGB", (max_width, total_height), (255, 255, 255))
    
    # Вставляем изображения вертикально
    y_offset = 0
    for i, img in enumerate(pil_images):
        # Центрируем изображение по горизонтали если оно уже максимальной ширины
        x_offset = (max_width - img.size[0]) // 2
        collage.paste(img, (x_offset, y_offset))
        y_offset += img.size[1]
        logger.info(f"Вставлено изображение #{i+1} на позицию y={y_offset - img.size[1]}")
    
    # Сохраняем в байты
    output = io.BytesIO()
    collage.save(output, format="JPEG", quality=100)
    output.seek(0)
    
    result_bytes = output.getvalue()
    logger.info(f"Коллаж создан: {len(result_bytes) / 1024:.1f} KB")
    
    return result_bytes

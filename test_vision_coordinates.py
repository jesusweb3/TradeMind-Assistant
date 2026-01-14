"""
Тест: может ли ИИ вернуть координаты для размещения текста на графике.
"""

import base64
import json
from pathlib import Path

import requests
from PIL import Image

from utils.config import config

# Путь к тестовому изображению
IMAGE_PATH = r"C:\Users\Hookller\Desktop\photo_2026-01-14_21-28-10.jpg"


def encode_image_to_base64(image_path: str) -> str:
    """Кодирует изображение в base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_image_size(image_path: str) -> tuple[int, int]:
    """Получает размер изображения."""
    with Image.open(image_path) as img:
        return img.size


def ask_for_coordinates(image_path: str, model: str = None) -> dict:
    """Отправляет изображение в LLM и просит вернуть координаты."""
    
    # Получаем размер изображения
    width, height = get_image_size(image_path)
    print(f"📐 Размер изображения: {width}x{height}")
    
    # Кодируем в base64
    image_base64 = encode_image_to_base64(image_path)
    
    # Улучшенный промпт
    prompt = f"""Проанализируй это изображение с несколькими графиками.
Размер изображения: {width}x{height} пикселей.

Найди 3-5 интересных мест на графиках где можно разместить текстовые подписи:
- Места с резкими движениями цены
- Горизонтальные уровни (линии)
- Области выделенные цветом (прямоугольники, зоны)
- Стрелки или маркеры если есть

Для каждого места укажи координаты (x, y) в пикселях от левого верхнего угла.
Подпись должна быть рядом с элементом, но не перекрывать его.

Ответь ТОЛЬКО валидным JSON без markdown:
{{
  "key_points": [
    {{
      "x": число,
      "y": число, 
      "element": "описание элемента",
      "suggested_label": "короткая подпись"
    }}
  ]
}}"""

    # Запрос к OpenRouter с vision
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Используем переданную модель или из конфига
    use_model = model or config.LLM_MODEL
    
    payload = {
        "model": use_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0,
        "max_tokens": 500
    }
    
    print(f"🤖 Отправляю в {use_model}...")
    
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    
    if response.status_code != 200:
        print(f"❌ Ошибка: {response.status_code}")
        print(response.text)
        return {}
    
    answer = response.json()['choices'][0]['message']['content']
    print(f"\n📝 Ответ LLM:\n{answer}\n")
    
    # Парсим JSON
    try:
        # Убираем возможные markdown-обёртки
        clean = answer.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1]
            clean = clean.rsplit("```", 1)[0]
        
        return json.loads(clean)
    except json.JSONDecodeError as e:
        print(f"⚠️ Не удалось распарсить JSON: {e}")
        return {"raw": answer}


def visualize_coordinates(image_path: str, data: dict) -> None:
    """Рисует точки на изображении для визуализации."""
    from PIL import ImageDraw, ImageFont
    
    # Поддержка обоих форматов
    points = data.get("key_points") or data.get("free_zones") or []
    
    if not points:
        print("Нет координат для визуализации")
        return
    
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    colors = [(255, 50, 50), (50, 255, 50), (50, 150, 255), (255, 255, 50), (255, 50, 255)]
    
    for i, point in enumerate(points):
        x = point.get("x", 0)
        y = point.get("y", 0)
        label = point.get("suggested_label") or point.get("suggested_text") or f"Point {i+1}"
        element = point.get("element") or point.get("description") or ""
        color = colors[i % len(colors)]
        
        # Рисуем маркер (круг с обводкой)
        draw.ellipse([x-8, y-8, x+8, y+8], fill=color, outline="white", width=2)
        
        # Рисуем подпись с фоном
        text_bbox = draw.textbbox((0, 0), label, font=font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        
        # Фон для текста
        padding = 4
        draw.rectangle(
            [x + 12, y - 5, x + 12 + text_w + padding*2, y - 5 + text_h + padding*2],
            fill=(0, 0, 0, 180)
        )
        draw.text((x + 12 + padding, y - 5 + padding), label, font=font, fill=color)
        
        print(f"📍 Point {i+1}: ({x}, {y})")
        print(f"   Element: {element}")
        print(f"   Label: {label}")
        print()
    
    # Сохраняем результат
    output_path = Path(image_path).parent / "test_coordinates_result.jpg"
    img.save(output_path, quality=95)
    print(f"💾 Результат сохранён: {output_path}")


if __name__ == "__main__":
    image_file = Path(IMAGE_PATH)
    
    if not image_file.exists():
        print(f"❌ Файл не найден: {image_file}")
        exit(1)
    
    print(f"🖼 Изображение: {image_file}")
    print(f"📦 Размер файла: {image_file.stat().st_size / 1024:.1f} KB")
    print()
    
    # Лучшие модели для vision
    VISION_MODELS = [
        "openai/gpt-4o",
        "anthropic/claude-3.5-sonnet",  # Отлично работает с vision
        "google/gemini-2.0-flash-exp",  # Быстрая и хорошая
        "google/gemini-1.5-pro",        # Более мощная
    ]
    
    # Выбери модель (0, 1 или 2)
    selected_model = VISION_MODELS[0]  # Claude по умолчанию
    
    print(f"🎯 Используем модель: {selected_model}")
    print()
    
    # Получаем координаты от ИИ
    result = ask_for_coordinates(str(image_file), model=selected_model)
    
    if result:
        print("\n" + "=" * 50)
        print("📊 Результат:")
        print("=" * 50)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # Визуализируем
        if "key_points" in result or "free_zones" in result:
            print("\n🎨 Создаю визуализацию...")
            visualize_coordinates(str(image_file), result)

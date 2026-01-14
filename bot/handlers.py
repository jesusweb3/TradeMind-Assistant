"""
Обработчики команд и сообщений бота.
"""

import io

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, BufferedInputFile
from aiogram.fsm.context import FSMContext

from bot.keyboards import get_main_menu, get_done_keyboard, get_cancel_keyboard
from bot.states import TradeStates
from bot.texts import WELCOME, MAIN_MENU, HELP
from services.image_processor import create_vertical_collage
from utils.logger import get_logger

# Инициализируем логгер
logger = get_logger(__name__)

# Создаём роутер для обработчиков
router = Router()


async def show_main_menu(message: Message) -> None:
    """Показать главное меню."""
    await message.answer(
        MAIN_MENU,
        reply_markup=get_main_menu(),
        parse_mode="HTML",
    )


# ==================== КОМАНДЫ ====================

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Обработчик команды /start — приветствие и главное меню."""
    await state.clear()
    
    user = message.from_user
    logger.info(f"Пользователь {user.id} (@{user.username}) запустил бота")
    
    await message.answer(
        WELCOME,
        reply_markup=get_main_menu(),
        parse_mode="HTML",
    )


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def cmd_help(message: Message) -> None:
    """Обработчик команды /help — справка."""
    logger.info(f"Пользователь {message.from_user.id} запросил помощь")
    
    await message.answer(HELP, parse_mode="HTML")


@router.message(Command("new"))
@router.message(F.text == "➕ Новая сделка")
async def cmd_new_trade(message: Message, state: FSMContext) -> None:
    """Начало записи новой сделки."""
    logger.info(f"Пользователь {message.from_user.id} начал новую сделку")
    
    await state.set_state(TradeStates.waiting_for_screenshots)
    await state.update_data(screenshots=[])
    
    await message.answer(
        "📸 <b>Новая сделка</b>\n\n"
        "Отправь скриншоты сделки (можно несколько).\n"
        "Когда закончишь — нажми «✅ Готово».",
        reply_markup=get_done_keyboard(),
        parse_mode="HTML",
    )


@router.message(Command("stats"))
@router.message(F.text == "📊 Статистика")
async def cmd_stats(message: Message) -> None:
    """Показать статистику сделок."""
    logger.info(f"Пользователь {message.from_user.id} запросил статистику")
    
    # TODO: Реализовать получение статистики из Google Sheets
    await message.answer(
        "📊 <b>Статистика</b>\n\n"
        "🚧 Функция в разработке...\n"
        "Скоро здесь появится аналитика твоих сделок!",
        parse_mode="HTML",
    )


@router.message(Command("cancel"))
@router.message(F.text == "❌ Отмена")
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Отмена текущего действия и возврат в главное меню."""
    current_state = await state.get_state()
    
    if current_state is None:
        await message.answer("🤷 Нечего отменять.")
        await show_main_menu(message)
        return
    
    logger.info(f"Пользователь {message.from_user.id} отменил действие (состояние: {current_state})")
    
    await state.clear()
    await message.answer("❌ Действие отменено.")
    await show_main_menu(message)


# ==================== ОБРАБОТКА СКРИНШОТОВ ====================

@router.message(TradeStates.waiting_for_screenshots, F.photo)
async def handle_screenshot(message: Message, state: FSMContext) -> None:
    """Обработка скриншотов — сохраняем file_id."""
    data = await state.get_data()
    screenshots = data.get("screenshots", [])
    
    # Берём фото максимального качества
    photo = message.photo[-1]
    screenshots.append(photo.file_id)
    
    await state.update_data(screenshots=screenshots)
    
    logger.info(f"Пользователь {message.from_user.id} загрузил скриншот #{len(screenshots)}")
    
    await message.answer(
        f"✅ Скриншот #{len(screenshots)} получен!\n"
        "Отправь ещё или нажми «✅ Готово»."
    )


@router.message(TradeStates.waiting_for_screenshots, F.text == "✅ Готово")
async def finish_screenshots(message: Message, state: FSMContext, bot: Bot) -> None:
    """Завершение загрузки скриншотов — создаём коллаж."""
    data = await state.get_data()
    screenshots = data.get("screenshots", [])
    
    if not screenshots:
        await message.answer(
            "⚠️ Ты не отправил ни одного скриншота!\n"
            "Отправь хотя бы один или нажми «❌ Отмена»."
        )
        return
    
    logger.info(f"Пользователь {message.from_user.id} завершил загрузку ({len(screenshots)} скриншотов)")
    
    # Уведомляем о начале обработки
    processing_msg = await message.answer("⏳ Создаю коллаж...")
    
    try:
        # Скачиваем все изображения
        images_bytes: list[bytes] = []
        for i, file_id in enumerate(screenshots):
            file = await bot.get_file(file_id)
            file_data = await bot.download_file(file.file_path)
            images_bytes.append(file_data.read())
            logger.info(f"Скачано изображение #{i+1}/{len(screenshots)}")
        
        # Создаём коллаж
        collage_bytes = create_vertical_collage(images_bytes)
        
        # Сохраняем коллаж в state для дальнейшего использования
        await state.update_data(collage=collage_bytes)
        
        # Отправляем коллаж пользователю
        collage_file = BufferedInputFile(
            file=collage_bytes,
            filename="trade_collage.jpg"
        )
        
        await message.answer_photo(
            photo=collage_file,
            caption=f"🖼 <b>Коллаж готов!</b>\n📸 Склеено изображений: {len(screenshots)}"
        )
        
        # Удаляем сообщение "Создаю коллаж..."
        await processing_msg.delete()
        
        # Переходим к описанию
        await state.set_state(TradeStates.waiting_for_description)
        await message.answer(
            "🎤 Теперь опиши сделку:\n"
            "• Отправь голосовое сообщение, или\n"
            "• Напиши текстом",
            reply_markup=get_cancel_keyboard(),
        )
        
    except Exception as e:
        logger.error(f"Ошибка создания коллажа: {e}")
        await processing_msg.edit_text("❌ Ошибка при создании коллажа. Попробуй ещё раз.")
        await state.clear()
        await show_main_menu(message)


# ==================== ОБРАБОТКА ОПИСАНИЯ ====================

@router.message(TradeStates.waiting_for_description)
async def handle_description(message: Message, state: FSMContext) -> None:
    """Обработка описания сделки (заглушка)."""
    # TODO: Обработка голосовых (voice) и текстовых сообщений
    
    if message.voice:
        logger.info(f"Пользователь {message.from_user.id} отправил голосовое сообщение")
        await message.answer(
            "🎤 Голосовое сообщение получено!\n"
            "🚧 Распознавание речи в разработке...",
        )
    else:
        logger.info(f"Пользователь {message.from_user.id} отправил текстовое описание")
        await message.answer(
            f"📝 Описание получено: {message.text}\n"
            "🚧 Обработка данных в разработке...",
        )
    
    await state.clear()
    await show_main_menu(message)

"""
Обработчики команд и сообщений бота.
"""

import os
import tempfile
from pathlib import Path

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, BufferedInputFile
from aiogram.fsm.context import FSMContext

from bot.keyboards import get_main_menu, get_done_keyboard, get_cancel_keyboard
from bot.states import TradeStates
from bot.texts import WELCOME, MAIN_MENU, HELP
from services.image_processor import create_collage_with_header, TradeHeader
from services.llm_processor import extract_trade_info
from services.speech_to_text import transcribe_audio
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


# ==================== ШАГ 1: СКРИНШОТЫ ====================

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
    """Завершение загрузки скриншотов — переходим к запросу информации."""
    data = await state.get_data()
    screenshots = data.get("screenshots", [])
    
    if not screenshots:
        await message.answer(
            "⚠️ Ты не отправил ни одного скриншота!\n"
            "Отправь хотя бы один или нажми «❌ Отмена»."
        )
        return
    
    logger.info(f"Пользователь {message.from_user.id} завершил загрузку ({len(screenshots)} скриншотов)")
    
    # Скачиваем изображения заранее
    processing_msg = await message.answer("⏳ Обрабатываю скриншоты...")
    
    try:
        images_bytes: list[bytes] = []
        for i, file_id in enumerate(screenshots):
            file = await bot.get_file(file_id)
            file_data = await bot.download_file(file.file_path)
            images_bytes.append(file_data.read())
            logger.info(f"Скачано изображение #{i+1}/{len(screenshots)}")
        
        # Сохраняем байты изображений в state
        await state.update_data(images_bytes=images_bytes)
        
        await processing_msg.delete()
        
        # Переходим к запросу информации о сделке
        await state.set_state(TradeStates.waiting_for_trade_info)
        await message.answer(
            "📝 <b>Отлично!</b> Скриншоты получены.\n\n"
            "Теперь расскажи о сделке:\n"
            "• <b>Актив</b> (например: BTC, ETH)\n"
            "• <b>Сценарий</b> (ЛП, Пробой, Ретест...)\n"
            "• <b>Дата</b> сделки\n\n"
            "🎤 Отправь голосовое или напиши текстом.",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML",
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки скриншотов: {e}")
        await processing_msg.edit_text("❌ Ошибка обработки. Попробуй ещё раз.")
        await state.clear()
        await show_main_menu(message)


# ==================== ШАГ 2: ИНФОРМАЦИЯ О СДЕЛКЕ ====================

@router.message(TradeStates.waiting_for_trade_info, F.voice)
async def handle_voice_info(message: Message, state: FSMContext, bot: Bot) -> None:
    """Обработка голосового сообщения с информацией о сделке."""
    logger.info(f"Пользователь {message.from_user.id} отправил голосовое сообщение")
    
    processing_msg = await message.answer("🎤 Распознаю речь...")
    
    try:
        # Скачиваем голосовое сообщение
        voice = message.voice
        file = await bot.get_file(voice.file_id)
        file_data = await bot.download_file(file.file_path)
        
        # Сохраняем во временный файл
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp_file:
            tmp_file.write(file_data.read())
            tmp_path = tmp_file.name
        
        try:
            # Транскрибируем
            text = transcribe_audio(tmp_path)
            logger.info(f"Распознанный текст: {text}")
            
            await processing_msg.edit_text(f"🎤 Распознано:\n<i>{text}</i>")
            
            # Обрабатываем текст через LLM
            await _process_trade_info(message, state, text)
            
        finally:
            # Удаляем временный файл
            Path(tmp_path).unlink(missing_ok=True)
        
    except Exception as e:
        logger.error(f"Ошибка обработки голосового: {e}")
        await processing_msg.edit_text(
            "❌ Не удалось распознать речь.\n"
            "Попробуй ещё раз или напиши текстом."
        )


@router.message(TradeStates.waiting_for_trade_info, F.text)
async def handle_text_info(message: Message, state: FSMContext) -> None:
    """Обработка текстового описания сделки."""
    text = message.text
    
    # Игнорируем кнопку отмены (она обрабатывается отдельно)
    if text == "❌ Отмена":
        return
    
    logger.info(f"Пользователь {message.from_user.id} отправил текст: {text}")
    
    await _process_trade_info(message, state, text)


async def _process_trade_info(message: Message, state: FSMContext, text: str) -> None:
    """Общая логика обработки информации о сделке."""
    processing_msg = await message.answer("🤖 Анализирую данные...")
    
    try:
        # Извлекаем информацию через LLM
        trade_info = extract_trade_info(text)
        
        if not trade_info:
            await processing_msg.edit_text(
                "❌ Не удалось извлечь данные.\n"
                "Попробуй описать подробнее: актив, сценарий, дату."
            )
            return
        
        logger.info(f"Извлечено: {trade_info.asset}, {trade_info.scenario}, {trade_info.date}")
        
        # Получаем сохранённые изображения
        data = await state.get_data()
        images_bytes = data.get("images_bytes", [])
        
        if not images_bytes:
            await processing_msg.edit_text("❌ Изображения не найдены. Начни сначала.")
            await state.clear()
            await show_main_menu(message)
            return
        
        await processing_msg.edit_text("🖼 Создаю коллаж...")
        
        # Создаём коллаж с заголовком
        header = TradeHeader(
            asset=trade_info.asset,
            scenario=trade_info.scenario,
            date=trade_info.date
        )
        
        collage_bytes = create_collage_with_header(images_bytes, header)
        
        # Отправляем коллаж
        collage_file = BufferedInputFile(
            file=collage_bytes,
            filename="trade_collage.jpg"
        )
        
        await message.answer_photo(
            photo=collage_file,
            caption=(
                f"📊 <b>Сделка готова!</b>\n\n"
                f"📈 Актив: <b>{trade_info.asset}</b>\n"
                f"📋 Сценарий: <b>{trade_info.scenario}</b>\n"
                f"📅 Дата: <b>{trade_info.date}</b>"
            ),
            parse_mode="HTML"
        )
        
        await processing_msg.delete()
        
        # Завершаем
        await state.clear()
        await show_main_menu(message)
        
    except Exception as e:
        logger.error(f"Ошибка обработки информации: {e}")
        await processing_msg.edit_text("❌ Ошибка обработки. Попробуй ещё раз.")

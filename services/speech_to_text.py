"""
Распознавание речи через Faster Whisper.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from faster_whisper import WhisperModel

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class WhisperConfig:
    """Конфигурация Whisper."""
    model_size: str = "medium"
    language: Optional[str] = "ru"
    beam_size: int = 5
    vad_filter: bool = True
    use_gpu: bool = False


# Кэш модели
_model: Optional[WhisperModel] = None
_model_cfg: Optional[WhisperConfig] = None


def _get_model(cfg: WhisperConfig) -> WhisperModel:
    """
    Получает модель Whisper (с кэшированием).
    Модель загружается один раз и переиспользуется.
    """
    global _model, _model_cfg

    if _model is not None and _model_cfg == cfg:
        return _model

    logger.info(f"Загрузка модели Whisper: {cfg.model_size}")

    if cfg.use_gpu:
        device = "cuda"
        compute_type = "float16"
    else:
        device = "cpu"
        compute_type = "int8"

    _model = WhisperModel(cfg.model_size, device=device, compute_type=compute_type)
    _model_cfg = cfg
    
    logger.info(f"Модель Whisper загружена: device={device}, compute_type={compute_type}")
    return _model


def transcribe_audio(
    audio_path: str | Path,
    cfg: WhisperConfig = WhisperConfig()
) -> str:
    """
    Транскрибирует аудиофайл в текст.
    
    Args:
        audio_path: Путь к аудиофайлу (ogg, mp3, wav и др.)
        cfg: Конфигурация Whisper
    
    Returns:
        Распознанный текст
    """
    audio_path = str(audio_path)
    model = _get_model(cfg)
    
    logger.info(f"Начало транскрипции: {audio_path}")

    segments, info = model.transcribe(
        audio_path,
        vad_filter=cfg.vad_filter,
        beam_size=cfg.beam_size,
        language=cfg.language,
    )

    # Собираем текст из всех сегментов
    text = " ".join(seg.text.strip() for seg in segments if seg.text)
    text = text.strip()
    
    logger.info(f"Транскрипция завершена: {len(text)} символов, язык={info.language}")
    
    return text

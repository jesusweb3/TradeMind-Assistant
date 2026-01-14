"""
Состояния диалога (FSM — Finite State Machine).
"""

from aiogram.fsm.state import State, StatesGroup


class TradeStates(StatesGroup):
    """Состояния для записи сделки."""
    
    # Шаг 1: Ожидание скриншотов
    waiting_for_screenshots = State()
    
    # Шаг 2: Ожидание информации о сделке (голос/текст)
    waiting_for_trade_info = State()
    
    # Шаг 3: Подтверждение данных
    waiting_for_confirmation = State()

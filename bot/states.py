"""
Состояния диалога (FSM — Finite State Machine).
"""

from aiogram.fsm.state import State, StatesGroup


class TradeStates(StatesGroup):
    """Состояния для записи сделки."""
    
    # Ожидание скриншотов
    waiting_for_screenshots = State()
    
    # Ожидание описания (голос/текст)
    waiting_for_description = State()
    
    # Подтверждение данных
    waiting_for_confirmation = State()

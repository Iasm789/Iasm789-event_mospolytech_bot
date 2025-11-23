"""
Модуль для валидации данных о мероприятиях.
"""

import re
from datetime import datetime
from typing import Tuple

from config import Config


class Validator:
    """Класс для валидации различных полей мероприятий."""

    @staticmethod
    def validate_date(date_text: str) -> Tuple[bool, str]:
        """Проверяет формат даты DD.MM.YYYY"""
        pattern = r'^\d{2}\.\d{2}\.\d{4}$'
        if not re.match(pattern, date_text):
            return False, "❌ Неправильный формат даты. Используйте: ДД.ММ.ГГГГ (например: 25.12.2024)"

        try:
            day, month, year = map(int, date_text.split('.'))
            # Проверяем, что дата реальная
            datetime(year, month, day)
            return True, "✅ Дата корректна"
        except ValueError:
            return False, "❌ Несуществующая дата. Проверьте число, месяц и год"

    @staticmethod
    def validate_time(time_text: str) -> Tuple[bool, str]:
        """Проверяет формат времени HH:MM"""
        pattern = r'^\d{1,2}:\d{2}$'
        if not re.match(pattern, time_text):
            return False, "❌ Неправильный формат времени. Используйте: ЧЧ:MM (например: 14:30 или 9:05)"

        try:
            hours, minutes = map(int, time_text.split(':'))
            if not (0 <= hours <= 23):
                return False, "❌ Часы должны быть от 0 до 23"
            if not (0 <= minutes <= 59):
                return False, "❌ Минуты должны быть от 0 до 59"
            return True, "✅ Время корректно"
        except ValueError:
            return False, "❌ Неправильный формат времени"

    @staticmethod
    def validate_place(place_text: str) -> Tuple[bool, str]:
        """Проверяет, что место не содержит только цифры или спецсимволы"""
        if len(place_text.strip()) < Config.EVENT_PLACE_MIN_LEN:
            return False, "❌ Место проведения слишком короткое"

        # Проверяем, что есть хотя бы N букв
        letters = sum(1 for char in place_text if char.isalpha())
        if letters < Config.EVENT_PLACE_MIN_LETTERS:
            return False, f"❌ Укажите нормальное название места (например: Главный корпус, Ауд. 301)"

        return True, "✅ Место корректно"

    @staticmethod
    def validate_title(title_text: str) -> Tuple[bool, str]:
        """Проверяет название мероприятия"""
        if len(title_text.strip()) < Config.EVENT_TITLE_MIN_LEN:
            return False, f"❌ Название слишком короткое (минимум {Config.EVENT_TITLE_MIN_LEN} символов)"

        if len(title_text) > Config.EVENT_TITLE_MAX_LEN:
            return False, f"❌ Название слишком длинное (максимум {Config.EVENT_TITLE_MAX_LEN} символов)"

        return True, "✅ Название корректно"

    @staticmethod
    def validate_description(description: str) -> Tuple[bool, str]:
        """Проверяет описание мероприятия"""
        if len(description) < Config.EVENT_DESCRIPTION_MIN_LEN:
            return False, f"❌ Описание слишком короткое (минимум {Config.EVENT_DESCRIPTION_MIN_LEN} символов)"

        if len(description) > Config.EVENT_DESCRIPTION_MAX_LEN:
            return False, f"❌ Описание слишком длинное (максимум {Config.EVENT_DESCRIPTION_MAX_LEN} символов)"

        return True, "✅ Описание корректно"

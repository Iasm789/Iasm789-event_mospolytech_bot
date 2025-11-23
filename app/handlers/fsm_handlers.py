"""
Модуль с FSM состояниями и обработчиками для добавления события.
"""

import logging

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from config import Config
from app.core import EventsManager
from app.utils import KeyboardBuilder, Validator

logger = logging.getLogger(__name__)


class AddEvent(StatesGroup):
    """FSM состояния для добавления события."""
    waiting_for_title = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_place = State()
    waiting_for_description = State()
    waiting_for_category = State()


class Search(StatesGroup):
    """FSM состояния для поиска."""
    waiting_for_query = State()


class FSMHandlers:
    """Класс с обработчиками FSM состояний."""

    def __init__(self, events_manager: EventsManager):
        self.events_manager = events_manager

    async def process_title(self, message: Message, state: FSMContext) -> None:
        """Обработчик для ввода названия мероприятия."""
        title = message.text.strip()

        is_valid, error_message = Validator.validate_title(title)
        if not is_valid:
            await message.answer(
                error_message + "\n\n📝 Введите название мероприятия:",
                reply_markup=KeyboardBuilder.cancel_add_kb()
            )
            return

        await state.update_data(title=title)
        await state.set_state(AddEvent.waiting_for_date)
        await message.answer(
            "✅ Название сохранено!\n\n"
            "📅 Теперь введите **дату** мероприятия:\n"
            "**Формат: ДД.ММ.ГГГГ**\n"
            "• Пример: 25.12.2024\n"
            "• Только цифры и точки\n"
            "• Реальная дата (не прошедшая)",
            reply_markup=KeyboardBuilder.cancel_add_kb(),
            parse_mode="Markdown"
        )

    async def process_date(self, message: Message, state: FSMContext) -> None:
        """Обработчик для ввода даты."""
        date_text = message.text.strip()

        is_valid, error_message = Validator.validate_date(date_text)
        if not is_valid:
            await message.answer(
                error_message + "\n\n"
                "📅 Введите дату в формате **ДД.ММ.ГГГГ**:\n"
                "• Пример: 25.12.2024\n"
                "• Только цифры и точки",
                reply_markup=KeyboardBuilder.cancel_add_kb(),
                parse_mode="Markdown"
            )
            return

        await state.update_data(date=date_text)
        await state.set_state(AddEvent.waiting_for_time)
        await message.answer(
            "✅ Дата сохранена!\n\n"
            "🕒 Теперь введите **время** мероприятия:\n"
            "**Формат: ЧЧ:MM**\n"
            "• Пример: 14:30 или 9:05\n"
            "• Часы: 0-23, Минуты: 0-59\n"
            "• Только цифры и двоеточие",
            reply_markup=KeyboardBuilder.cancel_add_kb(),
            parse_mode="Markdown"
        )

    async def process_time(self, message: Message, state: FSMContext) -> None:
        """Обработчик для ввода времени."""
        time_text = message.text.strip()

        is_valid, error_message = Validator.validate_time(time_text)
        if not is_valid:
            await message.answer(
                error_message + "\n\n"
                "🕒 Введите время в формате **ЧЧ:MM**:\n"
                "• Пример: 14:30 или 9:05\n"
                "• Часы: 0-23, Минуты: 0-59",
                reply_markup=KeyboardBuilder.cancel_add_kb(),
                parse_mode="Markdown"
            )
            return

        await state.update_data(time=time_text)
        await state.set_state(AddEvent.waiting_for_place)
        await message.answer(
            "✅ Время сохранено!\n\n"
            "📍 Теперь введите **место проведения**:\n"
            "• Пример: Главный корпус, Ауд. 301\n"
            "• Пример: Онлайн (Zoom)\n"
            "• Пример: Стадион Политеха\n\n"
            "❌ **Нельзя:** только цифры, только спецсимволы",
            reply_markup=KeyboardBuilder.cancel_add_kb(),
            parse_mode="Markdown"
        )

    async def process_place(self, message: Message, state: FSMContext) -> None:
        """Обработчик для ввода места."""
        place = message.text.strip()

        is_valid, error_message = Validator.validate_place(place)
        if not is_valid:
            await message.answer(
                error_message + "\n\n"
                "📍 Введите место проведения:\n"
                "• Пример: Главный корпус, Ауд. 301\n"
                "• Пример: Онлайн (Zoom)\n"
                "• Должно содержать буквы",
                reply_markup=KeyboardBuilder.cancel_add_kb(),
                parse_mode="Markdown"
            )
            return

        await state.update_data(place=place)
        await state.set_state(AddEvent.waiting_for_description)
        await message.answer(
            "✅ Место сохранено!\n\n"
            "📝 Теперь введите **описание** мероприятия:\n"
            "• Расскажите подробнее о мероприятии\n"
            "• Кто организатор?\n"
            "• Для кого предназначено?\n"
            "• Что будет происходить?",
            reply_markup=KeyboardBuilder.cancel_add_kb(),
            parse_mode="Markdown"
        )

    async def process_description(self, message: Message, state: FSMContext) -> None:
        """Обработчик для ввода описания."""
        description = message.text.strip()

        is_valid, error_message = Validator.validate_description(description)
        if not is_valid:
            await message.answer(
                error_message + "\n\n📝 Введите описание мероприятия:",
                reply_markup=KeyboardBuilder.cancel_add_kb()
            )
            return

        await state.update_data(description=description)
        await state.set_state(AddEvent.waiting_for_category)

        data = await state.get_data()
        preview_text = (
            "📋 **Предпросмотр мероприятия:**\n\n"
            f"📌 **Название:** {data['title']}\n"
            f"📅 **Дата:** {data['date']}\n"
            f"🕒 **Время:** {data['time']}\n"
            f"📍 **Место:** {data['place']}\n"
            f"📝 **Описание:** {data['description']}\n\n"
            "✅ Все данные корректны! Теперь выберите категорию:"
        )

        await message.answer(preview_text, reply_markup=KeyboardBuilder.categories_select_kb(), parse_mode="Markdown")

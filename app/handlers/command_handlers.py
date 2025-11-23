"""
Модуль с обработчиками команд (/start, /search, /add, и т.д.)
"""

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import Config
from app.core import EventsManager
from app.utils import KeyboardBuilder, Validator

logger = logging.getLogger(__name__)


class CommandHandlers:
    """Класс с обработчиками команд."""

    def __init__(self, events_manager: EventsManager):
        self.events_manager = events_manager
        self.category_names = Config.CATEGORY_NAMES

    async def cmd_start(self, message: Message) -> None:
        """Команда /start с подробным приветствием и обработкой параметров."""
        args = message.text.split(maxsplit=1)
        
        # Если есть параметр поделиться: share_EVENT_ID_CATEGORY
        if len(args) > 1 and args[1].startswith("share_"):
            share_param = args[1]
            parts = share_param.split("_", 2)
            
            if len(parts) >= 3:
                event_id = parts[1]
                category = parts[2]
                
                event = self.events_manager.get_event_by_id(category, event_id)
                if event:
                    # Показываем событие из ссылки поделиться
                    telegram_url = event.get('telegram_url', '')
                    desc_with_link = event['desc']
                    if telegram_url:
                        desc_with_link += f"\n\n🔗 [Открыть в Telegram]({telegram_url})"
                    
                    text = (
                        f"📌 **{event['title']}**\n\n"
                        f"🕒 **Время:** {event['time']}\n"
                        f"📍 **Место:** {event['place']}\n"
                        f"🏷 **Категория:** {self.category_names.get(category, category)}\n"
                        f"🔑 **ID:** {event['id']}\n\n"
                        f"📝 **Описание:**\n{desc_with_link}"
                    )
                    
                    await message.answer(
                        text,
                        reply_markup=KeyboardBuilder.event_action_kb(event_id, category),
                        parse_mode="Markdown"
                    )
                    return
        
        # Обычное приветствие
        welcome_text = (
            "👋 **Привет! Я Чат-бот Мероприятий Московского Политеха** 🎉\n\n"
            "Я помогу тебе:\n"
            "✅ Узнавать о мероприятиях в твоём любимом университете\n"
            "✅ Находить мероприятия по интересам\n"
            "✅ Анализировать описания событий\n"
            "✅ Добавлять свои мероприятия\n"
            "✅ Получать напоминания о событиях\n\n"
            "**Начнём! Выбери, что тебя интересует:**"
        )
        await message.answer(
            welcome_text,
            reply_markup=KeyboardBuilder.main_menu_with_quick_kb(),
            parse_mode="Markdown"
        )

    async def cmd_analyze(self, message: Message) -> None:
        """Команда /analyze"""
        await message.answer(
            "🔍 Пришлите мне текст, и я проанализирую, является ли он описанием мероприятия.",
            reply_markup=KeyboardBuilder.back_to_analyze_kb()
        )

    async def cmd_add(self, message: Message, state: FSMContext) -> None:
        """Команда /add"""
        from .fsm_handlers import AddEvent
        
        await state.set_state(AddEvent.waiting_for_title)
        await message.answer(
            "📝 Давайте добавим новое мероприятие!\n\n"
            "Введите название мероприятия:",
            reply_markup=KeyboardBuilder.cancel_add_kb()
        )

    async def cmd_search(self, message: Message) -> None:
        """Команда /search"""
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer(
                "🔍 Используйте команду так: /search <ключевое слово>\n\n"
                "Например: /search лекция",
                reply_markup=KeyboardBuilder.main_menu_kb()
            )
            return

        query = args[1]
        results = self.events_manager.search_events(query)

        if not results:
            await message.answer(
                f"❌ По запросу \"{query}\" ничего не найдено",
                reply_markup=KeyboardBuilder.main_menu_kb()
            )
            return

        # Формируем текст результатов с красивым форматом
        text = f"🔍 **Результаты поиска:** \"{query}\"\n"
        text += "=" * 35 + "\n\n"
        count = 0
        events_list = []

        for category, events in results.items():
            text += f"📂 **{self.category_names[category]}** ({len(events)})\n"
            text += "-" * 30 + "\n"
            for idx, event in enumerate(events, 1):
                event_with_category = {**event, 'category': category}
                events_list.append(event_with_category)
                
                telegram_url = event.get('telegram_url', '')
                
                text += f"{idx}. 📌 **{event['title']}**\n"
                text += f"   🕒 {event['time']} | 📍 {event['place']}\n"
                text += f"   🔑 Быстро: `/event{event['id']}`\n"
                
                if telegram_url:
                    text += f"   🔗 [Открыть в Telegram]({telegram_url})\n"
                
                text += "\n"
                count += 1

        text += f"\n**📊 Найдено:** {count} мероприятий"

        await message.answer(
            text, 
            reply_markup=KeyboardBuilder.search_events_list_kb(events_list, page=1, total_pages=1), 
            parse_mode="Markdown"
        )

    async def quick_add_command(self, message: Message) -> None:
        """Команда /добавить для быстрого добавления события"""
        try:
            parts = message.text.split('|')
            if len(parts) < 6:
                await message.answer(
                    "❌ Неправильный формат. Используйте:\n"
                    "`/добавить Название | дата | время | место | описание | категория`\n\n"
                    "**Пример:**\n"
                    "`/добавить Встреча выпускников | 25.12.2024 | 18:00 | Главный корпус | Ежегодная встреча | education`\n\n"
                    "**Форматы:**\n"
                    "• **Дата:** ДД.ММ.ГГГГ (25.12.2024)\n"
                    "• **Время:** ЧЧ:MM (18:00 или 9:00)\n"
                    "• **Категории:** education, careers, competitions, exhibitions, culture, volunteering, student_life",
                    parse_mode="Markdown"
                )
                return

            title = parts[0].replace('/добавить ', '').strip()
            date = parts[1].strip()
            time_str = parts[2].strip()
            place = parts[3].strip()
            description = parts[4].strip()
            category = parts[5].strip().lower()

            # ВАЛИДАЦИЯ ДАННЫХ
            # Проверяем название
            is_valid, error_msg = Validator.validate_title(title)
            if not is_valid:
                await message.answer(f"❌ Ошибка в названии: {error_msg}")
                return

            # Проверяем дату
            is_valid, error_msg = Validator.validate_date(date)
            if not is_valid:
                await message.answer(f"❌ Ошибка в дате: {error_msg}")
                return

            # Проверяем время
            is_valid, error_msg = Validator.validate_time(time_str)
            if not is_valid:
                await message.answer(f"❌ Ошибка во времени: {error_msg}")
                return

            # Проверяем место
            is_valid, error_msg = Validator.validate_place(place)
            if not is_valid:
                await message.answer(f"❌ Ошибка в месте: {error_msg}")
                return

            # Проверяем описание
            is_valid, error_msg = Validator.validate_description(description)
            if not is_valid:
                await message.answer(f"❌ Ошибка в описании: {error_msg}")
                return

            # Проверяем категорию
            if category not in self.category_names:
                await message.answer(
                    f"❌ Неизвестная категория: {category}\n\n"
                    f"Доступные категории: {', '.join(self.category_names.keys())}"
                )
                return

            new_event = self.events_manager.add_event(
                category=category,
                title=title,
                date=date,
                time=time_str,
                place=place,
                desc=description
            )

            # СОХРАНЯЕМ В ФАЙЛ
            await self.events_manager.save_events_to_file()

            success_text = (
                "✅ **Мероприятие успешно добавлено!**\n\n"
                f"📌 **{new_event['title']}**\n"
                f"🕒 **{new_event['time']}**\n"
                f"📍 **{new_event['place']}**\n"
                f"📝 **{new_event['desc']}**\n"
                f"🏷 **Категория:** {self.category_names[category]}"
            )

            await message.answer(success_text, reply_markup=KeyboardBuilder.main_menu_kb(), parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Ошибка при быстром добавлении события: {e}")
            await message.answer(
                "❌ Ошибка при добавлении. Проверьте формат команды.\n\n"
                "Правильный формат:\n"
                "`/добавить Название | дата | время | место | описание | категория`\n\n"
                "**Форматы:**\n"
                "• Дата: ДД.ММ.ГГГГ\n"
                "• Время: ЧЧ:MM",
                parse_mode="Markdown"
            )

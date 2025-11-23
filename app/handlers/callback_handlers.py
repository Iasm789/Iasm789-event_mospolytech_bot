"""
Модуль с обработчиками callback запросов от кнопок.
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import Config
from app.core import EventsManager
from app.utils import KeyboardBuilder

logger = logging.getLogger(__name__)


class CallbackHandlers:
    """Класс с обработчиками callback'ов от inline кнопок."""

    def __init__(self, events_manager, favorites_manager=None):
        self.events_manager = events_manager
        self.favorites_manager = favorites_manager
        self.category_names = Config.CATEGORY_NAMES

    async def handle_analyze_text(self, callback: CallbackQuery) -> None:
        """Запрос анализа текста."""
        await callback.message.edit_text(
            "🔍 Пришлите мне текст, и я проанализирую, является ли он описанием мероприятия.\n\n"
            "Пример текста для анализа:\n"
            "\"Завтра в 18:00 в главном корпусе состоится встреча студенческого совета, "
            "где мы обсудим подготовку к предстоящему фестивалю.\"",
            reply_markup=KeyboardBuilder.back_to_analyze_kb()
        )

    async def handle_add_event(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Начать добавление события."""
        from .fsm_handlers import AddEvent
        
        await state.set_state(AddEvent.waiting_for_title)
        await callback.message.edit_text(
            "📝 Давайте добавим новое мероприятие!\n\n"
            "Введите название мероприятия:",
            reply_markup=KeyboardBuilder.cancel_add_kb()
        )

    async def handle_start_add_from_text(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Начать добавление события из проанализированного текста."""
        from .fsm_handlers import AddEvent
        
        await state.set_state(AddEvent.waiting_for_title)
        await callback.message.edit_text(
            "📝 Отлично! Давайте оформим мероприятие.\n\n"
            "Введите название мероприятия:",
            reply_markup=KeyboardBuilder.cancel_add_kb()
        )

    async def handle_add_category(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Обработка выбора категории при добавлении события."""
        category = callback.data.replace("addcat_", "")
        data = await state.get_data()

        new_event = self.events_manager.add_event(
            category=category,
            title=data['title'],
            date=data['date'],
            time=data['time'],
            place=data['place'],
            desc=data['description']
        )

        # Сохраняем в файл
        await self.events_manager.save_events_to_file()

        success_text = (
            "🎉 **Мероприятие успешно добавлено!**\n\n"
            f"📌 **{new_event['title']}**\n"
            f"🕒 **{new_event['time']}**\n"
            f"📍 **{new_event['place']}**\n"
            f"📝 **{new_event['desc']}**\n"
            f"🏷 **Категория:** {self.category_names[category]}"
        )

        await callback.message.edit_text(success_text, reply_markup=KeyboardBuilder.main_menu_kb(), parse_mode="Markdown")
        await state.clear()

    async def handle_cancel_add(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Отмена добавления события."""
        await state.clear()
        await callback.message.edit_text(
            "❌ Добавление мероприятия отменено.",
            reply_markup=KeyboardBuilder.main_menu_kb()
        )

    async def handle_main_menu(self, callback: CallbackQuery) -> None:
        """Показать главное меню с приветствием."""
        menu_text = (
            "🏠 **Главное меню**\n\n"
            "Выберите действие:\n"
            "• 📅 Просмотрите все мероприятия\n"
            "• 📂 Выберите по категориям\n"
            "• 🔍 Найдите нужное событие\n"
            "• ➕ Добавьте свое мероприятие\n"
            "• ⭐ Управляйте напоминаниями"
        )
        await callback.message.edit_text(
            menu_text,
            reply_markup=KeyboardBuilder.main_menu_with_quick_kb(),
            parse_mode="Markdown"
        )
        await callback.answer("Вы вернулись в главное меню", show_alert=False)

    async def handle_all_events(self, callback: CallbackQuery) -> None:
        """Показать все события с пагинацией и быстрым доступом."""
        events, total_pages, total_count = self.events_manager.get_all_events_paginated(1, 5)

        if not events:
            await callback.answer("ℹ️ Мероприятий не найдено", show_alert=False)
            await callback.message.edit_text(
                "❌ Пока что мероприятий нет.\n\n"
                "Вы можете:\n"
                "• 📂 Посмотреть по категориям\n"
                "• ➕ Добавить новое мероприятие",
                reply_markup=KeyboardBuilder.main_menu_kb()
            )
            return

        text = f"📅 Все мероприятия (Всего: {total_count})\n"
        text += f"Страница 1 из {total_pages}\n\n"
        
        for idx, event in enumerate(events, 1):
            category = event.get('category', 'unknown')
            event_id = event.get('id', '')
            text += f"{idx}. 📌 {event['title']}\n"
            text += f"   🕒 {event['time']} | 📍 {event['place']}\n"
            text += f"   🔗 `/event{event_id}` — быстрый доступ\n\n"

        await callback.message.edit_text(
            text,
            reply_markup=KeyboardBuilder.all_events_kb(1, total_pages)
        )

    async def handle_paginate_all_events(self, callback: CallbackQuery) -> None:
        """Пагинация для всех событий с улучшенным форматом."""
        page = int(callback.data.split("_")[-1])
        events, total_pages, total_count = self.events_manager.get_all_events_paginated(page, 5)

        if not events:
            await callback.answer("Нет больше событий", show_alert=False)
            return

        text = f"📅 Все мероприятия (Всего: {total_count})\n"
        text += f"Страница {page} из {total_pages}\n\n"
        
        for idx, event in enumerate(events, 1):
            category = event.get('category', 'unknown')
            event_id = event.get('id', '')
            text += f"{idx}. 📌 {event['title']}\n"
            text += f"   🕒 {event['time']} | 📍 {event['place']}\n"
            text += f"   🔗 `/event{event_id}` — быстрый доступ\n\n"

        await callback.message.edit_text(
            text,
            reply_markup=KeyboardBuilder.all_events_kb(page, total_pages)
        )
        
        # Уведомление о навигации
        await callback.answer(f"Страница {page} из {total_pages}", show_alert=False)

    async def handle_search_again(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Начать новый поиск."""
        from .fsm_handlers import Search
        
        await state.set_state(Search.waiting_for_query)
        await callback.message.edit_text(
            "🔍 **Новый поиск**\n\n"
            "Введите ключевое слово для поиска:",
            reply_markup=KeyboardBuilder.cancel_search_kb(),
            parse_mode="Markdown"
        )

    async def handle_search_start(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Начать поиск с подсказками."""
        from .fsm_handlers import Search
        
        await state.set_state(Search.waiting_for_query)
        
        help_text = (
            "🔍 **Поиск мероприятий**\n\n"
            "Введите ключевое слово для поиска:\n"
            "• лекция\n"
            "• концерт\n"
            "• конкурс\n"
            "• встреча\n"
            "• фестиваль\n"
            "• и другие темы...\n\n"
            "Я найду все мероприятия, совпадающие по названию или описанию"
        )
        
        await callback.message.edit_text(
            help_text,
            reply_markup=KeyboardBuilder.cancel_search_kb(),
            parse_mode="Markdown"
        )
        await callback.answer("Введите поисковый запрос", show_alert=False)

    async def handle_categories(self, callback: CallbackQuery) -> None:
        """Показать категории мероприятий."""
        await callback.message.edit_text("📂 Категории мероприятий:", reply_markup=KeyboardBuilder.categories_kb())

    async def handle_show_events(self, callback: CallbackQuery) -> None:
        """Показать события определённой категории с улучшенным форматом."""
        category = callback.data.replace("cat_", "")
        events = self.events_manager.get_events_by_category(category)

        if not events:
            await callback.answer(f"В этой категории нет событий", show_alert=False)
            
            # Создаём кнопки для пустой категории
            buttons = [
                [InlineKeyboardButton(text="➕ Добавить мероприятие", callback_data="add_event")],
                [InlineKeyboardButton(text="🔍 Поискать в других категориях", callback_data="categories")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ]
            
            await callback.message.edit_text(
                f"❌ В категории **{self.category_names[category]}** пока нет мероприятий.\n\n"
                "Вы можете:\n"
                "• ➕ Добавить новое мероприятие\n"
                "• 🔍 Поискать в других категориях",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                parse_mode="Markdown"
            )
            return

        text = f"📂 {self.category_names[category]}\n"
        text += f"Всего: {len(events)} мероприятий\n\n"
        
        for idx, e in enumerate(events, 1):
            text += f"{idx}. 📌 {e['title']}\n"
            text += f"   🕒 {e['time']} | 📍 {e['place']}\n"
            text += f"   🔗 `/event{e['id']}` — быстрый доступ\n\n"

        # Создаём кнопки с мероприятиями
        buttons = []
        for e in events:
            buttons.append([InlineKeyboardButton(
                text=f"📌 {e['title'][:35]}",
                callback_data=f"event_{category}_{e['id']}"
            )])
        buttons.append([InlineKeyboardButton(text="⬅️ Категории", callback_data="categories")])
        buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])

        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="Markdown"
        )

    async def handle_show_event_detail(self, callback: CallbackQuery) -> None:
        """Показать детали события с улучшенным форматом."""
        parts = callback.data.split("_")
        event_id = parts[-1]
        category = "_".join(parts[1:-1])
        event = self.events_manager.get_event_by_id(category, event_id)

        if not event:
            await callback.answer("Событие не найдено ❌", show_alert=True)
            return

        # Формируем описание с ссылкой на оригинальное сообщение
        telegram_url = event.get('telegram_url', '')
        desc_with_link = event['desc']
        if telegram_url:
            desc_with_link += f"\n\n🔗 [Открыть в Telegram]({telegram_url})"
        
        text = (
            f"📌 **{event['title']}**\n\n"
            f"🕒 **Время:** {event['time']}\n"
            f"📍 **Место:** {event['place']}\n"
            f"🏷 **Категория:** {self.category_names[category]}\n"
            f"🔑 **ID:** {event['id']}\n\n"
            f"📝 **Описание:**\n{desc_with_link}"
        )

        await callback.message.edit_text(
            text,
            reply_markup=KeyboardBuilder.event_action_kb(event_id, category),
            parse_mode="Markdown"
        )
        
        await callback.answer("✅ Информация загружена", show_alert=False)

    async def handle_help(self, callback: CallbackQuery) -> None:
        """Показать справку по боту с подробной информацией."""
        help_text = (
            "ℹ️ **Справка по боту**\n\n"
            "**🎯 Основные функции:**\n"
            "1️⃣ **Просмотр мероприятий**\n"
            "   📅 Все события | 📂 По категориям\n\n"
            "2️⃣ **Поиск**\n"
            "   🔍 По ключевым словам | 🤖 Анализ текста\n\n"
            "3️⃣ **Добавление**\n"
            "   ➕ Добавить событие | 📝 Быстрое добавление\n\n"
            "4️⃣ **Управление**\n"
            "   ⭐ Избранное | 🔔 Напоминания\n\n"
            "**📂 Категории:**\n"
            "• 🎓 Образование\n"
            "• 💼 Карьера\n"
            "• 🏆 Соревнования\n"
            "• 🎨 Выставки\n"
            "• 🎭 Культура\n"
            "• 🤝 Волонтёрство и социальные\n"
            "• 👥 Студенческая жизнь\n\n"
            "**⚡ Быстрые команды:**\n"
            "`/search текст` - поиск\n"
            "`/analyze` - анализ текста\n"
            "`/add` - добавить мероприятие\n"
            "/dobavit' - быстрое добавление\n\n"
            "**💡 Советы:**\n"
            "• Кликайте на названия для полной информации\n"
            "• Используйте поиск для быстрого поиска\n"
            "• Добавляйте события в избранное ⭐\n"
            "• Устанавливайте напоминания 🔔"
        )
        await callback.message.edit_text(
            help_text,
            reply_markup=KeyboardBuilder.back_to_main_kb(),
            parse_mode="Markdown"
        )
        await callback.answer("Справка загружена", show_alert=False)

    async def handle_similar_events(self, callback: CallbackQuery) -> None:
        """Показать похожие события по категории."""
        parts = callback.data.split("_")
        event_id = parts[-1]
        category = "_".join(parts[1:-1])
        
        event = self.events_manager.get_event_by_id(category, event_id)
        if not event:
            await callback.answer("Событие не найдено ❌", show_alert=True)
            return
        
        # Получаем все события в этой категории и фильтруем текущее
        similar_events = [
            e for e in self.events_manager.get_events_by_category(category)
            if e['id'] != event_id
        ]
        
        if not similar_events:
            await callback.answer("❌ Похожих событий не найдено", show_alert=True)
            return
        
        text = f"🔗 **Похожие события в категории {self.category_names[category]}:**\n\n"
        text += "-" * 35 + "\n\n"
        
        for idx, e in enumerate(similar_events[:5], 1):
            text += f"{idx}. 📌 **{e['title']}**\n"
            text += f"   🕒 {e['time']} | 📍 {e['place']}\n"
            text += f"   🔑 `/event{e['id']}`\n\n"
        
        text += f"_и ещё {len(similar_events) - 5} событий..._" if len(similar_events) > 5 else ""
        
        # Кнопки для похожих событий
        buttons = []
        for e in similar_events[:5]:
            buttons.append([InlineKeyboardButton(
                text=f"📌 {e['title'][:30]}",
                callback_data=f"event_{category}_{e['id']}"
            )])
        buttons.extend([
            [InlineKeyboardButton(text="⬅️ Назад к событию", callback_data=f"event_{category}_{event_id}")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="Markdown"
        )
        await callback.answer("Похожие события загружены", show_alert=False)

    async def handle_add_to_favorites(self, callback: CallbackQuery) -> None:
        """Добавить событие в избранное."""
        if not self.favorites_manager:
            await callback.answer("❌ Функция избранного недоступна", show_alert=True)
            return

        # Извлекаем event_id из callback_data (формат: fav_event_id)
        event_id = callback.data.replace("fav_", "").split("_")[0]
        user_id = callback.from_user.id

        # Находим событие
        event, category = self.events_manager.get_event_by_id_only(event_id)

        if not event:
            await callback.answer("❌ Событие не найдено", show_alert=True)
            return

        # Переключаем избранное
        is_added = self.favorites_manager.toggle_favorite(
            user_id, event_id, category, event
        )

        if is_added:
            await callback.answer(
                f"⭐ Событие добавлено в избранное!",
                show_alert=False
            )
        else:
            await callback.answer(
                f"✅ Событие удалено из избранного",
                show_alert=False
            )

    async def handle_show_favorites(self, callback: CallbackQuery) -> None:
        """Показать избранные события."""
        if not self.favorites_manager:
            await callback.answer("❌ Функция избранного недоступна", show_alert=True)
            return

        user_id = callback.from_user.id
        favorites = self.favorites_manager.get_favorites(user_id)

        if not favorites:
            await callback.message.edit_text(
                "⭐ **Ваше избранное пусто**\n\n"
                "Добавьте события, которые вам нравятся:\n"
                "• Откройте событие\n"
                "• Нажмите кнопку ⭐ Избранное\n\n"
                "Все события будут сохранены в этом разделе на время сессии.",
                reply_markup=KeyboardBuilder.back_to_main_kb(),
                parse_mode="Markdown"
            )
            return

        # Формируем текст с избранными событиями
        text = f"⭐ **Ваше избранное** ({len(favorites)} событий)\n"
        text += "=" * 35 + "\n\n"

        buttons = []
        count = 0

        # Группируем по категориям
        favorites_by_category = {}
        for event_id, category, event_data in favorites:
            if category not in favorites_by_category:
                favorites_by_category[category] = []
            favorites_by_category[category].append((event_id, event_data))

        # Вывод по категориям
        for category, events in favorites_by_category.items():
            text += f"📂 **{self.category_names.get(category, category)}** ({len(events)})\n"
            text += "-" * 30 + "\n"

            for event_id, event_data in events:
                count += 1
                text += f"{count}. 📌 **{event_data['title']}**\n"
                text += f"   🕒 {event_data['time']} | 📍 {event_data['place']}\n"
                text += f"   🔑 `/event{event_id}`\n\n"

                buttons.append([InlineKeyboardButton(
                    text=f"📌 {event_data['title'][:35]}",
                    callback_data=f"event_{category}_{event_id}"
                )])

        # Кнопки навигации
        buttons.extend([
            [InlineKeyboardButton(text="🗑️ Очистить избранное", callback_data="clear_favorites")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])

        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="Markdown"
        )
        await callback.answer(f"Показано {len(favorites)} избранных событий", show_alert=False)

    async def handle_clear_favorites(self, callback: CallbackQuery) -> None:
        """Очистить избранное."""
        if not self.favorites_manager:
            await callback.answer("❌ Функция избранного недоступна", show_alert=True)
            return

        user_id = callback.from_user.id
        count = self.favorites_manager.get_favorites_count(user_id)

        if count == 0:
            await callback.answer("ℹ️ Избранное уже пусто", show_alert=True)
            return

        # Подтверждение очистки
        buttons = [
            [InlineKeyboardButton(text="✅ Да, очистить", callback_data="confirm_clear_favorites"),
             InlineKeyboardButton(text="❌ Отмена", callback_data="favorites")],
        ]

        await callback.message.edit_text(
            f"❓ Вы уверены?\n\n"
            f"Это удалит все {count} избранных событий.\n"
            f"_(Действие необратимо на время этой сессии)_",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="Markdown"
        )

    async def handle_confirm_clear_favorites(self, callback: CallbackQuery) -> None:
        """Подтвердить очистку избранного."""
        if not self.favorites_manager:
            await callback.answer("❌ Функция избранного недоступна", show_alert=True)
            return

        user_id = callback.from_user.id
        self.favorites_manager.clear_favorites(user_id)

        await callback.message.edit_text(
            "✅ **Избранное очищено**\n\n"
            "Все события удалены из избранного.",
            reply_markup=KeyboardBuilder.back_to_main_kb(),
            parse_mode="Markdown"
        )

    async def handle_share(self, callback: CallbackQuery) -> None:
        """Поделиться событием (Вариант 3: Ссылка на бота)."""
        # Извлекаем event_id из callback_data (формат: share_event_id)
        event_id = callback.data.replace("share_", "").strip()
        
        # Находим событие
        event, category = self.events_manager.get_event_by_id_only(event_id)
        
        if not event:
            await callback.answer("❌ Событие не найдено", show_alert=True)
            logger.warning(f"Event not found for share: event_id={event_id}")
            return
        
        # Генерируем ссылку на бота с параметром
        try:
            bot_info = await callback.bot.get_me()
            bot_username = bot_info.username
            share_link = f"https://t.me/{bot_username}?start=share_{event_id}_{category}"
        except Exception as e:
            logger.error(f"Ошибка при получении информации о боте: {e}")
            share_link = ""
        
        if not share_link:
            await callback.answer("❌ Ошибка при генерации ссылки", show_alert=True)
            return
        
        # Формируем сообщение со ссылкой
        share_text = (
            f"🔗 **Ссылка на событие:**\n\n"
            f"`{share_link}`\n\n"
            f"**Как использовать:**\n"
            f"1️⃣ Скопируйте ссылку выше\n"
            f"2️⃣ Отправьте другу в чат/группу\n"
            f"3️⃣ Друг нажимает на ссылку\n"
            f"4️⃣ Открывается событие в боте\n\n"
            f"📌 **{event['title']}**\n"
            f"🕒 {event['time']} | 📍 {event['place']}"
        )
        
        await callback.message.answer(
            share_text,
            reply_markup=KeyboardBuilder.back_to_main_kb(),
            parse_mode="Markdown"
        )
        
        await callback.answer("✅ Ссылка готова к отправке!", show_alert=False)
        await callback.answer("Избранное очищено", show_alert=False)


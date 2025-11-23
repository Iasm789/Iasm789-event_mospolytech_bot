"""
Модуль для создания inline клавиатур и UI элементов.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import Config


class KeyboardBuilder:
    """Класс для построения различных клавиатур."""

    @staticmethod
    def main_menu_kb() -> InlineKeyboardMarkup:
        """Главное меню."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📅 Все мероприятия", callback_data="all_events")],
            [InlineKeyboardButton(text="📂 По категориям", callback_data="categories")],
            [InlineKeyboardButton(text="🔍 Поиск", callback_data="search_start")],
            [InlineKeyboardButton(text="🔍 Анализ текста", callback_data="analyze_text")],
            [InlineKeyboardButton(text="➕ Добавить мероприятие", callback_data="add_event")],
            [InlineKeyboardButton(text="⭐ Мои напоминания", callback_data="reminders")],
            [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")]
        ])

    @staticmethod
    def categories_kb() -> InlineKeyboardMarkup:
        """Меню категорий для просмотра."""
        category_names = Config.CATEGORY_NAMES
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=category_names["education"], callback_data="cat_education")],
            [InlineKeyboardButton(text=category_names["careers"], callback_data="cat_careers"),
             InlineKeyboardButton(text=category_names["competitions"], callback_data="cat_competitions")],
            [InlineKeyboardButton(text=category_names["exhibitions"], callback_data="cat_exhibitions")],
            [InlineKeyboardButton(text=category_names["culture"], callback_data="cat_culture")],
            [InlineKeyboardButton(text=category_names["volunteering"], callback_data="cat_volunteering")],
            [InlineKeyboardButton(text=category_names["student_life"], callback_data="cat_student_life")],
            [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")]
        ])

    @staticmethod
    def categories_select_kb() -> InlineKeyboardMarkup:
        """Меню категорий для добавления события."""
        category_names = Config.CATEGORY_NAMES
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=category_names["education"], callback_data="addcat_education")],
            [InlineKeyboardButton(text=category_names["careers"], callback_data="addcat_careers"),
             InlineKeyboardButton(text=category_names["competitions"], callback_data="addcat_competitions")],
            [InlineKeyboardButton(text=category_names["exhibitions"], callback_data="addcat_exhibitions")],
            [InlineKeyboardButton(text=category_names["culture"], callback_data="addcat_culture")],
            [InlineKeyboardButton(text=category_names["volunteering"], callback_data="addcat_volunteering")],
            [InlineKeyboardButton(text=category_names["student_life"], callback_data="addcat_student_life")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_add")]
        ])

    @staticmethod
    def events_kb(events: list, category: str) -> InlineKeyboardMarkup:
        """Список событий."""
        buttons = []
        for e in events:
            buttons.append([InlineKeyboardButton(
                text=e["title"],
                callback_data=f"event_{category}_{e['id']}"
            )])
        buttons.append([InlineKeyboardButton(text="⬅️ Категории", callback_data="categories")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def event_detail_kb(category: str) -> InlineKeyboardMarkup:
        """Детали события."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data=f"cat_{category}")],
            [InlineKeyboardButton(text="📂 Категории", callback_data="categories")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])

    @staticmethod
    def back_to_main_kb() -> InlineKeyboardMarkup:
        """Кнопка возврата в главное меню."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])

    @staticmethod
    def cancel_add_kb() -> InlineKeyboardMarkup:
        """Кнопка отмены добавления."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_add")]
        ])

    @staticmethod
    def back_to_analyze_kb() -> InlineKeyboardMarkup:
        """Кнопки для возврата из анализа текста."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Анализ другого текста", callback_data="analyze_text")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])

    @staticmethod
    def search_kb(query: str, page: int = 1) -> InlineKeyboardMarkup:
        """Клавиатура для результатов поиска."""
        buttons = [
            [InlineKeyboardButton(text="🔍 Новый поиск", callback_data="search_again")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def all_events_kb(page: int = 1, total_pages: int = 1, show_events_buttons: bool = False, events: list = None) -> InlineKeyboardMarkup:
        """Клавиатура для просмотра всех событий с пагинацией и быстрым доступом."""
        buttons = []

        # Кнопки для быстрого доступа к событиям (если переданы)
        if show_events_buttons and events:
            for event in events:
                category = event.get('category', '')
                event_id = event.get('id', '')
                buttons.append([InlineKeyboardButton(
                    text=f"📌 {event['title'][:30]}...",
                    callback_data=f"event_{category}_{event_id}"
                )])

        # Кнопки пагинации
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"all_events_page_{page - 1}"))
        
        nav_buttons.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="noop"))
        
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"all_events_page_{page + 1}"))

        if nav_buttons:
            buttons.append(nav_buttons)

        buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def add_from_text_kb() -> InlineKeyboardMarkup:
        """Клавиатура для добавления события из проанализированного текста."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить это мероприятие", callback_data="start_add_from_text")],
            [InlineKeyboardButton(text="🔍 Анализ другого текста", callback_data="analyze_text")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])

    @staticmethod
    def retry_analysis_kb() -> InlineKeyboardMarkup:
        """Клавиатура для повторного анализа текста."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Попробовать другой текст", callback_data="analyze_text")],
            [InlineKeyboardButton(text="➕ Добавить мероприятие вручную", callback_data="add_event")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])

    @staticmethod
    def cancel_search_kb() -> InlineKeyboardMarkup:
        """Кнопка отмены поиска."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")]
        ])

    @staticmethod
    def quick_access_kb() -> InlineKeyboardMarkup:
        """Быстрый доступ к популярным функциям."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Ближайшие события", callback_data="upcoming_events")],
            [InlineKeyboardButton(text="🔥 Популярные события", callback_data="popular_events")],
            [InlineKeyboardButton(text="🆕 Недавно добавленные", callback_data="recent_events")]
        ])

    @staticmethod
    def main_menu_with_quick_kb() -> InlineKeyboardMarkup:
        """Главное меню с быстрым доступом."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📅 Все мероприятия", callback_data="all_events")],
            [InlineKeyboardButton(text="📂 По категориям", callback_data="categories")],
            [InlineKeyboardButton(text="🔍 Поиск", callback_data="search_start")],
            [InlineKeyboardButton(text="🔍 Анализ текста", callback_data="analyze_text")],
            [InlineKeyboardButton(text="➕ Добавить", callback_data="add_event"), 
             InlineKeyboardButton(text="📌 Избранное", callback_data="favorites")],
            [InlineKeyboardButton(text="⭐ Напоминания", callback_data="reminders")],
            [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")]
        ])

    @staticmethod
    def event_action_kb(event_id: str, category: str) -> InlineKeyboardMarkup:
        """Действия с конкретным событием."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Избранное", callback_data=f"fav_{event_id}"),
             InlineKeyboardButton(text="🔔 Напоминание", callback_data=f"remind_{event_id}")],
            [InlineKeyboardButton(text="📤 Поделиться", callback_data=f"share_{event_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"cat_{category}")],
            [InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")]
        ])

    @staticmethod
    def search_results_kb(query: str, found_count: int) -> InlineKeyboardMarkup:
        """Клавиатура для результатов поиска с инфо."""
        buttons = []
        if found_count > 0:
            buttons.append([InlineKeyboardButton(text=f"📊 Найдено: {found_count}", callback_data="noop")])
        buttons.extend([
            [InlineKeyboardButton(text="🔍 Новый поиск", callback_data="search_again")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def search_event_detail_kb(event_id: str, category: str, query: str) -> InlineKeyboardMarkup:
        """Клавиатура для детального просмотра события из поиска."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Избранное", callback_data=f"fav_{event_id}"),
             InlineKeyboardButton(text="🔔 Напоминание", callback_data=f"remind_{event_id}")],
            [InlineKeyboardButton(text="📤 Поделиться", callback_data=f"share_{event_id}")],
            [InlineKeyboardButton(text="🔍 Похожие события", callback_data=f"similar_{category}_{event_id}")],
            [InlineKeyboardButton(text="⬅️ К результатам", callback_data=f"search_results_{query}")],
            [InlineKeyboardButton(text="🔍 Новый поиск", callback_data="search_again")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])

    @staticmethod
    def search_events_list_kb(events_data: list, page: int = 1, total_pages: int = 1) -> InlineKeyboardMarkup:
        """Клавиатура для списка событий в результатах поиска с быстрым доступом."""
        buttons = []
        
        # Кнопки для каждого события
        for event in events_data:
            event_id = event.get('id', '')
            title = event.get('title', '')[:35]
            buttons.append([InlineKeyboardButton(
                text=f"📌 {title}",
                callback_data=f"event_{event.get('category', '')}_{event_id}"
            )])
        
        # Пагинация если нужна
        if total_pages > 1:
            nav_buttons = []
            if page > 1:
                nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"search_page_{page - 1}"))
            nav_buttons.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="noop"))
            if page < total_pages:
                nav_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"search_page_{page + 1}"))
            buttons.append(nav_buttons)
        
        # Кнопки действия
        buttons.extend([
            [InlineKeyboardButton(text="🔍 Новый поиск", callback_data="search_again")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def share_buttons_kb() -> InlineKeyboardMarkup:
        """Кнопки для поделиться событием."""
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
            [InlineKeyboardButton(text="🔍 Поиск", callback_data="search_start")]
        ])


"""Entry point приложения."""

import asyncio
import logging

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import Config
from event_classifier import EventClassifier
from app.core import EventsManager
from app.utils import KeyboardBuilder, FavoritesManager
from app.handlers import (
    AddEvent, Search, FSMHandlers,
    CommandHandlers, CallbackHandlers
)

load_dotenv()

# --- ИНИЦИАЛИЗАЦИЯ ЛОГИРОВАНИЯ ---
logging.basicConfig(
    level=Config.LOG_LEVEL,
    format=Config.LOG_FORMAT,
    datefmt=Config.LOG_DATE_FORMAT
)
logger = logging.getLogger(__name__)

# --- ИНИЦИАЛИЗАЦИЯ КОМПОНЕНТОВ ---
events_manager = EventsManager()
classifier = EventClassifier()
favorites_manager = FavoritesManager()
fsm_handlers = FSMHandlers(events_manager)
command_handlers = CommandHandlers(events_manager)
callback_handlers = CallbackHandlers(events_manager, favorites_manager)

# Бот и диспетчер
bot = Bot(token=Config.BOT_TOKEN)
dp = Dispatcher()


# --- КОМАНДЫ ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await command_handlers.cmd_start(message)


@dp.message(Command("analyze"))
async def cmd_analyze(message: Message):
    await command_handlers.cmd_analyze(message)


@dp.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext):
    await command_handlers.cmd_add(message, state)


@dp.message(Command("search"))
async def cmd_search(message: Message):
    await command_handlers.cmd_search(message)


@dp.message(Command("добавить"))
async def quick_add_command(message: Message):
    """
    Быстрое добавление мероприятия в формате:
    /добавить Название | дата | время | место | описание | категория
    """
    await command_handlers.quick_add_command(message)


@dp.message(F.text & F.text.startswith("/event"))
async def cmd_event_by_id(message: Message):
    """
    Быстрый доступ к событию по ID: /event1, /event2 и т.д.
    """
    # Извлекаем ID из команды (/event1, /event2 и т.д.)
    command_text = message.text.split("@")[0]  # Убираем упоминание бота если есть
    event_id = command_text.replace("/event", "").strip()
    
    if not event_id.isdigit():
        await message.answer(
            "❌ Неправильный формат команды.\n\n"
            "Используйте:\n"
            "/event1 - первое событие\n"
            "/event2 - второе событие\n"
            "и т.д.",
            reply_markup=KeyboardBuilder.main_menu_kb()
        )
        return
    
    event, category = events_manager.get_event_by_id_only(event_id)
    
    if not event:
        await message.answer(
            f"❌ Событие с ID {event_id} не найдено.\n\n"
            "Проверьте ID и попробуйте снова.",
            reply_markup=KeyboardBuilder.main_menu_kb()
        )
        return
    
    # Формируем описание с ссылкой на оригинальное сообщение
    telegram_url = event.get('telegram_url', '')
    desc_with_link = event['desc']
    if telegram_url:
        desc_with_link += f"\n\n🔗 [Открыть в Telegram]({telegram_url})"
    
    # Показываем детали события
    text = (
        f"📌 **{event['title']}**\n\n"
        f"🕒 **Время:** {event['time']}\n"
        f"📍 **Место:** {event['place']}\n"
        f"🏷 **Категория:** {Config.CATEGORY_NAMES.get(category, category)}\n"
        f"🔑 **ID:** {event['id']}\n\n"
        f"📝 **Описание:**\n{desc_with_link}"
    )
    
    await message.answer(
        text,
        reply_markup=KeyboardBuilder.event_action_kb(event_id, category),
        parse_mode="Markdown"
    )


# --- CALLBACK ОБРАБОТЧИКИ ---
@dp.callback_query(F.data == "analyze_text")
async def ask_for_text_analysis(callback: CallbackQuery):
    await callback_handlers.handle_analyze_text(callback)


@dp.callback_query(F.data == "add_event")
async def start_add_event(callback: CallbackQuery, state: FSMContext):
    await callback_handlers.handle_add_event(callback, state)


@dp.callback_query(F.data == "start_add_from_text")
async def start_add_from_text(callback: CallbackQuery, state: FSMContext):
    await callback_handlers.handle_start_add_from_text(callback, state)


@dp.callback_query(F.data.startswith("addcat_"))
async def process_category(callback: CallbackQuery, state: FSMContext):
    await callback_handlers.handle_add_category(callback, state)


@dp.callback_query(F.data == "cancel_add")
async def cancel_add(callback: CallbackQuery, state: FSMContext):
    await callback_handlers.handle_cancel_add(callback, state)


@dp.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery):
    await callback_handlers.handle_main_menu(callback)


@dp.callback_query(F.data == "all_events")
async def show_all_events(callback: CallbackQuery):
    await callback_handlers.handle_all_events(callback)


@dp.callback_query(F.data.startswith("all_events_page_"))
async def paginate_all_events(callback: CallbackQuery):
    await callback_handlers.handle_paginate_all_events(callback)


@dp.callback_query(F.data == "search_again")
async def search_again(callback: CallbackQuery, state: FSMContext):
    await callback_handlers.handle_search_again(callback, state)


@dp.callback_query(F.data == "search_start")
async def search_start(callback: CallbackQuery, state: FSMContext):
    await callback_handlers.handle_search_start(callback, state)


@dp.callback_query(F.data == "categories")
async def show_categories(callback: CallbackQuery):
    await callback_handlers.handle_categories(callback)


@dp.callback_query(F.data.startswith("cat_"))
async def show_events(callback: CallbackQuery):
    await callback_handlers.handle_show_events(callback)


@dp.callback_query(F.data.startswith("event_"))
async def show_event_detail(callback: CallbackQuery):
    await callback_handlers.handle_show_event_detail(callback)


@dp.callback_query(F.data.startswith("similar_"))
async def show_similar_events(callback: CallbackQuery):
    await callback_handlers.handle_similar_events(callback)


@dp.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    await callback_handlers.handle_help(callback)


@dp.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    """Обработчик для кнопок без действия (информационные)."""
    await callback.answer()


@dp.callback_query(F.data == "favorites")
async def show_favorites(callback: CallbackQuery):
    """Показать избранные события."""
    await callback_handlers.handle_show_favorites(callback)


@dp.callback_query(F.data == "reminders")
async def show_reminders(callback: CallbackQuery):
    """Показать напоминания (заглушка)."""
    await callback.answer("🔔 Функция напоминаний скоро будет доступна!", show_alert=True)


@dp.callback_query(F.data.startswith("fav_"))
async def add_to_favorites(callback: CallbackQuery):
    """Добавить в избранное."""
    await callback_handlers.handle_add_to_favorites(callback)


@dp.callback_query(F.data == "clear_favorites")
async def clear_favorites(callback: CallbackQuery):
    """Очистить избранное с подтверждением."""
    await callback_handlers.handle_clear_favorites(callback)


@dp.callback_query(F.data == "confirm_clear_favorites")
async def confirm_clear_favorites(callback: CallbackQuery):
    """Подтвердить очистку избранного."""
    await callback_handlers.handle_confirm_clear_favorites(callback)


@dp.callback_query(F.data.startswith("remind_"))
async def set_reminder(callback: CallbackQuery):
    """Установить напоминание (заглушка)."""
    await callback.answer("🔔 Напоминание установлено!", show_alert=False)


@dp.callback_query(F.data.startswith("share_"))
async def share_event(callback: CallbackQuery):
    """Поделиться событием."""
    await callback_handlers.handle_share(callback)


# --- FSM ОБРАБОТЧИКИ ---
@dp.message(AddEvent.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    await fsm_handlers.process_title(message, state)


@dp.message(AddEvent.waiting_for_date)
async def process_date(message: Message, state: FSMContext):
    await fsm_handlers.process_date(message, state)


@dp.message(AddEvent.waiting_for_time)
async def process_time(message: Message, state: FSMContext):
    await fsm_handlers.process_time(message, state)


@dp.message(AddEvent.waiting_for_place)
async def process_place(message: Message, state: FSMContext):
    await fsm_handlers.process_place(message, state)


@dp.message(AddEvent.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    await fsm_handlers.process_description(message, state)


# --- ОБРАБОТЧИК ТЕКСТА ДЛЯ АНАЛИЗА И ПОИСКА ---
@dp.message(F.text & ~F.text.startswith('/'))
async def handle_text_input(message: Message, state: FSMContext):
    """
    Обработчик текстового ввода для анализа и поиска
    """
    current_state = await state.get_state()

    # Если пользователь в режиме поиска
    if current_state == Search.waiting_for_query:
        query = message.text.strip()

        if len(query) < 2:
            await message.answer("❌ Поисковый запрос должен быть не менее 2 символов. Попробуйте снова.")
            return

        results = events_manager.search_events(query)

        if not results:
            await message.answer(
                f"❌ По запросу **\"{query}\"** ничего не найдено 😞\n\n"
                "Попробуйте:\n"
                "• Изменить ключевое слово\n"
                "• 📂 Посмотреть по категориям\n"
                "• 📅 Все мероприятия",
                reply_markup=KeyboardBuilder.main_menu_kb(),
                parse_mode="Markdown"
            )
            await state.set_state(None)
            return

        # Формируем текст результатов с красивым форматом
        text = f"🔍 **Результаты поиска:** \"{query}\"\n"
        text += "=" * 35 + "\n\n"
        count = 0
        events_list = []

        for category, events in results.items():
            text += f"📂 **{Config.CATEGORY_NAMES[category]}** ({len(events)})\n"
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

        # Передаем список событий для создания кнопок
        await message.answer(
            text, 
            reply_markup=KeyboardBuilder.search_events_list_kb(events_list, page=1, total_pages=1), 
            parse_mode="Markdown"
        )
        await state.set_state(None)
        return

    # Если пользователь в процессе добавления мероприятия - пропускаем анализ
    if current_state is not None:
        return

    text = message.text

    if len(text) < Config.TEXT_ANALYSIS_MIN_LEN:
        await message.answer(
            f"📝 Текст слишком короткий для анализа 😔\n\n"
            f"Пожалуйста, пришлите описание минимум из **{Config.TEXT_ANALYSIS_MIN_LEN} символов**.\n\n"
            "Пример хорошего текста:\n"
            "\"_Завтра в 18:00 в главном корпусе состоится встреча студенческого совета, "
            "где мы обсудим подготовку к предстоящему фестивалю._\"",
            reply_markup=KeyboardBuilder.back_to_analyze_kb(),
            parse_mode="Markdown"
        )
        return

    # Анализируем текст
    analysis = classifier.analyze_text(text)

    if analysis.is_event:
        response = "✅ **Это похоже на описание мероприятия!**\n\n"
        response += "🔍 **Найдены признаки:**\n"

        if analysis.keywords_found:
            keywords = ", ".join(analysis.keywords_found)
            response += f"• 🏷 Ключевые слова: `{keywords}`\n"
        if analysis.has_time_references:
            response += "• ⏰ Указания на время\n"
        if analysis.has_location_references:
            response += "• 📍 Указания на место\n"
        if analysis.has_date_patterns:
            response += "• 📅 Паттерны дат/времени\n"

        response += "\n**Хотите добавить это событие?**"

        await message.answer(response, reply_markup=KeyboardBuilder.add_from_text_kb(), parse_mode="Markdown")
    else:
        response = "❌ **Это не похоже на описание мероприятия** 🤔\n\n"
        response += "Для распознавания мероприятия нужны:\n"
        response += "• 🏷 Ключевые слова (встреча, концерт, лекция и т.д.)\n"
        response += "• ⏰ Указание времени или даты\n"
        response += "• 📍 Место проведения\n\n"
        response += "**Попробуйте ещё раз** или **добавьте событие вручную** ➕"

        await message.answer(response, reply_markup=KeyboardBuilder.retry_analysis_kb(), parse_mode="Markdown")


# --- MAIN ---
async def main():
    # Загружаем данные при запуске бота
    await events_manager.load_events_from_file()
    logger.info("🚀 Бот запущен!")
    logger.info(f"📊 Загружено мероприятий: {sum(len(events) for events in events_manager.events.values())}")

    # Показываем информацию о конфигурации в debug режиме
    if Config.DEBUG:
        Config.info()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

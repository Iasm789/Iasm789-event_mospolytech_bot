"""
Конфигурационный файл для бота мероприятий.
Централизованное хранилище всех настроек приложения.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()


class Config:
    """Основная конфигурация приложения"""
    
    # --- ОСНОВНЫЕ ПУТИ ---
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / "data"
    LOGS_DIR = BASE_DIR / "logs"
    PARSER_DIR = BASE_DIR / "parser"
    
    # Инициализируем директории
    DATA_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    
    # --- TELEGRAM BOT SETTINGS ---
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError(
            "❌ BOT_TOKEN не найден в переменных окружения!\n"
            "Инструкция:\n"
            "1. Откройте Telegram и найдите @BotFather\n"
            "2. Выполните команду /mybots\n"
            "3. Выберите своего бота и нажмите API Token\n"
            "4. Скопируйте токен в файл .env: BOT_TOKEN=your_token_here"
        )
    
    # --- ФАЙЛЫ И ДИРЕКТОРИИ ---
    EVENTS_FILE = str(DATA_DIR / "events_data.json")
    BACKUP_DIR = DATA_DIR / "backups"
    
    # --- ЛОГИРОВАНИЕ ---
    LOG_FILE = str(LOGS_DIR / "bot.log")
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = '%(asctime)s [%(levelname)s] %(funcName)s: %(message)s'
    LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    
    # Максимальный размер логового файла (10 MB)
    LOG_MAX_BYTES = 10 * 1024 * 1024
    # Количество резервных копий логов
    LOG_BACKUP_COUNT = 5
    
    # --- LLM МОДЕЛЬ ---
    USE_LLM = True
    LLM_MODEL = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    LLM_DTYPE = "float16"  # float16 для оптимизации памяти
    
    # --- ПАРСЕР TELEGRAM ---
    PARSER_DAYS_BACK = 20  # Парсить сообщения за последние N дней
    
    # Список каналов для парсинга
    PARSER_CHANNELS = [
        "mospolytech",                      # Официальный канал
        "mospolymedia",                     # Медиа отделение
        "mospolywork",                      # Центр карьеры
        "profkommospolytech",               # Профсоюз студентов
        "mospolyoverheard",                 # Подслушано в политехе
        "autonet_nti",                      # Автонет НТИ
        "cckmospolytech",                   # ССК Мосполитех
        "ia_panorama_mospolytech",          # ИА Панорама
        "mospolyab",                        # МИР Политеха
        "volunteer_mp",                     # Волонтерский центр
        "vocalmospolytech",                 # Вокальный ансамбль
        "house_of_illusion_mospolytech",   # Иллюзионная мастерская
        "dancelab_mospolitech",             # Лаборатория танцев
        "tm_mospolytech",                   # Творческая мастерская
        "kinocubelife",                     # Кино Куб
        "playpolytech",                     # Play Политех
        "faculty_fm",                       # Факультет машиностроения
        "freedancefamily",                  # Free Dance Family
    ]
    
    # HTTP клиент для парсера
    PARSER_TIMEOUT = 15  # Таймаут для запросов (секунды)
    PARSER_MAX_RETRIES = 3  # Максимум попыток переподключения
    PARSER_RETRY_DELAY = 2  # Задержка между попытками (секунды)
    PARSER_OUTPUT_DIR = str(DATA_DIR / "parsed_events")
    
    # --- КАТЕГОРИИ МЕРОПРИЯТИЙ ---
    CATEGORY_NAMES = {
        "education": "🎓 Образовательные мероприятия",
        "careers": "💼 Профориентационные",
        "competitions": "🏆 Конкурсы / Фестивали",
        "exhibitions": "🎨 Выставки / Экспозиции",
        "culture": "🎭 Культурные и творческие",
        "volunteering": "🤝 Волонтёрские и социальные",
        "student_life": "👥 Студенческая жизнь"
    }
    
    # --- ВАЛИДАЦИЯ ---
    # Ограничения на длину текстов
    EVENT_TITLE_MIN_LEN = 3
    EVENT_TITLE_MAX_LEN = 100
    EVENT_DESCRIPTION_MIN_LEN = 10
    EVENT_DESCRIPTION_MAX_LEN = 1000
    EVENT_PLACE_MIN_LEN = 2
    EVENT_PLACE_MIN_LETTERS = 2  # Минимум букв в названии места
    
    # Минимальная длина текста для анализа
    TEXT_ANALYSIS_MIN_LEN = 20
    
    # --- НАПОМИНАНИЯ (для будущего) ---
    REMINDER_HOURS_BEFORE = 2  # Напоминать за N часов до события
    REMINDER_CHECK_INTERVAL = 3600  # Проверять каждый час (секунды)
    
    # --- РЕЗЕРВНОЕ КОПИРОВАНИЕ ---
    AUTO_BACKUP = True
    BACKUP_INTERVAL = 3600  # Каждый час (секунды)
    BACKUP_KEEP_DAYS = 7  # Хранить резервные копии N дней
    
    # --- РЕЖИМ РАЗРАБОТКИ ---
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    @classmethod
    def get_settings(cls):
        """Возвращает словарь всех настроек"""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith('_') and key.isupper()
        }
    
    @classmethod
    def info(cls):
        """Выводит информацию о конфигурации"""
        print("\n" + "="*60)
        print("📋 КОНФИГУРАЦИЯ БОТА")
        print("="*60)
        print(f"🔑 BOT_TOKEN: {'✓ Установлен' if cls.BOT_TOKEN else '❌ Не найден'}")
        print(f"📁 Data Directory: {cls.DATA_DIR}")
        print(f"📝 Events File: {cls.EVENTS_FILE}")
        print(f"📊 Log File: {cls.LOG_FILE}")
        print(f"🤖 LLM: {'✓ Включен' if cls.USE_LLM else '❌ Отключен'}")
        print(f"📡 Parser Channels: {len(cls.PARSER_CHANNELS)} каналов")
        print(f"🏷️  Categories: {len(cls.CATEGORY_NAMES)} категорий")
        print(f"🐛 Debug Mode: {'✓ Включен' if cls.DEBUG else '❌ Отключен'}")
        print("="*60 + "\n")


# Для удобства импорта
config = Config()


if __name__ == "__main__":
    # Показать информацию о конфигурации при запуске как скрипт
    Config.info()

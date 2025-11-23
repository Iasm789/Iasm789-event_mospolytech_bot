"""
Parser package для Telegram бота.
Содержит классы для парсинга Telegram-каналов и извлечения информации о событиях.
"""

# Используем условные импорты для работы как в пакете, так и как скрипт
try:
    from .telegram_parser_v2 import TelegramParserV2, TelegramMessage
    from .llm_event_extractor import RussianEventExtractor, EventData
    from .huggingface_handler import HuggingFaceHandler
except ImportError:
    from telegram_parser_v2 import TelegramParserV2, TelegramMessage
    from llm_event_extractor import RussianEventExtractor, EventData
    from huggingface_handler import HuggingFaceHandler

__all__ = [
    'TelegramParserV2',
    'TelegramMessage',
    'RussianEventExtractor',
    'EventData',
    'HuggingFaceHandler',
]

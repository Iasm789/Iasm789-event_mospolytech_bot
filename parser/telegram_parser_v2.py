"""
Новый парсер Telegram-каналов с переработанной системой извлечения информации о событиях.
Использует комбинированный подход: регулярные выражения + LLM уточнение.

Преимущества:
- Высокая точность извлечения информации
- Работа с неструктурированным текстом на русском языке
- Быстрая обработка (сначала regex, потом LLM только для уточнения)
- Надежная обработка ошибок
"""

import asyncio
import logging
import json
import time
import hashlib
import pytz
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Set
from dataclasses import dataclass

import aiofiles
import httpx
from bs4 import BeautifulSoup

# Используем условный импорт для работы как в пакете, так и как скрипт
try:
    from .llm_event_extractor import RussianEventExtractor, EventData
except ImportError:
    from llm_event_extractor import RussianEventExtractor, EventData

# Импортируем Config из родительской директории
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config

# Настройки логирования из Config
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(Config.LOG_FORMAT, Config.LOG_DATE_FORMAT))
    logger.addHandler(handler)
logger.setLevel(Config.LOG_LEVEL)


@dataclass
class TelegramMessage:
    """Структура для хранения данных о сообщении из Telegram."""
    id: str
    text: str
    datetime: datetime
    url: str
    channel: str
    message_hash: str = ""

    def to_dict(self) -> dict:
        """Конвертация в словарь."""
        return {
            'id': self.id,
            'text': self.text,
            'datetime': self.datetime.isoformat(),
            'url': self.url,
            'channel': self.channel,
            'message_hash': self.message_hash
        }


class TelegramParserV2:
    """Парсер Telegram-каналов с новой системой извлечения событий."""
    
    def __init__(self, output_dir: str = "output", days_back: int = 20, use_llm: bool = True):
        """
        Args:
            output_dir: Директория для сохранения результатов
            days_back: Количество дней для парсинга
            use_llm: Использовать ли LLM для уточнения (если False, только regex)
        """
        self.output_dir = Path(output_dir)
        self.days_back = days_back
        self.moscow_tz = pytz.timezone('Europe/Moscow')
        self.seen_messages: Set[str] = set()
        
        # Инициализируем экстрактор событий ОДН РАЗ (переиспользуется для всех каналов)
        self.extractor = RussianEventExtractor(use_llm=use_llm)
        logger.info(f"✓ Экстрактор событий инициализирован. LLM: {'Включена (ленивая загрузка)' if use_llm else 'Отключена'}")
        
        # Настройки запросов из Config
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.timeout = Config.PARSER_TIMEOUT
        self.max_retries = Config.PARSER_MAX_RETRIES
        self.retry_delay = Config.PARSER_RETRY_DELAY
        
        # Создаем директорию для выходных файлов
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"✓ Парсер инициализирован. LLM: {'Включена' if use_llm else 'Отключена'}")

    def _generate_message_hash(self, message: TelegramMessage) -> str:
        """Генерация уникального хеша сообщения для фильтрации дубликатов."""
        content = f"{message.text}|{message.datetime.isoformat()}|{message.channel}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    async def _fetch_page(self, url: str) -> Optional[str]:
        """Получение HTML-страницы асинхронно с повторными попытками при ошибках."""
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, headers=self.headers)
                    if response.status_code == 200:
                        return response.text
                    logging.warning(f"HTTP {response.status_code} при запросе {url}")
            except httpx.RequestError as e:
                logging.warning(f"Ошибка при запросе (попытка {attempt + 1}/{self.max_retries}): {e}")
            
            if attempt < self.max_retries - 1:
                # Экспоненциальная задержка: 2, 4, 8 сек (вместо 2, 4, 6)
                wait_time = min(self.retry_delay * (2 ** attempt), 30)
                logging.debug(f"Жду {wait_time:.1f}s перед повторной попыткой...")
                await asyncio.sleep(wait_time)
        
        return None

    def _clean_text(self, text: str) -> str:
        """Очистка текста сообщения от служебной информации."""
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            # Пропускаем служебные строки
            if any(skip in line.lower() for skip in [
                'views', 'forward', 'подписаться', 'subscribe',
                'reactions', 'комментарий', 'просмотр'
            ]):
                continue
            lines.append(line)
        
        return '\n'.join(lines).strip()

    async def parse_channel(self, channel_name: str) -> List[TelegramMessage]:
        """
        Парсинг сообщений из канала (асинхронно).
        
        Args:
            channel_name: Имя канала в Telegram (без @)
            
        Returns:
            Список сообщений
        """
        logging.info(f"📡 Начинаем парсинг канала: {channel_name}")
        messages = []
        url = f"https://t.me/s/{channel_name}"
        
        html = await self._fetch_page(url)
        if not html:
            logging.error(f"❌ Не удалось получить содержимое канала {channel_name}")
            return []

        cutoff_date = datetime.now(self.moscow_tz) - timedelta(days=self.days_back)
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            message_divs = soup.find_all('div', class_='tgme_widget_message')
            
            logging.info(f"📝 Найдено {len(message_divs)} сообщений в канале")
            
            for div in message_divs:
                try:
                    # Получаем время сообщения
                    time_tag = div.find('time', datetime=True)
                    if not time_tag:
                        continue
                    
                    msg_date = datetime.fromisoformat(time_tag['datetime'])
                    if msg_date.tzinfo is None:
                        msg_date = pytz.utc.localize(msg_date)
                    msg_date = msg_date.astimezone(self.moscow_tz)
                    
                    # Проверяем дату
                    if msg_date < cutoff_date:
                        continue
                    
                    # Получаем текст
                    text_div = div.find('div', class_='tgme_widget_message_text')
                    if not text_div:
                        continue
                    
                    text = self._clean_text(text_div.get_text())
                    if not text or len(text) < 10:
                        continue
                    
                    # Получаем ID и URL
                    msg_link = div.find('a', class_='tgme_widget_message_date')
                    if not msg_link or 'href' not in msg_link.attrs:
                        continue
                    
                    msg_url = msg_link['href']
                    msg_id = msg_url.split('/')[-1]
                    
                    # Создаем объект сообщения
                    message = TelegramMessage(
                        id=msg_id,
                        text=text,
                        datetime=msg_date,
                        url=msg_url,
                        channel=channel_name
                    )
                    
                    # Проверяем на дубликаты
                    message.message_hash = self._generate_message_hash(message)
                    if message.message_hash not in self.seen_messages:
                        self.seen_messages.add(message.message_hash)
                        messages.append(message)
                
                except Exception as e:
                    logging.debug(f"Ошибка при обработке сообщения: {e}")
                    continue
            
            logging.info(f"✓ Получено {len(messages)} уникальных сообщений из канала {channel_name}")
            return messages
        
        except Exception as e:
            logging.error(f"❌ Критическая ошибка при парсинге канала: {e}")
            return []

    async def process_channel_messages(self, messages: List[TelegramMessage], channel_name: str) -> dict:
        """
        Обрабатывает сообщения канала и извлекает события (с batch LLM обработкой).
        
        Args:
            messages: Список сообщений
            channel_name: Имя канала
            
        Returns:
            Словарь со статистикой обработки
        """
        if not messages:
            return {'total': 0, 'events': 0, 'skipped': 0}
        
        # Сортируем сообщения по дате
        messages.sort(key=lambda x: x.datetime)
        
        events = []
        all_messages = []
        skipped = 0
        
        logging.info(f"🔍 Анализируем {len(messages)} сообщений на предмет событий...")
        
        # Подготавливаем данные для batch обработки
        batch_data = [(msg.text, msg.url) for msg in messages]
        
        # Batch обработка через LLM
        batch_results = self.extractor.process_batch(batch_data)
        
        # Собираем результаты
        for i, (msg, event_data) in enumerate(zip(messages, batch_results), 1):
            try:
                if event_data:
                    event_data.telegram_url = msg.url  # Добавляем URL
                    events.append(event_data)
                    logging.debug(f"✓ [{i}/{len(messages)}] Найдено событие: {event_data.title}")
                else:
                    skipped += 1
                
                all_messages.append(msg)
                
            except Exception as e:
                logging.debug(f"Ошибка при обработке результата {i}: {e}")
                skipped += 1
                continue
        
        # Асинхронно сохраняем результаты
        await self._save_results(events, all_messages, channel_name)
        
        return {
            'total': len(messages),
            'events': len(events),
            'skipped': skipped
        }


    async def _save_results(self, events: List[EventData], all_messages: List[TelegramMessage], 
                     channel_name: str):
        """
        Асинхронно сохраняет результаты обработки в файлы (инкрементально в JSONL с форматированием).
        
        Args:
            events: Список найденных событий
            all_messages: Все сообщения канала
            channel_name: Имя канала
        """
        # Сохраняем события в JSONL (инкрементально, по одному событию на строку с отступами)
        if events:
            events_jsonl_path = self.output_dir / f"{channel_name}_v2_events.jsonl"
            async with aiofiles.open(events_jsonl_path, 'w', encoding='utf-8') as f:
                for event in events:
                    event_dict = event.to_dict()
                    # Форматируем JSON с отступами
                    event_line = json.dumps(event_dict, ensure_ascii=False, indent=2)
                    await f.write(event_line + '\n')
            logging.info(f"💾 События (JSONL) сохранены в {events_jsonl_path}")
            
            # Сохраняем события в текстовый файл для удобства чтения
            events_txt_path = self.output_dir / f"{channel_name}_v2_events.txt"
            async with aiofiles.open(events_txt_path, 'w', encoding='utf-8') as f:
                await f.write(f"События из канала '{channel_name}'\n")
                await f.write(f"Дата обработки: {datetime.now(self.moscow_tz).strftime('%d.%m.%Y %H:%M:%S')}\n")
                await f.write(f"Всего найдено: {len(events)} событий\n")
                await f.write("=" * 80 + "\n\n")
                
                for i, event in enumerate(events, 1):
                    await f.write(f"[{i}] {event.title}\n")
                    await f.write(f"📅 Дата: {event.date}\n")
                    await f.write(f"⏰ Время: {event.time}\n")
                    await f.write(f"📍 Место: {event.location}\n")
                    await f.write(f"🏷️  Категория: {event.category}\n")
                    await f.write(f"🔗 URL: {event.telegram_url}\n")
                    await f.write(f"📊 Уверенность: {event.confidence:.0%}\n")
                    await f.write(f"\n📝 Описание:\n{event.description}\n")
                    await f.write("-" * 80 + "\n\n")
            
            logging.info(f"📝 Информация о событиях сохранена в {events_txt_path}")

    async def parse_and_process(self, channels: List[str]) -> dict:
        """
        Полный цикл парсинга и обработки нескольких каналов (асинхронно и параллельно).
        
        Args:
            channels: Список имен каналов
            
        Returns:
            Словарь со статистикой обработки всех каналов
        """
        statistics = {
            'total_channels': len(channels),
            'processed': 0,
            'failed': 0,
            'total_messages': 0,
            'total_events': 0,
            'channels_stats': {}
        }
        
        start_time = time.time()
        
        # Используем Semaphore для ограничения одновременных запросов (макс 3 канала)
        semaphore = asyncio.Semaphore(3)
        
        async def parse_and_process_channel(channel: str) -> tuple:
            """Вспомогательная функция для обработки одного канала."""
            async with semaphore:  # Ограничиваем параллелизм
                try:
                    # Парсим канал асинхронно (больше не блокирует!)
                    messages = await self.parse_channel(channel)
                    
                    if not messages:
                        logger.warning(f"⚠️  Канал пуст или недоступен: {channel}")
                        return channel, None
                    
                    # Асинхронно обрабатываем сообщения
                    stats = await self.process_channel_messages(messages, channel)
                    
                    logger.info(f"✓ Канал {channel} обработан:")
                    logger.info(f"  - Всего сообщений: {stats['total']}")
                    logger.info(f"  - Найдено событий: {stats['events']}")
                    logger.info(f"  - Пропущено: {stats['skipped']}")
                    
                    return channel, stats
                
                except Exception as e:
                    logger.error(f"❌ Ошибка при обработке канала {channel}: {e}")
                    return channel, None
        
        # Запускаем все каналы параллельно (но с лимитом Semaphore)
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 Запускаем параллельную обработку {len(channels)} каналов")
        logger.info(f"{'='*80}\n")
        
        tasks = [parse_and_process_channel(channel) for channel in channels]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обработка результатов
        for result in results:
            if isinstance(result, Exception):
                statistics['failed'] += 1
                continue
            
            channel, stats = result
            if stats is not None:
                statistics['processed'] += 1
                statistics['total_messages'] += stats['total']
                statistics['total_events'] += stats['events']
                statistics['channels_stats'][channel] = stats
            else:
                statistics['failed'] += 1
        
        # Итоговая статистика
        elapsed_time = time.time() - start_time
        
        logger.info(f"\n{'='*80}")
        logger.info("📊 ИТОГОВАЯ СТАТИСТИКА")
        logger.info(f"{'='*80}")
        logger.info(f"Всего каналов: {statistics['total_channels']}")
        logger.info(f"Успешно обработано: {statistics['processed']}")
        logger.info(f"Ошибки: {statistics['failed']}")
        logger.info(f"Всего сообщений обработано: {statistics['total_messages']}")
        logger.info(f"Всего найдено событий: {statistics['total_events']}")
        logger.info(f"⏱️  Время выполнения: {elapsed_time:.1f} сек (параллелизм 3 канала одновременно)")
        logger.info(f"{'='*80}\n")
        
        return statistics


async def main():
    """Основная асинхронная функция для запуска парсера."""
    
    # Инициализируем парсер с параметрами из Config
    parser = TelegramParserV2(
        output_dir=str(Config.PARSER_OUTPUT_DIR),
        days_back=Config.PARSER_DAYS_BACK,
        use_llm=Config.USE_LLM
    )
    
    # Асинхронно запускаем парсинг с каналами из Config
    statistics = await parser.parse_and_process(Config.PARSER_CHANNELS)
    
    # Асинхронно сохраняем статистику
    stats_file = Path(Config.PARSER_OUTPUT_DIR) / "parse_statistics_v2.json"
    async with aiofiles.open(stats_file, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(statistics, ensure_ascii=False, indent=2))
    
    logger.info(f"📊 Статистика сохранена в {stats_file}")


if __name__ == "__main__":
    asyncio.run(main())
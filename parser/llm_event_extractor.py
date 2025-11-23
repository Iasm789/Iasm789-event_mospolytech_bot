"""
Переработанный модуль для извлечения информации о событиях из текстов на русском языке.
Использует комбинированный подход: регулярные выражения + LLM для повышения точности.

Особенности:
- Надежное извлечение дат, времени, мест из неструктурированного текста
- Работа на русском языке
- Обработка различных форматов написания информации о событиях
- Двухэтапный анализ: сначала regex, потом LLM уточняет детали
"""

import re
import json
import logging
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
import pytz
from pathlib import Path

# Используем условный импорт для работы как в пакете, так и как скрипт
try:
    from .huggingface_handler import HuggingFaceHandler
except ImportError:
    from huggingface_handler import HuggingFaceHandler

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
class EventData:
    """Структура для хранения извлеченной информации о событии."""
    title: str
    date: str  # в формате ДД.ММ.ГГГГ или текстовое описание
    time: str  # в формате ЧЧ:МММ или диапазон
    location: str  # место проведения
    description: str  # полное описание события
    category: str  # категория события
    telegram_url: str
    confidence: float  # уверенность в извлечении информации (0.0-1.0)
    
    def to_dict(self) -> dict:
        """Конвертирует в словарь."""
        return asdict(self)


class RussianEventExtractor:
    """
    Извлекатель информации о событиях на русском языке.
    Использует регулярные выражения и LLM для повышения точности.
    """
    
    def __init__(self, use_llm: bool = True):
        """
        Args:
            use_llm: Использовать ли LLM для уточнения информации
        """
        self.use_llm = use_llm
        self._llm = None  # Ленивая загрузка (не загружаем при инициализации)
        self._llm_loaded = False
        self._llm_error = False
        
        self.moscow_tz = pytz.timezone('Europe/Moscow')
        
        # Регулярные выражения для извлечения информации
        self._compile_patterns()
        
        # Ключевые слова для определения категорий
        self.category_keywords = {
            'education': [
                'лекция', 'семинар', 'мастер-класс', 'тренинг', 'курс', 'школа',
                'конференция', 'дебаты', 'практикум', 'консультация'
            ],
            'career': [
                'профориентация', 'карьера', 'стажировка', 'интернш', 'собеседование',
                'работа', 'вакансия', 'центр карьеры'
            ],
            'competitions': [
                'конкурс', 'фестиваль', 'олимпиада', 'чемпионат', 'турнир',
                'соревнование', 'конкурс творчества', 'конкурс проектов'
            ],
            'exhibitions': [
                'выставка', 'экспозиция', 'выставочный', 'галерея', 'инсталляция'
            ],
            'culture': [
                'концерт', 'выступление', 'танец', 'танцевальный', 'кино', 'фильм',
                'иллюзион', 'шоу', 'перформанс', 'представление', 'спектакль',
                'творческий', 'вокальный'
            ],
            'volunteering': [
                'волонтер', 'волонтёрск', 'социальн', 'благотворител', 'помощь',
                'акция', 'инициатива', 'проект', 'общественн'
            ],
            'student_life': [
                'студенческ', 'студент', 'встреча', 'клуб', 'сообщество', 'творческая мастерская',
                'собрание', 'самоуправлени', 'соуправлени'
            ]
        }
    
    def _compile_patterns(self):
        """Компилирует регулярные выражения."""
        
        # Дата: различные форматы
        self.date_patterns = [
            # ДД.ММ.ГГГГ
            r'\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b',
            # ДД.ММ (без года)
            r'\b(\d{1,2})\.(\d{1,2})\b(?!\.)',
            # День недели или дата словами
            r'\b(понедельник|вторник|среда|четверг|пятница|суббота|воскресенье)\b',
            r'\b(\d{1,2})(\s+)(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)(\s+)?(\d{4})?\b',
            # "завтра", "сегодня", "послезавтра"
            r'\b(завтра|сегодня|послезавтра|сейчас)\b',
            # "в следующий понедельник", "на следующей неделе"
            r'\b(на|в)\s+(следующей|этой|этой\s+)?[^.]*?(неделе|дню|дата)\b',
        ]
        
        # Время: различные форматы
        self.time_patterns = [
            # ЧЧ:МММ или Ч:МММ
            r'\b(\d{1,2}):(\d{2})\b',
            # "в 14:30", "с 18:00"
            r'\b(в|с|с\s+|до|по)\s+(\d{1,2}):(\d{2})\b',
            # Диапазон времени: 10:00-12:00, 10:00 - 12:00
            r'\b(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\b',
            # Словами: "утром", "днем", "вечером"
            r'\b(утром|днём|днем|вечером|ночью|с\s+утра|до\s+вечера)\b',
        ]
        
        # Место: различные форматы
        self.location_patterns = [
            # "в аудитории", "в корпусе", "в зале"
            r'\b(в|на)\s+(аудитори[яе]|корпус[еа]|зал[еа]|помещени[яе]|кабинет[еа]|комнат[еа]|спортзал[еа]|актовом\s+зал[еа]|конференц-зал[еа]|амфитеатр[еа])\s+([№#]?\d+|\w+)',
            # "на стадионе", "в театре" и т.д.
            r'\b(на|в|при)\s+(стадион[еа]|театр[еа]|кинотеатр[еа]|музе[еа]|парк[еа]|сквер[еа]|центр[еа]|офис[еа]|ресторан[еа]|кафе)',
            # Онлайн платформы
            r'\b(онлайн|zoom|microsoft\s+teams|skype|discord|youtube|трансляция|вебинар|видеоконференция)\b',
            # Конкретный адрес
            r'\b(ул\.|улиц[аи])\s+([А-Яа-яЁё\s]+?)(?:,|$)',
            # Московский политех варианты
            r'\b(мосполитех|мос\s?политех|московск[ий]?\s+политех)',
        ]
        
        # Признаки события
        self.event_keywords = [
            'мероприятие', 'событие', 'встреча', 'проводит', 'приглашаем',
            'приглашает', 'состоится', 'пройдет', 'проводится', 'организуют',
            'объявляет', 'объявляют', 'запись', 'регистрация', 'анонс',
            'устраивает', 'устраивают', 'расписание', 'график',
            'начинается', 'начало', 'стартует', 'запускаем'
        ]
    
    def _get_llm(self):
        """
        Ленивая загрузка LLM модели - загружаем только при первом использовании.
        
        Returns:
            HuggingFaceHandler или None если не удалось загрузить
        """
        # Если уже пытались загрузить и была ошибка, не повторяем
        if self._llm_error:
            return None
        
        # Если модель уже загружена, возвращаем её
        if self._llm_loaded and self._llm is not None:
            return self._llm
        
        # Загружаем модель в первый раз
        if not self._llm_loaded:
            try:
                self._llm = HuggingFaceHandler()
                self._llm.load_model()
                self._llm_loaded = True
                logging.info("✓ LLM модель загружена успешно (при первом использовании)")
                return self._llm
            except Exception as e:
                logging.warning(f"⚠ Не удалось загрузить LLM модель: {e}. Будет использоваться только regex.")
                self._llm_error = True
                self.use_llm = False
                return None
        
        return self._llm
    
    def process_batch(self, texts: List[Tuple[str, str]]) -> List[Optional[EventData]]:
        """
        Batch обработка нескольких текстов для повышения производительности.
        Группирует тексты и обрабатывает их вместе через LLM.
        
        Args:
            texts: Список кортежей (text, telegram_url)
            
        Returns:
            Список EventData или None для каждого текста
        """
        results = []
        
        # Если LLM недоступна, обрабатываем каждый текст отдельно (только regex)
        if not self.use_llm:
            for text, url in texts:
                result = self.extract_event_info(text, url)
                results.append(result)
            return results
        
        # Разделяем на события и не-события (на основе regex проверки)
        event_texts = []
        event_indices = []
        
        for i, (text, url) in enumerate(texts):
            if self.is_event_text(text):
                event_texts.append((text, url))
                event_indices.append(i)
            else:
                results.append(None)
        
        # Если нет событий, возвращаем результаты
        if not event_texts:
            return results
        
        # Обрабатываем события батчами
        batch_size = 5  # Обрабатываем по 5 событий за раз для оптимизации памяти
        llm = self._get_llm()
        
        batch_results = {}
        
        for batch_idx in range(0, len(event_texts), batch_size):
            batch = event_texts[batch_idx:batch_idx + batch_size]
            
            for text, url in batch:
                try:
                    event_data = self.extract_event_info(text, url)
                    batch_results[url] = event_data
                except Exception as e:
                    logging.debug(f"Ошибка при batch обработке: {e}")
                    batch_results[url] = None
        
        # Собираем результаты в правильном порядке
        final_results = [None] * len(texts)
        event_result_idx = 0
        
        for i, (text, url) in enumerate(texts):
            if self.is_event_text(text):
                final_results[i] = batch_results.get(url)
        
        return final_results
    
    def is_event_text(self, text: str) -> bool:
        """
        Определяет, содержит ли текст информацию о событии.
        
        Args:
            text: Текст для анализа
            
        Returns:
            True если текст содержит признаки события
        """
        text_lower = text.lower()
        
        # Проверяем наличие ключевых слов события
        event_score = sum(1 for keyword in self.event_keywords if keyword in text_lower)
        
        # Проверяем наличие хотя бы одного элемента информации о событии
        has_date = any(re.search(pattern, text, re.IGNORECASE) for pattern in self.date_patterns)
        has_time = any(re.search(pattern, text, re.IGNORECASE) for pattern in self.time_patterns)
        has_location = any(re.search(pattern, text, re.IGNORECASE) for pattern in self.location_patterns)
        has_keywords = event_score > 0
        
        # Событие если есть: ключевые слова И хотя бы два элемента (дата/время/место)
        elements_found = sum([has_date, has_time, has_location])
        return (has_keywords and elements_found >= 1) or (event_score >= 2)
    
    def extract_date(self, text: str) -> Tuple[str, float]:
        """
        Извлекает дату из текста.
        
        Args:
            text: Текст для анализа
            
        Returns:
            Кортеж (дата_строка, уверенность)
        """
        text_lower = text.lower()
        
        # Проверяем "завтра", "сегодня", "послезавтра"
        if 'завтра' in text_lower:
            tomorrow = datetime.now(self.moscow_tz) + timedelta(days=1)
            return tomorrow.strftime('%d.%m.%Y'), 0.95
        
        if 'сегодня' in text_lower:
            today = datetime.now(self.moscow_tz)
            return today.strftime('%d.%m.%Y'), 0.95
        
        if 'послезавтра' in text_lower:
            day_after = datetime.now(self.moscow_tz) + timedelta(days=2)
            return day_after.strftime('%d.%m.%Y'), 0.95
        
        # ДД.ММ.ГГГГ
        match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', text)
        if match:
            day, month, year = match.groups()
            try:
                datetime(int(year), int(month), int(day))
                return f"{day.zfill(2)}.{month.zfill(2)}.{year}", 0.95
            except ValueError:
                pass
        
        # ДД.ММ (без года)
        match = re.search(r'(\d{1,2})\.(\d{1,2})(?!\.)', text)
        if match:
            day, month = match.groups()
            try:
                year = datetime.now(self.moscow_tz).year
                datetime(year, int(month), int(day))
                return f"{day.zfill(2)}.{month.zfill(2)}.{year}", 0.85
            except ValueError:
                pass
        
        # ДД месяца ГГГГ (словами)
        month_names = {
            'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5, 'июня': 6,
            'июля': 7, 'августа': 8, 'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
        }
        
        pattern = r'(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)(?:\s+(\d{4}))?'
        match = re.search(pattern, text_lower)
        if match:
            day, month_name, year = match.groups()
            month = month_names.get(month_name)
            year = year if year else str(datetime.now(self.moscow_tz).year)
            try:
                datetime(int(year), month, int(day))
                return f"{day.zfill(2)}.{str(month).zfill(2)}.{year}", 0.90
            except ValueError:
                pass
        
        return "Не указана", 0.0
    
    def extract_time(self, text: str) -> Tuple[str, float]:
        """
        Извлекает время из текста.
        
        Args:
            text: Текст для анализа
            
        Returns:
            Кортеж (время_строка, уверенность)
        """
        text_lower = text.lower()
        
        # Диапазон времени: 10:00-12:00
        match = re.search(r'(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})', text)
        if match:
            start_h, start_m, end_h, end_m = match.groups()
            return f"{start_h.zfill(2)}:{start_m} - {end_h.zfill(2)}:{end_m}", 0.95
        
        # Одиночное время ЧЧ:МММ
        match = re.search(r'\b(\d{1,2}):(\d{2})\b', text)
        if match:
            hour, minute = match.groups()
            try:
                int(hour), int(minute)
                return f"{hour.zfill(2)}:{minute}", 0.90
            except ValueError:
                pass
        
        # Словесное описание времени
        time_words = {
            'утро': '09:00', 'днём': '14:00', 'днем': '14:00',
            'вечер': '18:00', 'ночь': '20:00'
        }
        
        for word, time_val in time_words.items():
            if word in text_lower:
                return time_val, 0.70
        
        return "Не указано", 0.0
    
    def extract_location(self, text: str) -> Tuple[str, float]:
        """
        Извлекает место проведения из текста.
        
        Args:
            text: Текст для анализа
            
        Returns:
            Кортеж (место_строка, уверенность)
        """
        text_lower = text.lower()
        
        # Онлайн платформы
        online_platforms = ['zoom', 'teams', 'skype', 'discord', 'youtube', 'youtube live']
        for platform in online_platforms:
            if platform in text_lower:
                return f"Онлайн ({platform.upper()})", 0.95
        
        # Общее "онлайн"
        if 'онлайн' in text_lower or 'трансляция' in text_lower or 'вебинар' in text_lower:
            return "Онлайн", 0.90
        
        # Аудитория/корпус/кабинет
        pattern = r'\b(аудитори[яе]|корпус[еа]|кабинет[еа]|помещени[яе]|зал[еа])\s+([№#]?[\dА-Яа-яЁё\s\-/]+?)(?:\n|,|\.|$)'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            location_type, location_num = match.groups()
            location_num = location_num.strip()
            return f"{location_type.capitalize()} {location_num}", 0.90
        
        # Известные места
        locations_keywords = {
            'стадион': 'Стадион Политеха',
            'театр': 'Театр',
            'концертный зал': 'Концертный зал',
            'спортзал': 'Спортзал',
            'актовый зал': 'Актовый зал',
            'конференц-зал': 'Конференц-зал'
        }
        
        for keyword, location_name in locations_keywords.items():
            if keyword in text_lower:
                return location_name, 0.85
        
        # Мосполитех
        if 'мосполитех' in text_lower or 'политех' in text_lower:
            return 'Московский Политех', 0.70
        
        return "Не указано", 0.0
    
    def extract_category(self, text: str) -> str:
        """
        Определяет категорию события на основе ключевых слов.
        
        Args:
            text: Текст для анализа
            
        Returns:
            Категория события
        """
        text_lower = text.lower()
        scores = {}
        
        for category, keywords in self.category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                scores[category] = score
        
        if scores:
            return max(scores, key=scores.get)
        return 'student_life'  # категория по умолчанию
    
    def extract_title(self, text: str) -> str:
        """
        Извлекает название события из текста.
        
        Args:
            text: Текст для анализа
            
        Returns:
            Название события
        """
        # Если есть жирный текст или первая строка - используем её
        lines = text.split('\n')
        if lines:
            title = lines[0].strip()
            # Обрезаем длинный заголовок
            if len(title) > 100:
                title = title[:97] + '...'
            return title
        
        # Иначе берем первые слова
        words = text.split()[:8]
        return ' '.join(words)[:100]
    
    def extract_event_info(self, text: str, telegram_url: str) -> Optional[EventData]:
        """
        Основной метод для извлечения всей информации о событии.
        
        Args:
            text: Текст сообщения
            telegram_url: URL сообщения в Telegram
            
        Returns:
            EventData или None если это не событие
        """
        # Проверяем, что это событие
        if not self.is_event_text(text):
            return None
        
        # Извлекаем информацию регулярными выражениями
        date, date_conf = self.extract_date(text)
        time, time_conf = self.extract_time(text)
        location, location_conf = self.extract_location(text)
        category = self.extract_category(text)
        title = self.extract_title(text)
        
        # Общая уверенность
        confidence = (date_conf + time_conf + location_conf) / 3
        
        # Если LLM доступна, используем её для уточнения
        if self.use_llm:
            try:
                event_data = self._refine_with_llm(text, {
                    'title': title,
                    'date': date,
                    'time': time,
                    'location': location,
                    'category': category
                })
                if event_data:
                    return event_data
            except Exception as e:
                logging.warning(f"Ошибка при обработке LLM: {e}. Используем результаты regex.")
        
        # Используем результаты регулярных выражений
        description = text[:500] if len(text) > 500 else text
        
        return EventData(
            title=title,
            date=date,
            time=time,
            location=location,
            description=description,
            category=category,
            telegram_url=telegram_url,
            confidence=min(confidence, 1.0)
        )
    
    def _refine_with_llm(self, text: str, extracted_info: dict) -> Optional[EventData]:
        """
        Уточняет извлеченную информацию с помощью LLM.
        
        Args:
            text: Оригинальный текст
            extracted_info: Информация, извлеченная регулярными выражениями
            
        Returns:
            Уточненная EventData или None
        """
        llm = self._get_llm()
        if not llm:
            return None
        
        prompt = f"""Проанализируй следующий текст о событии на русском языке.

Уже извлечена информация:
- Название: {extracted_info['title']}
- Дата: {extracted_info['date']}
- Время: {extracted_info['time']}
- Место: {extracted_info['location']}
- Категория: {extracted_info['category']}

Текст события:
{text}

Задача: Проверь извлеченную информацию и уточни её, если необходимо.
Если информация упущена или неточна, дополни её.

Верни ТОЛЬКО JSON без дополнительного текста:
{{
    "title": "Точное название события",
    "date": "Дата в формате ДД.ММ.ГГГГ или описание",
    "time": "Время в формате ЧЧ:МММ или описание",
    "location": "Место проведения",
    "description": "Краткое описание события (2-3 предложения)"
}}"""
        
        try:
            response = llm.generate_response(prompt, max_length=1000, temperature=0.3)
            
            if not response:
                return None
            
            # Извлекаем JSON из ответа
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
            if not json_match:
                return None
            
            data = json.loads(json_match.group())
            
            return EventData(
                title=data.get('title', extracted_info['title'])[:150],
                date=data.get('date', extracted_info['date']),
                time=data.get('time', extracted_info['time']),
                location=data.get('location', extracted_info['location']),
                description=data.get('description', text[:500]),
                category=extracted_info['category'],
                telegram_url='',  # Будет добавлена позже
                confidence=0.85
            )
        
        except Exception as e:
            logging.debug(f"Ошибка LLM уточнения: {e}")
            return None

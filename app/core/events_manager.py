"""
Менеджер для работы с событиями.
Отвечает за загрузку, сохранение, поиск и фильтрацию событий.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import aiofiles

from config import Config

logger = logging.getLogger(__name__)


class EventsManager:
    """Менеджер для работы с событиями и их хранилищем."""

    def __init__(self):
        self.events: Dict[str, List[Dict]] = {}
        self.event_counter = 7
        self.events_file = Config.EVENTS_FILE

    async def load_events_from_file(self) -> None:
        """Асинхронно загружает мероприятия из JSON файла или из parsed_events."""
        try:
            if os.path.exists(self.events_file):
                # Пытаемся загрузить из сохраненного файла
                async with aiofiles.open(self.events_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    loaded_events = json.loads(content)

                self.events.clear()
                self.events.update(loaded_events)
                
                # Инициализируем все категории, даже если они пусты
                all_categories = ["education", "careers", "competitions", "exhibitions", "culture", "volunteering", "student_life"]
                for category in all_categories:
                    if category not in self.events:
                        self.events[category] = []
            else:
                # Если сохраненного файла нет, загружаем из parsed_events
                logger.info("Файл с мероприятиями не найден, загружаю из parsed_events...")
                await self._load_from_parsed_events()
                return

            # Обновляем счетчик ID на основе максимального существующего ID
            max_id = 0
            for category_events in self.events.values():
                for event in category_events:
                    try:
                        event_id = int(event['id'])
                        if event_id > max_id:
                            max_id = event_id
                    except (ValueError, KeyError):
                        pass
            self.event_counter = max_id + 1

            total = sum(len(events) for events in self.events.values())
            logger.info(f"Загружено {total} мероприятий из {self.events_file}")
        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}")
            await self._load_from_parsed_events()

    async def save_events_to_file(self) -> None:
        """Асинхронно сохраняет мероприятия в JSON файл."""
        try:
            async with aiofiles.open(self.events_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(self.events, ensure_ascii=False, indent=2))
            logger.info("Мероприятия сохранены в файл")
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")

    async def _load_from_parsed_events(self) -> None:
        """Загружает события из JSONL файлов в директории parsed_events."""
        parsed_events_dir = Path(Config.DATA_DIR) / "parsed_events"
        
        if not parsed_events_dir.exists():
            logger.warning(f"Директория {parsed_events_dir} не найдена")
            self.initialize_default_events()
            return
        
        # Инициализируем категории
        self.events = {
            "education": [],
            "careers": [],
            "competitions": [],
            "exhibitions": [],
            "culture": [],
            "volunteering": [],
            "student_life": []
        }
        event_id_counter = 1
        
        # Маппинг категорий из parsed_events в категории бота
        category_mapping = {
            "career": "careers",
            "education": "education",
            "culture": "culture",
            "competitions": "competitions",
            "exhibitions": "exhibitions",
            "volunteering": "volunteering",
            "student_life": "student_life",
        }
        
        # Находим все JSONL файлы
        jsonl_files = sorted(parsed_events_dir.glob("*_events.jsonl"))
        
        if not jsonl_files:
            logger.warning("JSONL файлы не найдены в parsed_events")
            self.initialize_default_events()
            return
        
        for jsonl_file in jsonl_files:
            try:
                async with aiofiles.open(jsonl_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                
                # Извлекаем JSON объекты из файла
                json_objects = self._extract_json_objects(content)
                
                for obj_str in json_objects:
                    try:
                        event_data = json.loads(obj_str)
                        
                        # Преобразуем структуру события
                        category = category_mapping.get(
                            event_data.get('category', '').lower(),
                            'education'
                        )
                        
                        # Форматируем время и дату
                        date_str = event_data.get('date', '')
                        time_str = event_data.get('time', '10:00')
                        if time_str == "Не указано" or not time_str:
                            time_str = "10:00"
                        
                        new_event = {
                            'id': str(event_id_counter),
                            'title': event_data.get('title', 'Событие без названия')[:100],
                            'time': f"{time_str} {date_str}" if date_str else time_str,
                            'place': event_data.get('location', 'Место не указано')[:100],
                            'desc': event_data.get('description', '')[:1000],
                            'source': jsonl_file.stem,
                            'telegram_url': event_data.get('telegram_url', ''),
                        }
                        
                        self.events[category].append(new_event)
                        event_id_counter += 1
                        
                    except json.JSONDecodeError:
                        continue
                
                logger.info(f"Загружено из {jsonl_file.name}")
            
            except Exception as e:
                logger.error(f"Ошибка при загрузке {jsonl_file}: {e}")
                continue
        
        # Если ничего не загружилось, используем начальные данные
        if all(len(events) == 0 for events in self.events.values()):
            logger.warning("Не удалось загрузить события из JSONL")
            self.initialize_default_events()
        else:
            self.event_counter = event_id_counter

    def _extract_json_objects(self, content: str) -> List[str]:
        """Извлекает JSON объекты из строки."""
        objects = []
        brace_count = 0
        current_obj = ""
        in_string = False
        escape_next = False
        
        for char in content:
            # Обработка экранирования
            if escape_next:
                current_obj += char
                escape_next = False
                continue
            
            if char == '\\' and in_string:
                current_obj += char
                escape_next = True
                continue
            
            # Обработка кавычек
            if char == '"':
                in_string = not in_string
                current_obj += char
                continue
            
            # Если не в строке, считаем скобки
            if not in_string:
                if char == '{':
                    brace_count += 1
                    current_obj += char
                elif char == '}':
                    current_obj += char
                    brace_count -= 1
                    if brace_count == 0 and current_obj.strip():
                        # Завершился JSON объект
                        objects.append(current_obj.strip())
                        current_obj = ""
                    continue
                elif brace_count > 0:
                    current_obj += char
                else:
                    # Пропускаем символы вне JSON объектов
                    if not char.isspace():
                        current_obj += char
            else:
                current_obj += char
        
        return objects

    def initialize_default_events(self) -> None:
        """Инициализирует минимальные начальные данные мероприятий (fallback)."""
        self.events = {
            "education": [
                {
                    "id": "1",
                    "title": "Пример события",
                    "time": "14:00 25.11.2025",
                    "place": "Московский Политех",
                    "desc": "Это пример события. Для загрузки реальных мероприятий убедитесь, что есть файл с JSON или JSONL файлы в data/parsed_events",
                    "source": "default"
                }
            ],
            "careers": [],
            "competitions": [],
            "exhibitions": [],
            "culture": [],
            "volunteering": [],
            "student_life": [],
        }
        self.event_counter = 2
        logger.info("Используются события по умолчанию")

    def search_events(self, query: str) -> Dict[str, List[Dict]]:
        """Поиск мероприятий по названию и описанию."""
        query_lower = query.lower()
        results = {}

        for category, events in self.events.items():
            matching = []
            for event in events:
                title_match = query_lower in event['title'].lower()
                desc_match = query_lower in event['desc'].lower()

                if title_match or desc_match:
                    matching.append(event)

            if matching:
                results[category] = matching

        return results

    def get_events_by_category(self, category: str) -> List[Dict]:
        """Получить события определённой категории."""
        return self.events.get(category, [])

    def get_all_events_paginated(self, page: int = 1, items_per_page: int = 5) -> Tuple[List[Dict], int, int]:
        """Получить все события с пагинацией."""
        all_events = []

        # Собираем все события со всех категорий с информацией о категории
        for category, events in self.events.items():
            for event in events:
                all_events.append({**event, 'category': category})

        # Сортируем по времени
        try:
            all_events.sort(
                key=lambda x: datetime.strptime(
                    x['time'].split()[-1] + ' ' + x['time'].split()[0],
                    '%Y.%m.%d %H:%M'
                )
            )
        except Exception:
            pass  # Если сортировка не удалась, не сортируем

        # Пагинация
        total_pages = (len(all_events) + items_per_page - 1) // items_per_page
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page

        return all_events[start_idx:end_idx], total_pages, len(all_events)

    def add_event(self, category: str, title: str, date: str, time: str, place: str, desc: str) -> Dict:
        """Добавить новое мероприятие."""
        new_event = {
            "id": str(self.event_counter),
            "title": title,
            "time": f"{time} {date}",
            "place": place,
            "desc": desc
        }

        if category not in self.events:
            self.events[category] = []

        self.events[category].append(new_event)
        self.event_counter += 1

        return new_event

    def get_event_by_id(self, category: str, event_id: str) -> Dict | None:
        """Получить событие по ID и категории."""
        events = self.events.get(category, [])
        return next((e for e in events if e["id"] == event_id), None)

    def get_event_by_id_only(self, event_id: str) -> Tuple[Dict | None, str]:
        """
        Получить событие только по ID, без знания категории.
        Возвращает кортеж (событие, категория) или (None, "").
        """
        for category, category_events in self.events.items():
            for event in category_events:
                if event["id"] == event_id:
                    return event, category
        return None, ""

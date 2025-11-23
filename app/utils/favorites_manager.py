"""
Менеджер для управления избранными событиями.
Хранит избранное в памяти во время сессии (без сохранения пользовательских данных).
"""

import logging
from typing import Dict, List, Tuple, Set

logger = logging.getLogger(__name__)


class FavoritesManager:
    """Менеджер для работы с избранными событиями в памяти."""

    def __init__(self):
        # Структура: {user_id: {event_id: (category, event_data)}}
        self.favorites: Dict[int, Dict[str, Tuple[str, dict]]] = {}

    def add_favorite(self, user_id: int, event_id: str, category: str, event_data: dict) -> bool:
        """Добавить событие в избранное."""
        if user_id not in self.favorites:
            self.favorites[user_id] = {}

        if event_id not in self.favorites[user_id]:
            self.favorites[user_id][event_id] = (category, event_data)
            logger.info(f"Добавлено в избранное: user_id={user_id}, event_id={event_id}")
            return True
        return False

    def remove_favorite(self, user_id: int, event_id: str) -> bool:
        """Удалить событие из избранного."""
        if user_id in self.favorites and event_id in self.favorites[user_id]:
            del self.favorites[user_id][event_id]
            
            # Удаляем пользователя если у него нет избранного
            if not self.favorites[user_id]:
                del self.favorites[user_id]
            
            logger.info(f"Удалено из избранного: user_id={user_id}, event_id={event_id}")
            return True
        return False

    def is_favorite(self, user_id: int, event_id: str) -> bool:
        """Проверить, находится ли событие в избранном."""
        return user_id in self.favorites and event_id in self.favorites[user_id]

    def get_favorites(self, user_id: int) -> List[Tuple[str, str, dict]]:
        """
        Получить все избранные события пользователя.
        Возвращает список кортежей (event_id, category, event_data).
        """
        if user_id not in self.favorites:
            return []

        result = []
        for event_id, (category, event_data) in self.favorites[user_id].items():
            result.append((event_id, category, event_data))
        
        return result

    def get_favorites_count(self, user_id: int) -> int:
        """Получить количество избранных событий."""
        if user_id not in self.favorites:
            return 0
        return len(self.favorites[user_id])

    def clear_favorites(self, user_id: int) -> bool:
        """Очистить все избранные события пользователя."""
        if user_id in self.favorites:
            del self.favorites[user_id]
            logger.info(f"Очищено избранное: user_id={user_id}")
            return True
        return False

    def toggle_favorite(self, user_id: int, event_id: str, category: str, event_data: dict) -> bool:
        """
        Переключить избранное (добавить или удалить).
        Возвращает True если добавлено, False если удалено.
        """
        if self.is_favorite(user_id, event_id):
            self.remove_favorite(user_id, event_id)
            return False
        else:
            self.add_favorite(user_id, event_id, category, event_data)
            return True

    def get_user_ids_with_favorites(self) -> Set[int]:
        """Получить список user_id у которых есть избранное."""
        return set(self.favorites.keys())

    def get_memory_usage_kb(self) -> float:
        """Получить примерное использование памяти в КБ."""
        import sys
        total_size = 0
        for user_favs in self.favorites.values():
            for event_id, (category, event_data) in user_favs.items():
                total_size += sys.getsizeof(event_id)
                total_size += sys.getsizeof(category)
                total_size += sys.getsizeof(event_data)
        return total_size / 1024


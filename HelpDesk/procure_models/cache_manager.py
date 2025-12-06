"""
Модуль для кэширования результатов анализа тендеров
"""
from typing import Dict, List, Optional, Any
import json
import hashlib
import os
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CacheManager:
    """Менеджер кэша для оптимизации производительности"""
    
    def __init__(self, cache_dir: str = "data/cache", ttl_hours: int = 24):
        """
        Инициализация менеджера кэша
        
        Args:
            cache_dir: Директория для хранения кэша
            ttl_hours: Время жизни кэша в часах
        """
        self.cache_dir = cache_dir
        self.ttl_hours = ttl_hours
        self._ensure_cache_dir()
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }
    
    def _ensure_cache_dir(self):
        """Создаёт директорию для кэша если не существует"""
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _generate_cache_key(self, data: str, operation: str = "analyze") -> str:
        """
        Генерирует ключ кэша на основе данных
        
        Args:
            data: Данные для хэширования
            operation: Тип операции
            
        Returns:
            Ключ кэша
        """
        # Создаём хэш из данных
        hash_obj = hashlib.md5(f"{operation}:{data}".encode('utf-8'))
        return f"{operation}_{hash_obj.hexdigest()}.json"
    
    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Получает данные из кэша
        
        Args:
            cache_key: Ключ кэша
            
        Returns:
            Данные из кэша или None если не найдено/истекло
        """
        cache_file = os.path.join(self.cache_dir, cache_key)
        
        if not os.path.exists(cache_file):
            self.cache_stats['misses'] += 1
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Проверяем TTL
            cached_time = datetime.fromisoformat(cache_data.get('timestamp', '2000-01-01'))
            if datetime.now() - cached_time > timedelta(hours=self.ttl_hours):
                # Кэш истёк
                os.remove(cache_file)
                self.cache_stats['misses'] += 1
                self.cache_stats['evictions'] += 1
                return None
            
            self.cache_stats['hits'] += 1
            return cache_data.get('data')
            
        except Exception as e:
            logger.error(f"Ошибка при чтении кэша: {e}")
            self.cache_stats['misses'] += 1
            return None
    
    def set(self, cache_key: str, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        """
        Сохраняет данные в кэш
        
        Args:
            cache_key: Ключ кэша
            data: Данные для кэширования
            metadata: Дополнительные метаданные
        """
        cache_file = os.path.join(self.cache_dir, cache_key)
        
        cache_entry = {
            'timestamp': datetime.now().isoformat(),
            'data': data,
            'metadata': metadata or {}
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_entry, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка при сохранении в кэш: {e}")
    
    def get_or_compute(self, cache_key: str, compute_func, *args, **kwargs) -> Any:
        """
        Получает из кэша или вычисляет и кэширует
        
        Args:
            cache_key: Ключ кэша
            compute_func: Функция для вычисления если кэш пуст
            *args, **kwargs: Аргументы для compute_func
            
        Returns:
            Результат из кэша или вычисленный результат
        """
        cached = self.get(cache_key)
        if cached is not None:
            return cached
        
        # Вычисляем
        result = compute_func(*args, **kwargs)
        
        # Кэшируем
        self.set(cache_key, result)
        
        return result
    
    def invalidate(self, cache_key: Optional[str] = None, pattern: Optional[str] = None):
        """
        Удаляет данные из кэша
        
        Args:
            cache_key: Конкретный ключ для удаления
            pattern: Паттерн для удаления (например, "analyze_*")
        """
        if cache_key:
            cache_file = os.path.join(self.cache_dir, cache_key)
            if os.path.exists(cache_file):
                os.remove(cache_file)
                self.cache_stats['evictions'] += 1
        elif pattern:
            import fnmatch
            for filename in os.listdir(self.cache_dir):
                if fnmatch.fnmatch(filename, pattern):
                    os.remove(os.path.join(self.cache_dir, filename))
                    self.cache_stats['evictions'] += 1
    
    def clear_expired(self):
        """Удаляет все истёкшие записи из кэша"""
        now = datetime.now()
        expired_count = 0
        
        for filename in os.listdir(self.cache_dir):
            if not filename.endswith('.json'):
                continue
            
            cache_file = os.path.join(self.cache_dir, filename)
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                cached_time = datetime.fromisoformat(cache_data.get('timestamp', '2000-01-01'))
                if now - cached_time > timedelta(hours=self.ttl_hours):
                    os.remove(cache_file)
                    expired_count += 1
            except:
                pass
        
        if expired_count > 0:
            logger.info(f"Удалено {expired_count} истёкших записей из кэша")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Получает статистику кэша
        
        Returns:
            Словарь со статистикой
        """
        total_files = len([f for f in os.listdir(self.cache_dir) if f.endswith('.json')])
        hit_rate = 0
        if self.cache_stats['hits'] + self.cache_stats['misses'] > 0:
            hit_rate = self.cache_stats['hits'] / (self.cache_stats['hits'] + self.cache_stats['misses'])
        
        return {
            'hits': self.cache_stats['hits'],
            'misses': self.cache_stats['misses'],
            'evictions': self.cache_stats['evictions'],
            'hit_rate': round(hit_rate * 100, 2),
            'total_cached_items': total_files
        }
    
    def clear_all(self):
        """Очищает весь кэш"""
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.json'):
                os.remove(os.path.join(self.cache_dir, filename))
        self.cache_stats['evictions'] += len(os.listdir(self.cache_dir))
        logger.info("Весь кэш очищен")


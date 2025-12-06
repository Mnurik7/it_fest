"""
Модуль для сбора данных о тендерах из открытых источников
"""
from typing import Dict, List, Optional, Any
import json
from datetime import datetime
import time
import re
import logging
import os

# Опциональные импорты
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logging.warning("requests не установлен. Парсинг веб-страниц недоступен.")

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False
    logging.warning("beautifulsoup4 не установлен. Парсинг HTML недоступен.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataCollector:
    """Сборщик данных о тендерах из открытых источников"""
    
    def __init__(self):
        self.sources = {
            'goszakupki_kz': {
                'name': 'Госзакупки Казахстана',
                'base_url': 'https://goszakupki.gov.kz',
                'enabled': False  # Требует настройки API
            },
            'zakupki_kz': {
                'name': 'Zakupki.kz',
                'base_url': 'https://zakupki.kz',
                'enabled': False
            },
            'synthetic': {
                'name': 'Синтетические данные',
                'enabled': True
            }
        }
        self.collected_tenders = []
    
    def collect_from_source(self, source_name: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Собирает данные о тендерах из указанного источника
        
        Args:
            source_name: Название источника
            filters: Фильтры для поиска (категория, дата, бюджет и т.д.)
            
        Returns:
            Список найденных тендеров
        """
        if source_name not in self.sources:
            logger.error(f"Источник {source_name} не найден")
            return []
        
        source = self.sources[source_name]
        if not source.get('enabled', False):
            logger.warning(f"Источник {source_name} отключен")
            return []
        
        if source_name == 'synthetic':
            return self._generate_synthetic_tenders(filters)
        elif source_name == 'goszakupki_kz':
            return self._collect_from_goszakupki(filters)
        elif source_name == 'zakupki_kz':
            return self._collect_from_zakupki(filters)
        else:
            return []
    
    def _generate_synthetic_tenders(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Генерирует синтетические данные о тендерах для тестирования"""
        categories = [
            'IT и программное обеспечение',
            'Офисное оборудование',
            'Строительные материалы',
            'Медицинское оборудование',
            'Транспорт и логистика',
            'Консалтинг и услуги',
            'Мебель и интерьер',
            'Безопасность и охрана'
        ]
        
        customers = [
            'ТОО "КазОфисСнаб"',
            'АО "Национальная компания"',
            'ТОО "СтройМатериалы"',
            'ГУ "Государственное учреждение"',
            'ТОО "ТехноСервис"'
        ]
        
        tenders = []
        count = filters.get('count', 10) if filters else 10
        
        for i in range(count):
            import random
            category = random.choice(categories)
            customer = random.choice(customers)
            budget = random.randint(100000, 5000000)
            
            tender = {
                'tender_id': f'SYNTH-{datetime.now().strftime("%Y%m%d")}-{i+1:04d}',
                'source': 'synthetic',
                'title': f'Закупка {category.lower()}',
                'category': category,
                'customer': {
                    'name': customer,
                    'type': 'компания' if 'ТОО' in customer or 'АО' in customer else 'госструктура'
                },
                'budget': {
                    'amount': str(budget),
                    'currency': 'KZT'
                },
                'publication_date': (datetime.now()).strftime('%Y-%m-%d'),
                'application_end': (datetime.now()).strftime('%Y-%m-%d'),
                'description': f'Закупка {category.lower()} для нужд организации',
                'status': 'active',
                'collected_at': datetime.now().isoformat()
            }
            tenders.append(tender)
        
        self.collected_tenders.extend(tenders)
        return tenders
    
    def _collect_from_goszakupki(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Собирает данные с портала госзакупок Казахстана
        Требует настройки API или веб-скрапинга
        """
        # Проверяем наличие API ключа
        api_key = os.getenv('GOSZAKUPKI_API_KEY', '')
        api_url = os.getenv('GOSZAKUPKI_API_URL', 'https://goszakupki.gov.kz/api/v1')
        
        if not api_key and REQUESTS_AVAILABLE:
            # Пытаемся парсить через веб-скрапинг
            try:
                base_url = 'https://goszakupki.gov.kz'
                # Парсим главную страницу с тендерами
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(f"{base_url}/tenders", headers=headers, timeout=10)
                
                if response.status_code == 200 and BEAUTIFULSOUP_AVAILABLE:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    # Извлекаем информацию о тендерах (требует знания структуры сайта)
                    # Это базовая реализация, требует доработки под конкретную структуру
                    tenders = []
                    # TODO: Реализовать парсинг конкретных элементов страницы
                    logger.info("Парсинг goszakupki.gov.kz через веб-скрапинг")
                    return tenders
            except Exception as e:
                logger.error(f"Ошибка при парсинге goszakupki.gov.kz: {e}")
        
        if api_key and REQUESTS_AVAILABLE:
            # Используем API если доступен
            try:
                headers = {'Authorization': f'Bearer {api_key}'}
                params = filters or {}
                response = requests.get(f"{api_url}/tenders", headers=headers, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    tenders = data.get('tenders', [])
                    logger.info(f"Получено {len(tenders)} тендеров через API goszakupki")
                    return tenders
            except Exception as e:
                logger.error(f"Ошибка при запросе к API goszakupki: {e}")
        
        logger.warning("Сбор с goszakupki.gov.kz требует настройки API ключа или доступа к сайту")
        return []
    
    def _collect_from_zakupki(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Собирает данные с коммерческой площадки zakupki.kz
        """
        if not REQUESTS_AVAILABLE:
            logger.warning("requests не установлен для парсинга zakupki.kz")
            return []
        
        try:
            base_url = 'https://zakupki.kz'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Парсим страницу с тендерами
            response = requests.get(f"{base_url}/tenders", headers=headers, timeout=10)
            
            if response.status_code == 200 and BEAUTIFULSOUP_AVAILABLE:
                soup = BeautifulSoup(response.content, 'html.parser')
                tenders = []
                # TODO: Реализовать парсинг конкретных элементов страницы zakupki.kz
                # Это требует изучения структуры сайта
                logger.info("Парсинг zakupki.kz через веб-скрапинг")
                return tenders
        except Exception as e:
            logger.error(f"Ошибка при парсинге zakupki.kz: {e}")
        
        logger.warning("Сбор с zakupki.kz требует настройки")
        return []
    
    def parse_web_page(self, url: str) -> Optional[str]:
        """
        Парсит веб-страницу и извлекает текст тендера
        
        Args:
            url: URL страницы с тендером
            
        Returns:
            Текст тендера или None
        """
        if not REQUESTS_AVAILABLE:
            logger.error("requests не установлен. Установите: pip install requests")
            return None
        
        if not BEAUTIFULSOUP_AVAILABLE:
            logger.error("beautifulsoup4 не установлен. Установите: pip install beautifulsoup4")
            return None
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Удаляем скрипты и стили
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Извлекаем текст
            text = soup.get_text()
            
            # Очищаем текст
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            logger.error(f"Ошибка при парсинге страницы {url}: {e}")
            return None
    
    def monitor_new_tenders(self, source_name: str, interval: int = 3600, callback=None) -> None:
        """
        Мониторит новые тендеры на указанном источнике
        
        Args:
            source_name: Название источника
            interval: Интервал проверки в секундах
            callback: Функция обратного вызова при обнаружении новых тендеров
        """
        logger.info(f"Запуск мониторинга источника {source_name} с интервалом {interval} сек")
        
        last_tenders = set()
        
        while True:
            try:
                new_tenders = self.collect_from_source(source_name)
                new_tender_ids = {t.get('tender_id') for t in new_tenders}
                
                # Находим новые тендеры
                truly_new = new_tender_ids - last_tenders
                if truly_new:
                    new_tenders_list = [t for t in new_tenders if t.get('tender_id') in truly_new]
                    logger.info(f"Обнаружено {len(new_tenders_list)} новых тендеров")
                    
                    if callback:
                        callback(new_tenders_list)
                
                last_tenders = new_tender_ids
                time.sleep(interval)
            except KeyboardInterrupt:
                logger.info("Мониторинг остановлен")
                break
            except Exception as e:
                logger.error(f"Ошибка при мониторинге: {e}")
                time.sleep(interval)
    
    def get_collected_tenders(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Возвращает собранные тендеры с фильтрацией
        
        Args:
            filters: Фильтры (source, date_from, date_to, category, min_budget, max_budget)
            
        Returns:
            Отфильтрованный список тендеров
        """
        tenders = self.collected_tenders.copy()
        
        if not filters:
            return tenders
        
        if 'source' in filters:
            tenders = [t for t in tenders if t.get('source') == filters['source']]
        
        if 'date_from' in filters:
            date_from = datetime.fromisoformat(filters['date_from']) if isinstance(filters['date_from'], str) else filters['date_from']
            tenders = [t for t in tenders if datetime.fromisoformat(t.get('collected_at', '2000-01-01')) >= date_from]
        
        if 'date_to' in filters:
            date_to = datetime.fromisoformat(filters['date_to']) if isinstance(filters['date_to'], str) else filters['date_to']
            tenders = [t for t in tenders if datetime.fromisoformat(t.get('collected_at', '2100-01-01')) <= date_to]
        
        if 'category' in filters:
            tenders = [t for t in tenders if filters['category'].lower() in t.get('category', '').lower()]
        
        if 'min_budget' in filters:
            tenders = [t for t in tenders if float(t.get('budget', {}).get('amount', 0)) >= filters['min_budget']]
        
        if 'max_budget' in filters:
            tenders = [t for t in tenders if float(t.get('budget', {}).get('amount', float('inf'))) <= filters['max_budget']]
        
        return tenders
    
    def add_custom_source(self, source_name: str, source_config: Dict[str, Any]) -> None:
        """
        Добавляет пользовательский источник данных
        
        Args:
            source_name: Название источника
            source_config: Конфигурация источника
        """
        self.sources[source_name] = source_config
        logger.info(f"Добавлен источник: {source_name}")


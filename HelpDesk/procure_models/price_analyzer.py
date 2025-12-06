"""
Модуль для анализа цен и сравнения с рыночными
"""
from typing import Dict, List, Optional, Any
import json
from datetime import datetime
import statistics
import re
import logging
import os

# Опциональные импорты для внешних источников
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logging.warning("requests не установлен. Интеграция с внешними источниками цен недоступна.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PriceAnalyzer:
    """Анализатор цен для выявления аномалий и сравнения с рынком"""
    
    def __init__(self):
        # База рыночных цен по категориям
        self.market_prices = {
            'IT и программное обеспечение': {
                'avg_price_per_unit': 50000,
                'price_range': (20000, 150000),
                'currency': 'KZT'
            },
            'Офисное оборудование': {
                'avg_price_per_unit': 15000,
                'price_range': (5000, 50000),
                'currency': 'KZT'
            },
            'Строительные материалы': {
                'avg_price_per_unit': 3000,
                'price_range': (1000, 10000),
                'currency': 'KZT'
            },
            'Медицинское оборудование': {
                'avg_price_per_unit': 500000,
                'price_range': (100000, 2000000),
                'currency': 'KZT'
            },
            'Транспорт и логистика': {
                'avg_price_per_unit': 200000,
                'price_range': (50000, 1000000),
                'currency': 'KZT'
            },
            'Консалтинг и услуги': {
                'avg_price_per_unit': 100000,
                'price_range': (30000, 500000),
                'currency': 'KZT'
            },
            'Мебель и интерьер': {
                'avg_price_per_unit': 25000,
                'price_range': (5000, 100000),
                'currency': 'KZT'
            },
            'Безопасность и охрана': {
                'avg_price_per_unit': 80000,
                'price_range': (20000, 300000),
                'currency': 'KZT'
            }
        }
        
        # История цен для анализа трендов
        self.price_history = []
    
    def analyze_price(self, tender_params: Dict[str, Any], market_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Анализирует цену тендера и сравнивает с рыночными
        
        Args:
            tender_params: Параметры тендера
            market_data: Дополнительные рыночные данные
            
        Returns:
            Анализ цены с выявленными аномалиями
        """
        budget = tender_params.get('budget', {})
        amount = budget.get('amount', '0')
        currency = budget.get('currency', 'KZT')
        
        # Парсим сумму
        try:
            # Убираем пробелы и запятые
            amount_str = str(amount).replace(' ', '').replace(',', '')
            tender_amount = float(amount_str)
        except (ValueError, TypeError):
            tender_amount = 0
        
        # Определяем категорию
        subject = tender_params.get('subject', {})
        description = subject.get('description', '').lower()
        category = self._detect_category(description)
        
        # Получаем рыночные данные
        if market_data:
            market_info = market_data
        else:
            # Пытаемся получить из внешних источников
            external_market_data = self._fetch_external_market_data(category)
            if external_market_data:
                market_info = external_market_data
            else:
                market_info = self.market_prices.get(category, {
                    'avg_price_per_unit': 50000,
                    'price_range': (10000, 200000),
                    'currency': 'KZT'
                })
        
        # Анализируем количество
        quantity_str = subject.get('quantity', '1')
        quantity = self._parse_quantity(quantity_str)
        
        # Рассчитываем цену за единицу
        price_per_unit = tender_amount / quantity if quantity > 0 else tender_amount
        
        # Сравниваем с рыночными ценами
        avg_market_price = market_info.get('avg_price_per_unit', price_per_unit)
        price_range = market_info.get('price_range', (price_per_unit * 0.5, price_per_unit * 2))
        
        # Вычисляем отклонение
        deviation_percent = ((price_per_unit - avg_market_price) / avg_market_price * 100) if avg_market_price > 0 else 0
        
        # Определяем аномалии
        anomalies = []
        risk_level = 'низкий'
        
        if price_per_unit > price_range[1]:
            anomalies.append({
                'type': 'завышенная_цена',
                'severity': 'высокая',
                'description': f'Цена за единицу ({price_per_unit:,.0f} {currency}) превышает максимальную рыночную ({price_range[1]:,.0f} {currency})',
                'deviation_percent': round(deviation_percent, 2)
            })
            risk_level = 'высокий'
        elif price_per_unit < price_range[0]:
            anomalies.append({
                'type': 'заниженная_цена',
                'severity': 'средняя',
                'description': f'Цена за единицу ({price_per_unit:,.0f} {currency}) ниже минимальной рыночной ({price_range[0]:,.0f} {currency})',
                'deviation_percent': round(deviation_percent, 2)
            })
            risk_level = 'средний'
        
        if abs(deviation_percent) > 50:
            anomalies.append({
                'type': 'значительное_отклонение',
                'severity': 'высокая',
                'description': f'Цена отклоняется от среднерыночной на {abs(deviation_percent):.1f}%',
                'deviation_percent': round(deviation_percent, 2)
            })
            if risk_level == 'низкий':
                risk_level = 'средний'
        
        # Сохраняем в историю
        self.price_history.append({
            'tender_id': tender_params.get('metadata', {}).get('tender_id', 'unknown'),
            'category': category,
            'price_per_unit': price_per_unit,
            'total_amount': tender_amount,
            'quantity': quantity,
            'currency': currency,
            'date': datetime.now().isoformat(),
            'deviation_percent': round(deviation_percent, 2)
        })
        
        return {
            'tender_amount': tender_amount,
            'quantity': quantity,
            'price_per_unit': round(price_per_unit, 2),
            'currency': currency,
            'category': category,
            'market_comparison': {
                'avg_market_price': avg_market_price,
                'market_range': price_range,
                'deviation_percent': round(deviation_percent, 2),
                'is_within_range': price_range[0] <= price_per_unit <= price_range[1]
            },
            'anomalies': anomalies,
            'risk_level': risk_level,
            'recommendations': self._generate_price_recommendations(anomalies, deviation_percent),
            'analysis_date': datetime.now().isoformat()
        }
    
    def _detect_category(self, description: str) -> str:
        """Определяет категорию по описанию"""
        category_keywords = {
            'IT и программное обеспечение': ['программ', 'софт', 'it', 'компьютер', 'система', 'приложение'],
            'Офисное оборудование': ['офис', 'принтер', 'сканер', 'копир', 'ручка', 'бумага'],
            'Строительные материалы': ['строитель', 'цемент', 'кирпич', 'бетон', 'материал'],
            'Медицинское оборудование': ['медицин', 'оборудование', 'аппарат', 'диагностик'],
            'Транспорт и логистика': ['транспорт', 'автомобиль', 'доставка', 'логистик'],
            'Консалтинг и услуги': ['консалтинг', 'услуг', 'консультация', 'поддержка'],
            'Мебель и интерьер': ['мебель', 'стол', 'стул', 'интерьер', 'офисная мебель'],
            'Безопасность и охрана': ['безопасность', 'охрана', 'система безопасности', 'видеонаблюдение']
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in description for keyword in keywords):
                return category
        
        return 'Другое'
    
    def _parse_quantity(self, quantity_str: str) -> float:
        """Парсит количество из строки"""
        try:
            # Извлекаем число из строки
            numbers = re.findall(r'\d+[\.,]?\d*', str(quantity_str))
            if numbers:
                return float(numbers[0].replace(',', '.'))
        except:
            pass
        return 1.0
    
    def _fetch_external_market_data(self, category: str) -> Optional[Dict[str, Any]]:
        """
        Получает рыночные данные из внешних источников
        
        Args:
            category: Категория товара/услуги
            
        Returns:
            Рыночные данные или None
        """
        if not REQUESTS_AVAILABLE:
            return None
        
        # Проверяем наличие API ключа для внешних источников
        price_api_key = os.getenv('PRICE_API_KEY', '')
        price_api_url = os.getenv('PRICE_API_URL', '')
        
        if price_api_key and price_api_url:
            try:
                headers = {'Authorization': f'Bearer {price_api_key}'}
                params = {'category': category}
                response = requests.get(f"{price_api_url}/market-prices", headers=headers, params=params, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'avg_price_per_unit': data.get('average_price', 0),
                        'price_range': (data.get('min_price', 0), data.get('max_price', 0)),
                        'currency': data.get('currency', 'KZT'),
                        'source': 'external_api'
                    }
            except Exception as e:
                logger.debug(f"Не удалось получить данные из внешнего API: {e}")
        
        # Можно добавить другие источники (скрапинг, публичные API и т.д.)
        return None
    
    def _generate_price_recommendations(self, anomalies: List[Dict[str, Any]], deviation_percent: float) -> List[str]:
        """Генерирует рекомендации на основе анализа"""
        recommendations = []
        
        if not anomalies:
            recommendations.append("Цена находится в пределах рыночного диапазона")
            return recommendations
        
        for anomaly in anomalies:
            if anomaly['type'] == 'завышенная_цена':
                recommendations.append("⚠️ Цена значительно превышает рыночную. Рекомендуется проверить обоснованность цены и запросить детализацию.")
                recommendations.append("Проверьте наличие скрытых расходов или дополнительных услуг, которые могут оправдать высокую цену.")
            elif anomaly['type'] == 'заниженная_цена':
                recommendations.append("⚠️ Цена ниже рыночной. Возможны риски: некачественное исполнение, скрытые доплаты, или недобросовестная конкуренция.")
            elif anomaly['type'] == 'значительное_отклонение':
                recommendations.append(f"⚠️ Значительное отклонение от среднерыночной цены ({abs(deviation_percent):.1f}%). Требуется дополнительный анализ.")
        
        recommendations.append("Рекомендуется провести сравнительный анализ с аналогичными тендерами.")
        
        return recommendations
    
    def compare_with_similar_tenders(self, tender_params: Dict[str, Any], similar_tenders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Сравнивает цену тендера с похожими тендерами
        
        Args:
            tender_params: Параметры текущего тендера
            similar_tenders: Список похожих тендеров
            
        Returns:
            Сравнительный анализ
        """
        if not similar_tenders:
            return {
                'comparison_available': False,
                'message': 'Нет данных для сравнения'
            }
        
        # Извлекаем цену текущего тендера
        current_amount = float(str(tender_params.get('budget', {}).get('amount', '0')).replace(' ', '').replace(',', ''))
        
        # Извлекаем цены похожих тендеров
        similar_prices = []
        for tender in similar_tenders:
            try:
                amount = float(str(tender.get('budget', {}).get('amount', '0')).replace(' ', '').replace(',', ''))
                if amount > 0:
                    similar_prices.append(amount)
            except:
                continue
        
        if not similar_prices:
            return {
                'comparison_available': False,
                'message': 'Не удалось извлечь цены из похожих тендеров'
            }
        
        # Статистика
        avg_price = statistics.mean(similar_prices)
        median_price = statistics.median(similar_prices)
        min_price = min(similar_prices)
        max_price = max(similar_prices)
        
        deviation_from_avg = ((current_amount - avg_price) / avg_price * 100) if avg_price > 0 else 0
        deviation_from_median = ((current_amount - median_price) / median_price * 100) if median_price > 0 else 0
        
        return {
            'comparison_available': True,
            'current_price': current_amount,
            'similar_tenders_count': len(similar_prices),
            'statistics': {
                'average': round(avg_price, 2),
                'median': round(median_price, 2),
                'min': round(min_price, 2),
                'max': round(max_price, 2)
            },
            'deviation': {
                'from_average_percent': round(deviation_from_avg, 2),
                'from_median_percent': round(deviation_from_median, 2)
            },
            'position': {
                'percentile': self._calculate_percentile(current_amount, similar_prices),
                'is_outlier': current_amount < min_price * 0.7 or current_amount > max_price * 1.3
            }
        }
    
    def _calculate_percentile(self, value: float, values: List[float]) -> float:
        """Вычисляет процентиль значения в списке"""
        sorted_values = sorted(values)
        count = len(sorted_values)
        below = sum(1 for v in sorted_values if v < value)
        return (below / count * 100) if count > 0 else 50
    
    def update_market_prices(self, category: str, price_data: Dict[str, Any]) -> None:
        """
        Обновляет рыночные цены для категории
        
        Args:
            category: Категория товара/услуги
            price_data: Данные о ценах
        """
        self.market_prices[category] = price_data
        logger.info(f"Обновлены рыночные цены для категории: {category}")
    
    def get_price_statistics(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Возвращает статистику по ценам
        
        Args:
            category: Категория (если None - по всем категориям)
            
        Returns:
            Статистика цен
        """
        if category:
            history = [h for h in self.price_history if h.get('category') == category]
        else:
            history = self.price_history
        
        if not history:
            return {
                'total_records': 0,
                'message': 'Нет данных для статистики'
            }
        
        prices = [h['price_per_unit'] for h in history]
        
        return {
            'total_records': len(history),
            'category': category or 'Все категории',
            'statistics': {
                'average': round(statistics.mean(prices), 2),
                'median': round(statistics.median(prices), 2),
                'min': round(min(prices), 2),
                'max': round(max(prices), 2),
                'std_dev': round(statistics.stdev(prices) if len(prices) > 1 else 0, 2)
            },
            'date_range': {
                'from': min(h['date'] for h in history),
                'to': max(h['date'] for h in history)
            }
        }


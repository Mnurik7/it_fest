"""
Модуль для отслеживания метрик производительности и качества
"""
from typing import Dict, List, Optional, Any
import json
from datetime import datetime, timedelta
import os
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetricsTracker:
    """Трекер метрик для оценки производительности системы"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.metrics_file = os.path.join(data_dir, "procure_metrics.json")
        self._ensure_data_dir()
        self.metrics = self._load_metrics()
        
        # Метрики в памяти для текущей сессии
        self.session_metrics = {
            'extractions': [],
            'supplier_matches': [],
            'risk_analyses': [],
            'reports_generated': [],
            'errors': []
        }
    
    def _ensure_data_dir(self):
        """Создаёт директорию для данных если не существует"""
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _load_metrics(self) -> Dict[str, Any]:
        """Загружает метрики из файла"""
        if os.path.exists(self.metrics_file):
            try:
                with open(self.metrics_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            'extraction_accuracy': [],
            'risk_detection_accuracy': [],
            'processing_times': [],
            'tenders_processed': 0,
            'suppliers_matched': 0,
            'reports_generated': 0,
            'errors_count': 0,
            'user_feedback': [],
            'daily_stats': {}
        }
    
    def _save_metrics(self):
        """Сохраняет метрики в файл"""
        try:
            with open(self.metrics_file, 'w', encoding='utf-8') as f:
                json.dump(self.metrics, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка при сохранении метрик: {e}")
    
    def track_extraction(self, tender_params: Dict[str, Any], completeness: Dict[str, Any], processing_time: float):
        """
        Отслеживает извлечение параметров тендера
        
        Args:
            tender_params: Извлечённые параметры
            completeness: Анализ полноты
            processing_time: Время обработки в секундах
        """
        extraction_metric = {
            'timestamp': datetime.now().isoformat(),
            'completeness_percentage': completeness.get('completeness_percentage', 0),
            'processing_time': processing_time,
            'fields_extracted': self._count_extracted_fields(tender_params),
            'status': completeness.get('status', 'unknown')
        }
        
        self.session_metrics['extractions'].append(extraction_metric)
        self.metrics['tenders_processed'] += 1
        self.metrics['processing_times'].append(processing_time)
        
        # Сохраняем точность извлечения
        self.metrics['extraction_accuracy'].append(completeness.get('completeness_percentage', 0))
        
        self._update_daily_stats('extractions', 1)
        self._save_metrics()
    
    def track_supplier_match(self, suppliers_count: int, processing_time: float):
        """
        Отслеживает подбор поставщиков
        
        Args:
            suppliers_count: Количество найденных поставщиков
            processing_time: Время обработки в секундах
        """
        match_metric = {
            'timestamp': datetime.now().isoformat(),
            'suppliers_count': suppliers_count,
            'processing_time': processing_time
        }
        
        self.session_metrics['supplier_matches'].append(match_metric)
        self.metrics['suppliers_matched'] += suppliers_count
        self._update_daily_stats('supplier_matches', 1)
        self._save_metrics()
    
    def track_risk_analysis(self, risk_analysis: Dict[str, Any], processing_time: float):
        """
        Отслеживает анализ рисков
        
        Args:
            risk_analysis: Результаты анализа рисков
            processing_time: Время обработки в секундах
        """
        risk_metric = {
            'timestamp': datetime.now().isoformat(),
            'risk_level': risk_analysis.get('overall_risk_level', 'unknown'),
            'risk_score': risk_analysis.get('risk_score', 0),
            'risks_count': len(risk_analysis.get('risks', [])),
            'processing_time': processing_time
        }
        
        self.session_metrics['risk_analyses'].append(risk_metric)
        self._update_daily_stats('risk_analyses', 1)
        self._save_metrics()
    
    def track_report_generation(self, processing_time: float):
        """
        Отслеживает генерацию отчёта
        
        Args:
            processing_time: Время обработки в секундах
        """
        report_metric = {
            'timestamp': datetime.now().isoformat(),
            'processing_time': processing_time
        }
        
        self.session_metrics['reports_generated'].append(report_metric)
        self.metrics['reports_generated'] += 1
        self._update_daily_stats('reports_generated', 1)
        self._save_metrics()
    
    def track_error(self, error_type: str, error_message: str):
        """
        Отслеживает ошибки
        
        Args:
            error_type: Тип ошибки
            error_message: Сообщение об ошибке
        """
        error_metric = {
            'timestamp': datetime.now().isoformat(),
            'error_type': error_type,
            'error_message': error_message
        }
        
        self.session_metrics['errors'].append(error_metric)
        self.metrics['errors_count'] += 1
        self._update_daily_stats('errors', 1)
        self._save_metrics()
    
    def add_user_feedback(self, feedback_type: str, feedback_data: Dict[str, Any]):
        """
        Добавляет обратную связь от пользователя
        
        Args:
            feedback_type: Тип обратной связи (accuracy, usefulness, etc.)
            feedback_data: Данные обратной связи
        """
        feedback = {
            'timestamp': datetime.now().isoformat(),
            'type': feedback_type,
            'data': feedback_data
        }
        
        self.metrics['user_feedback'].append(feedback)
        self._save_metrics()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Возвращает метрики производительности"""
        extraction_accuracy = self.metrics.get('extraction_accuracy', [])
        processing_times = self.metrics.get('processing_times', [])
        
        avg_accuracy = sum(extraction_accuracy) / len(extraction_accuracy) if extraction_accuracy else 0
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        return {
            'extraction_accuracy': {
                'average': round(avg_accuracy, 2),
                'min': round(min(extraction_accuracy), 2) if extraction_accuracy else 0,
                'max': round(max(extraction_accuracy), 2) if extraction_accuracy else 0,
                'target': 90.0,
                'meets_target': avg_accuracy >= 90.0
            },
            'processing_time': {
                'average_seconds': round(avg_processing_time, 2),
                'min_seconds': round(min(processing_times), 2) if processing_times else 0,
                'max_seconds': round(max(processing_times), 2) if processing_times else 0
            },
            'total_operations': {
                'tenders_processed': self.metrics.get('tenders_processed', 0),
                'suppliers_matched': self.metrics.get('suppliers_matched', 0),
                'reports_generated': self.metrics.get('reports_generated', 0),
                'errors_count': self.metrics.get('errors_count', 0)
            },
            'success_rate': self._calculate_success_rate()
        }
    
    def get_risk_detection_metrics(self) -> Dict[str, Any]:
        """Возвращает метрики обнаружения рисков"""
        risk_analyses = self.session_metrics.get('risk_analyses', [])
        
        if not risk_analyses:
            return {
                'total_analyses': 0,
                'message': 'Нет данных для анализа'
            }
        
        risk_levels = defaultdict(int)
        high_risk_count = 0
        
        for analysis in risk_analyses:
            risk_level = analysis.get('risk_level', 'unknown')
            risk_levels[risk_level] += 1
            if risk_level in ['высокий', 'критический']:
                high_risk_count += 1
        
        return {
            'total_analyses': len(risk_analyses),
            'risk_level_distribution': dict(risk_levels),
            'high_risk_detected': high_risk_count,
            'high_risk_percentage': round(high_risk_count / len(risk_analyses) * 100, 2) if risk_analyses else 0
        }
    
    def get_usability_metrics(self) -> Dict[str, Any]:
        """
        Возвращает метрики удобства использования
        Completion rate = доля запросов, завершившихся формированием отчёта или списком релевантных поставщиков
        """
        # Подсчитываем все запросы (извлечение, подбор поставщиков, анализ рисков)
        total_requests = (
            len(self.session_metrics['extractions']) +
            len(self.session_metrics['supplier_matches']) +
            len(self.session_metrics['risk_analyses'])
        )
        
        # Успешные завершения: отчёты ИЛИ успешный подбор поставщиков
        reports_generated = len(self.session_metrics['reports_generated'])
        successful_supplier_matches = len([m for m in self.session_metrics['supplier_matches'] if m.get('success', False)])
        
        # Completion = отчёты + успешные подборы поставщиков
        successful_completions = reports_generated + successful_supplier_matches
        
        completion_rate = (successful_completions / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'total_requests': total_requests,
            'reports_generated': reports_generated,
            'successful_supplier_matches': successful_supplier_matches,
            'successful_completions': successful_completions,
            'completion_rate_percent': round(completion_rate, 2),
            'target_completion_rate': 80.0,
            'meets_target': completion_rate >= 80.0,
            'breakdown': {
                'reports_percentage': round(reports_generated / total_requests * 100, 2) if total_requests > 0 else 0,
                'suppliers_percentage': round(successful_supplier_matches / total_requests * 100, 2) if total_requests > 0 else 0
            }
        }
    
    def get_daily_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Возвращает статистику за последние N дней"""
        daily_stats = self.metrics.get('daily_stats', {})
        today = datetime.now().date()
        
        stats = {}
        for i in range(days):
            date = today - timedelta(days=i)
            date_str = date.isoformat()
            stats[date_str] = daily_stats.get(date_str, {
                'extractions': 0,
                'supplier_matches': 0,
                'risk_analyses': 0,
                'reports_generated': 0,
                'errors': 0
            })
        
        return stats
    
    def _count_extracted_fields(self, tender_params: Dict[str, Any]) -> int:
        """Подсчитывает количество извлечённых полей"""
        count = 0
        
        def count_fields(obj, depth=0):
            nonlocal count
            if depth > 5:  # Защита от бесконечной рекурсии
                return
            
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if value and value != "" and value != [] and value != {}:
                        count += 1
                        if isinstance(value, (dict, list)):
                            count_fields(value, depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    count_fields(item, depth + 1)
        
        count_fields(tender_params)
        return count
    
    def _calculate_success_rate(self) -> float:
        """Вычисляет процент успешных операций"""
        total = self.metrics.get('tenders_processed', 0)
        errors = self.metrics.get('errors_count', 0)
        
        if total == 0:
            return 100.0
        
        success_rate = ((total - errors) / total) * 100
        return round(success_rate, 2)
    
    def _update_daily_stats(self, stat_type: str, value: int):
        """Обновляет дневную статистику"""
        today = datetime.now().date().isoformat()
        daily_stats = self.metrics.get('daily_stats', {})
        
        if today not in daily_stats:
            daily_stats[today] = {
                'extractions': 0,
                'supplier_matches': 0,
                'risk_analyses': 0,
                'reports_generated': 0,
                'errors': 0
            }
        
        daily_stats[today][stat_type] = daily_stats[today].get(stat_type, 0) + value
        self.metrics['daily_stats'] = daily_stats
    
    def reset_session_metrics(self):
        """Сбрасывает метрики текущей сессии"""
        self.session_metrics = {
            'extractions': [],
            'supplier_matches': [],
            'risk_analyses': [],
            'reports_generated': [],
            'errors': []
        }


"""
Модуль для отслеживания метрик производительности, бизнес-эффективности и удобства использования
"""
import json
import os
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict


class MetricsTracker:
    """Трекер метрик для AI Business Analyst"""
    
    def __init__(self, metrics_file: str = "data/business_analyst_metrics.json"):
        """
        Инициализация трекера метрик
        
        Args:
            metrics_file: Путь к файлу для сохранения метрик
        """
        self.metrics_file = metrics_file
        self.metrics = self._load_metrics()
        
    def _load_metrics(self) -> Dict:
        """Загрузить метрики из файла"""
        if os.path.exists(self.metrics_file):
            try:
                with open(self.metrics_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # Инициализация структуры метрик
        return {
            'performance': {
                'brd_generation_times': [],
                'total_operations': 0,
                'sla_violations': 0
            },
            'business': {
                'analyst_time_saved': 0,  # в часах
                'documents_generated': 0,
                'automation_rate': 0.0
            },
            'usability': {
                'completed_dialogs': 0,
                'failed_dialogs': 0,
                'dialogs_with_help': 0,
                'dialogs_without_help': 0,
                'average_dialog_duration': 0.0
            },
            'daily_stats': defaultdict(lambda: {
                'operations': 0,
                'brd_count': 0,
                'completed_dialogs': 0,
                'avg_time': 0.0
            })
        }
    
    def _save_metrics(self):
        """Сохранить метрики в файл"""
        os.makedirs(os.path.dirname(self.metrics_file), exist_ok=True)
        
        # Преобразуем defaultdict в обычный dict для JSON
        metrics_to_save = json.loads(json.dumps(self.metrics))
        
        with open(self.metrics_file, 'w', encoding='utf-8') as f:
            json.dump(metrics_to_save, f, indent=2, ensure_ascii=False)
    
    def track_brd_generation(self, duration_seconds: float, success: bool = True):
        """
        Отследить генерацию BRD документа
        
        Args:
            duration_seconds: Время генерации в секундах
            success: Успешно ли выполнена генерация
        """
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Performance метрики
        self.metrics['performance']['brd_generation_times'].append({
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': duration_seconds,
            'success': success
        })
        self.metrics['performance']['total_operations'] += 1
        
        # Проверка SLA (5 минут = 300 секунд)
        if duration_seconds > 300:
            self.metrics['performance']['sla_violations'] += 1
        
        # Business метрики
        self.metrics['business']['documents_generated'] += 1
        # Оценка экономии времени (вручную BRD занимает ~2 часа)
        if success:
            time_saved = 2.0  # часа
            self.metrics['business']['analyst_time_saved'] += time_saved
        
        # Daily stats
        self.metrics['daily_stats'][today]['operations'] += 1
        self.metrics['daily_stats'][today]['brd_count'] += 1
        
        # Обновляем среднее время
        times = [t['duration_seconds'] for t in self.metrics['performance']['brd_generation_times'][-100:]]  # Последние 100
        if times:
            self.metrics['daily_stats'][today]['avg_time'] = sum(times) / len(times)
        
        self._save_metrics()
    
    def track_dialog_completion(self, duration_seconds: float, completed_without_help: bool):
        """
        Отследить завершение диалога
        
        Args:
            duration_seconds: Длительность диалога в секундах
            completed_without_help: Завершен ли диалог без помощи специалиста
        """
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Usability метрики
        if completed_without_help:
            self.metrics['usability']['dialogs_without_help'] += 1
            self.metrics['usability']['completed_dialogs'] += 1
        else:
            self.metrics['usability']['dialogs_with_help'] += 1
            self.metrics['usability']['completed_dialogs'] += 1
        
        # Обновляем среднюю длительность диалога
        total_completed = self.metrics['usability']['completed_dialogs']
        current_avg = self.metrics['usability']['average_dialog_duration']
        # Экспоненциальное скользящее среднее
        alpha = 0.3
        self.metrics['usability']['average_dialog_duration'] = (
            alpha * duration_seconds + (1 - alpha) * current_avg
        )
        
        # Daily stats
        self.metrics['daily_stats'][today]['completed_dialogs'] += 1
        
        self._save_metrics()
    
    def track_dialog_failure(self, reason: str = None):
        """
        Отследить неудачный диалог
        
        Args:
            reason: Причина неудачи (опционально)
        """
        self.metrics['usability']['failed_dialogs'] += 1
        self._save_metrics()
    
    def get_performance_metrics(self) -> Dict:
        """Получить метрики производительности"""
        times = self.metrics['performance']['brd_generation_times']
        recent_times = [t['duration_seconds'] for t in times[-100:]] if times else []
        
        avg_time = sum(recent_times) / len(recent_times) if recent_times else 0
        sla_compliance = 1.0 - (self.metrics['performance']['sla_violations'] / 
                               max(self.metrics['performance']['total_operations'], 1))
        
        return {
            'average_brd_generation_time_seconds': avg_time,
            'average_brd_generation_time_minutes': avg_time / 60,
            'total_operations': self.metrics['performance']['total_operations'],
            'sla_violations': self.metrics['performance']['sla_violations'],
            'sla_compliance_rate': sla_compliance * 100,
            'sla_target_minutes': 5,
            'sla_target_seconds': 300
        }
    
    def get_business_metrics(self) -> Dict:
        """Получить бизнес-метрики"""
        total_docs = self.metrics['business']['documents_generated']
        time_saved = self.metrics['business']['analyst_time_saved']
        
        # Расчет коэффициента автоматизации
        # Предполагаем, что каждый документ экономит время аналитика
        automation_rate = min(100.0, (total_docs * 2.0 / max(time_saved, 0.01)) * 50) if total_docs > 0 else 0
        
        return {
            'analyst_time_saved_hours': time_saved,
            'analyst_time_saved_days': time_saved / 8,  # Предполагаем 8-часовой рабочий день
            'documents_generated': total_docs,
            'automation_rate_percent': automation_rate,
            'estimated_cost_savings': time_saved * 5000,  # Предполагаем стоимость часа работы аналитика
            'load_reduction_percent': min(100, (time_saved / max(total_docs * 2, 0.01)) * 100) if total_docs > 0 else 0
        }
    
    def get_usability_metrics(self) -> Dict:
        """Получить метрики удобства использования"""
        total = self.metrics['usability']['completed_dialogs'] + self.metrics['usability']['failed_dialogs']
        completed = self.metrics['usability']['completed_dialogs']
        without_help = self.metrics['usability']['dialogs_without_help']
        
        success_rate = (completed / total * 100) if total > 0 else 0
        independent_success_rate = (without_help / completed * 100) if completed > 0 else 0
        
        return {
            'total_dialogs': total,
            'completed_dialogs': completed,
            'failed_dialogs': self.metrics['usability']['failed_dialogs'],
            'dialogs_without_help': without_help,
            'dialogs_with_help': self.metrics['usability']['dialogs_with_help'],
            'success_rate_percent': success_rate,
            'independent_completion_rate_percent': independent_success_rate,
            'average_dialog_duration_minutes': self.metrics['usability']['average_dialog_duration'] / 60,
            'average_dialog_duration_seconds': self.metrics['usability']['average_dialog_duration']
        }
    
    def get_all_metrics(self) -> Dict:
        """Получить все метрики"""
        return {
            'performance': self.get_performance_metrics(),
            'business': self.get_business_metrics(),
            'usability': self.get_usability_metrics(),
            'last_updated': datetime.now().isoformat()
        }
    
    def get_daily_stats(self, days: int = 7) -> List[Dict]:
        """Получить статистику за последние N дней"""
        end_date = datetime.now()
        stats = []
        
        for i in range(days):
            date = (end_date - timedelta(days=i)).strftime('%Y-%m-%d')
            day_stats = self.metrics['daily_stats'].get(date, {
                'operations': 0,
                'brd_count': 0,
                'completed_dialogs': 0,
                'avg_time': 0.0
            })
            day_stats['date'] = date
            stats.append(day_stats)
        
        return stats
    
    def reset_metrics(self):
        """Сбросить все метрики (использовать с осторожностью)"""
        self.metrics = {
            'performance': {
                'brd_generation_times': [],
                'total_operations': 0,
                'sla_violations': 0
            },
            'business': {
                'analyst_time_saved': 0,
                'documents_generated': 0,
                'automation_rate': 0.0
            },
            'usability': {
                'completed_dialogs': 0,
                'failed_dialogs': 0,
                'dialogs_with_help': 0,
                'dialogs_without_help': 0,
                'average_dialog_duration': 0.0
            },
            'daily_stats': {}
        }
        self._save_metrics()


"""
Модуль отслеживания метрик для AI-Scrum Master
Performance, Business, Usability метрики
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict


class ScrumMetricsTracker:
    """Отслеживание метрик производительности AI-Scrum Master"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.metrics_file = os.path.join(data_dir, "scrum_metrics.json")
        self._ensure_data_dir()
        self._load_metrics()
    
    def _ensure_data_dir(self):
        """Создаёт директорию для данных"""
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _load_metrics(self):
        """Загружает метрики из файла"""
        if os.path.exists(self.metrics_file):
            try:
                with open(self.metrics_file, 'r', encoding='utf-8') as f:
                    self.metrics = json.load(f)
            except:
                self.metrics = self._init_metrics()
        else:
            self.metrics = self._init_metrics()
    
    def _init_metrics(self) -> Dict[str, Any]:
        """Инициализирует структуру метрик"""
        return {
            'performance': {
                'task_decomposition': {
                    'total_tasks': 0,
                    'correctly_decomposed': 0,
                    'accuracy': 0.0
                },
                'decision_tracking': {
                    'total_decisions': 0,
                    'correctly_tracked': 0,
                    'accuracy': 0.0
                },
                'deadline_reminders': {
                    'total_reminders': 0,
                    'sent_on_time': 0,
                    'on_time_rate': 0.0
                }
            },
            'business': {
                'time_savings': {
                    'tasks_created_manually': 0,
                    'tasks_created_automatically': 0,
                    'time_saved_minutes': 0
                },
                'task_completion': {
                    'tasks_completed_in_sprint': 0,
                    'tasks_planned_in_sprint': 0,
                    'completion_rate': 0.0
                }
            },
            'usability': {
                'jira_sync': {
                    'total_syncs': 0,
                    'automatic_syncs': 0,
                    'automatic_sync_rate': 0.0
                },
                'user_actions': {
                    'total_actions': 0,
                    'successful_actions': 0,
                    'success_rate': 0.0
                }
            },
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
    
    def _save_metrics(self):
        """Сохраняет метрики в файл"""
        self.metrics['updated_at'] = datetime.now().isoformat()
        with open(self.metrics_file, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, ensure_ascii=False, indent=2)
    
    # ==================== Performance Metrics ====================
    
    def record_task_decomposition(self, total_tasks: int, correctly_decomposed: int):
        """
        Записывает метрики декомпозиции задач
        
        Args:
            total_tasks: Всего задач
            correctly_decomposed: Корректно разбитых задач
        """
        perf = self.metrics['performance']['task_decomposition']
        perf['total_tasks'] += total_tasks
        perf['correctly_decomposed'] += correctly_decomposed
        
        if perf['total_tasks'] > 0:
            perf['accuracy'] = (perf['correctly_decomposed'] / perf['total_tasks']) * 100
        
        self._save_metrics()
    
    def record_decision_tracking(self, total_decisions: int, correctly_tracked: int):
        """
        Записывает метрики отслеживания решений
        
        Args:
            total_decisions: Всего решений
            correctly_tracked: Корректно зафиксированных решений
        """
        perf = self.metrics['performance']['decision_tracking']
        perf['total_decisions'] += total_decisions
        perf['correctly_tracked'] += correctly_tracked
        
        if perf['total_decisions'] > 0:
            perf['accuracy'] = (perf['correctly_tracked'] / perf['total_decisions']) * 100
        
        self._save_metrics()
    
    def record_deadline_reminder(self, sent_on_time: bool):
        """
        Записывает метрики напоминаний о дедлайнах
        
        Args:
            sent_on_time: Отправлено вовремя
        """
        perf = self.metrics['performance']['deadline_reminders']
        perf['total_reminders'] += 1
        
        if sent_on_time:
            perf['sent_on_time'] += 1
        
        if perf['total_reminders'] > 0:
            perf['on_time_rate'] = (perf['sent_on_time'] / perf['total_reminders']) * 100
        
        self._save_metrics()
    
    # ==================== Business Metrics ====================
    
    def record_task_creation(self, created_automatically: bool, time_saved_minutes: int = 0):
        """
        Записывает метрики создания задач
        
        Args:
            created_automatically: Создано автоматически
            time_saved_minutes: Сэкономлено минут
        """
        business = self.metrics['business']['time_savings']
        
        if created_automatically:
            business['tasks_created_automatically'] += 1
            business['time_saved_minutes'] += time_saved_minutes
        else:
            business['tasks_created_manually'] += 1
        
        self._save_metrics()
    
    def record_task_completion(self, tasks_completed: int, tasks_planned: int):
        """
        Записывает метрики завершения задач в спринте
        
        Args:
            tasks_completed: Завершено задач
            tasks_planned: Запланировано задач
        """
        business = self.metrics['business']['task_completion']
        business['tasks_completed_in_sprint'] += tasks_completed
        business['tasks_planned_in_sprint'] += tasks_planned
        
        if business['tasks_planned_in_sprint'] > 0:
            business['completion_rate'] = (
                business['tasks_completed_in_sprint'] / 
                business['tasks_planned_in_sprint']
            ) * 100
        
        self._save_metrics()
    
    # ==================== Usability Metrics ====================
    
    def record_jira_sync(self, automatic: bool):
        """
        Записывает метрики синхронизации с Jira
        
        Args:
            automatic: Автоматическая синхронизация
        """
        usability = self.metrics['usability']['jira_sync']
        usability['total_syncs'] += 1
        
        if automatic:
            usability['automatic_syncs'] += 1
        
        if usability['total_syncs'] > 0:
            usability['automatic_sync_rate'] = (
                usability['automatic_syncs'] / usability['total_syncs']
            ) * 100
        
        self._save_metrics()
    
    def record_user_action(self, successful: bool):
        """
        Записывает метрики действий пользователя
        
        Args:
            successful: Действие успешно
        """
        usability = self.metrics['usability']['user_actions']
        usability['total_actions'] += 1
        
        if successful:
            usability['successful_actions'] += 1
        
        if usability['total_actions'] > 0:
            usability['success_rate'] = (
                usability['successful_actions'] / usability['total_actions']
            ) * 100
        
        self._save_metrics()
    
    # ==================== Методы получения метрик ====================
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Получает Performance метрики"""
        perf = self.metrics['performance']
        
        return {
            'task_decomposition': {
                'accuracy': perf['task_decomposition']['accuracy'],
                'total_tasks': perf['task_decomposition']['total_tasks'],
                'correctly_decomposed': perf['task_decomposition']['correctly_decomposed'],
                'target': 85.0,
                'meets_target': perf['task_decomposition']['accuracy'] >= 85.0
            },
            'decision_tracking': {
                'accuracy': perf['decision_tracking']['accuracy'],
                'total_decisions': perf['decision_tracking']['total_decisions'],
                'correctly_tracked': perf['decision_tracking']['correctly_tracked'],
                'target': 90.0,
                'meets_target': perf['decision_tracking']['accuracy'] >= 90.0
            },
            'deadline_reminders': {
                'on_time_rate': perf['deadline_reminders']['on_time_rate'],
                'total_reminders': perf['deadline_reminders']['total_reminders'],
                'sent_on_time': perf['deadline_reminders']['sent_on_time'],
                'target': 95.0,
                'meets_target': perf['deadline_reminders']['on_time_rate'] >= 95.0
            },
            'overall_score': self._calculate_performance_score(perf)
        }
    
    def get_business_metrics(self) -> Dict[str, Any]:
        """Получает Business метрики"""
        business = self.metrics['business']
        
        total_tasks = (
            business['time_savings']['tasks_created_manually'] +
            business['time_savings']['tasks_created_automatically']
        )
        
        automation_rate = 0.0
        if total_tasks > 0:
            automation_rate = (
                business['time_savings']['tasks_created_automatically'] / total_tasks
            ) * 100
        
        return {
            'time_savings': {
                'tasks_created_automatically': business['time_savings']['tasks_created_automatically'],
                'tasks_created_manually': business['time_savings']['tasks_created_manually'],
                'total_tasks': total_tasks,
                'automation_rate': automation_rate,
                'time_saved_minutes': business['time_savings']['time_saved_minutes'],
                'time_saved_hours': round(business['time_savings']['time_saved_minutes'] / 60, 2)
            },
            'task_completion': {
                'completion_rate': business['task_completion']['completion_rate'],
                'tasks_completed': business['task_completion']['tasks_completed_in_sprint'],
                'tasks_planned': business['task_completion']['tasks_planned_in_sprint']
            },
            'overall_score': self._calculate_business_score(business)
        }
    
    def get_usability_metrics(self) -> Dict[str, Any]:
        """Получает Usability метрики"""
        usability = self.metrics['usability']
        
        return {
            'jira_sync': {
                'automatic_sync_rate': usability['jira_sync']['automatic_sync_rate'],
                'total_syncs': usability['jira_sync']['total_syncs'],
                'automatic_syncs': usability['jira_sync']['automatic_syncs'],
                'target': 90.0,
                'meets_target': usability['jira_sync']['automatic_sync_rate'] >= 90.0
            },
            'user_actions': {
                'success_rate': usability['user_actions']['success_rate'],
                'total_actions': usability['user_actions']['total_actions'],
                'successful_actions': usability['user_actions']['successful_actions']
            },
            'overall_score': self._calculate_usability_score(usability)
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Получает все метрики"""
        return {
            'performance': self.get_performance_metrics(),
            'business': self.get_business_metrics(),
            'usability': self.get_usability_metrics(),
            'updated_at': self.metrics['updated_at']
        }
    
    def _calculate_performance_score(self, perf: Dict[str, Any]) -> float:
        """Вычисляет общий Performance score"""
        scores = []
        
        if perf['task_decomposition']['total_tasks'] > 0:
            scores.append(perf['task_decomposition']['accuracy'])
        
        if perf['decision_tracking']['total_decisions'] > 0:
            scores.append(perf['decision_tracking']['accuracy'])
        
        if perf['deadline_reminders']['total_reminders'] > 0:
            scores.append(perf['deadline_reminders']['on_time_rate'])
        
        return round(sum(scores) / len(scores), 2) if scores else 0.0
    
    def _calculate_business_score(self, business: Dict[str, Any]) -> float:
        """Вычисляет общий Business score"""
        scores = []
        
        # Automation rate (0-100)
        total_tasks = (
            business['time_savings']['tasks_created_manually'] +
            business['time_savings']['tasks_created_automatically']
        )
        if total_tasks > 0:
            automation_rate = (
                business['time_savings']['tasks_created_automatically'] / total_tasks
            ) * 100
            scores.append(automation_rate)
        
        # Completion rate
        if business['task_completion']['tasks_planned_in_sprint'] > 0:
            scores.append(business['task_completion']['completion_rate'])
        
        return round(sum(scores) / len(scores), 2) if scores else 0.0
    
    def _calculate_usability_score(self, usability: Dict[str, Any]) -> float:
        """Вычисляет общий Usability score"""
        scores = []
        
        if usability['jira_sync']['total_syncs'] > 0:
            scores.append(usability['jira_sync']['automatic_sync_rate'])
        
        if usability['user_actions']['total_actions'] > 0:
            scores.append(usability['user_actions']['success_rate'])
        
        return round(sum(scores) / len(scores), 2) if scores else 0.0
    
    def reset_metrics(self):
        """Сбрасывает все метрики (для тестирования)"""
        self.metrics = self._init_metrics()
        self._save_metrics()


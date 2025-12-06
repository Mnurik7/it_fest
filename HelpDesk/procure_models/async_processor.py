"""
Модуль для асинхронной обработки тендеров
"""
from typing import Dict, List, Optional, Any, Callable
import json
import threading
import queue
import time
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AsyncProcessor:
    """Процессор для асинхронной обработки тендеров"""
    
    def __init__(self, max_workers: int = 4):
        """
        Инициализация асинхронного процессора
        
        Args:
            max_workers: Максимальное количество потоков
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.task_queue = queue.Queue()
        self.active_tasks = {}
        self.completed_tasks = []
        self.failed_tasks = []
        self.task_results_file = "data/async_tasks.json"
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """Создаёт директорию для данных если не существует"""
        import os
        os.makedirs(os.path.dirname(self.task_results_file), exist_ok=True)
    
    def submit_task(self, task_id: str, task_func: Callable, *args, **kwargs) -> str:
        """
        Отправляет задачу на асинхронное выполнение
        
        Args:
            task_id: Уникальный ID задачи
            task_func: Функция для выполнения
            *args, **kwargs: Аргументы для функции
            
        Returns:
            ID задачи
        """
        future = self.executor.submit(self._execute_task, task_id, task_func, *args, **kwargs)
        self.active_tasks[task_id] = {
            'future': future,
            'status': 'pending',
            'submitted_at': datetime.now().isoformat(),
            'task_func': task_func.__name__ if hasattr(task_func, '__name__') else 'unknown'
        }
        
        # Добавляем callback для обработки результата
        future.add_done_callback(lambda f: self._task_done_callback(task_id, f))
        
        logger.info(f"Задача {task_id} отправлена на выполнение")
        return task_id
    
    def _execute_task(self, task_id: str, task_func: Callable, *args, **kwargs) -> Any:
        """
        Выполняет задачу
        
        Args:
            task_id: ID задачи
            task_func: Функция для выполнения
            *args, **kwargs: Аргументы
            
        Returns:
            Результат выполнения
        """
        try:
            self.active_tasks[task_id]['status'] = 'running'
            self.active_tasks[task_id]['started_at'] = datetime.now().isoformat()
            
            result = task_func(*args, **kwargs)
            
            self.active_tasks[task_id]['status'] = 'completed'
            self.active_tasks[task_id]['completed_at'] = datetime.now().isoformat()
            
            return {
                'task_id': task_id,
                'status': 'success',
                'result': result,
                'completed_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Ошибка при выполнении задачи {task_id}: {e}")
            return {
                'task_id': task_id,
                'status': 'failed',
                'error': str(e),
                'completed_at': datetime.now().isoformat()
            }
    
    def _task_done_callback(self, task_id: str, future):
        """Callback при завершении задачи"""
        try:
            result = future.result()
            
            if result['status'] == 'success':
                self.completed_tasks.append(result)
                if task_id in self.active_tasks:
                    self.active_tasks[task_id]['result'] = result['result']
            else:
                self.failed_tasks.append(result)
                if task_id in self.active_tasks:
                    self.active_tasks[task_id]['error'] = result.get('error')
            
            # Сохраняем результат
            self._save_task_result(result)
            
        except Exception as e:
            logger.error(f"Ошибка в callback для задачи {task_id}: {e}")
            self.failed_tasks.append({
                'task_id': task_id,
                'status': 'failed',
                'error': str(e),
                'completed_at': datetime.now().isoformat()
            })
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает статус задачи
        
        Args:
            task_id: ID задачи
            
        Returns:
            Статус задачи или None если не найдена
        """
        if task_id in self.active_tasks:
            task_info = self.active_tasks[task_id].copy()
            # Удаляем future объект (не сериализуется)
            task_info.pop('future', None)
            return task_info
        
        # Проверяем в завершённых
        for task in self.completed_tasks:
            if task.get('task_id') == task_id:
                return {
                    'task_id': task_id,
                    'status': 'completed',
                    'result': task.get('result')
                }
        
        # Проверяем в неудачных
        for task in self.failed_tasks:
            if task.get('task_id') == task_id:
                return {
                    'task_id': task_id,
                    'status': 'failed',
                    'error': task.get('error')
                }
        
        return None
    
    def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Ожидает завершения задачи
        
        Args:
            task_id: ID задачи
            timeout: Таймаут в секундах (None = без таймаута)
            
        Returns:
            Результат задачи или None если таймаут
        """
        if task_id not in self.active_tasks:
            return self.get_task_status(task_id)
        
        future = self.active_tasks[task_id]['future']
        
        try:
            result = future.result(timeout=timeout)
            return result
        except Exception as e:
            logger.error(f"Ошибка при ожидании задачи {task_id}: {e}")
            return None
    
    def get_all_tasks(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Получает все задачи
        
        Returns:
            Словарь с активными, завершёнными и неудачными задачами
        """
        active = []
        for task_id, task_info in self.active_tasks.items():
            task_copy = task_info.copy()
            task_copy.pop('future', None)
            task_copy['task_id'] = task_id
            active.append(task_copy)
        
        return {
            'active': active,
            'completed': self.completed_tasks[-100:],  # Последние 100
            'failed': self.failed_tasks[-100:]  # Последние 100
        }
    
    def _save_task_result(self, result: Dict[str, Any]):
        """Сохраняет результат задачи в файл"""
        import os
        if os.path.exists(self.task_results_file):
            try:
                with open(self.task_results_file, 'r', encoding='utf-8') as f:
                    all_results = json.load(f)
            except:
                all_results = []
        else:
            all_results = []
        
        all_results.append(result)
        # Оставляем последние 1000
        all_results = all_results[-1000:]
        
        try:
            with open(self.task_results_file, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка при сохранении результата задачи: {e}")
    
    def shutdown(self, wait: bool = True):
        """
        Завершает работу процессора
        
        Args:
            wait: Ждать завершения активных задач
        """
        self.executor.shutdown(wait=wait)
        logger.info("AsyncProcessor завершён")


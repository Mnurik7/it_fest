"""
Модуль для пакетной обработки множественных тендеров
"""
from typing import Dict, List, Optional, Any
import json
import logging
from datetime import datetime
import os

from .async_processor import AsyncProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BatchProcessor:
    """Процессор для пакетной обработки тендеров"""
    
    def __init__(self, async_processor: Optional[AsyncProcessor] = None):
        """
        Инициализация пакетного процессора
        
        Args:
            async_processor: Экземпляр AsyncProcessor для асинхронной обработки
        """
        self.async_processor = async_processor or AsyncProcessor(max_workers=4)
        self.batch_results_file = "data/batch_results.json"
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """Создаёт директорию для данных если не существует"""
        os.makedirs(os.path.dirname(self.batch_results_file), exist_ok=True)
    
    def process_batch(self, tenders: List[Dict[str, Any]], analyze_func: callable, 
                      batch_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Обрабатывает пакет тендеров
        
        Args:
            tenders: Список тендеров для обработки
            analyze_func: Функция для анализа одного тендера
            batch_id: ID пакета (генерируется если не указан)
            
        Returns:
            Результаты пакетной обработки
        """
        if not batch_id:
            batch_id = f"BATCH_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        logger.info(f"Начало пакетной обработки: {batch_id}, тендеров: {len(tenders)}")
        
        start_time = datetime.now()
        task_ids = []
        
        # Отправляем все задачи на асинхронную обработку
        for i, tender in enumerate(tenders):
            tender_text = tender.get('text', tender.get('description', ''))
            if not tender_text:
                logger.warning(f"Тендер {i} не содержит текста, пропускаем")
                continue
            
            task_id = f"{batch_id}_TENDER_{i}"
            task_ids.append(task_id)
            
            # Отправляем на асинхронную обработку
            self.async_processor.submit_task(
                task_id,
                analyze_func,
                tender_text,
                tender.get('source_type', 'text')
            )
        
        # Ждём завершения всех задач
        results = []
        for task_id in task_ids:
            result = self.async_processor.wait_for_task(task_id, timeout=300)  # 5 минут на тендер
            if result:
                results.append(result)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Формируем сводку
        summary = {
            'batch_id': batch_id,
            'total_tenders': len(tenders),
            'processed_tenders': len(results),
            'successful': len([r for r in results if r.get('status') == 'success']),
            'failed': len([r for r in results if r.get('status') == 'failed']),
            'processing_time_seconds': processing_time,
            'avg_time_per_tender': processing_time / len(tenders) if tenders else 0,
            'started_at': start_time.isoformat(),
            'completed_at': end_time.isoformat(),
            'results': results
        }
        
        # Сохраняем результаты
        self._save_batch_results(summary)
        
        logger.info(f"Пакетная обработка завершена: {batch_id}, успешно: {summary['successful']}, ошибок: {summary['failed']}")
        
        return summary
    
    def process_batch_sync(self, tenders: List[Dict[str, Any]], analyze_func: callable) -> Dict[str, Any]:
        """
        Обрабатывает пакет тендеров синхронно (для небольших пакетов)
        
        Args:
            tenders: Список тендеров для обработки
            analyze_func: Функция для анализа одного тендера
            
        Returns:
            Результаты пакетной обработки
        """
        batch_id = f"BATCH_SYNC_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        logger.info(f"Начало синхронной пакетной обработки: {batch_id}, тендеров: {len(tenders)}")
        
        start_time = datetime.now()
        results = []
        
        for i, tender in enumerate(tenders):
            try:
                tender_text = tender.get('text', tender.get('description', ''))
                if not tender_text:
                    logger.warning(f"Тендер {i} не содержит текста, пропускаем")
                    continue
                
                result = analyze_func(tender_text, tender.get('source_type', 'text'))
                results.append({
                    'task_id': f"{batch_id}_TENDER_{i}",
                    'status': 'success',
                    'result': result,
                    'tender_index': i
                })
            except Exception as e:
                logger.error(f"Ошибка при обработке тендера {i}: {e}")
                results.append({
                    'task_id': f"{batch_id}_TENDER_{i}",
                    'status': 'failed',
                    'error': str(e),
                    'tender_index': i
                })
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        summary = {
            'batch_id': batch_id,
            'total_tenders': len(tenders),
            'processed_tenders': len(results),
            'successful': len([r for r in results if r.get('status') == 'success']),
            'failed': len([r for r in results if r.get('status') == 'failed']),
            'processing_time_seconds': processing_time,
            'avg_time_per_tender': processing_time / len(tenders) if tenders else 0,
            'started_at': start_time.isoformat(),
            'completed_at': end_time.isoformat(),
            'results': results
        }
        
        self._save_batch_results(summary)
        
        logger.info(f"Синхронная пакетная обработка завершена: {batch_id}")
        
        return summary
    
    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает статус пакетной обработки
        
        Args:
            batch_id: ID пакета
            
        Returns:
            Статус пакета или None если не найден
        """
        if os.path.exists(self.batch_results_file):
            try:
                with open(self.batch_results_file, 'r', encoding='utf-8') as f:
                    all_batches = json.load(f)
                    for batch in all_batches:
                        if batch.get('batch_id') == batch_id:
                            return batch
            except:
                pass
        return None
    
    def _save_batch_results(self, summary: Dict[str, Any]):
        """Сохраняет результаты пакетной обработки"""
        if os.path.exists(self.batch_results_file):
            try:
                with open(self.batch_results_file, 'r', encoding='utf-8') as f:
                    all_batches = json.load(f)
            except:
                all_batches = []
        else:
            all_batches = []
        
        all_batches.append(summary)
        # Оставляем последние 100
        all_batches = all_batches[-100:]
        
        try:
            with open(self.batch_results_file, 'w', encoding='utf-8') as f:
                json.dump(all_batches, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка при сохранении результатов пакетной обработки: {e}")


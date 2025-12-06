"""
Обработка транзакций в реальном времени
Стриминг данных, батчинг, оптимизация производительности
"""
import pandas as pd
import numpy as np
from datetime import datetime
from collections import deque
import threading
import time
from .fraud_detection_model import FraudDetectionModel
import warnings
warnings.filterwarnings('ignore')


class RealtimeProcessor:
    """
    Процессор для обработки транзакций в реальном времени
    """
    
    def __init__(self, model, batch_size=10, max_wait_time=1.0):
        """
        Инициализация процессора
        
        Args:
            model: обученная модель FraudDetectionModel
            batch_size: размер батча для обработки
            max_wait_time: максимальное время ожидания батча (секунды)
        """
        self.model = model
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.transaction_queue = deque()
        self.results = {}
        self.lock = threading.Lock()
        self.processing = False
        self.processor_thread = None
    
    def add_transaction(self, transaction_data):
        """
        Добавление транзакции в очередь
        
        Args:
            transaction_data: словарь с данными транзакции
            
        Returns:
            transaction_id для отслеживания
        """
        transaction_id = f"txn_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        transaction = {
            'id': transaction_id,
            'data': transaction_data,
            'timestamp': datetime.now(),
            'status': 'pending'
        }
        
        with self.lock:
            self.transaction_queue.append(transaction)
        
        # Автоматический запуск обработки если очередь заполнена
        if len(self.transaction_queue) >= self.batch_size:
            self._process_batch()
        
        return transaction_id
    
    def get_result(self, transaction_id):
        """
        Получение результата обработки транзакции
        
        Args:
            transaction_id: ID транзакции
            
        Returns:
            результат или None если еще не обработано
        """
        with self.lock:
            return self.results.get(transaction_id)
    
    def _process_batch(self):
        """Обработка батча транзакций"""
        if self.processing:
            return
        
        self.processing = True
        
        with self.lock:
            if len(self.transaction_queue) < self.batch_size:
                self.processing = False
                return
            
            # Извлечение батча
            batch = []
            for _ in range(min(self.batch_size, len(self.transaction_queue))):
                batch.append(self.transaction_queue.popleft())
        
        # Обработка батча
        try:
            # Преобразование в DataFrame
            batch_data = [txn['data'] for txn in batch]
            df = pd.DataFrame(batch_data)
            
            # Feature Engineering
            df = self.model.feature_engineering(df)
            
            # Подготовка признаков
            X = self.model.prepare_features(df, is_training=False)
            
            # Предсказание
            predictions = self.model.predict(X, threshold=0.3)
            
            # Сохранение результатов
            with self.lock:
                for i, txn in enumerate(batch):
                    result = {
                        'transaction_id': txn['id'],
                        'is_fraud': predictions['is_fraud'][i] if isinstance(predictions['is_fraud'], list) else predictions['is_fraud'],
                        'fraud_probability': predictions['fraud_probability'][i] if isinstance(predictions['fraud_probability'], list) else predictions['fraud_probability'],
                        'processed_at': datetime.now().isoformat(),
                        'status': 'completed'
                    }
                    self.results[txn['id']] = result
                    txn['status'] = 'completed'
        
        except Exception as e:
            print(f"Ошибка при обработке батча: {e}")
            with self.lock:
                for txn in batch:
                    self.results[txn['id']] = {
                        'transaction_id': txn['id'],
                        'error': str(e),
                        'status': 'error'
                    }
        
        finally:
            self.processing = False
    
    def start_background_processing(self):
        """Запуск фоновой обработки"""
        def process_loop():
            while True:
                time.sleep(self.max_wait_time)
                if len(self.transaction_queue) > 0:
                    self._process_batch()
        
        self.processor_thread = threading.Thread(target=process_loop, daemon=True)
        self.processor_thread.start()
        print("✓ Фоновая обработка запущена")
    
    def process_single(self, transaction_data):
        """
        Обработка одной транзакции немедленно
        
        Args:
            transaction_data: данные транзакции
            
        Returns:
            результат предсказания
        """
        df = pd.DataFrame([transaction_data])
        
        # Feature Engineering
        df = self.model.feature_engineering(df)
        
        # Подготовка признаков
        X = self.model.prepare_features(df, is_training=False)
        
        # Предсказание
        result = self.model.predict(X, threshold=0.3)
        
        return {
            'is_fraud': result['is_fraud'],
            'fraud_probability': result['fraud_probability'],
            'processed_at': datetime.now().isoformat()
        }
    
    def get_queue_size(self):
        """Получение размера очереди"""
        with self.lock:
            return len(self.transaction_queue)
    
    def clear_results(self, older_than_hours=24):
        """
        Очистка старых результатов
        
        Args:
            older_than_hours: удалить результаты старше N часов
        """
        cutoff_time = datetime.now().timestamp() - (older_than_hours * 3600)
        
        with self.lock:
            to_remove = []
            for txn_id, result in self.results.items():
                if 'processed_at' in result:
                    try:
                        processed_time = datetime.fromisoformat(result['processed_at']).timestamp()
                        if processed_time < cutoff_time:
                            to_remove.append(txn_id)
                    except:
                        pass
            
            for txn_id in to_remove:
                del self.results[txn_id]
        
        print(f"✓ Удалено результатов: {len(to_remove)}")


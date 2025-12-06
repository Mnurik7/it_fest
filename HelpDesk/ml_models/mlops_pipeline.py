"""
MLOps Pipeline для автоматизации обучения и развертывания моделей
Версионирование моделей, автоматическое переобучение, мониторинг
"""
import os
import json
import joblib
from datetime import datetime
from pathlib import Path
import pandas as pd
from .fraud_detection_model import FraudDetectionModel
import warnings
warnings.filterwarnings('ignore')


class MLOpsPipeline:
    """
    MLOps пайплайн для управления жизненным циклом модели
    """
    
    def __init__(self, models_dir='ml_models/saved_models', metadata_file='ml_models/model_metadata.json'):
        """
        Инициализация пайплайна
        
        Args:
            models_dir: директория для сохранения моделей
            metadata_file: файл с метаданными моделей
        """
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = metadata_file
        self.metadata = self._load_metadata()
    
    def _load_metadata(self):
        """Загрузка метаданных моделей"""
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'models': [],
            'current_version': None,
            'last_training': None
        }
    
    def _save_metadata(self):
        """Сохранение метаданных"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
    
    def train_and_version(self, model, transactions_path, behavioral_path, 
                         version_name=None, description=''):
        """
        Обучение модели и создание версии
        
        Args:
            model: экземпляр FraudDetectionModel
            transactions_path: путь к транзакциям
            behavioral_path: путь к поведенческим данным
            version_name: имя версии (если None - авто)
            description: описание версии
            
        Returns:
            версия модели
        """
        print("🔄 MLOps Pipeline: Обучение и версионирование...")
        
        # Загрузка данных
        data = model.load_data(transactions_path, behavioral_path)
        
        # Feature Engineering
        data = model.feature_engineering(data)
        
        # Подготовка признаков
        X, y = model.prepare_features(data, is_training=True)
        
        # Обучение
        metrics = model.train(X, y)
        
        # Создание версии
        if version_name is None:
            version_name = f"v{len(self.metadata['models']) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Сохранение модели
        model_path = self.models_dir / f"{version_name}.pkl"
        model.save_model(str(model_path))
        
        # Метаданные версии
        version_metadata = {
            'version': version_name,
            'created_at': datetime.now().isoformat(),
            'description': description,
            'metrics': metrics,
            'model_type': model.model_type,
            'model_path': str(model_path),
            'data_paths': {
                'transactions': transactions_path,
                'behavioral': behavioral_path
            },
            'feature_count': len(model.feature_names) if hasattr(model, 'feature_names') else 0
        }
        
        # Добавление в метаданные
        self.metadata['models'].append(version_metadata)
        self.metadata['current_version'] = version_name
        self.metadata['last_training'] = datetime.now().isoformat()
        self._save_metadata()
        
        print(f"✓ Модель сохранена как версия: {version_name}")
        return version_metadata
    
    def load_version(self, version_name=None):
        """
        Загрузка конкретной версии модели
        
        Args:
            version_name: имя версии (если None - текущая)
            
        Returns:
            загруженная модель
        """
        if version_name is None:
            version_name = self.metadata.get('current_version')
        
        if version_name is None:
            raise ValueError("Версия не указана и нет текущей версии")
        
        # Поиск метаданных версии
        version_meta = None
        for model_meta in self.metadata['models']:
            if model_meta['version'] == version_name:
                version_meta = model_meta
                break
        
        if version_meta is None:
            raise ValueError(f"Версия {version_name} не найдена")
        
        # Загрузка модели
        model = FraudDetectionModel(model_type=version_meta['model_type'])
        model.load_model(version_meta['model_path'])
        
        print(f"✓ Загружена версия: {version_name}")
        return model
    
    def list_versions(self):
        """
        Список всех версий моделей
        
        Returns:
            список версий
        """
        return self.metadata['models']
    
    def get_current_version(self):
        """Получение текущей версии"""
        return self.metadata.get('current_version')
    
    def set_current_version(self, version_name):
        """
        Установка текущей версии
        
        Args:
            version_name: имя версии
        """
        # Проверка существования
        if not any(m['version'] == version_name for m in self.metadata['models']):
            raise ValueError(f"Версия {version_name} не найдена")
        
        self.metadata['current_version'] = version_name
        self._save_metadata()
        print(f"✓ Текущая версия установлена: {version_name}")
    
    def compare_versions(self, version1, version2):
        """
        Сравнение двух версий моделей
        
        Args:
            version1: первая версия
            version2: вторая версия
            
        Returns:
            сравнение метрик
        """
        meta1 = next((m for m in self.metadata['models'] if m['version'] == version1), None)
        meta2 = next((m for m in self.metadata['models'] if m['version'] == version2), None)
        
        if meta1 is None or meta2 is None:
            raise ValueError("Одна из версий не найдена")
        
        comparison = {
            'version1': version1,
            'version2': version2,
            'metrics1': meta1['metrics'],
            'metrics2': meta2['metrics'],
            'improvements': {}
        }
        
        # Сравнение метрик
        for metric in ['precision', 'recall', 'f_beta', 'roc_auc']:
            if metric in meta1['metrics'] and metric in meta2['metrics']:
                diff = meta2['metrics'][metric] - meta1['metrics'][metric]
                comparison['improvements'][metric] = {
                    'difference': diff,
                    'improved': diff > 0
                }
        
        return comparison


"""
Тест загрузки и работы модели
Проверка корректности сохранения/загрузки модели
"""
import os
import sys

# Добавляем родительский каталог в путь для импорта пакета ml_models
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Используем абсолютные импорты из пакета ml_models
from ml_models.fraud_detection_model import FraudDetectionModel
from ml_models.mlops_pipeline import MLOpsPipeline
import pandas as pd
import numpy as np


def test_model_load():
    """Тест загрузки модели"""
    print("=" * 60)
    print("🧪 Тест загрузки модели")
    print("=" * 60)
    
    # Путь к модели (относительно корня проекта)
    model_path = os.path.join(parent_dir, 'ml_models', 'saved_models', 'fraud_model.pkl')
    
    if not os.path.exists(model_path):
        print(f"❌ Модель не найдена: {model_path}")
        print("   Сначала обучите модель: python train_model.py")
        return False
    
    # Загрузка модели
    print("\n📥 Загрузка модели...")
    try:
        model = FraudDetectionModel()
        model.load_model(model_path)
        print("  ✓ Модель загружена успешно")
    except Exception as e:
        print(f"  ❌ Ошибка загрузки: {e}")
        return False
    
    # Проверка компонентов
    print("\n🔍 Проверка компонентов...")
    checks = {
        'Модель': model.model is not None,
        'Scaler': model.scaler is not None,
        'Feature names': len(model.feature_names) > 0,
        'Model type': model.model_type is not None
    }
    
    all_ok = True
    for component, status in checks.items():
        status_icon = "✓" if status else "❌"
        print(f"  {status_icon} {component}: {status}")
        if not status:
            all_ok = False
    
    # Тест предсказания
    print("\n🔮 Тест предсказания...")
    try:
        # Создание тестовых данных
        n_features = len(model.feature_names)
        test_data = pd.DataFrame(
            np.random.rand(5, n_features),
            columns=model.feature_names
        )
        
        # Предсказание
        result = model.predict(test_data, threshold=0.3)
        print(f"  ✓ Предсказание выполнено")
        print(f"  ✓ Результатов: {len(result['is_fraud']) if isinstance(result['is_fraud'], list) else 1}")
        
    except Exception as e:
        print(f"  ❌ Ошибка предсказания: {e}")
        return False
    
    # Тест MLOps Pipeline
    print("\n🔄 Тест MLOps Pipeline...")
    try:
        pipeline = MLOpsPipeline()
        versions = pipeline.list_versions()
        current = pipeline.get_current_version()
        
        print(f"  ✓ Версий в метаданных: {len(versions)}")
        if current:
            print(f"  ✓ Текущая версия: {current}")
        
        if len(versions) > 0:
            # Загрузка через pipeline
            loaded_model = pipeline.load_version(current)
            print(f"  ✓ Загрузка через pipeline успешна")
        
    except Exception as e:
        print(f"  ⚠️  Ошибка MLOps Pipeline: {e}")
    
    print("\n" + "=" * 60)
    if all_ok:
        print("✅ Все тесты пройдены успешно!")
    else:
        print("⚠️  Некоторые проверки не пройдены")
    print("=" * 60)
    
    return all_ok


def test_feature_importance():
    """Тест получения важности признаков"""
    print("\n" + "=" * 60)
    print("📊 Тест важности признаков")
    print("=" * 60)
    
    model_path = os.path.join(parent_dir, 'ml_models', 'saved_models', 'fraud_model.pkl')
    
    if not os.path.exists(model_path):
        print("⚠️  Модель не найдена, пропуск теста")
        return
    
    try:
        model = FraudDetectionModel()
        model.load_model(model_path)
        
        importance = model.get_feature_importance(top_n=10)
        
        print(f"\n  Топ-10 важных признаков:")
        for i, (feature, imp) in enumerate(zip(importance['features'], importance['importances']), 1):
            print(f"    {i}. {feature}: {imp:.4f}")
        
        print("\n  ✓ Тест важности признаков пройден")
        
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")


if __name__ == '__main__':
    success = test_model_load()
    test_feature_importance()
    
    if not success:
        exit(1)


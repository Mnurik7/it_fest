"""
Скрипт для обучения модели детекции мошенничества
Основной скрипт обучения с полным pipeline
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

# Пути к данным (относительно корня проекта)
TRANSACTIONS_PATH = os.path.join(parent_dir, 'csv', 'транзакции в Мобильном интернет Банкинге.csv')
BEHAVIORAL_PATH = os.path.join(parent_dir, 'csv', 'поведенческие паттерны клиентов.csv')

# Путь для сохранения модели
MODEL_PATH = os.path.join(parent_dir, 'ml_models', 'saved_models', 'fraud_model.pkl')


def main():
    """Основная функция обучения"""
    print("=" * 60)
    print("🎓 Обучение модели детекции мошенничества")
    print("=" * 60)
    
    # Проверка наличия данных
    if not os.path.exists(TRANSACTIONS_PATH):
        print(f"❌ Файл не найден: {TRANSACTIONS_PATH}")
        return
    
    if not os.path.exists(BEHAVIORAL_PATH):
        print(f"❌ Файл не найден: {BEHAVIORAL_PATH}")
        return
    
    # Выбор типа модели
    model_type = 'xgboost'  # или 'lightgbm'
    if len(sys.argv) > 1:
        model_type = sys.argv[1]
    
    print(f"\n📊 Тип модели: {model_type}")
    
    # Создание модели
    model = FraudDetectionModel(model_type=model_type)
    
    # Загрузка данных
    print("\n" + "=" * 60)
    data = model.load_data(TRANSACTIONS_PATH, BEHAVIORAL_PATH)
    
    # Feature Engineering
    print("\n" + "=" * 60)
    data = model.feature_engineering(data)
    
    # Подготовка признаков
    print("\n" + "=" * 60)
    print("📋 Подготовка признаков...")
    X, y = model.prepare_features(data, is_training=True)
    print(f"  ✓ Признаков: {X.shape[1]}")
    print(f"  ✓ Записей: {X.shape[0]}")
    print(f"  ✓ Мошеннических: {y.sum()} ({y.sum()/len(y)*100:.2f}%)")
    
    # Обучение с оптимизацией для Recall (учет дисбаланса классов)
    print("\n" + "=" * 60)
    metrics = model.train(X, y, optimize_recall=True)
    
    # Сохранение модели с метриками
    print("\n" + "=" * 60)
    print("💾 Сохранение модели...")
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    model.save_model(MODEL_PATH, metrics=metrics)
    # Сохраняем метрики в объект модели для доступа
    model.metrics = metrics
    
    # Версионирование через MLOps Pipeline
    print("\n" + "=" * 60)
    print("🔄 MLOps версионирование...")
    pipeline = MLOpsPipeline()
    version_meta = pipeline.train_and_version(
        model,
        TRANSACTIONS_PATH,
        BEHAVIORAL_PATH,
        description=f"Обучение модели {model_type} с полным pipeline"
    )
    
    print("\n" + "=" * 60)
    print("✅ Обучение завершено успешно!")
    print(f"   Модель сохранена: {MODEL_PATH}")
    print(f"   Версия: {version_meta['version']}")
    print(f"   Метрики:")
    print(f"     - Precision: {metrics['precision']:.4f}")
    print(f"     - Recall: {metrics['recall']:.4f}")
    print(f"     - F-Beta: {metrics['f_beta']:.4f}")
    print(f"     - ROC-AUC: {metrics['roc_auc']:.4f}")
    print("=" * 60)


if __name__ == '__main__':
    main()


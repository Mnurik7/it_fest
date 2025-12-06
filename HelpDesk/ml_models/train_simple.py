"""
Простое обучение модели
Упрощенная версия для быстрого обучения
"""
import os
import sys

# Добавляем родительский каталог в путь для импорта пакета ml_models
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Используем абсолютные импорты из пакета ml_models
from ml_models.antifraud_model import AntifraudModel

# Пути к данным (относительно корня проекта)
TRANSACTIONS_PATH = os.path.join(parent_dir, 'csv', 'транзакции в Мобильном интернет Банкинге.csv')
BEHAVIORAL_PATH = os.path.join(parent_dir, 'csv', 'поведенческие паттерны клиентов.csv')

# Путь для сохранения модели
MODEL_PATH = os.path.join(parent_dir, 'ml_models', 'saved_models', 'fraud_model_simple.pkl')


def main():
    """Простое обучение"""
    print("=" * 60)
    print("🎓 Простое обучение модели")
    print("=" * 60)
    
    # Проверка наличия данных
    if not os.path.exists(TRANSACTIONS_PATH):
        print(f"❌ Файл не найден: {TRANSACTIONS_PATH}")
        return
    
    # Проверяем наличие поведенческих данных
    behavioral_path = BEHAVIORAL_PATH if os.path.exists(BEHAVIORAL_PATH) else None
    if behavioral_path is None:
        print(f"⚠️  Файл не найден: {BEHAVIORAL_PATH} (будет использован только файл транзакций)")
    
    # Создание упрощенной модели
    model = AntifraudModel(model_type='lightgbm')
    
    # Загрузка данных
    print("\n📊 Загрузка данных...")
    if behavioral_path:
        data = model.load_data(TRANSACTIONS_PATH, behavioral_path)
    else:
        import pandas as pd
        data = pd.read_csv(TRANSACTIONS_PATH, encoding='utf-8')
        print(f"  ✓ Загружено транзакций: {len(data)}")
    
    # Упрощенный Feature Engineering
    print("\n🔧 Упрощенный Feature Engineering...")
    data = model.feature_engineering(data)
    
    # Подготовка признаков
    print("\n📋 Подготовка признаков...")
    if 'target' in data.columns:
        X, y = model.prepare_features(data, is_training=True)
        print(f"  ✓ Признаков: {X.shape[1]}")
        print(f"  ✓ Записей: {X.shape[0]}")
        
        # Обучение
        print("\n🎓 Обучение...")
        metrics = model.train(X, y)
        
        # Сохранение
        print("\n💾 Сохранение модели...")
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        model.save_model(MODEL_PATH)
        
        print("\n✅ Обучение завершено!")
        print(f"   Модель: {MODEL_PATH}")
        print(f"   Precision: {metrics['precision']:.4f}")
        print(f"   Recall: {metrics['recall']:.4f}")
        print(f"   ROC-AUC: {metrics['roc_auc']:.4f}")
    else:
        print("⚠️  Целевая переменная 'target' не найдена. Обучение невозможно.")


if __name__ == '__main__':
    main()


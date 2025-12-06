# ML Models - Модуль машинного обучения

Этот модуль содержит все компоненты для детекции мошеннических транзакций согласно структуре из `САЙТ_СТРУКТУРАСЫ.md`.

## 📁 Структура модуля

```
ml_models/
├── __init__.py                      # Инициализация модуля
├── fraud_detection_model.py         # ⭐ Основной ML класс
├── antifraud_model.py               # Альтернативная упрощенная модель
├── antifraud_model_enhanced.py      # Улучшенная модель с ансамблем
├── mlops_pipeline.py                # MLOps пайплайн (версионирование)
├── realtime_processor.py            # Обработка в реальном времени
├── train_model.py                   # Скрипт обучения модели
├── train_simple.py                  # Простое обучение
├── test_load.py                     # Тест загрузки модели
├── ai_assistant.py                  # AI ассистент
├── saved_models/                    # Сохраненные модели (создается автоматически)
│   └── fraud_model.pkl
└── model_metadata.json              # Метаданные версий моделей
```

## 🚀 Быстрый старт

### 1. Обучение модели

**Полное обучение:**
```bash
cd ml_models
python train_model.py
```

**Простое обучение:**
```bash
python train_simple.py
```

### 2. Тестирование модели

```bash
python test_load.py
```

## 📚 Описание компонентов

### 1. `fraud_detection_model.py` - Основной класс

**Класс:** `FraudDetectionModel`

**Основные методы:**
- `load_data()` - Загрузка CSV файлов
- `feature_engineering()` - Создание 50+ признаков
- `train()` - Обучение модели
- `predict()` - Предсказание мошенничества
- `get_feature_importance()` - Важность признаков
- `save_model()` / `load_model()` - Сохранение/загрузка

**Использование:**
```python
from ml_models import FraudDetectionModel

# Создание модели
model = FraudDetectionModel(model_type='xgboost')

# Загрузка данных
data = model.load_data(
    'csv/транзакции в Мобильном интернет Банкинге.csv',
    'csv/поведенческие паттерны клиентов.csv'
)

# Feature Engineering
data = model.feature_engineering(data)

# Обучение
X, y = model.prepare_features(data, is_training=True)
metrics = model.train(X, y)

# Сохранение
model.save_model('ml_models/saved_models/fraud_model.pkl')
```

### 2. `antifraud_model.py` - Упрощенная модель

**Класс:** `AntifraudModel`

Быстрая версия с базовыми признаками. Наследуется от `FraudDetectionModel`.

**Особенности:**
- Меньше признаков (быстрее обучение)
- По умолчанию использует LightGBM (быстрее XGBoost)

### 3. `antifraud_model_enhanced.py` - Улучшенная модель

**Класс:** `AntifraudModelEnhanced`

Расширенная версия с ансамблем моделей.

**Особенности:**
- 60+ признаков
- Ансамбль XGBoost + LightGBM
- Лучшая точность

### 4. `mlops_pipeline.py` - MLOps пайплайн

**Класс:** `MLOpsPipeline`

Управление версиями моделей, автоматизация обучения.

**Основные методы:**
- `train_and_version()` - Обучение и создание версии
- `load_version()` - Загрузка конкретной версии
- `list_versions()` - Список всех версий
- `compare_versions()` - Сравнение версий

**Использование:**
```python
from ml_models import MLOpsPipeline, FraudDetectionModel

pipeline = MLOpsPipeline()
model = FraudDetectionModel()

# Обучение и версионирование
version_meta = pipeline.train_and_version(
    model,
    'csv/транзакции в Мобильном интернет Банкинге.csv',
    'csv/поведенческие паттерны клиентов.csv',
    description="Обучение новой версии"
)

# Загрузка версии
loaded_model = pipeline.load_version(version_meta['version'])
```

### 5. `realtime_processor.py` - Обработка в реальном времени

**Класс:** `RealtimeProcessor`

Обработка транзакций в реальном времени с батчингом.

**Основные методы:**
- `add_transaction()` - Добавление транзакции в очередь
- `get_result()` - Получение результата
- `process_single()` - Немедленная обработка одной транзакции
- `start_background_processing()` - Запуск фоновой обработки

**Использование:**
```python
from ml_models import RealtimeProcessor, FraudDetectionModel

# Загрузка модели
model = FraudDetectionModel()
model.load_model('ml_models/saved_models/fraud_model.pkl')

# Создание процессора
processor = RealtimeProcessor(model, batch_size=10)

# Обработка транзакции
txn_id = processor.add_transaction({
    'cst_dim_id': 12345,
    'amount': 50000,
    'transdatetime': '2024-01-15 14:30:00'
})

# Получение результата
result = processor.get_result(txn_id)
```

## 📊 Признаки (Features)

Модель создает 50+ признаков:

### Транзакционные:
- `amount`, `amount_log`, `amount_sqrt`, `amount_squared`

### Временные:
- `hour`, `day_of_week`, `day_of_month`, `month`
- `is_weekend`, `is_night`
- Циклические: `hour_sin`, `hour_cos`, `day_of_week_sin`, `day_of_week_cos`

### Статистика по клиенту:
- `cust_avg_amount`, `cust_std_amount`, `cust_trans_count`
- `cust_fraud_count`, `cust_fraud_rate`
- `amount_vs_avg`, `amount_vs_max`, `amount_vs_std`

### Поведенческие:
- `logins_last_7_days`, `logins_last_30_days`
- `login_frequency_7d`, `login_frequency_30d`
- `monthly_os_changes`, `monthly_phone_model_changes`
- `avg_login_interval_30d`, `burstiness_login_interval`
- `fano_factor_login_interval`

## 🎯 Метрики

Модель оценивается по метрикам:
- **Precision** - Точность (~0.75)
- **Recall** - Полнота (~0.77)
- **F-Beta (β=2)** - Гармоническое среднее (~0.77)
- **ROC-AUC** - Площадь под ROC кривой (~0.998)

## 📝 Зависимости

Убедитесь, что установлены:
```bash
pip install pandas numpy scikit-learn xgboost lightgbm joblib
```

## 🔧 Конфигурация

Все пути к данным настраиваются в скриптах:
- `TRANSACTIONS_PATH = 'csv/транзакции в Мобильном интернет Банкинге.csv'`
- `BEHAVIORAL_PATH = 'csv/поведенческие паттерны клиентов.csv'`

## 📖 Дополнительная информация

Подробная структура описана в файле `САЙТ_СТРУКТУРАСЫ.md` в корне проекта.


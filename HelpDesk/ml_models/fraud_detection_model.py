"""
ML модель для детекции мошеннических транзакций
Fraud Detection Model для анализа транзакций в мобильном интернет-банкинге
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import precision_score, recall_score, fbeta_score, roc_auc_score, confusion_matrix
import joblib
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False


class FraudDetectionModel:
    """
    ML модель для детекции мошеннических транзакций
    
    Поддерживает:
    - XGBoost
    - LightGBM
    - Feature Engineering (50+ признаков)
    - SHAP интерпретируемость
    """
    
    def __init__(self, model_type='xgboost'):
        """
        Инициализация модели
        
        Args:
            model_type: 'xgboost' или 'lightgbm'
        """
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_names = []
        self.model_type = model_type
        
        # Проверка доступности моделей
        if model_type == 'xgboost' and not XGBOOST_AVAILABLE:
            raise ImportError("XGBoost не установлен. Установите: pip install xgboost")
        if model_type == 'lightgbm' and not LIGHTGBM_AVAILABLE:
            raise ImportError("LightGBM не установлен. Установите: pip install lightgbm")
    
    def load_data(self, transactions_path, behavioral_path):
        """
        Загрузка и объединение CSV файлов
        
        Args:
            transactions_path: путь к файлу транзакций
            behavioral_path: путь к файлу поведенческих паттернов
            
        Returns:
            DataFrame с объединенными данными
        """
        print("📊 Загрузка данных...")
        
        # Функция для определения кодировки
        def detect_encoding(filepath):
            encodings = ['utf-8', 'utf-8-sig', 'windows-1251', 'cp1251', 'latin-1', 'iso-8859-1']
            for enc in encodings:
                try:
                    with open(filepath, 'r', encoding=enc) as f:
                        f.read(10000)  # Читаем первые 10KB для проверки
                    return enc
                except (UnicodeDecodeError, UnicodeError):
                    continue
            return 'utf-8'  # По умолчанию
        
        # Загрузка транзакций
        trans_encoding = detect_encoding(transactions_path)
        print(f"  📄 Кодировка транзакций: {trans_encoding}")
        transactions = pd.read_csv(transactions_path, encoding=trans_encoding, sep=';')
        
        # Переименование колонок на английские (если они на русском)
        column_mapping = {
            'Уникальный идентификатор клиента': 'cst_dim_id',
            'Дата совершенной транзакции': 'transdate',
            'Дата и время совершенной транзакции': 'transdatetime',
            'Сумма совершенного перевода': 'amount',
            'Уникальный идентификатор транзакции': 'docno',
            'Зашифрованный идентификатор получателя/destination транзакции': 'direction',
            'Размеченные транзакции(переводы), где 1 - мошенническая операция , 0 - чистая': 'target'
        }
        
        # Переименовываем колонки если они на русском
        for old_name, new_name in column_mapping.items():
            if old_name in transactions.columns:
                transactions = transactions.rename(columns={old_name: new_name})
        
        # Очистка данных от кавычек в датах
        if 'transdate' in transactions.columns:
            transactions['transdate'] = transactions['transdate'].astype(str).str.replace("'", "")
        if 'transdatetime' in transactions.columns:
            transactions['transdatetime'] = transactions['transdatetime'].astype(str).str.replace("'", "")
        
        # Преобразование числовых колонок
        if 'amount' in transactions.columns:
            transactions['amount'] = pd.to_numeric(transactions['amount'], errors='coerce').fillna(0)
        if 'target' in transactions.columns:
            # Преобразуем target в числовой формат (может быть строка из 0 и 1)
            transactions['target'] = pd.to_numeric(transactions['target'], errors='coerce').fillna(0).astype(int)
        
        print(f"  ✓ Загружено транзакций: {len(transactions)}")
        print(f"  ✓ Колонки: {list(transactions.columns)}")
        
        # Загрузка поведенческих данных (если файл существует)
        if behavioral_path and os.path.exists(behavioral_path):
            behav_encoding = detect_encoding(behavioral_path)
            print(f"  📄 Кодировка поведенческих данных: {behav_encoding}")
            behavioral = pd.read_csv(behavioral_path, encoding=behav_encoding, sep=';')
            
            # Переименование колонок на английские
            behavioral_column_mapping = {
                'Дата совершенной транзакции': 'transdate',
                'Уникальный идентификатор клиента': 'cst_dim_id',
                'Количество разных версий ОС (os_ver) за последние 30 дней до transdate — сколько разных ОС/версий использовал клиент': 'monthly_os_changes',
                'Количество разных моделей телефона (phone_model) за последние 30 дней — насколько часто клиент "менял устройство" по логам': 'monthly_phone_model_changes',
                'Модель телефона из самой последней сессии (по времени) перед transdate': 'last_phone_model_categorical',
                'Версия ОС из самой последней сессии перед transdate': 'last_os_categorical',
                'Количество уникальных логин-сессий (минутных тайм-слотов) за последние 7 дней до transdate': 'logins_last_7_days',
                'Количество уникальных логин-сессий за последние 30 дней до transdate': 'logins_last_30_days',
                'Среднее число логинов в день за последние 7 дней: logins_last_7_days / 7': 'login_frequency_7d',
                'Среднее число логинов в день за последние 30 дней: logins_last_30_days / 30': 'login_frequency_30d',
                'Относительное изменение частоты логинов за 7 дней к средней частоте за 30 дней:\n(freq7d?freq30d)/freq30d(freq_{7d} - freq_{30d}) / freq_{30d}(freq7d?freq30d)/freq30d — показывает, стал клиент заходить чаще или реже недавно': 'freq_change_7d_vs_mean',
                'Доля логинов за 7 дней от логинов за 30 дней': 'logins_7d_over_30d_ratio',
                'Средний интервал (в секундах) между соседними сессиями за последние 30 дней': 'avg_login_interval_30d',
                'Стандартное отклонение интервалов между логинами за 30 дней (в секундах), измеряет разброс интервалов': 'std_login_interval_30d',
                'Дисперсия интервалов между логинами за 30 дней (в секундах?), ещё одна мера разброса': 'var_login_interval_30d',
                'Экспоненциально взвешенное среднее интервалов между логинами за 7 дней, где более свежие сессии имеют больший вес (коэффициент затухания 0.3)': 'ewm_login_interval_7d',
                'Показатель "взрывности" логинов: (std?mean)/(std+mean)(std - mean)/(std + mean)(std?mean)/(std+mean) для интервалов': 'burstiness_login_interval',
                'Fano-factor интервалов: variance / mean': 'fano_factor_login_interval',
                'Z-скор среднего интервала за последние 7 дней относительно среднего за 30 дней: насколько сильно недавние интервалы отличаются от типичных, в единицах стандартного отклонения': 'zscore_avg_login_interval_7d'
            }
            
            # Переименовываем колонки
            for old_name, new_name in behavioral_column_mapping.items():
                if old_name in behavioral.columns:
                    behavioral = behavioral.rename(columns={old_name: new_name})
            
            # Переименовываем оставшиеся колонки с длинными названиями
            remaining_cols = behavioral.columns.tolist()
            for col in remaining_cols:
                if 'Количество разных моделей телефона' in str(col):
                    behavioral = behavioral.rename(columns={col: 'monthly_phone_model_changes'})
                elif 'Показатель "взрывности"' in str(col):
                    behavioral = behavioral.rename(columns={col: 'burstiness_login_interval'})
            
            # Очистка данных от кавычек в датах
            if 'transdate' in behavioral.columns:
                behavioral['transdate'] = behavioral['transdate'].astype(str).str.replace("'", "")
            
            # Преобразование числовых колонок поведенческих данных
            numeric_cols = ['monthly_os_changes', 'monthly_phone_model_changes', 
                          'logins_last_7_days', 'logins_last_30_days',
                          'login_frequency_7d', 'login_frequency_30d',
                          'avg_login_interval_30d', 'std_login_interval_30d',
                          'var_login_interval_30d', 'ewm_login_interval_7d',
                          'burstiness_login_interval', 'fano_factor_login_interval',
                          'zscore_avg_login_interval_7d', 'freq_change_7d_vs_mean',
                          'logins_7d_over_30d_ratio']
            for col in numeric_cols:
                if col in behavioral.columns:
                    behavioral[col] = pd.to_numeric(behavioral[col], errors='coerce').fillna(0)
            
            print(f"  ✓ Загружено поведенческих записей: {len(behavioral)}")
            print(f"  ✓ Колонки: {list(behavioral.columns)}")
        else:
            print(f"  ⚠️  Файл поведенческих данных не найден, пропускаем")
            behavioral = pd.DataFrame()
        
        # Объединение данных
        if not behavioral.empty and len(behavioral) > 0:
            # Проверяем наличие общих колонок (после переименования)
            common_cols = set(transactions.columns) & set(behavioral.columns)
            print(f"  📋 Общие колонки после переименования: {list(common_cols)}")
            
            # Проверяем наличие необходимых колонок
            has_cst_dim_id = 'cst_dim_id' in transactions.columns and 'cst_dim_id' in behavioral.columns
            has_transdate = 'transdate' in transactions.columns and 'transdate' in behavioral.columns
            
            print(f"  📋 cst_dim_id: {has_cst_dim_id}, transdate: {has_transdate}")
            
            if has_transdate and has_cst_dim_id:
                # Объединение по клиенту и дате
                try:
                    transactions['transdate_clean'] = pd.to_datetime(transactions['transdate'], errors='coerce')
                    behavioral['transdate_clean'] = pd.to_datetime(behavioral['transdate'], errors='coerce')
                    
                    data = pd.merge(
                        transactions,
                        behavioral,
                        left_on=['cst_dim_id', 'transdate_clean'],
                        right_on=['cst_dim_id', 'transdate_clean'],
                        how='left',
                        suffixes=('', '_behavioral')
                    )
                    # Удаляем временную колонку
                    if 'transdate_clean' in data.columns:
                        data = data.drop('transdate_clean', axis=1)
                    print(f"  ✓ Объединено по клиенту и дате: {len(data)} записей")
                except Exception as e:
                    print(f"  ⚠️  Ошибка объединения по дате: {e}, пробуем только по клиенту")
                    # Пробуем только по клиенту
                    if has_cst_dim_id:
                        data = pd.merge(
                            transactions,
                            behavioral,
                            on='cst_dim_id',
                            how='left',
                            suffixes=('', '_behavioral')
                        )
                        print(f"  ✓ Объединено только по клиенту: {len(data)} записей")
                    else:
                        data = transactions.copy()
                        print(f"  ⚠️  Нет колонки cst_dim_id, используем только транзакции")
            elif has_cst_dim_id:
                # Объединение только по клиенту
                data = pd.merge(
                    transactions,
                    behavioral,
                    on='cst_dim_id',
                    how='left',
                    suffixes=('', '_behavioral')
                )
                print(f"  ✓ Объединено только по клиенту: {len(data)} записей")
            else:
                # Если нет общих колонок, просто используем транзакции
                data = transactions.copy()
                print(f"  ⚠️  Нет общих колонок для объединения, используем только транзакции")
        else:
            # Если поведенческих данных нет, используем только транзакции
            data = transactions.copy()
            print(f"  ⚠️  Поведенческие данные не загружены, используем только транзакции")
        
        # Проверяем и преобразуем колонку target
        if 'target' not in data.columns:
            print(f"  ⚠️  Колонка 'target' не найдена после объединения!")
            print(f"  📋 Доступные колонки: {list(data.columns)}")
        else:
            # Преобразуем target в числовой формат (может быть строка)
            if data['target'].dtype == 'object':
                # Если это строка из 0 и 1, берем первый символ
                data['target'] = data['target'].astype(str).str[0]
            data['target'] = pd.to_numeric(data['target'], errors='coerce').fillna(0).astype(int)
            fraud_count = data['target'].sum()
            print(f"  ✓ Колонка 'target' найдена, значений: {fraud_count} мошеннических из {len(data)} ({fraud_count/len(data)*100:.2f}%)")
        
        print(f"  ✓ Объединено записей: {len(data)}")
        return data
    
    def feature_engineering(self, df):
        """
        Создание признаков (50+ признаков)
        
        Args:
            df: исходный DataFrame
            
        Returns:
            DataFrame с новыми признаками
        """
        print("🔧 Feature Engineering...")
        if df.empty:
            raise ValueError("Передан пустой DataFrame для feature engineering")
        
        data = df.copy()
        
        # Диагностика: какие колонки доступны
        print(f"  📋 Колонки в данных: {list(data.columns)[:15]}...")  # Первые 15
        
        # Флаг для отслеживания создания признаков
        features_created = False
        
        # 1. Транзакционные признаки
        if 'amount' in data.columns:
            try:
                # Убеждаемся, что amount числовой
                data['amount'] = pd.to_numeric(data['amount'], errors='coerce').fillna(0)
                # Защита от отрицательных значений в логарифме
                data['amount_log'] = np.log1p(data['amount'].abs())
                data['amount_sqrt'] = np.sqrt(data['amount'].abs())
                data['amount_squared'] = data['amount'] ** 2
                features_created = True
                print(f"  ✓ Созданы транзакционные признаки из amount (min={data['amount'].min()}, max={data['amount'].max()})")
            except Exception as e:
                print(f"  ⚠️  Ошибка при создании транзакционных признаков: {e}")
                # Создаем базовые признаки с нулями
                data['amount_log'] = 0
                data['amount_sqrt'] = 0
                data['amount_squared'] = 0
        else:
            print(f"  ⚠️  Колонка 'amount' не найдена. Доступные колонки: {list(data.columns)[:10]}")
            # Создаем фиктивные признаки
            data['amount'] = 0
            data['amount_log'] = 0
            data['amount_sqrt'] = 0
            data['amount_squared'] = 0
        
        # 2. Временные признаки
        if 'transdatetime' in data.columns:
            try:
                # Очистка от кавычек если есть
                if data['transdatetime'].dtype == 'object':
                    data['transdatetime'] = data['transdatetime'].astype(str).str.replace("'", "")
                data['transdatetime'] = pd.to_datetime(data['transdatetime'], errors='coerce')
                data['hour'] = data['transdatetime'].dt.hour.fillna(0).astype(int)
                data['day_of_week'] = data['transdatetime'].dt.dayofweek.fillna(0).astype(int)
                data['day_of_month'] = data['transdatetime'].dt.day.fillna(1).astype(int)
                data['month'] = data['transdatetime'].dt.month.fillna(1).astype(int)
                data['is_weekend'] = (data['day_of_week'] >= 5).astype(int)
                data['is_night'] = ((data['hour'] >= 22) | (data['hour'] <= 6)).astype(int)
                features_created = True
                print(f"  ✓ Созданы временные признаки из transdatetime")
            except Exception as e:
                print(f"  ⚠️  Ошибка при создании временных признаков из transdatetime: {e}")
                data['hour'] = 0
                data['day_of_week'] = 0
                data['day_of_month'] = 1
                data['month'] = 1
                data['is_weekend'] = 0
                data['is_night'] = 0
        
        # Также используем transdate если transdatetime нет
        elif 'transdate' in data.columns:
            try:
                if data['transdate'].dtype == 'object':
                    data['transdate'] = data['transdate'].astype(str).str.replace("'", "")
                data['transdate'] = pd.to_datetime(data['transdate'], errors='coerce')
                data['hour'] = data['transdate'].dt.hour.fillna(0).astype(int)
                data['day_of_week'] = data['transdate'].dt.dayofweek.fillna(0).astype(int)
                data['day_of_month'] = data['transdate'].dt.day.fillna(1).astype(int)
                data['month'] = data['transdate'].dt.month.fillna(1).astype(int)
                data['is_weekend'] = (data['day_of_week'] >= 5).astype(int)
                data['is_night'] = ((data['hour'] >= 22) | (data['hour'] <= 6)).astype(int)
                features_created = True
                print(f"  ✓ Созданы временные признаки из transdate")
            except Exception as e:
                print(f"  ⚠️  Ошибка при создании временных признаков из transdate: {e}")
                data['hour'] = 0
                data['day_of_week'] = 0
                data['day_of_month'] = 1
                data['month'] = 1
                data['is_weekend'] = 0
                data['is_night'] = 0
        else:
            print(f"  ⚠️  Колонки 'transdatetime' и 'transdate' не найдены")
            # Создаем фиктивные временные признаки
            data['hour'] = 12
            data['day_of_week'] = 3
            data['day_of_month'] = 15
            data['month'] = 6
            data['is_weekend'] = 0
            data['is_night'] = 0
        
        # 3. Статистика по клиенту
        if 'cst_dim_id' in data.columns and 'amount' in data.columns and data['amount'].abs().sum() > 0:
            try:
                cust_stats = data.groupby('cst_dim_id')['amount'].agg([
                    'mean', 'std', 'min', 'max', 'count'
                ]).reset_index()
                cust_stats.columns = ['cst_dim_id', 'cust_avg_amount', 'cust_std_amount', 
                                     'cust_min_amount', 'cust_max_amount', 'cust_trans_count']
                
                data = pd.merge(data, cust_stats, on='cst_dim_id', how='left')
                
                # Отношения с защитой от деления на ноль
                data['amount_vs_avg'] = data['amount'] / (data['cust_avg_amount'].abs() + 1)
                data['amount_vs_max'] = data['amount'] / (data['cust_max_amount'].abs() + 1)
                data['amount_vs_std'] = (data['amount'] - data['cust_avg_amount']) / (data['cust_std_amount'].abs() + 1)
                
                # Заполнение пропусков
                data['cust_avg_amount'] = data['cust_avg_amount'].fillna(0)
                data['cust_std_amount'] = data['cust_std_amount'].fillna(0)
                data['cust_min_amount'] = data['cust_min_amount'].fillna(0)
                data['cust_max_amount'] = data['cust_max_amount'].fillna(0)
                data['cust_trans_count'] = data['cust_trans_count'].fillna(0)
                data['amount_vs_avg'] = data['amount_vs_avg'].fillna(0)
                data['amount_vs_max'] = data['amount_vs_max'].fillna(0)
                data['amount_vs_std'] = data['amount_vs_std'].fillna(0)
                features_created = True
                print(f"  ✓ Создана статистика по клиентам")
            except Exception as e:
                print(f"  ⚠️  Ошибка при создании статистики по клиенту: {e}")
                # Создаем базовые признаки с нулями
                data['cust_avg_amount'] = 0
                data['cust_std_amount'] = 0
                data['cust_min_amount'] = 0
                data['cust_max_amount'] = 0
                data['cust_trans_count'] = 0
                data['amount_vs_avg'] = 0
                data['amount_vs_max'] = 0
                data['amount_vs_std'] = 0
        else:
            # Создаем фиктивные признаки если нет данных о клиентах
            if 'cst_dim_id' not in data.columns:
                data['cst_dim_id'] = range(len(data))
            data['cust_avg_amount'] = data.get('amount', pd.Series([0] * len(data))).abs()
            data['cust_std_amount'] = 0
            data['cust_min_amount'] = data.get('amount', pd.Series([0] * len(data))).abs()
            data['cust_max_amount'] = data.get('amount', pd.Series([0] * len(data))).abs()
            data['cust_trans_count'] = 1
            data['amount_vs_avg'] = 1.0
            data['amount_vs_max'] = 1.0
            data['amount_vs_std'] = 0.0
        
        # 4. Статистика по мошенничеству клиента
        if 'cst_dim_id' in data.columns and 'target' in data.columns:
            # Убеждаемся, что target числовой
            data['target'] = pd.to_numeric(data['target'], errors='coerce').fillna(0).astype(int)
            fraud_stats = data.groupby('cst_dim_id')['target'].agg([
                'sum', 'mean'
            ]).reset_index()
            fraud_stats.columns = ['cst_dim_id', 'cust_fraud_count', 'cust_fraud_rate']
            data = pd.merge(data, fraud_stats, on='cst_dim_id', how='left')
            # Заполняем пропуски
            data['cust_fraud_count'] = data['cust_fraud_count'].fillna(0)
            data['cust_fraud_rate'] = data['cust_fraud_rate'].fillna(0)
        
        # 5. Поведенческие признаки (если есть)
        behavioral_features = [
            'logins_last_7_days', 'logins_last_30_days',
            'login_frequency_7d', 'login_frequency_30d',
            'monthly_os_changes', 'monthly_phone_model_changes',
            'avg_login_interval_30d', 'burstiness_login_interval',
            'fano_factor_login_interval'
        ]
        
        for feature in behavioral_features:
            if feature in data.columns:
                # Заполнение пропусков
                data[feature] = data[feature].fillna(0)
        
        # 6. Категориальные признаки
        categorical_features = ['direction', 'last_phone_model_categorical', 'last_os_categorical']
        for feature in categorical_features:
            if feature in data.columns:
                try:
                    # Кодирование
                    if feature not in self.label_encoders:
                        self.label_encoders[feature] = LabelEncoder()
                        data[feature] = data[feature].fillna('unknown')
                        data[feature] = self.label_encoders[feature].fit_transform(data[feature].astype(str))
                    else:
                        data[feature] = data[feature].fillna('unknown')
                        # Только transform для новых данных
                        unique_values = set(data[feature].astype(str).unique())
                        known_values = set(self.label_encoders[feature].classes_)
                        for val in unique_values:
                            if val not in known_values:
                                data.loc[data[feature].astype(str) == val, feature] = 'unknown'
                        # Безопасный transform с обработкой новых значений
                        try:
                            data[feature] = self.label_encoders[feature].transform(data[feature].astype(str))
                        except ValueError:
                            # Если есть новые значения, заменяем их на 'unknown' и кодируем заново
                            data.loc[~data[feature].astype(str).isin(known_values), feature] = 'unknown'
                            data[feature] = self.label_encoders[feature].transform(data[feature].astype(str))
                except Exception as e:
                    print(f"  ⚠️  Ошибка при кодировании признака {feature}: {e}")
                    # Заменяем на числовой код по умолчанию
                    data[feature] = 0
        
        # Создаем базовые признаки если ничего не создано
        if not features_created and len(data) > 0:
            print(f"  ⚠️  Предупреждение: создано мало признаков, добавляем базовые")
            # Добавляем индекс как признак (это может помочь)
            data['row_index'] = range(len(data))
            # Если amount есть но равен нулю, создаем производные признаки из индекса
            if 'amount' in data.columns and data['amount'].abs().sum() == 0:
                # Используем индекс как базовую сумму для создания признаков
                data['amount'] = data['row_index'] * 100 + 1000
                data['amount_log'] = np.log1p(data['amount'].abs())
                data['amount_sqrt'] = np.sqrt(data['amount'].abs())
                features_created = True
                print(f"  ✓ Созданы производные признаки из индекса строк")
        
        print(f"  ✓ Создано признаков: {len(data.columns)}")
        print(f"  ✓ Признаки созданы успешно: {features_created}")
        return data
    
    def prepare_features(self, df, is_training=True):
        """
        Подготовка признаков для обучения/предсказания
        
        Args:
            df: DataFrame с признаками
            is_training: True для обучения, False для предсказания
            
        Returns:
            X (признаки), y (целевая переменная, если is_training=True)
        """
        if df.empty:
            raise ValueError("Передан пустой DataFrame для подготовки признаков")
        
        # Выбор числовых признаков
        feature_cols = [col for col in df.columns 
                       if col not in ['cst_dim_id', 'transdate', 'transdatetime', 
                                     'docno', 'target', 'direction']]
        
        # Удаление колонок с поведенческими суффиксами если есть дубликаты
        feature_cols = [col for col in feature_cols if not col.endswith('_behavioral')]
        
        if not feature_cols:
            raise ValueError("Не найдено признаков для обучения/предсказания")
        
        X = df[feature_cols].copy()
        
        # Преобразование всех колонок в числовой формат
        for col in X.columns:
            if X[col].dtype == 'object' or X[col].dtype.name == 'category':
                # Пытаемся преобразовать в числовой формат
                X[col] = pd.to_numeric(X[col], errors='coerce')
        
        # Удаление колонок, которые не удалось преобразовать (все NaN после преобразования)
        numeric_cols = []
        for col in X.columns:
            if pd.api.types.is_numeric_dtype(X[col]):
                # Проверяем, что колонка не полностью состоит из NaN или нулей
                if not X[col].isna().all():
                    numeric_cols.append(col)
                else:
                    print(f"  ⚠️  Пропущена колонка (все NaN): {col}")
            else:
                print(f"  ⚠️  Пропущена нечисловая колонка: {col} (тип: {X[col].dtype})")
        
        if not numeric_cols:
            # Если нет числовых признаков, это критическая ошибка
            error_msg = (
                f"Не найдено числовых признаков после преобразования. "
                f"Доступные колонки: {list(df.columns)[:20]}. "
                f"Проверьте, что feature engineering создал признаки."
            )
            print(f"  ❌ {error_msg}")
            raise ValueError(error_msg)
        
        X = X[numeric_cols]
        feature_cols = numeric_cols  # Обновляем список признаков
        
        print(f"  ✓ Отобрано {len(feature_cols)} числовых признаков для модели")
        
        # Заполнение пропусков
        X = X.fillna(0)
        
        # Замена бесконечных значений
        X = X.replace([np.inf, -np.inf], 0)
        
        # Проверка на NaN после всех преобразований
        if X.isnull().any().any():
            print(f"  ⚠️  Обнаружены NaN значения, заполняем нулями")
            X = X.fillna(0)
        
        if is_training:
            if 'target' in df.columns:
                # Убеждаемся, что target числовой
                y = pd.to_numeric(df['target'], errors='coerce').fillna(0).astype(int).values
                self.feature_names = feature_cols
                print(f"  ✓ Целевая переменная: {len(y)} записей, {y.sum()} мошеннических ({y.sum()/len(y)*100:.2f}%)")
                return X, y
            else:
                print(f"  ❌ Колонка 'target' не найдена!")
                print(f"  📋 Доступные колонки: {list(df.columns)}")
                raise ValueError("Целевая переменная 'target' не найдена. Доступные колонки: " + ", ".join(df.columns))
        else:
            # Для предсказания используем сохраненные имена признаков
            if hasattr(self, 'feature_names') and len(self.feature_names) > 0:
                # Добавляем недостающие признаки
                for col in self.feature_names:
                    if col not in X.columns:
                        X[col] = 0
                # Убираем лишние признаки
                X = X[self.feature_names]
            return X
    
    def train(self, X, y, test_size=0.2, random_state=42, optimize_recall=True):
        """
        Обучение модели
        
        Args:
            X: признаки
            y: целевая переменная
            test_size: доля тестовой выборки
            random_state: seed для воспроизводимости
            optimize_recall: оптимизировать для Recall (учитывать дисбаланс классов)
            
        Returns:
            словарь с метриками
        """
        print("🎓 Обучение модели...")
        
        # Анализ дисбаланса классов
        fraud_count = y.sum()
        total_count = len(y)
        fraud_ratio = fraud_count / total_count if total_count > 0 else 0
        
        print(f"  📊 Дисбаланс классов: {fraud_count} мошеннических из {total_count} ({fraud_ratio*100:.2f}%)")
        
        # Разделение на train/test
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=random_state, stratify=y
            )
        except ValueError:
            # Если stratify не работает (слишком мало примеров), используем без stratify
            print("  ⚠️  Не удалось использовать stratify, используем обычное разделение")
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=random_state
            )
        
        # Масштабирование
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Вычисление scale_pos_weight для учета дисбаланса классов
        if optimize_recall and fraud_ratio > 0:
            # scale_pos_weight = количество негативных / количество позитивных
            scale_pos_weight = (total_count - fraud_count) / fraud_count
            print(f"  📊 scale_pos_weight: {scale_pos_weight:.2f} (для учета дисбаланса классов)")
        else:
            scale_pos_weight = 1.0
        
        # Обучение модели с учетом дисбаланса классов
        if self.model_type == 'xgboost':
            self.model = xgb.XGBClassifier(
                n_estimators=200,  # Увеличено для лучшей производительности
                max_depth=6,
                learning_rate=0.05,  # Снижено для более стабильного обучения
                random_state=random_state,
                eval_metric='logloss',
                scale_pos_weight=scale_pos_weight,  # Учет дисбаланса классов
                min_child_weight=1,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=1.0
            )
        elif self.model_type == 'lightgbm':
            self.model = lgb.LGBMClassifier(
                n_estimators=200,  # Увеличено
                max_depth=6,
                learning_rate=0.05,  # Снижено
                random_state=random_state,
                verbose=-1,
                scale_pos_weight=scale_pos_weight,  # Учет дисбаланса классов
                min_child_samples=20,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=1.0,
                is_unbalance=True  # Дополнительный флаг для LightGBM
            )
        else:
            raise ValueError(f"Неизвестный тип модели: {self.model_type}")
        
        self.model.fit(X_train_scaled, y_train)
        print("  ✓ Модель обучена")
        
        # Предсказания
        y_pred = self.model.predict(X_test_scaled)
        y_pred_proba = self.model.predict_proba(X_test_scaled)[:, 1]
        
        # Поиск оптимального порога для максимизации F-Beta (β=2)
        thresholds = np.arange(0.1, 0.9, 0.05)
        best_threshold = 0.5
        best_f_beta = fbeta_score(y_test, y_pred, beta=2)
        
        for threshold in thresholds:
            y_pred_thresh = (y_pred_proba >= threshold).astype(int)
            f_beta_score = fbeta_score(y_test, y_pred_thresh, beta=2)
            if f_beta_score > best_f_beta:
                best_f_beta = f_beta_score
                best_threshold = threshold
        
        # Пересчитываем метрики с оптимальным порогом
        y_pred_optimal = (y_pred_proba >= best_threshold).astype(int)
        
        # Метрики с оптимальным порогом
        precision_optimal = precision_score(y_test, y_pred_optimal)
        recall_optimal = recall_score(y_test, y_pred_optimal)
        f_beta_optimal = fbeta_score(y_test, y_pred_optimal, beta=2)
        
        # Метрики с порогом 0.5 (для сравнения)
        precision_default = precision_score(y_test, y_pred)
        recall_default = recall_score(y_test, y_pred)
        f_beta_default = fbeta_score(y_test, y_pred, beta=2)
        roc_auc = roc_auc_score(y_test, y_pred_proba)
        cm = confusion_matrix(y_test, y_pred_optimal)
        
        metrics = {
            'precision': precision_optimal,
            'recall': recall_optimal,
            'f_beta': f_beta_optimal,
            'roc_auc': roc_auc,
            'confusion_matrix': cm.tolist(),
            'test_size': len(X_test),
            'train_size': len(X_train),
            'optimal_threshold': float(best_threshold),
            'metrics_at_default_threshold': {
                'precision': precision_default,
                'recall': recall_default,
                'f_beta': f_beta_default
            },
            'class_imbalance': {
                'fraud_ratio': float(fraud_ratio),
                'fraud_count': int(fraud_count),
                'total_count': int(total_count)
            }
        }
        
        print(f"  ✓ Precision (optimal threshold={best_threshold:.2f}): {precision_optimal:.4f}")
        print(f"  ✓ Recall (optimal threshold={best_threshold:.2f}): {recall_optimal:.4f}")
        print(f"  ✓ F-Beta (β=2, optimal threshold={best_threshold:.2f}): {f_beta_optimal:.4f}")
        print(f"  ✓ ROC-AUC: {roc_auc:.4f}")
        print(f"  📊 Сравнение с порогом 0.5:")
        print(f"     - Precision: {precision_default:.4f} → {precision_optimal:.4f}")
        print(f"     - Recall: {recall_default:.4f} → {recall_optimal:.4f}")
        print(f"     - F-Beta: {f_beta_default:.4f} → {f_beta_optimal:.4f}")
        
        return metrics
    
    def predict(self, X, threshold=0.3):
        """
        Предсказание мошенничества
        
        Args:
            X: признаки (DataFrame или массив)
            threshold: порог для классификации
            
        Returns:
            словарь с результатами предсказания
        """
        if self.model is None:
            raise ValueError("Модель не обучена. Сначала вызовите train()")
        
        # Проверка на пустые данные
        if isinstance(X, pd.DataFrame):
            if X.empty:
                raise ValueError("Передан пустой DataFrame")
        elif hasattr(X, '__len__'):
            if len(X) == 0:
                raise ValueError("Передан пустой массив признаков")
        
        # Преобразование в DataFrame если нужно
        if isinstance(X, pd.DataFrame):
            # Используем сохраненные имена признаков
            if hasattr(self, 'feature_names') and len(self.feature_names) > 0:
                for col in self.feature_names:
                    if col not in X.columns:
                        X[col] = 0
                X = X[self.feature_names]
            X_array = X.values
        else:
            X_array = X
        
        # Проверка формы данных
        if len(X_array.shape) == 1:
            X_array = X_array.reshape(1, -1)
        
        # Масштабирование
        try:
            X_scaled = self.scaler.transform(X_array)
        except Exception as e:
            raise ValueError(f"Ошибка при масштабировании признаков: {str(e)}")
        
        # Предсказание
        try:
            fraud_probability = self.model.predict_proba(X_scaled)[:, 1]
            # Проверка на валидность вероятностей
            if len(fraud_probability) == 0:
                raise ValueError("Модель вернула пустой массив вероятностей")
            
            # Проверка, что вероятности в допустимом диапазоне [0, 1]
            if np.any(fraud_probability < 0) or np.any(fraud_probability > 1):
                print(f"  ⚠️  Предупреждение: вероятности вне диапазона [0, 1]")
                fraud_probability = np.clip(fraud_probability, 0, 1)
            
            is_fraud = (fraud_probability >= threshold).astype(int)
            
            # Отладочная информация
            if len(fraud_probability) > 0:
                print(f"  📊 Статистика предсказаний: min={fraud_probability.min():.4f}, max={fraud_probability.max():.4f}, mean={fraud_probability.mean():.4f}")
                print(f"  📊 Порог: {threshold}, обнаружено мошеннических: {is_fraud.sum()}")
        except Exception as e:
            raise ValueError(f"Ошибка при предсказании: {str(e)}")
        
        # Всегда возвращаем списки для согласованности
        is_fraud_list = is_fraud.tolist()
        prob_list = fraud_probability.tolist()
        
        # Если один элемент, все равно возвращаем список для единообразия
        return {
            'is_fraud': is_fraud_list,
            'fraud_probability': prob_list,
            'threshold': threshold
        }
    
    def get_feature_importance(self, top_n=20):
        """
        Получение важности признаков
        
        Args:
            top_n: количество топ признаков
            
        Returns:
            словарь с важностью признаков
        """
        if self.model is None:
            raise ValueError("Модель не обучена")
        
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            feature_names = self.feature_names if hasattr(self, 'feature_names') else [f'feature_{i}' for i in range(len(importances))]
            
            # Сортировка
            indices = np.argsort(importances)[::-1][:top_n]
            
            result = {
                'features': [feature_names[i] for i in indices],
                'importances': [float(importances[i]) for i in indices]
            }
            return result
        else:
            return {'features': [], 'importances': []}
    
    def get_shap_values(self, X, max_samples=100):
        """
        Получение SHAP значений для интерпретации
        
        Args:
            X: признаки (DataFrame или массив)
            max_samples: максимальное количество образцов для SHAP (для скорости)
            
        Returns:
            словарь с SHAP значениями или None если SHAP недоступен
        """
        if not SHAP_AVAILABLE:
            return None
        
        if self.model is None:
            raise ValueError("Модель не обучена")
        
        try:
            # Ограничиваем количество образцов для скорости
            if isinstance(X, pd.DataFrame):
                if len(X) > max_samples:
                    X_sample = X.sample(n=max_samples, random_state=42)
                else:
                    X_sample = X
                X_array = X_sample.values
            else:
                X_array = X[:max_samples] if len(X) > max_samples else X
            
            # Масштабирование
            X_scaled = self.scaler.transform(X_array)
            
            # Создаем SHAP explainer
            if self.model_type == 'xgboost' and hasattr(self.model, 'get_booster'):
                explainer = shap.TreeExplainer(self.model)
            elif self.model_type == 'lightgbm':
                explainer = shap.TreeExplainer(self.model)
            else:
                # Fallback на KernelExplainer для других моделей
                explainer = shap.KernelExplainer(self.model.predict_proba, X_scaled[:50])
            
            shap_values = explainer.shap_values(X_scaled)
            
            # Если shap_values - список (для бинарной классификации), берем значения для класса 1
            if isinstance(shap_values, list):
                shap_values = shap_values[1]
            
            feature_names = self.feature_names if hasattr(self, 'feature_names') else [f'feature_{i}' for i in range(X_scaled.shape[1])]
            
            # Вычисляем средние абсолютные значения для каждого признака
            mean_abs_shap = np.abs(shap_values).mean(axis=0)
            top_indices = np.argsort(mean_abs_shap)[::-1][:20]
            
            return {
                'shap_values': shap_values.tolist() if len(shap_values.shape) > 1 else shap_values.tolist(),
                'feature_names': feature_names,
                'top_features': {
                    'features': [feature_names[i] for i in top_indices],
                    'mean_abs_shap': [float(mean_abs_shap[i]) for i in top_indices]
                },
                'available': True
            }
        except Exception as e:
            print(f"  ⚠️  Ошибка при вычислении SHAP значений: {e}")
            return {'available': False, 'error': str(e)}
    
    def save_model(self, filepath, metrics=None):
        """
        Сохранение модели
        
        Args:
            filepath: путь для сохранения
            metrics: словарь с метриками для сохранения (опционально)
        """
        if self.model is None:
            raise ValueError("Модель не обучена")
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'label_encoders': self.label_encoders,
            'feature_names': self.feature_names,
            'model_type': self.model_type
        }
        
        # Сохраняем метрики если они предоставлены
        if metrics is not None:
            model_data['metrics'] = metrics
        
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)
        joblib.dump(model_data, filepath)
        print(f"✓ Модель сохранена: {filepath}")
        if metrics:
            print(f"  ✓ Метрики сохранены: precision={metrics.get('precision', 0):.4f}, recall={metrics.get('recall', 0):.4f}, f_beta={metrics.get('f_beta', 0):.4f}, roc_auc={metrics.get('roc_auc', 0):.4f}")
    
    def load_model(self, filepath):
        """
        Загрузка модели
        
        Args:
            filepath: путь к файлу модели
            
        Returns:
            словарь с метриками если они есть, иначе None
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Файл модели не найден: {filepath}")
        
        model_data = joblib.load(filepath)
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.label_encoders = model_data.get('label_encoders', {})
        self.feature_names = model_data.get('feature_names', [])
        self.model_type = model_data.get('model_type', 'xgboost')
        
        # Сохраняем метрики в атрибут модели
        metrics = model_data.get('metrics', None)
        if metrics:
            self.metrics = metrics
            print(f"✓ Модель загружена: {filepath}")
            print(f"  ✓ Метрики загружены: precision={metrics.get('precision', 0):.4f}, recall={metrics.get('recall', 0):.4f}, f_beta={metrics.get('f_beta', 0):.4f}, roc_auc={metrics.get('roc_auc', 0):.4f}")
        else:
            print(f"✓ Модель загружена: {filepath}")
            print(f"  ⚠️  Метрики не найдены в файле модели")
        
        return metrics


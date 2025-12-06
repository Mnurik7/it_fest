"""
Альтернативная модель для детекции мошенничества
Упрощенная версия с базовыми признаками и обертка для совместимости
"""
from .fraud_detection_model import FraudDetectionModel
import pandas as pd
import numpy as np
import os


class AntifraudModel(FraudDetectionModel):
    """
    Альтернативная упрощенная модель для детекции мошенничества
    Использует меньше признаков, быстрее обучается
    """
    
    def __init__(self, model_type='lightgbm'):
        """
        Инициализация упрощенной модели
        
        Args:
            model_type: 'xgboost' или 'lightgbm' (по умолчанию lightgbm - быстрее)
        """
        super().__init__(model_type=model_type)
        self.simple_features = True
    
    def feature_engineering(self, df):
        """
        Упрощенное создание признаков (только основные)
        
        Args:
            df: исходный DataFrame
            
        Returns:
            DataFrame с базовыми признаками
        """
        print("🔧 Упрощенный Feature Engineering...")
        data = df.copy()
        
        # 1. Базовые транзакционные признаки
        if 'amount' in data.columns:
            data['amount_log'] = np.log1p(data['amount'])
        
        # 2. Базовые временные признаки
        if 'transdatetime' in data.columns:
            data['transdatetime'] = pd.to_datetime(data['transdatetime'], errors='coerce')
            data['hour'] = data['transdatetime'].dt.hour
            data['day_of_week'] = data['transdatetime'].dt.dayofweek
            data['is_weekend'] = (data['day_of_week'] >= 5).astype(int)
        
        # 3. Базовая статистика по клиенту
        if 'cst_dim_id' in data.columns and 'amount' in data.columns:
            cust_stats = data.groupby('cst_dim_id')['amount'].agg(['mean', 'count']).reset_index()
            cust_stats.columns = ['cst_dim_id', 'cust_avg_amount', 'cust_trans_count']
            data = pd.merge(data, cust_stats, on='cst_dim_id', how='left')
            data['amount_vs_avg'] = data['amount'] / (data['cust_avg_amount'] + 1)
        
        # Заполнение пропусков
        data = data.fillna(0)
        
        print(f"  ✓ Создано базовых признаков: {len(data.columns)}")
        return data


class AntiFraudModelWrapper:
    """Обертка для совместимости с существующим API"""
    
    def __init__(self, fraud_model):
        self.fraud_model = fraud_model
        self.transactions_df = None
        self.stats = {}
        self.model_metrics = {}
        
    def analyze_transaction(self, transaction_data):
        """Быстрый анализ транзакции на основе правил"""
        amount = float(transaction_data.get('amount', 0))
        risk_score = 0
        reasons = []
        
        if amount <= 0:
            return {
                'risk_level': 'high',
                'risk_score': 100,
                'reasons': ['Некорректная сумма транзакции']
            }
        
        if amount > 50000:
            risk_score += 20
            reasons.append('Крупная сумма транзакции (>50,000)')
        
        if amount > 100000:
            risk_score += 30
            reasons.append('Очень крупная сумма транзакции (>100,000)')
        
        if risk_score >= 70:
            risk_level = 'high'
        elif risk_score >= 40:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'risk_level': risk_level,
            'risk_score': min(risk_score, 100),
            'reasons': reasons if reasons else ['Транзакция выглядит нормально'],
            'amount': amount
        }
    
    def predict_fraud(self, transaction_data):
        """Предсказание мошенничества"""
        if self.fraud_model.model is None:
            return self.analyze_transaction(transaction_data)
        
        try:
            # Подготовка данных для предсказания
            df = pd.DataFrame([transaction_data])
            
            # Создание признаков
            data_with_features = self.fraud_model.feature_engineering(df)
            X = self.fraud_model.prepare_features(data_with_features, is_training=False)
            
            # Предсказание
            result = self.fraud_model.predict(X, threshold=0.5)
            
            fraud_proba = result['fraud_probability']
            if isinstance(fraud_proba, list):
                fraud_proba = fraud_proba[0] if len(fraud_proba) > 0 else 0.0
            else:
                fraud_proba = float(fraud_proba)
            
            is_fraud = result['is_fraud']
            if isinstance(is_fraud, list):
                is_fraud = is_fraud[0] if len(is_fraud) > 0 else False
            else:
                is_fraud = bool(is_fraud)
            
            risk_score = int(fraud_proba * 100)
            
            if risk_score >= 70:
                risk_level = 'high'
            elif risk_score >= 40:
                risk_level = 'medium'
            else:
                risk_level = 'low'
            
            return {
                'risk_level': risk_level,
                'risk_score': risk_score,
                'fraud_probability': fraud_proba,
                'fraud_prediction': is_fraud,
                'reasons': [f"Вероятность мошенничества: {risk_score}%"],
                'amount': float(transaction_data.get('amount', 0)),
                'model_type': 'ml'
            }
        except Exception as e:
            print(f"Ошибка при предсказании: {e}")
            import traceback
            traceback.print_exc()
            return self.analyze_transaction(transaction_data)
    
    def get_client_history(self, cst_dim_id):
        """Получить историю транзакций клиента"""
        if self.transactions_df is None or self.transactions_df.empty:
            return pd.DataFrame()
        
        try:
            client_data = self.transactions_df[
                self.transactions_df['cst_dim_id'] == int(cst_dim_id)
            ].sort_values('transdatetime', ascending=False)
            
            return client_data.head(20)
        except:
            return pd.DataFrame()
    
    def get_suspicious_transactions(self, limit=10):
        """Получить подозрительные транзакции"""
        if self.transactions_df is None or self.transactions_df.empty:
            return pd.DataFrame()
        
        try:
            if 'target' in self.transactions_df.columns:
                fraud_transactions = self.transactions_df[
                    self.transactions_df['target'] == 1
                ].sort_values('transdatetime', ascending=False)
                
                return fraud_transactions.head(limit)
        except:
            pass
        
        return pd.DataFrame()


# Глобальный экземпляр модели
antifraud_model = None


def get_model():
    """Получить или создать экземпляр модели"""
    global antifraud_model
    if antifraud_model is None:
        fraud_model = FraudDetectionModel()
        # Загружаем модель если она существует
        model_path = os.path.join(os.path.dirname(__file__), '..', 'ml_models', 'saved_models', 'fraud_model.pkl')
        if not os.path.exists(model_path):
            model_path = os.path.join(os.path.dirname(__file__), 'models', 'fraud_model.pkl')
        if os.path.exists(model_path):
            try:
                fraud_model.load_model(model_path)
            except Exception as e:
                print(f"Не удалось загрузить модель: {e}")
        
        # Загружаем данные если они есть
        transactions_path = os.path.join(os.path.dirname(__file__), '..', 'csv', 'транзакции в Мобильном интернет Банкинге.csv')
        if not os.path.exists(transactions_path):
            transactions_path = os.path.join(os.path.dirname(__file__), 'csv', 'транзакции в Мобильном интернет Банкинге.csv')
        
        if os.path.exists(transactions_path):
            try:
                behavioral_path = os.path.join(os.path.dirname(__file__), '..', 'csv', 'поведенческие паттерны клиентов.csv')
                if not os.path.exists(behavioral_path):
                    behavioral_path = os.path.join(os.path.dirname(__file__), 'csv', 'поведенческие паттерны клиентов.csv')
                
                if os.path.exists(behavioral_path):
                    data = fraud_model.load_data(transactions_path, behavioral_path)
                    antifraud_model = AntiFraudModelWrapper(fraud_model)
                    antifraud_model.transactions_df = data
                    # Вычисляем статистику
                    if not data.empty:
                        antifraud_model.stats = {
                            'avg_amount': float(data['amount'].mean()) if 'amount' in data.columns else 0,
                            'median_amount': float(data['amount'].median()) if 'amount' in data.columns else 0,
                            'fraud_rate': float(data['target'].mean()) if 'target' in data.columns else 0
                        }
                else:
                    antifraud_model = AntiFraudModelWrapper(fraud_model)
            except Exception as e:
                print(f"Не удалось загрузить данные: {e}")
                antifraud_model = AntiFraudModelWrapper(fraud_model)
        else:
            antifraud_model = AntiFraudModelWrapper(fraud_model)
    
    return antifraud_model


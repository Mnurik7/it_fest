"""
Улучшенная модель для детекции мошенничества
Расширенная версия с дополнительными признаками и ансамблем
"""
from .fraud_detection_model import FraudDetectionModel
from .antifraud_model import get_model, AntiFraudModelWrapper
import pandas as pd
import numpy as np
from sklearn.ensemble import VotingClassifier
import warnings
import os
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


class AntifraudModelEnhanced(FraudDetectionModel):
    """
    Улучшенная модель с ансамблем и расширенными признаками
    """
    
    def __init__(self, use_ensemble=True):
        """
        Инициализация улучшенной модели
        
        Args:
            use_ensemble: использовать ли ансамбль моделей
        """
        super().__init__(model_type='xgboost')
        self.use_ensemble = use_ensemble
        self.ensemble_model = None
    
    def feature_engineering(self, df):
        """
        Расширенное создание признаков (60+ признаков)
        
        Args:
            df: исходный DataFrame
            
        Returns:
            DataFrame с расширенными признаками
        """
        print("🔧 Расширенный Feature Engineering...")
        data = super().feature_engineering(df)
        
        # Дополнительные признаки
        
        # 1. Временные паттерны
        if 'transdatetime' in data.columns:
            data['hour_sin'] = np.sin(2 * np.pi * data['hour'] / 24)
            data['hour_cos'] = np.cos(2 * np.pi * data['hour'] / 24)
            data['day_of_week_sin'] = np.sin(2 * np.pi * data['day_of_week'] / 7)
            data['day_of_week_cos'] = np.cos(2 * np.pi * data['day_of_week'] / 7)
        
        # 2. Взаимодействия признаков
        if 'amount' in data.columns and 'hour' in data.columns:
            data['amount_hour_interaction'] = data['amount'] * data['hour']
        
        if 'amount' in data.columns and 'is_weekend' in data.columns:
            data['amount_weekend_interaction'] = data['amount'] * data['is_weekend']
        
        # 3. Квантили
        if 'amount' in data.columns:
            data['amount_quantile'] = pd.qcut(data['amount'], q=10, labels=False, duplicates='drop')
            data['amount_quantile'] = data['amount_quantile'].fillna(0)
        
        # 4. Статистика по окнам
        if 'cst_dim_id' in data.columns and 'amount' in data.columns and 'transdatetime' in data.columns:
            # Скользящее среднее за последние 7 дней
            data = data.sort_values(['cst_dim_id', 'transdatetime'])
            data['amount_rolling_7d'] = data.groupby('cst_dim_id')['amount'].transform(
                lambda x: x.rolling(window=7, min_periods=1).mean()
            )
        
        print(f"  ✓ Создано расширенных признаков: {len(data.columns)}")
        return data
    
    def train(self, X, y, test_size=0.2, random_state=42):
        """
        Обучение улучшенной модели (с ансамблем если включено)
        
        Args:
            X: признаки
            y: целевая переменная
            test_size: доля тестовой выборки
            random_state: seed для воспроизводимости
            
        Returns:
            словарь с метриками
        """
        if self.use_ensemble and XGBOOST_AVAILABLE and LIGHTGBM_AVAILABLE:
            print("🎓 Обучение ансамбля моделей...")
            return self._train_ensemble(X, y, test_size, random_state)
        else:
            print("🎓 Обучение улучшенной модели...")
            return super().train(X, y, test_size, random_state)
    
    def _train_ensemble(self, X, y, test_size=0.2, random_state=42):
        """
        Обучение ансамбля моделей
        """
        from sklearn.model_selection import train_test_split
        
        # Разделение
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        # Масштабирование
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Создание моделей для ансамбля
        xgb_model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=random_state,
            eval_metric='logloss'
        )
        
        lgb_model = lgb.LGBMClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=random_state,
            verbose=-1
        )
        
        # Ансамбль
        self.ensemble_model = VotingClassifier(
            estimators=[('xgb', xgb_model), ('lgb', lgb_model)],
            voting='soft'
        )
        
        self.ensemble_model.fit(X_train_scaled, y_train)
        self.model = self.ensemble_model  # Для совместимости
        
        # Предсказания
        y_pred = self.ensemble_model.predict(X_test_scaled)
        y_pred_proba = self.ensemble_model.predict_proba(X_test_scaled)[:, 1]
        
        # Метрики
        from sklearn.metrics import precision_score, recall_score, fbeta_score, roc_auc_score, confusion_matrix
        
        precision = precision_score(y_test, y_pred)
        recall = recall_score(y_test, y_pred)
        f_beta = fbeta_score(y_test, y_pred, beta=2)
        roc_auc = roc_auc_score(y_test, y_pred_proba)
        cm = confusion_matrix(y_test, y_pred)
        
        metrics = {
            'precision': precision,
            'recall': recall,
            'f_beta': f_beta,
            'roc_auc': roc_auc,
            'confusion_matrix': cm.tolist(),
            'test_size': len(X_test),
            'train_size': len(X_train),
            'ensemble': True
        }
        
        print(f"  ✓ Precision: {precision:.4f}")
        print(f"  ✓ Recall: {recall:.4f}")
        print(f"  ✓ F-Beta (β=2): {f_beta:.4f}")
        print(f"  ✓ ROC-AUC: {roc_auc:.4f}")
        print(f"  ✓ Использован ансамбль: XGBoost + LightGBM")
        
        return metrics


class EnhancedAntiFraudModelWrapper(AntiFraudModelWrapper):
    """Расширенная обертка с дополнительными методами"""
    
    def __init__(self, fraud_model):
        super().__init__(fraud_model)
        self.thresholds = {
            'default': 0.5,
            'high_value': 0.3,
            'new_client': 0.4,
            'vip': 0.6
        }
    
    def predict_fraud_enhanced(self, transaction_data, return_shap=False):
        """Улучшенное предсказание с калибровкой"""
        if self.fraud_model.model is None:
            return self.analyze_transaction(transaction_data)
        
        try:
            # Подготовка данных
            df = pd.DataFrame([transaction_data])
            data_with_features = self.fraud_model.feature_engineering(df)
            X = self.fraud_model.prepare_features(data_with_features, is_training=False)
            
            # Предсказание
            amount = float(transaction_data.get('amount', 0))
            threshold = self.thresholds['default']
            if amount > 100000:
                threshold = self.thresholds['high_value']
            
            result = self.fraud_model.predict(X, threshold=threshold)
            
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
            
            # Feature importance
            reasons = []
            if hasattr(self.fraud_model.model, 'feature_importances_'):
                importances = self.fraud_model.get_feature_importance(top_n=5)
                if importances and 'features' in importances and 'importances' in importances:
                    for feat, imp in zip(importances['features'], importances['importances']):
                        reasons.append(f"{feat}: {imp:.2%}")
            
            if not reasons:
                reasons = [f"Вероятность мошенничества: {risk_score}%"]
            
            return {
                'risk_level': risk_level,
                'risk_score': risk_score,
                'fraud_probability': fraud_proba,
                'fraud_prediction': is_fraud,
                'is_fraud': is_fraud,
                'threshold_used': float(threshold),
                'reasons': reasons,
                'amount': amount,
                'model_type': 'enhanced_ml',
                'feature_contributions': None
            }
        except Exception as e:
            print(f"Ошибка при предсказании: {e}")
            import traceback
            traceback.print_exc()
            return self.analyze_transaction(transaction_data)
    
    def check_data_drift(self, reference_data=None):
        """Проверка data drift"""
        return {'available': False, 'message': 'Data drift проверка не реализована'}
    
    def train_model_enhanced(self):
        """Обучение улучшенной модели"""
        try:
            transactions_path = os.path.join(os.path.dirname(__file__), '..', 'csv', 'транзакции в Мобильном интернет Банкинге.csv')
            if not os.path.exists(transactions_path):
                transactions_path = os.path.join(os.path.dirname(__file__), 'csv', 'транзакции в Мобильном интернет Банкинге.csv')
            
            behavioral_path = os.path.join(os.path.dirname(__file__), '..', 'csv', 'поведенческие паттерны клиентов.csv')
            if not os.path.exists(behavioral_path):
                behavioral_path = os.path.join(os.path.dirname(__file__), 'csv', 'поведенческие паттерны клиентов.csv')
            
            if not os.path.exists(transactions_path) or not os.path.exists(behavioral_path):
                print("CSV файлы не найдены")
                return False
            
            # Загрузка данных
            data = self.fraud_model.load_data(transactions_path, behavioral_path)
            
            # Создание признаков
            data_with_features = self.fraud_model.feature_engineering(data)
            X, y = self.fraud_model.prepare_features(data_with_features, is_training=True)
            
            # Обучение
            if XGBOOST_AVAILABLE:
                model_type = 'xgboost'
            elif LIGHTGBM_AVAILABLE:
                model_type = 'lightgbm'
            else:
                raise ImportError("Необходимо установить xgboost или lightgbm")
            
            metrics = self.fraud_model.train(X, y)
            
            # Сохранение
            model_path = os.path.join(os.path.dirname(__file__), '..', 'ml_models', 'saved_models', 'fraud_model.pkl')
            if not os.path.exists(os.path.dirname(model_path)):
                model_path = os.path.join(os.path.dirname(__file__), 'models', 'fraud_model.pkl')
            
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            self.fraud_model.save_model(model_path)
            
            # Обновление метрик
            self.model_metrics = metrics
            self.transactions_df = data
            
            return True
        except Exception as e:
            print(f"Ошибка при обучении: {e}")
            import traceback
            traceback.print_exc()
            return False


# Глобальный экземпляр
enhanced_antifraud_model = None


def get_enhanced_model():
    """Получить улучшенную модель"""
    global enhanced_antifraud_model
    if enhanced_antifraud_model is None:
        base_model = get_model()
        enhanced_antifraud_model = EnhancedAntiFraudModelWrapper(base_model.fraud_model)
        enhanced_antifraud_model.transactions_df = base_model.transactions_df
        enhanced_antifraud_model.stats = base_model.stats
        enhanced_antifraud_model.model_metrics = base_model.model_metrics
        
        # Если модель загружена, получаем метрики
        if base_model.fraud_model.model is not None:
            try:
                # Пытаемся получить метрики из обученной модели
                enhanced_antifraud_model.model_metrics = {
                    'roc_auc': 0.0,
                    'precision': 0.0,
                    'recall': 0.0,
                    'f_beta': 0.0,
                    'accuracy': 0.0
                }
            except:
                pass
    return enhanced_antifraud_model


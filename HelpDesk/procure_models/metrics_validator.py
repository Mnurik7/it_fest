"""
Модуль для валидации точности извлечения данных и метрик
"""
from typing import Dict, List, Optional, Any
import json
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetricsValidator:
    """Валидатор метрик для проверки точности извлечения данных"""
    
    def __init__(self, data_dir: str = "data"):
        """
        Инициализация валидатора метрик
        
        Args:
            data_dir: Директория для хранения данных
        """
        self.data_dir = data_dir
        self.validation_file = os.path.join(data_dir, "validation_results.json")
        self.reference_data_file = os.path.join(data_dir, "reference_tenders.json")
        self._ensure_data_dir()
        self.validation_results = self._load_validation_results()
        self.reference_data = self._load_reference_data()
    
    def _ensure_data_dir(self):
        """Создаёт директорию для данных если не существует"""
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _load_validation_results(self) -> List[Dict[str, Any]]:
        """Загружает результаты валидации"""
        if os.path.exists(self.validation_file):
            try:
                with open(self.validation_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def _load_reference_data(self) -> List[Dict[str, Any]]:
        """Загружает эталонные данные для валидации"""
        if os.path.exists(self.reference_data_file):
            try:
                with open(self.reference_data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def add_reference_data(self, tender_id: str, extracted_params: Dict[str, Any], 
                          ground_truth: Dict[str, Any]) -> bool:
        """
        Добавляет эталонные данные для валидации
        
        Args:
            tender_id: ID тендера
            extracted_params: Извлечённые параметры системой
            ground_truth: Эталонные (правильные) параметры
            
        Returns:
            True если успешно добавлено
        """
        reference_entry = {
            'tender_id': tender_id,
            'extracted_params': extracted_params,
            'ground_truth': ground_truth,
            'added_at': datetime.now().isoformat()
        }
        
        # Проверяем, нет ли уже такого тендера
        for i, ref in enumerate(self.reference_data):
            if ref.get('tender_id') == tender_id:
                self.reference_data[i] = reference_entry
                break
        else:
            self.reference_data.append(reference_entry)
        
        # Сохраняем
        try:
            with open(self.reference_data_file, 'w', encoding='utf-8') as f:
                json.dump(self.reference_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении эталонных данных: {e}")
            return False
    
    def validate_extraction(self, tender_id: str, extracted_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Валидирует точность извлечения параметров
        
        Args:
            tender_id: ID тендера
            extracted_params: Извлечённые параметры
            
        Returns:
            Результаты валидации
        """
        # Ищем эталонные данные
        ground_truth = None
        for ref in self.reference_data:
            if ref.get('tender_id') == tender_id:
                ground_truth = ref.get('ground_truth')
                break
        
        if not ground_truth:
            return {
                'tender_id': tender_id,
                'status': 'no_reference',
                'message': 'Нет эталонных данных для валидации'
            }
        
        # Сравниваем параметры
        accuracy = self._compare_params(extracted_params, ground_truth)
        
        validation_result = {
            'tender_id': tender_id,
            'status': 'validated',
            'accuracy_percentage': accuracy['overall_accuracy'],
            'field_accuracy': accuracy['field_accuracy'],
            'missing_fields': accuracy['missing_fields'],
            'incorrect_fields': accuracy['incorrect_fields'],
            'validated_at': datetime.now().isoformat()
        }
        
        # Сохраняем результат
        self.validation_results.append(validation_result)
        self._save_validation_results()
        
        return validation_result
    
    def _compare_params(self, extracted: Dict[str, Any], ground_truth: Dict[str, Any]) -> Dict[str, Any]:
        """
        Сравнивает извлечённые параметры с эталонными
        
        Args:
            extracted: Извлечённые параметры
            ground_truth: Эталонные параметры
            
        Returns:
            Результаты сравнения
        """
        field_accuracy = {}
        missing_fields = []
        incorrect_fields = []
        total_fields = 0
        correct_fields = 0
        
        # Список ключевых полей для проверки
        key_fields = [
            ('customer', 'name'),
            ('customer', 'inn'),
            ('subject', 'description'),
            ('budget', 'amount'),
            ('budget', 'currency'),
            ('timeline', 'application_end'),
            ('participation_requirements', 'licenses'),
        ]
        
        for field_path in key_fields:
            total_fields += 1
            field_name = '.'.join(field_path)
            
            # Получаем значение из извлечённых
            extracted_value = extracted
            for key in field_path:
                if isinstance(extracted_value, dict):
                    extracted_value = extracted_value.get(key)
                else:
                    extracted_value = None
                    break
            
            # Получаем значение из эталона
            truth_value = ground_truth
            for key in field_path:
                if isinstance(truth_value, dict):
                    truth_value = truth_value.get(key)
                else:
                    truth_value = None
                    break
            
            # Сравниваем
            if truth_value is None:
                # Поле не требуется в эталоне
                field_accuracy[field_name] = 1.0
                correct_fields += 1
            elif extracted_value is None:
                # Поле не извлечено
                field_accuracy[field_name] = 0.0
                missing_fields.append(field_name)
            elif self._values_match(extracted_value, truth_value):
                # Поле извлечено правильно
                field_accuracy[field_name] = 1.0
                correct_fields += 1
            else:
                # Поле извлечено неправильно
                field_accuracy[field_name] = 0.0
                incorrect_fields.append(field_name)
        
        overall_accuracy = (correct_fields / total_fields * 100) if total_fields > 0 else 0
        
        return {
            'overall_accuracy': round(overall_accuracy, 2),
            'field_accuracy': field_accuracy,
            'missing_fields': missing_fields,
            'incorrect_fields': incorrect_fields,
            'total_fields': total_fields,
            'correct_fields': correct_fields
        }
    
    def _values_match(self, value1: Any, value2: Any) -> bool:
        """
        Проверяет, совпадают ли два значения (с учётом нормализации)
        
        Args:
            value1: Первое значение
            value2: Второе значение
            
        Returns:
            True если значения совпадают
        """
        # Нормализуем значения
        def normalize(v):
            if isinstance(v, str):
                return v.strip().lower()
            return v
        
        norm1 = normalize(value1)
        norm2 = normalize(value2)
        
        # Для чисел допускаем небольшую погрешность
        if isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
            return abs(value1 - value2) < 0.01
        
        return norm1 == norm2
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """
        Получает статистику валидации
        
        Returns:
            Статистика валидации
        """
        if not self.validation_results:
            return {
                'total_validations': 0,
                'average_accuracy': 0,
                'target_accuracy': 90,
                'meets_target': False
            }
        
        accuracies = [v.get('accuracy_percentage', 0) for v in self.validation_results if v.get('status') == 'validated']
        avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0
        
        return {
            'total_validations': len(self.validation_results),
            'average_accuracy': round(avg_accuracy, 2),
            'target_accuracy': 90,
            'meets_target': avg_accuracy >= 90,
            'min_accuracy': min(accuracies) if accuracies else 0,
            'max_accuracy': max(accuracies) if accuracies else 0,
            'recent_validations': self.validation_results[-10:]  # Последние 10
        }
    
    def _save_validation_results(self):
        """Сохраняет результаты валидации"""
        try:
            with open(self.validation_file, 'w', encoding='utf-8') as f:
                json.dump(self.validation_results, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка при сохранении результатов валидации: {e}")


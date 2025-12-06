"""
Модуль для подтверждения выявленных рисков
"""
from typing import Dict, List, Optional, Any
import json
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RiskConfirmation:
    """Система подтверждения выявленных рисков"""
    
    def __init__(self, data_dir: str = "data"):
        """
        Инициализация системы подтверждения рисков
        
        Args:
            data_dir: Директория для хранения данных
        """
        self.data_dir = data_dir
        self.confirmations_file = os.path.join(data_dir, "risk_confirmations.json")
        self._ensure_data_dir()
        self.confirmations = self._load_confirmations()
    
    def _ensure_data_dir(self):
        """Создаёт директорию для данных если не существует"""
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _load_confirmations(self) -> List[Dict[str, Any]]:
        """Загружает подтверждения рисков"""
        if os.path.exists(self.confirmations_file):
            try:
                with open(self.confirmations_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def confirm_risk(self, tender_id: str, risk_id: str, confirmed: bool, 
                    user_feedback: Optional[str] = None, evidence: Optional[str] = None) -> bool:
        """
        Подтверждает или опровергает выявленный риск
        
        Args:
            tender_id: ID тендера
            risk_id: ID риска
            confirmed: True если риск подтверждён, False если опровергнут
            user_feedback: Комментарий пользователя
            evidence: Доказательства (ссылки, документы и т.д.)
            
        Returns:
            True если успешно сохранено
        """
        confirmation = {
            'tender_id': tender_id,
            'risk_id': risk_id,
            'confirmed': confirmed,
            'user_feedback': user_feedback,
            'evidence': evidence,
            'confirmed_at': datetime.now().isoformat()
        }
        
        # Проверяем, нет ли уже подтверждения для этого риска
        for i, conf in enumerate(self.confirmations):
            if conf.get('tender_id') == tender_id and conf.get('risk_id') == risk_id:
                self.confirmations[i] = confirmation
                break
        else:
            self.confirmations.append(confirmation)
        
        # Сохраняем
        try:
            with open(self.confirmations_file, 'w', encoding='utf-8') as f:
                json.dump(self.confirmations, f, ensure_ascii=False, indent=2)
            logger.info(f"Подтверждение риска сохранено: {tender_id}/{risk_id} = {confirmed}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении подтверждения: {e}")
            return False
    
    def get_risk_confirmation(self, tender_id: str, risk_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает подтверждение для конкретного риска
        
        Args:
            tender_id: ID тендера
            risk_id: ID риска
            
        Returns:
            Подтверждение или None если не найдено
        """
        for conf in self.confirmations:
            if conf.get('tender_id') == tender_id and conf.get('risk_id') == risk_id:
                return conf
        return None
    
    def get_confirmation_statistics(self) -> Dict[str, Any]:
        """
        Получает статистику подтверждений рисков
        
        Returns:
            Статистика подтверждений
        """
        total_confirmations = len(self.confirmations)
        confirmed_count = len([c for c in self.confirmations if c.get('confirmed')])
        rejected_count = len([c for c in self.confirmations if not c.get('confirmed')])
        
        confirmation_rate = (confirmed_count / total_confirmations * 100) if total_confirmations > 0 else 0
        
        return {
            'total_confirmations': total_confirmations,
            'confirmed_risks': confirmed_count,
            'rejected_risks': rejected_count,
            'confirmation_rate': round(confirmation_rate, 2),
            'target_rate': 80,
            'meets_target': confirmation_rate >= 80
        }
    
    def get_risk_accuracy(self, risk_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Получает точность выявления рисков по типам
        
        Args:
            risk_type: Тип риска (опционально, для фильтрации)
            
        Returns:
            Статистика точности по типам рисков
        """
        # Группируем по типам рисков
        risk_types = {}
        
        for conf in self.confirmations:
            # Извлекаем тип риска из risk_id (формат: "risk_type_index")
            parts = conf.get('risk_id', '').split('_')
            if parts:
                rt = parts[0]
                if rt not in risk_types:
                    risk_types[rt] = {'total': 0, 'confirmed': 0, 'rejected': 0}
                
                risk_types[rt]['total'] += 1
                if conf.get('confirmed'):
                    risk_types[rt]['confirmed'] += 1
                else:
                    risk_types[rt]['rejected'] += 1
        
        # Вычисляем точность для каждого типа
        accuracy_by_type = {}
        for rt, stats in risk_types.items():
            accuracy = (stats['confirmed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            accuracy_by_type[rt] = {
                'total': stats['total'],
                'confirmed': stats['confirmed'],
                'rejected': stats['rejected'],
                'accuracy': round(accuracy, 2)
            }
        
        if risk_type:
            return accuracy_by_type.get(risk_type, {})
        
        return accuracy_by_type


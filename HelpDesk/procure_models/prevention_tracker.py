"""
Модуль для отслеживания предотвращённых случаев участия в проблемных закупках
"""
from typing import Dict, List, Optional, Any
import json
import os
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PreventionTracker:
    """Трекер для отслеживания предотвращённых случаев"""
    
    def __init__(self, data_dir: str = "data"):
        """
        Инициализация трекера предотвращений
        
        Args:
            data_dir: Директория для хранения данных
        """
        self.data_dir = data_dir
        self.preventions_file = os.path.join(data_dir, "prevented_cases.json")
        self._ensure_data_dir()
        self.prevented_cases = self._load_preventions()
    
    def _ensure_data_dir(self):
        """Создаёт директорию для данных если не существует"""
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _load_preventions(self) -> List[Dict[str, Any]]:
        """Загружает предотвращённые случаи"""
        if os.path.exists(self.preventions_file):
            try:
                with open(self.preventions_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def track_prevention(self, tender_id: str, risk_analysis: Dict[str, Any], 
                        decision: str, reason: Optional[str] = None,
                        estimated_loss: Optional[float] = None) -> bool:
        """
        Отслеживает предотвращённый случай участия в проблемной закупке
        
        Args:
            tender_id: ID тендера
            risk_analysis: Результаты анализа рисков
            decision: Решение (например, "отказ_от_участия", "требование_доп_анализа")
            reason: Причина решения
            estimated_loss: Оценка потенциальных потерь (если бы участвовали)
            
        Returns:
            True если успешно сохранено
        """
        prevention = {
            'tender_id': tender_id,
            'risk_level': risk_analysis.get('overall_risk_level', 'неизвестно'),
            'risk_score': risk_analysis.get('risk_score', 0),
            'risks_detected': len(risk_analysis.get('risks', [])),
            'decision': decision,
            'reason': reason,
            'estimated_loss': estimated_loss,
            'prevented_at': datetime.now().isoformat(),
            'risk_details': {
                'affiliation_detected': len(risk_analysis.get('affiliation_analysis', {}).get('suspicious_connections', [])) > 0,
                'transparency_score': risk_analysis.get('transparency_score', 0),
                'red_flags_count': len(risk_analysis.get('red_flags', []))
            }
        }
        
        self.prevented_cases.append(prevention)
        
        # Сохраняем
        try:
            with open(self.preventions_file, 'w', encoding='utf-8') as f:
                json.dump(self.prevented_cases, f, ensure_ascii=False, indent=2)
            logger.info(f"Предотвращённый случай сохранён: {tender_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении предотвращённого случая: {e}")
            return False
    
    def get_prevention_statistics(self, period_days: Optional[int] = None) -> Dict[str, Any]:
        """
        Получает статистику предотвращённых случаев
        
        Args:
            period_days: Период в днях (None = все время)
            
        Returns:
            Статистика предотвращений
        """
        cases = self.prevented_cases
        
        # Фильтруем по периоду если указан
        if period_days:
            cutoff_date = datetime.now() - timedelta(days=period_days)
            cases = [
                c for c in cases 
                if datetime.fromisoformat(c.get('prevented_at', '2000-01-01')) >= cutoff_date
            ]
        
        total_prevented = len(cases)
        total_estimated_loss = sum(c.get('estimated_loss', 0) for c in cases if c.get('estimated_loss'))
        
        # Статистика по уровням риска
        risk_levels = {}
        for case in cases:
            level = case.get('risk_level', 'неизвестно')
            if level not in risk_levels:
                risk_levels[level] = 0
            risk_levels[level] += 1
        
        # Статистика по решениям
        decisions = {}
        for case in cases:
            decision = case.get('decision', 'неизвестно')
            if decision not in decisions:
                decisions[decision] = 0
            decisions[decision] += 1
        
        # Статистика по аффилированности
        affiliation_cases = len([c for c in cases if c.get('risk_details', {}).get('affiliation_detected')])
        
        return {
            'total_prevented_cases': total_prevented,
            'period_days': period_days or 'all_time',
            'total_estimated_loss_prevented': round(total_estimated_loss, 2),
            'avg_loss_per_case': round(total_estimated_loss / total_prevented, 2) if total_prevented > 0 else 0,
            'by_risk_level': risk_levels,
            'by_decision': decisions,
            'affiliation_cases': affiliation_cases,
            'affiliation_percentage': round(affiliation_cases / total_prevented * 100, 2) if total_prevented > 0 else 0
        }
    
    def get_recent_preventions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получает последние предотвращённые случаи
        
        Args:
            limit: Максимальное количество
            
        Returns:
            Список последних случаев
        """
        return sorted(
            self.prevented_cases,
            key=lambda x: x.get('prevented_at', ''),
            reverse=True
        )[:limit]
    
    def get_prevention_by_tender(self, tender_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о предотвращении для конкретного тендера
        
        Args:
            tender_id: ID тендера
            
        Returns:
            Информация о предотвращении или None
        """
        for case in self.prevented_cases:
            if case.get('tender_id') == tender_id:
                return case
        return None


"""
Модуль для генерации итоговых отчётов по ревью
"""
from typing import Dict, List, Optional, Any
from datetime import datetime


class ReportGenerator:
    """Генератор итоговых отчётов по ревью кода"""
    
    def __init__(self, model):
        self.model = model
    
    def generate_report(self, analyses: List[Dict[str, Any]], 
                       merge_recommendation: Optional[str] = None,
                       mr_info: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Генерирует итоговый отчёт по ревью
        
        Args:
            analyses: Список результатов анализа
            merge_recommendation: Рекомендация по merge (ready-for-merge/needs-fixes/reject)
            mr_info: Информация о MR (опционально)
        
        Returns:
            Итоговый отчёт
        """
        analyses_summary = []
        for analysis in analyses:
            if not analysis.get('error'):
                analyses_summary.append({
                    'type': analysis.get('type', 'unknown'),
                    'file_path': analysis.get('file_path', 'unknown'),
                    'has_issues': len(analysis.get('issues', [])) > 0
                })
        
        prompt = f"""Краткий итоговый отчёт. Без лишних слов.

{f'MR: {mr_info}' if mr_info else ''}

Статус: {merge_recommendation or 'needs-review'}

Анализы ({len(analyses)}):
{chr(10).join([f"- {a.get('type', 'unknown')}: {a.get('file_path', 'unknown')}" for a in analyses_summary])}

Формат:

**СТАТУС:** {merge_recommendation or 'needs-review'}

**КРИТИЧНО:**
- [Проблема]: [кратко]

**ВАЖНО:**
- [Проблема]: [кратко]

**ПЛЮСЫ:**
- [Что хорошо]: [кратко]

**РИСКИ:**
- [Риск]: [кратко]

**ДЕЙСТВИЯ:**
1. [Приоритет 1]
2. [Приоритет 2]

Только факты. Максимум 1-2 предложения на пункт."""
        
        try:
            response = self.model.generate_content(prompt)
            report_text = response.text if hasattr(response, 'text') else str(response)
            
            # Определяем финальную рекомендацию
            final_recommendation = merge_recommendation or self._extract_recommendation(report_text)
            
            return {
                'report': report_text,
                'recommendation': final_recommendation,
                'timestamp': datetime.now().isoformat(),
                'analyses_count': len(analyses),
                'success': True
            }
        except Exception as e:
            return {
                'error': f'Ошибка при генерации отчёта: {str(e)}',
                'analyses_count': len(analyses)
            }
    
    def _extract_recommendation(self, report_text: str) -> str:
        """Извлекает рекомендацию из текста отчёта"""
        text_lower = report_text.lower()
        
        if 'reject' in text_lower or 'отклонить' in text_lower:
            return 'reject'
        elif 'needs-fixes' in text_lower or 'требует исправлений' in text_lower:
            return 'needs-fixes'
        elif 'ready' in text_lower or 'готов' in text_lower:
            return 'ready-for-merge'
        else:
            return 'needs-review'


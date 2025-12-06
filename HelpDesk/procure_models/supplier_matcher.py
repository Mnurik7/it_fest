"""
Модуль для подбора релевантных поставщиков
"""
from typing import Dict, List, Optional, Any
import google.generativeai as genai
import json
import re


class SupplierMatcher:
    """Подбор поставщиков по критериям тендера"""
    
    def __init__(self, gemini_model):
        self.model = gemini_model
        # В реальной системе это была бы база данных поставщиков
        self.suppliers_db = []
    
    def match_suppliers(self, tender_params: Dict[str, Any], criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Подбирает релевантных поставщиков для тендера
        
        Args:
            tender_params: Параметры тендера
            criteria: Дополнительные критерии поиска
            
        Returns:
            Список подходящих поставщиков с оценкой релевантности
        """
        if criteria is None:
            criteria = {}
        
        prompt = f"""Ты эксперт по подбору поставщиков для тендеров. На основе параметров тендера подбери релевантных поставщиков.

Параметры тендера:
{json.dumps(tender_params, ensure_ascii=False, indent=2)}

Дополнительные критерии:
{json.dumps(criteria, ensure_ascii=False, indent=2)}

Создай список из 5-10 потенциальных поставщиков в формате JSON:

{{
    "suppliers": [
        {{
            "name": "название компании",
            "relevance_score": 0.95,
            "match_reasons": ["причина 1", "причина 2"],
            "strengths": ["сильная сторона 1", "сильная сторона 2"],
            "weaknesses": ["слабая сторона 1"],
            "experience": "опыт работы в данной сфере",
            "rating": 4.5,
            "completed_projects": 50,
            "specialization": "специализация",
            "location": "местоположение",
            "certificates": ["сертификат 1", "сертификат 2"],
            "estimated_price": "предполагаемая цена",
            "delivery_time": "сроки поставки",
            "guarantee": "гарантийные обязательства",
            "recommendation": "рекомендация по участию"
        }}
    ],
    "summary": {{
        "total_found": 8,
        "high_relevance": 3,
        "medium_relevance": 4,
        "low_relevance": 1,
        "recommendations": "общие рекомендации по выбору поставщиков"
    }}
}}

Верни ТОЛЬКО валидный JSON без дополнительных комментариев."""

        try:
            response = self.model.generate_content(prompt)
            if hasattr(response, 'text'):
                text = response.text.strip()
                
                # Убираем markdown форматирование
                if '```json' in text:
                    text = text.split('```json')[1].split('```')[0].strip()
                elif '```' in text:
                    parts = text.split('```')
                    for part in parts:
                        part = part.strip()
                        if part.startswith('{') or part.startswith('['):
                            text = part
                            break
                
                text = text.strip()
                
                # Пытаемся найти JSON в тексте
                if not text.startswith('{') and not text.startswith('['):
                    start_idx = text.find('{')
                    if start_idx == -1:
                        start_idx = text.find('[')
                    if start_idx != -1:
                        text = text[start_idx:]
                    end_idx = text.rfind('}')
                    if end_idx == -1:
                        end_idx = text.rfind(']')
                    if end_idx != -1:
                        text = text[:end_idx + 1]
                
                try:
                    result = json.loads(text)
                    return result.get('suppliers', []), result.get('summary', {})
                except json.JSONDecodeError as json_err:
                    print(f"Ошибка парсинга JSON при подборе поставщиков: {json_err}")
                    # Пытаемся исправить частые ошибки JSON
                    try:
                        text = re.sub(r"'(\w+)':", r'"\1":', text)
                        text = re.sub(r":\s*'([^']*)'", r': "\1"', text)
                        result = json.loads(text)
                        return result.get('suppliers', []), result.get('summary', {})
                    except:
                        return self._fallback_matching(tender_params)
            else:
                return self._fallback_matching(tender_params)
        except Exception as e:
            print(f"Ошибка при подборе поставщиков: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_matching(tender_params)
    
    def _fallback_matching(self, tender_params: Dict[str, Any]) -> tuple:
        """Простой подбор поставщиков если AI не сработал"""
        suppliers = [
            {
                "name": "Поставщик 1",
                "relevance_score": 0.85,
                "match_reasons": ["Соответствие требованиям", "Опыт работы"],
                "strengths": ["Большой опыт", "Наличие сертификатов"],
                "weaknesses": ["Высокая цена"],
                "experience": "5+ лет",
                "rating": 4.5,
                "completed_projects": 50,
                "specialization": tender_params.get('subject', {}).get('description', '')[:50],
                "location": "Алматы",
                "certificates": ["ISO 9001"],
                "estimated_price": tender_params.get('budget', {}).get('amount', 'N/A'),
                "delivery_time": "30 дней",
                "guarantee": "12 месяцев",
                "recommendation": "Рекомендуется для участия"
            }
        ]
        summary = {
            "total_found": 1,
            "high_relevance": 1,
            "medium_relevance": 0,
            "low_relevance": 0,
            "recommendations": "Рекомендуется провести дополнительный анализ поставщиков"
        }
        return suppliers, summary
    
    def find_partnership_opportunities(self, beginner_supplier: Dict[str, Any], tender_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Находит возможности партнёрства для новичков с опытными поставщиками
        
        Args:
            beginner_supplier: Данные новичка
            tender_params: Параметры тендера
            
        Returns:
            Список потенциальных партнёров
        """
        prompt = f"""Ты эксперт по формированию партнёрств в тендерах. Помоги новичку найти опытного партнёра.

Данные новичка:
{json.dumps(beginner_supplier, ensure_ascii=False, indent=2)}

Параметры тендера:
{json.dumps(tender_params, ensure_ascii=False, indent=2)}

Предложи 3-5 опытных поставщиков, которые могут стать партнёрами для новичка в формате JSON:

{{
    "partners": [
        {{
            "name": "название компании",
            "experience": "опыт",
            "complementary_skills": ["навык 1", "навык 2"],
            "partnership_benefits": ["выгода 1", "выгода 2"],
            "risk_level": "низкий/средний/высокий",
            "recommendation": "рекомендация по партнёрству"
        }}
    ],
    "partnership_strategy": "стратегия партнёрства"
}}

Верни ТОЛЬКО валидный JSON."""

        try:
            response = self.model.generate_content(prompt)
            if hasattr(response, 'text'):
                text = response.text.strip()
                if text.startswith('```'):
                    text = text.split('```')[1]
                    if text.startswith('json'):
                        text = text[4:]
                text = text.strip()
                
                result = json.loads(text)
                return result.get('partners', []), result.get('partnership_strategy', '')
            else:
                return [], "Не удалось найти партнёров"
        except Exception as e:
            print(f"Ошибка при поиске партнёрств: {e}")
            return [], "Ошибка при поиске партнёрств"


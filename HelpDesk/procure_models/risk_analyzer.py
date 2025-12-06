"""
Модуль для анализа рисков в тендерах
"""
from typing import Dict, List, Optional, Any
import google.generativeai as genai
import json
import re
from datetime import datetime


class RiskAnalyzer:
    """Анализатор рисков: аффилированность, подозрительные контракты, несоответствия"""
    
    def __init__(self, gemini_model):
        self.model = gemini_model
    
    def analyze_risks(self, tender_params: Dict[str, Any], winner_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Анализирует риски тендера
        
        Args:
            tender_params: Параметры тендера
            winner_info: Информация о победителе (если известен)
            
        Returns:
            Словарь с анализом рисков
        """
        prompt = f"""Ты эксперт по выявлению рисков и коррупции в тендерах. Проанализируй следующий тендер на предмет рисков.

Параметры тендера:
{json.dumps(tender_params, ensure_ascii=False, indent=2)}

{f'Информация о победителе: {json.dumps(winner_info, ensure_ascii=False, indent=2)}' if winner_info else ''}

Проведи детальный анализ рисков и верни результат в формате JSON:

{{
    "overall_risk_level": "низкий/средний/высокий/критический",
    "risk_score": 0.0-100.0,
    "risks": [
        {{
            "type": "аффилированность/подозрительный_контракт/несоответствие_документации/непрозрачность/другое",
            "severity": "низкая/средняя/высокая/критическая",
            "description": "описание риска",
            "evidence": "доказательства",
            "probability": 0.0-1.0,
            "impact": "низкое/среднее/высокое",
            "recommendations": ["рекомендация 1", "рекомендация 2"]
        }}
    ],
    "affiliation_analysis": {{
        "suspicious_connections": [
            {{
                "entity1": "сущность 1",
                "entity2": "сущность 2",
                "connection_type": "тип связи",
                "risk_level": "низкий/средний/высокий"
            }}
        ],
        "graph_summary": "краткое описание графа связей"
    }},
    "transparency_score": 0.0-100.0,
    "red_flags": [
        "красный флаг 1",
        "красный флаг 2"
    ],
    "recommendations": [
        "общая рекомендация 1",
        "общая рекомендация 2"
    ],
    "compliance_check": {{
        "legal_compliance": true/false,
        "documentation_completeness": true/false,
        "process_transparency": true/false,
        "issues": ["проблема 1", "проблема 2"]
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
                    return result
                except json.JSONDecodeError as json_err:
                    print(f"Ошибка парсинга JSON при анализе рисков: {json_err}")
                    # Пытаемся исправить частые ошибки JSON
                    try:
                        text = re.sub(r"'(\w+)':", r'"\1":', text)
                        text = re.sub(r":\s*'([^']*)'", r': "\1"', text)
                        result = json.loads(text)
                        return result
                    except:
                        return self._fallback_risk_analysis(tender_params)
            else:
                return self._fallback_risk_analysis(tender_params)
        except Exception as e:
            print(f"Ошибка при анализе рисков: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_risk_analysis(tender_params)
    
    def _fallback_risk_analysis(self, tender_params: Dict[str, Any]) -> Dict[str, Any]:
        """Простой анализ рисков если AI не сработал"""
        return {
            "overall_risk_level": "средний",
            "risk_score": 50.0,
            "risks": [
                {
                    "type": "непрозрачность",
                    "severity": "средняя",
                    "description": "Недостаточно информации для полной оценки",
                    "evidence": "Отсутствие некоторых ключевых параметров",
                    "probability": 0.5,
                    "impact": "среднее",
                    "recommendations": ["Запросить дополнительную информацию", "Провести дополнительную проверку"]
                }
            ],
            "affiliation_analysis": {
                "suspicious_connections": [],
                "graph_summary": "Недостаточно данных для анализа связей"
            },
            "transparency_score": 60.0,
            "red_flags": [],
            "recommendations": ["Рекомендуется провести дополнительный анализ"],
            "compliance_check": {
                "legal_compliance": True,
                "documentation_completeness": False,
                "process_transparency": True,
                "issues": ["Неполная документация"]
            }
        }
    
    def check_affiliation(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Проверяет аффилированность между сущностями
        
        Args:
            entities: Список сущностей (заказчик, поставщики, победитель)
            
        Returns:
            Анализ аффилированности
        """
        prompt = f"""Ты эксперт по выявлению аффилированности компаний. Проанализируй связи между следующими сущностями:

Сущности:
{json.dumps(entities, ensure_ascii=False, indent=2)}

Верни анализ в формате JSON:

{{
    "connections": [
        {{
            "entity1": "название 1",
            "entity2": "название 2",
            "connection_type": "общие_учредители/общие_директора/дочерние_компании/договорные_связи/другое",
            "evidence": "доказательства связи",
            "risk_level": "низкий/средний/высокий",
            "confidence": 0.0-1.0
        }}
    ],
    "graph_structure": "описание структуры связей",
    "suspicious_patterns": ["паттерн 1", "паттерн 2"],
    "recommendations": ["рекомендация 1"]
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
                
                return json.loads(text)
            else:
                return {"connections": [], "graph_structure": "Недостаточно данных", "suspicious_patterns": [], "recommendations": []}
        except Exception as e:
            print(f"Ошибка при проверке аффилированности: {e}")
            return {"connections": [], "graph_structure": "Ошибка анализа", "suspicious_patterns": [], "recommendations": []}


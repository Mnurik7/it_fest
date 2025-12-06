"""
Модуль для генерации отчётов по анализу тендеров
"""
from typing import Dict, List, Optional, Any
import google.generativeai as genai
import json
import re
from datetime import datetime


class ReportGenerator:
    """Генератор отчётов с результатами анализа, рисками и обоснованием"""
    
    def __init__(self, gemini_model):
        self.model = gemini_model
    
    def generate_comprehensive_report(self, 
                                     tender_params: Dict[str, Any],
                                     suppliers: List[Dict[str, Any]],
                                     risk_analysis: Dict[str, Any],
                                     completeness: Dict[str, Any],
                                     winner: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Генерирует комплексный отчёт по тендеру
        
        Args:
            tender_params: Параметры тендера
            suppliers: Список подобранных поставщиков
            risk_analysis: Анализ рисков
            completeness: Анализ полноты информации
            winner: Информация о победителе (если известен)
            
        Returns:
            Структурированный отчёт
        """
        prompt = f"""Ты эксперт по составлению отчётов по анализу тендеров. Создай детальный отчёт на основе следующих данных.

Параметры тендера:
{json.dumps(tender_params, ensure_ascii=False, indent=2)}

Подобранные поставщики:
{json.dumps(suppliers, ensure_ascii=False, indent=2)}

Анализ рисков:
{json.dumps(risk_analysis, ensure_ascii=False, indent=2)}

Полнота информации:
{json.dumps(completeness, ensure_ascii=False, indent=2)}

{f'Победитель: {json.dumps(winner, ensure_ascii=False, indent=2)}' if winner else ''}

Создай структурированный отчёт в формате JSON:

{{
    "executive_summary": {{
        "tender_overview": "краткое описание тендера",
        "key_findings": ["находка 1", "находка 2"],
        "overall_assessment": "общая оценка",
        "recommendation": "рекомендация по участию/неучастию"
    }},
    "tender_analysis": {{
        "customer_analysis": "анализ заказчика",
        "subject_analysis": "анализ предмета закупки",
        "budget_analysis": "анализ бюджета",
        "timeline_analysis": "анализ сроков",
        "requirements_analysis": "анализ требований"
    }},
    "supplier_analysis": {{
        "top_suppliers": [
            {{
                "name": "название",
                "ranking": 1,
                "score": 0.95,
                "pros": ["плюс 1", "плюс 2"],
                "cons": ["минус 1"],
                "recommendation": "рекомендация"
            }}
        ],
        "comparison_table": "таблица сравнения поставщиков",
        "market_analysis": "анализ рынка"
    }},
    "risk_assessment": {{
        "summary": "краткое резюме рисков",
        "critical_risks": [
            {{
                "risk": "риск",
                "impact": "влияние",
                "mitigation": "меры по снижению"
            }}
        ],
        "affiliation_concerns": "опасения по аффилированности",
        "transparency_issues": "проблемы прозрачности"
    }},
    "winner_justification": {{
        "winner_name": "название победителя",
        "justification": "обоснование выбора",
        "fairness_assessment": "оценка справедливости",
        "concerns": ["опасение 1", "опасение 2"]
    }},
    "recommendations": {{
        "for_customer": ["рекомендация 1", "рекомендация 2"],
        "for_suppliers": ["рекомендация 1", "рекомендация 2"],
        "for_regulators": ["рекомендация 1"]
    }},
    "conclusion": "заключение",
    "metadata": {{
        "report_date": "{datetime.now().isoformat()}",
        "analysis_version": "1.0",
        "data_completeness": completeness.get("completeness_percentage", 0)
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
                    # Ищем часть с JSON (обычно вторая часть)
                    for part in parts:
                        part = part.strip()
                        if part.startswith('{') or part.startswith('['):
                            text = part
                            break
                
                text = text.strip()
                
                # Пытаемся найти JSON в тексте
                if not text.startswith('{') and not text.startswith('['):
                    # Ищем первую открывающую скобку
                    start_idx = text.find('{')
                    if start_idx == -1:
                        start_idx = text.find('[')
                    if start_idx != -1:
                        text = text[start_idx:]
                    # Ищем последнюю закрывающую скобку
                    end_idx = text.rfind('}')
                    if end_idx == -1:
                        end_idx = text.rfind(']')
                    if end_idx != -1:
                        text = text[:end_idx + 1]
                
                try:
                    report = json.loads(text)
                    # Добавляем исходные данные для справки
                    report["raw_data"] = {
                        "tender_params": tender_params,
                        "suppliers": suppliers,
                        "risk_analysis": risk_analysis,
                        "completeness": completeness
                    }
                    return report
                except json.JSONDecodeError as json_err:
                    print(f"Ошибка парсинга JSON в отчёте: {json_err}")
                    print(f"Текст ответа (первые 500 символов): {text[:500]}")
                    # Пытаемся исправить частые ошибки JSON
                    try:
                        # Заменяем одинарные кавычки на двойные в ключах
                        text = re.sub(r"'(\w+)':", r'"\1":', text)
                        text = re.sub(r":\s*'([^']*)'", r': "\1"', text)
                        report = json.loads(text)
                        report["raw_data"] = {
                            "tender_params": tender_params,
                            "suppliers": suppliers,
                            "risk_analysis": risk_analysis,
                            "completeness": completeness
                        }
                        return report
                    except:
                        return self._fallback_report(tender_params, suppliers, risk_analysis, completeness)
            else:
                return self._fallback_report(tender_params, suppliers, risk_analysis, completeness)
        except Exception as e:
            print(f"Ошибка при генерации отчёта: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_report(tender_params, suppliers, risk_analysis, completeness)
    
    def _fallback_report(self, tender_params, suppliers, risk_analysis, completeness):
        """Простой отчёт если AI не сработал"""
        return {
            "executive_summary": {
                "tender_overview": tender_params.get('subject', {}).get('description', 'Тендер')[:200],
                "key_findings": ["Тендер проанализирован", "Найдены поставщики"],
                "overall_assessment": "Требуется дополнительный анализ",
                "recommendation": "Рекомендуется участие с осторожностью"
            },
            "tender_analysis": {
                "customer_analysis": "Требуется дополнительная информация о заказчике",
                "subject_analysis": tender_params.get('subject', {}).get('description', ''),
                "budget_analysis": f"Бюджет: {tender_params.get('budget', {}).get('amount', 'N/A')}",
                "timeline_analysis": f"Сроки: {tender_params.get('timeline', {}).get('application_end', 'N/A')}",
                "requirements_analysis": "Требования требуют проверки"
            },
            "supplier_analysis": {
                "top_suppliers": suppliers[:3] if suppliers else [],
                "comparison_table": "Сравнение недоступно",
                "market_analysis": "Анализ рынка требует дополнительных данных"
            },
            "risk_assessment": risk_analysis,
            "winner_justification": {
                "winner_name": "Не определен",
                "justification": "Победитель не выбран",
                "fairness_assessment": "N/A",
                "concerns": []
            },
            "recommendations": {
                "for_customer": ["Улучшить прозрачность процесса"],
                "for_suppliers": ["Проверить соответствие требованиям"],
                "for_regulators": []
            },
            "conclusion": "Отчёт сгенерирован автоматически. Требуется дополнительный анализ.",
            "metadata": {
                "report_date": datetime.now().isoformat(),
                "analysis_version": "1.0",
                "data_completeness": completeness.get("completeness_percentage", 0)
            }
        }
    
    def generate_beginner_guide(self, tender_params: Dict[str, Any], step: int = 1) -> Dict[str, Any]:
        """
        Генерирует пошаговую инструкцию для новичков
        
        Args:
            tender_params: Параметры тендера
            step: Номер шага (1-10)
            
        Returns:
            Инструкция для текущего шага
        """
        steps = {
            1: "Анализ тендера и понимание требований",
            2: "Проверка соответствия требованиям участия",
            3: "Подготовка документов",
            4: "Формирование заявки",
            5: "Расчёт цены",
            6: "Проверка заявки",
            7: "Подача заявки",
            8: "Ожидание результатов",
            9: "Подписание договора (если выиграли)",
            10: "Исполнение обязательств"
        }
        
        prompt = f"""Ты эксперт-наставник для новичков в тендерах. Создай детальную инструкцию для шага {step}: "{steps[step]}".

Параметры тендера:
{json.dumps(tender_params, ensure_ascii=False, indent=2)}

Создай инструкцию в формате JSON:

{{
    "step_number": {step},
    "step_name": "{steps[step]}",
    "description": "детальное описание шага",
    "actions": [
        {{
            "action": "действие 1",
            "description": "описание",
            "tips": ["совет 1", "совет 2"],
            "common_mistakes": ["ошибка 1", "ошибка 2"]
        }}
    ],
    "required_documents": ["документ 1", "документ 2"],
    "checklist": ["пункт 1", "пункт 2"],
    "ai_tips": ["совет от AI 1", "совет от AI 2"],
    "next_steps": "что делать дальше",
    "estimated_time": "время на выполнение"
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
                return self._fallback_guide(step, steps[step])
        except Exception as e:
            print(f"Ошибка при генерации инструкции: {e}")
            return self._fallback_guide(step, steps[step])
    
    def _fallback_guide(self, step: int, step_name: str) -> Dict[str, Any]:
        """Простая инструкция если AI не сработал"""
        return {
            "step_number": step,
            "step_name": step_name,
            "description": f"Выполните шаг {step}: {step_name}",
            "actions": [
                {
                    "action": f"Действие для шага {step}",
                    "description": "Описание действия",
                    "tips": ["Внимательно изучите требования", "Проконсультируйтесь с экспертом"],
                    "common_mistakes": ["Неполная документация", "Ошибки в заполнении"]
                }
            ],
            "required_documents": [],
            "checklist": [f"Проверка {step}"],
            "ai_tips": ["Следуйте инструкциям", "Проверяйте все документы"],
            "next_steps": f"Перейти к шагу {step + 1}" if step < 10 else "Завершить процесс",
            "estimated_time": "1-2 часа"
        }


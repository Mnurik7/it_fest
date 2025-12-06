"""
Модуль интеллектуальной декомпозиции задач
"""
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import google.generativeai as genai


class TaskDecomposer:
    """Интеллектуальная декомпозиция задач с учётом команды, ресурсов, календаря"""
    
    def __init__(self, gemini_model):
        self.model = gemini_model
    
    def decompose_task(self, task: Dict[str, Any], team_info: Dict[str, Any], 
                      resources: Dict[str, Any], calendar: Dict[str, Any]) -> Dict[str, Any]:
        """
        Декомпозирует задачу с учётом контекста
        
        Args:
            task: Задача для декомпозиции
            team_info: Информация о команде (навыки, загрузка)
            resources: Доступные ресурсы
            calendar: Календарь (дедлайны, отпуска, праздники)
            
        Returns:
            Декомпозированная задача с подзадачами
        """
        prompt = f"""Ты AI-Scrum Master. Декомпозируй следующую задачу интеллектуально, учитывая контекст команды и ресурсов.

Задача:
{json.dumps(task, ensure_ascii=False, indent=2)}

Информация о команде:
{json.dumps(team_info, ensure_ascii=False, indent=2)}

Ресурсы:
{json.dumps(resources, ensure_ascii=False, indent=2)}

Календарь:
{json.dumps(calendar, ensure_ascii=False, indent=2)}

Создай декомпозицию в формате JSON:

{{
    "decomposition": {{
        "original_task": "ID исходной задачи",
        "subtasks": [
            {{
                "title": "название подзадачи",
                "description": "описание",
                "estimated_hours": 1-40,
                "complexity": "low/medium/high",
                "assignee": "имя исполнителя (на основе навыков и загрузки)",
                "dependencies": ["ID другой подзадачи"],
                "deadline": "дедлайн с учётом календаря",
                "skills_required": ["навык 1", "навык 2"]
            }}
        ],
        "execution_plan": {{
            "phases": [
                {{
                    "phase_name": "название фазы",
                    "tasks": ["ID подзадач"],
                    "duration_days": 1-30,
                    "start_date": "дата начала",
                    "end_date": "дата окончания"
                }}
            ],
            "critical_path": ["ID подзадач"],
            "total_duration_days": 0
        }},
        "resource_allocation": {{
            "team_members": [
                {{
                    "username": "имя",
                    "assigned_tasks": ["ID подзадач"],
                    "total_hours": 0,
                    "workload_percentage": 0.0-100.0,
                    "risk_of_overload": true/false
                }}
            ],
            "bottlenecks": ["узкое место 1", "узкое место 2"],
            "recommendations": ["рекомендация 1", "рекомендация 2"]
        }},
        "risks": [
            {{
                "risk": "описание риска",
                "probability": "low/medium/high",
                "impact": "low/medium/high",
                "mitigation": "меры по снижению"
            }}
        ],
        "alternative_plans": [
            {{
                "plan_name": "название альтернативного плана",
                "description": "описание",
                "pros": ["плюс 1", "плюс 2"],
                "cons": ["минус 1", "минус 2"],
                "duration_days": 0
            }}
        ]
    }}
}}

Верни ТОЛЬКО валидный JSON."""

        try:
            response = self.model.generate_content(prompt)
            if hasattr(response, 'text'):
                text_response = response.text.strip()
                text_response = self._extract_json(text_response)
                
                try:
                    result = json.loads(text_response)
                    result["decomposed_at"] = datetime.now().isoformat()
                    return result
                except json.JSONDecodeError:
                    return self._fallback_decomposition(task)
            else:
                return self._fallback_decomposition(task)
        except Exception as e:
            print(f"Ошибка при декомпозиции задачи: {e}")
            return self._fallback_decomposition(task)
    
    def _extract_json(self, text: str) -> str:
        """Извлекает JSON из текста"""
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0].strip()
        elif '```' in text:
            parts = text.split('```')
            for part in parts:
                part = part.strip()
                if part.startswith('{'):
                    text = part
                    break
        
        text = text.strip()
        if not text.startswith('{'):
            start_idx = text.find('{')
            if start_idx != -1:
                text = text[start_idx:]
            end_idx = text.rfind('}')
            if end_idx != -1:
                text = text[:end_idx + 1]
        
        text = re.sub(r"'(\w+)':", r'"\1":', text)
        text = re.sub(r":\s*'([^']*)'", r': "\1"', text)
        return text
    
    def _fallback_decomposition(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Простая декомпозиция если AI не сработал"""
        return {
            "decomposition": {
                "original_task": task.get("task_id", "UNKNOWN"),
                "subtasks": [
                    {
                        "title": f"Подзадача для {task.get('title', 'Задача')}",
                        "description": "Требуется декомпозиция",
                        "estimated_hours": task.get("estimated_hours", 8) // 2,
                        "complexity": "medium",
                        "assignee": None,
                        "dependencies": [],
                        "deadline": None,
                        "skills_required": []
                    }
                ],
                "execution_plan": {
                    "phases": [{
                        "phase_name": "Выполнение",
                        "tasks": [],
                        "duration_days": 1,
                        "start_date": datetime.now().isoformat(),
                        "end_date": (datetime.now() + timedelta(days=1)).isoformat()
                    }],
                    "critical_path": [],
                    "total_duration_days": 1
                },
                "resource_allocation": {
                    "team_members": [],
                    "bottlenecks": [],
                    "recommendations": ["Требуется ручная декомпозиция"]
                },
                "risks": [],
                "alternative_plans": []
            },
            "decomposed_at": datetime.now().isoformat()
        }
    
    def optimize_allocation(self, tasks: List[Dict[str, Any]], team: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Оптимизирует распределение задач между участниками команды
        
        Args:
            tasks: Список задач
            team: Список участников команды
            
        Returns:
            Оптимизированное распределение
        """
        prompt = f"""Ты AI-Scrum Master. Оптимизируй распределение задач между участниками команды.

Задачи:
{json.dumps(tasks, ensure_ascii=False, indent=2)}

Команда:
{json.dumps(team, ensure_ascii=False, indent=2)}

Верни оптимизированное распределение в формате JSON:

{{
    "optimized_allocation": [
        {{
            "task_id": "ID задачи",
            "assignee": "имя исполнителя",
            "reason": "обоснование назначения",
            "estimated_completion": "дата завершения"
        }}
    ],
    "workload_balance": {{
        "team_members": [
            {{
                "username": "имя",
                "total_hours": 0,
                "workload_percentage": 0.0,
                "tasks_count": 0
            }}
        ],
        "is_balanced": true/false
    }},
    "recommendations": ["рекомендация 1", "рекомендация 2"]
}}

Верни ТОЛЬКО валидный JSON."""

        try:
            response = self.model.generate_content(prompt)
            if hasattr(response, 'text'):
                text_response = response.text.strip()
                text_response = self._extract_json(text_response)
                return json.loads(text_response)
            else:
                return {"optimized_allocation": [], "workload_balance": {}, "recommendations": []}
        except Exception as e:
            print(f"Ошибка при оптимизации распределения: {e}")
            return {"optimized_allocation": [], "workload_balance": {}, "recommendations": []}


"""
Модуль аналитики и AI-инсайтов
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import google.generativeai as genai


class AnalyticsEngine:
    """Аналитика производительности, инсайты, прогнозы"""
    
    def __init__(self, gemini_model, data_dir: str = "data"):
        self.model = gemini_model
        self.data_dir = data_dir
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """Создаёт директорию для данных"""
        os.makedirs(self.data_dir, exist_ok=True)
        # Импортируем deadline_tracker для доступа к статистике
        from scrum_models.deadline_tracker import DeadlineTracker
        self.deadline_tracker = DeadlineTracker(self.data_dir)
    
    def generate_insights(self, project_id: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Генерирует AI-инсайты на основе данных проекта
        
        Args:
            project_id: ID проекта
            data: Данные для анализа (опционально, если не указаны - загружаются автоматически)
            
        Returns:
            AI-инсайты и рекомендации
        """
        # Загружаем реальные данные если не предоставлены
        if data is None:
            data = self._load_project_data(project_id)
        
        prompt = f"""Ты AI-Scrum Master. Проанализируй данные проекта и предоставь инсайты.

Данные проекта:
{json.dumps(data, ensure_ascii=False, indent=2)}

Проанализируй и верни инсайты в формате JSON:

{{
    "efficiency_analysis": {{
        "completion_rate": 0.0,
        "on_time_percentage": 0.0,
        "velocity_trend": "increasing/stable/decreasing",
        "efficiency_score": 0-100
    }},
    "problem_areas": [
        {{
            "area": "название проблемной зоны",
            "severity": "low/medium/high",
            "description": "описание проблемы",
            "impact": "влияние на проект",
            "recommendations": ["рекомендация 1", "рекомендация 2"]
        }}
    ],
    "hidden_risks": [
        {{
            "risk": "описание скрытого риска",
            "probability": "low/medium/high",
            "impact": "low/medium/high",
            "early_warning_signs": ["признак 1", "признак 2"],
            "mitigation": "меры по снижению"
        }}
    ],
    "team_insights": {{
        "high_performers": ["имя 1", "имя 2"],
        "overloaded_members": ["имя 1"],
        "bottlenecks": ["узкое место 1"],
        "recommendations": ["рекомендация 1", "рекомендация 2"]
    }},
    "predictions": {{
        "sprint_completion_forecast": {{
            "probability": 0.0-1.0,
            "expected_completion_date": "дата",
            "confidence": "low/medium/high"
        }},
        "project_timeline_risk": "low/medium/high",
        "resource_needs": ["потребность 1", "потребность 2"]
    }},
    "recommendations": [
        {{
            "category": "process/organizational/technical",
            "recommendation": "рекомендация",
            "priority": "high/medium/low",
            "expected_impact": "ожидаемое влияние"
        }}
    ],
    "improvement_suggestions": [
        "предложение 1",
        "предложение 2"
    ]
}}

Верни ТОЛЬКО валидный JSON."""

        try:
            response = self.model.generate_content(prompt)
            if hasattr(response, 'text'):
                text_response = response.text.strip()
                text_response = self._extract_json(text_response)
                
                try:
                    result = json.loads(text_response)
                    result["project_id"] = project_id
                    result["generated_at"] = datetime.now().isoformat()
                    return result
                except json.JSONDecodeError:
                    return self._fallback_insights(project_id)
            else:
                return self._fallback_insights(project_id)
        except Exception as e:
            print(f"Ошибка при генерации инсайтов: {e}")
            return self._fallback_insights(project_id)
    
    def generate_performance_report(self, project_id: str, period_days: int = 30) -> Dict[str, Any]:
        """
        Генерирует отчёт по эффективности
        
        Args:
            project_id: ID проекта
            period_days: Период для анализа (дни)
            
        Returns:
            Отчёт по эффективности
        """
        # Загружаем реальные данные
        data = self._load_project_data(project_id)
        tasks = data.get("tasks", [])
        
        # Рассчитываем метрики
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.get("status") == "completed"])
        in_progress_tasks = len([t for t in tasks if t.get("status") == "in_progress"])
        planned_tasks = len([t for t in tasks if t.get("status") == "planned"])
        
        # Анализ дедлайнов
        deadline_stats = self.deadline_tracker.get_statistics(project_id)
        
        # Velocity из спринтов
        sprints = data.get("sprints", [])
        completed_sprints = [s for s in sprints if s.get("status") == "completed"]
        total_story_points = sum(t.get("story_points", 0) for t in tasks if t.get("story_points"))
        completed_story_points = sum(t.get("story_points", 0) for t in tasks if t.get("status") == "completed" and t.get("story_points"))
        
        avg_velocity = completed_story_points / len(completed_sprints) if completed_sprints and len(completed_sprints) > 0 else 0
        
        return {
            "project_id": project_id,
            "period_days": period_days,
            "metrics": {
                "tasks_completed": completed_tasks,
                "tasks_total": total_tasks,
                "tasks_in_progress": in_progress_tasks,
                "tasks_planned": planned_tasks,
                "completion_percentage": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
                "overdue_tasks": deadline_stats.get("completed_overdue", 0),
                "on_time_percentage": deadline_stats.get("on_time_percentage", 0),
                "average_velocity": avg_velocity,
                "total_story_points": total_story_points,
                "completed_story_points": completed_story_points,
                "team_efficiency": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            },
            "trends": {
                "completion_trend": "increasing" if completed_tasks > total_tasks * 0.5 else "stable" if completed_tasks > 0 else "decreasing",
                "velocity_trend": "stable",
                "efficiency_trend": "stable"
            },
            "generated_at": datetime.now().isoformat()
        }
    
    def _load_project_data(self, project_id: str) -> Dict[str, Any]:
        """Загружает данные проекта из файлов"""
        import os
        
        data = {
            "tasks": [],
            "sprints": [],
            "team_members": [],
            "meetings": []
        }
        
        # Загружаем задачи
        tasks_file = os.path.join(self.data_dir, "scrum_tasks.json")
        if os.path.exists(tasks_file):
            try:
                with open(tasks_file, 'r', encoding='utf-8') as f:
                    all_tasks = json.load(f)
                    data["tasks"] = [t for t in all_tasks if t.get("project_id") == project_id]
            except:
                pass
        
        # Загружаем спринты
        sprints_file = os.path.join(self.data_dir, "scrum_sprints.json")
        if os.path.exists(sprints_file):
            try:
                with open(sprints_file, 'r', encoding='utf-8') as f:
                    all_sprints = json.load(f)
                    data["sprints"] = [s for s in all_sprints if s.get("project_id") == project_id]
            except:
                pass
        
        # Загружаем участников
        members_file = os.path.join(self.data_dir, "scrum_members.json")
        if os.path.exists(members_file):
            try:
                with open(members_file, 'r', encoding='utf-8') as f:
                    all_members = json.load(f)
                    data["team_members"] = [m for m in all_members if m.get("project_id") == project_id]
            except:
                pass
        
        # Загружаем встречи
        meetings_file = os.path.join(self.data_dir, "scrum_meetings.json")
        if os.path.exists(meetings_file):
            try:
                with open(meetings_file, 'r', encoding='utf-8') as f:
                    all_meetings = json.load(f)
                    data["meetings"] = [m for m in all_meetings if m.get("project_id") == project_id]
            except:
                pass
        
        return data
    
    def predict_sprint_completion(self, sprint_id: str, current_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Прогнозирует завершение спринта
        
        Args:
            sprint_id: ID спринта
            current_data: Текущие данные спринта
            
        Returns:
            Прогноз завершения
        """
        prompt = f"""Ты AI-Scrum Master. Спрогнозируй завершение спринта на основе текущих данных.

Данные спринта:
{json.dumps(current_data, ensure_ascii=False, indent=2)}

Верни прогноз в формате JSON:

{{
    "sprint_id": "{sprint_id}",
    "prediction": {{
        "will_complete_on_time": true/false,
        "probability": 0.0-1.0,
        "expected_completion_date": "дата",
        "confidence": "low/medium/high",
        "factors": ["фактор 1", "фактор 2"]
    }},
    "risks": [
        {{
            "risk": "риск",
            "impact": "влияние на завершение",
            "mitigation": "меры"
        }}
    ],
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
                return self._fallback_prediction(sprint_id)
        except Exception as e:
            print(f"Ошибка при прогнозировании: {e}")
            return self._fallback_prediction(sprint_id)
    
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
        
        import re
        text = re.sub(r"'(\w+)':", r'"\1":', text)
        text = re.sub(r":\s*'([^']*)'", r': "\1"', text)
        return text
    
    def _fallback_insights(self, project_id: str) -> Dict[str, Any]:
        """Простые инсайты если AI не сработал"""
        return {
            "efficiency_analysis": {
                "completion_rate": 0.0,
                "on_time_percentage": 0.0,
                "velocity_trend": "stable",
                "efficiency_score": 50
            },
            "problem_areas": [],
            "hidden_risks": [],
            "team_insights": {
                "high_performers": [],
                "overloaded_members": [],
                "bottlenecks": [],
                "recommendations": ["Требуется дополнительный анализ"]
            },
            "predictions": {
                "sprint_completion_forecast": {
                    "probability": 0.5,
                    "expected_completion_date": None,
                    "confidence": "low"
                },
                "project_timeline_risk": "medium",
                "resource_needs": []
            },
            "recommendations": [],
            "improvement_suggestions": ["Провести ретроспективу", "Улучшить коммуникацию"],
            "project_id": project_id,
            "generated_at": datetime.now().isoformat()
        }
    
    def _fallback_prediction(self, sprint_id: str) -> Dict[str, Any]:
        """Простой прогноз если AI не сработал"""
        return {
            "sprint_id": sprint_id,
            "prediction": {
                "will_complete_on_time": True,
                "probability": 0.5,
                "expected_completion_date": None,
                "confidence": "low",
                "factors": ["Недостаточно данных"]
            },
            "risks": [],
            "recommendations": ["Собрать больше данных для точного прогноза"]
        }


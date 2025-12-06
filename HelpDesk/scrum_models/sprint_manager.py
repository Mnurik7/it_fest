"""
Модуль управления спринтами
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import google.generativeai as genai


class SprintManager:
    """Управление спринтами: формирование backlog, анализ, оптимизация"""
    
    def __init__(self, gemini_model, data_dir: str = "data"):
        self.model = gemini_model
        self.data_dir = data_dir
        self.sprints_file = os.path.join(data_dir, "scrum_sprints.json")
        self.tasks_file = os.path.join(data_dir, "scrum_tasks.json")
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """Создаёт директорию для данных"""
        os.makedirs(self.data_dir, exist_ok=True)
    
    def create_sprint(self, project_id: str, name: str, start_date: str, 
                     end_date: str, goal: str) -> Dict[str, Any]:
        """
        Создаёт новый спринт
        
        Args:
            project_id: ID проекта
            name: Название спринта
            start_date: Дата начала
            end_date: Дата окончания
            goal: Цель спринта
            
        Returns:
            Созданный спринт
        """
        sprints = self._load_sprints()
        
        sprint = {
            "sprint_id": f"SPRINT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "project_id": project_id,
            "name": name,
            "start_date": start_date,
            "end_date": end_date,
            "goal": goal,
            "status": "planned",
            "tasks": [],
            "velocity": 0,
            "burndown_data": [],
            "created_at": datetime.now().isoformat()
        }
        
        sprints.append(sprint)
        self._save_sprints(sprints)
        return sprint
    
    def build_sprint_backlog(self, sprint_id: str, available_tasks: List[Dict[str, Any]], 
                           team_capacity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Автоматически формирует Sprint Backlog
        
        Args:
            sprint_id: ID спринта
            available_tasks: Доступные задачи
            team_capacity: Ёмкость команды
            
        Returns:
            Сформированный backlog
        """
        prompt = f"""Ты AI-Scrum Master. Сформируй оптимальный Sprint Backlog.

Доступные задачи:
{json.dumps(available_tasks, ensure_ascii=False, indent=2)}

Ёмкость команды:
{json.dumps(team_capacity, ensure_ascii=False, indent=2)}

Сформируй backlog в формате JSON:

{{
    "sprint_backlog": [
        {{
            "task_id": "ID задачи",
            "priority": "high/medium/low",
            "story_points": 0,
            "assignee": "имя исполнителя",
            "estimated_hours": 0,
            "reason": "почему включена в спринт"
        }}
    ],
    "total_story_points": 0,
    "total_hours": 0,
    "team_utilization": {{
        "member": "имя",
        "assigned_hours": 0,
        "utilization_percentage": 0.0
    }},
    "recommendations": ["рекомендация 1", "рекомендация 2"]
}}

Верни ТОЛЬКО валидный JSON."""

        try:
            response = self.model.generate_content(prompt)
            if hasattr(response, 'text'):
                text_response = response.text.strip()
                text_response = self._extract_json(text_response)
                
                try:
                    result = json.loads(text_response)
                    
                    # Обновляем спринт
                    sprints = self._load_sprints()
                    for sprint in sprints:
                        if sprint["sprint_id"] == sprint_id:
                            sprint["tasks"] = [t["task_id"] for t in result.get("sprint_backlog", [])]
                            sprint["status"] = "active"
                            sprint["updated_at"] = datetime.now().isoformat()
                            self._save_sprints(sprints)
                            break
                    
                    result["sprint_id"] = sprint_id
                    result["created_at"] = datetime.now().isoformat()
                    return result
                except json.JSONDecodeError:
                    return self._fallback_backlog(available_tasks, team_capacity)
            else:
                return self._fallback_backlog(available_tasks, team_capacity)
        except Exception as e:
            print(f"Ошибка при формировании backlog: {e}")
            return self._fallback_backlog(available_tasks, team_capacity)
    
    def calculate_burndown(self, sprint_id: str) -> Dict[str, Any]:
        """
        Рассчитывает Burndown Chart для спринта
        
        Args:
            sprint_id: ID спринта
            
        Returns:
            Данные для Burndown Chart
        """
        sprints = self._load_sprints()
        tasks = self._load_tasks()
        
        sprint = None
        for s in sprints:
            if s["sprint_id"] == sprint_id:
                sprint = s
                break
        
        if not sprint:
            return {"error": "Спринт не найден"}
        
        start_date = datetime.fromisoformat(sprint["start_date"])
        end_date = datetime.fromisoformat(sprint["end_date"])
        total_days = (end_date - start_date).days + 1
        
        # Считаем общие story points
        sprint_tasks = [t for t in tasks if t.get("task_id") in sprint.get("tasks", [])]
        total_story_points = sum(t.get("story_points", 0) for t in sprint_tasks)
        
        # Идеальный burndown
        ideal_burndown = []
        points_per_day = total_story_points / total_days if total_days > 0 else 0
        
        for day in range(total_days):
            date = start_date + timedelta(days=day)
            remaining = max(0, total_story_points - (points_per_day * day))
            ideal_burndown.append({
                "date": date.isoformat(),
                "remaining_points": remaining
            })
        
        # Фактический burndown (упрощённый)
        actual_burndown = []
        completed_points = 0
        for day in range(total_days):
            date = start_date + timedelta(days=day)
            # В реальной системе здесь была бы проверка статусов задач на эту дату
            remaining = max(0, total_story_points - completed_points)
            actual_burndown.append({
                "date": date.isoformat(),
                "remaining_points": remaining
            })
        
        return {
            "sprint_id": sprint_id,
            "total_story_points": total_story_points,
            "ideal_burndown": ideal_burndown,
            "actual_burndown": actual_burndown,
            "calculated_at": datetime.now().isoformat()
        }
    
    def calculate_velocity(self, project_id: str, sprints_count: int = 5) -> Dict[str, Any]:
        """
        Рассчитывает Velocity команды
        
        Args:
            project_id: ID проекта
            sprints_count: Количество спринтов для анализа
            
        Returns:
            Данные о velocity
        """
        sprints = self._load_sprints()
        tasks = self._load_tasks()
        
        project_sprints = [s for s in sprints if s.get("project_id") == project_id and s.get("status") == "completed"]
        project_sprints = sorted(project_sprints, key=lambda x: x.get("end_date", ""), reverse=True)[:sprints_count]
        
        velocities = []
        for sprint in project_sprints:
            sprint_tasks = [t for t in tasks if t.get("task_id") in sprint.get("tasks", [])]
            completed_tasks = [t for t in sprint_tasks if t.get("status") == "completed"]
            completed_points = sum(t.get("story_points", 0) for t in completed_tasks)
            
            velocities.append({
                "sprint_id": sprint["sprint_id"],
                "sprint_name": sprint.get("name", ""),
                "completed_points": completed_points,
                "total_tasks": len(sprint_tasks),
                "completed_tasks": len(completed_tasks)
            })
        
        avg_velocity = sum(v["completed_points"] for v in velocities) / len(velocities) if velocities else 0
        
        return {
            "project_id": project_id,
            "average_velocity": avg_velocity,
            "sprint_velocities": velocities,
            "calculated_at": datetime.now().isoformat()
        }
    
    def analyze_sprint_performance(self, sprint_id: str) -> Dict[str, Any]:
        """
        Анализирует производительность спринта
        
        Args:
            sprint_id: ID спринта
            
        Returns:
            Анализ производительности
        """
        sprints = self._load_sprints()
        tasks = self._load_tasks()
        
        sprint = None
        for s in sprints:
            if s["sprint_id"] == sprint_id:
                sprint = s
                break
        
        if not sprint:
            return {"error": "Спринт не найден"}
        
        sprint_tasks = [t for t in tasks if t.get("task_id") in sprint.get("tasks", [])]
        
        total_tasks = len(sprint_tasks)
        completed_tasks = len([t for t in sprint_tasks if t.get("status") == "completed"])
        in_progress_tasks = len([t for t in sprint_tasks if t.get("status") == "in_progress"])
        blocked_tasks = len([t for t in sprint_tasks if t.get("status") == "blocked"])
        
        # Анализ загрузки команды
        team_workload = {}
        for task in sprint_tasks:
            assignee = task.get("assignee")
            if assignee:
                if assignee not in team_workload:
                    team_workload[assignee] = {"tasks": 0, "hours": 0}
                team_workload[assignee]["tasks"] += 1
                team_workload[assignee]["hours"] += task.get("estimated_hours", 0)
        
        # Проблемные зоны
        bottlenecks = []
        if blocked_tasks > 0:
            bottlenecks.append(f"{blocked_tasks} заблокированных задач")
        
        overloaded_members = [m for m, w in team_workload.items() if w["hours"] > 40]
        if overloaded_members:
            bottlenecks.append(f"Перегружены: {', '.join(overloaded_members)}")
        
        return {
            "sprint_id": sprint_id,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "in_progress_tasks": in_progress_tasks,
            "blocked_tasks": blocked_tasks,
            "completion_percentage": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            "team_workload": team_workload,
            "bottlenecks": bottlenecks,
            "recommendations": self._generate_recommendations(sprint_tasks, team_workload),
            "analyzed_at": datetime.now().isoformat()
        }
    
    def _generate_recommendations(self, tasks: List[Dict[str, Any]], 
                                 team_workload: Dict[str, Any]) -> List[str]:
        """Генерирует рекомендации по спринту"""
        recommendations = []
        
        blocked = [t for t in tasks if t.get("status") == "blocked"]
        if blocked:
            recommendations.append("Разблокировать задачи: " + ", ".join([t.get("title", "") for t in blocked[:3]]))
        
        overloaded = [m for m, w in team_workload.items() if w["hours"] > 40]
        if overloaded:
            recommendations.append(f"Перераспределить нагрузку: {', '.join(overloaded)}")
        
        return recommendations
    
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
    
    def _fallback_backlog(self, available_tasks: List[Dict[str, Any]], 
                         team_capacity: Dict[str, Any]) -> Dict[str, Any]:
        """Простой backlog если AI не сработал"""
        return {
            "sprint_backlog": [
                {
                    "task_id": task.get("task_id", ""),
                    "priority": task.get("priority", "medium"),
                    "story_points": task.get("story_points", 0),
                    "assignee": None,
                    "estimated_hours": task.get("estimated_hours", 0),
                    "reason": "Включена в спринт"
                }
                for task in available_tasks[:10]
            ],
            "total_story_points": sum(t.get("story_points", 0) for t in available_tasks[:10]),
            "total_hours": sum(t.get("estimated_hours", 0) for t in available_tasks[:10]),
            "team_utilization": {},
            "recommendations": ["Требуется ручная проверка backlog"]
        }
    
    def _load_sprints(self) -> List[Dict[str, Any]]:
        """Загружает спринты"""
        if os.path.exists(self.sprints_file):
            try:
                with open(self.sprints_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_sprints(self, sprints: List[Dict[str, Any]]):
        """Сохраняет спринты"""
        with open(self.sprints_file, 'w', encoding='utf-8') as f:
            json.dump(sprints, f, ensure_ascii=False, indent=2)
    
    def _load_tasks(self) -> List[Dict[str, Any]]:
        """Загружает задачи"""
        if os.path.exists(self.tasks_file):
            try:
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []


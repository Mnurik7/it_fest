"""
Модуль контроля дедлайнов и напоминаний
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any


class DeadlineTracker:
    """Отслеживание дедлайнов, напоминания, выявление рисков"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.deadlines_file = os.path.join(data_dir, "scrum_deadlines.json")
        self.reminders_file = os.path.join(data_dir, "scrum_reminders.json")
        self.history_file = os.path.join(data_dir, "scrum_deadline_history.json")
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """Создаёт директорию для данных"""
        os.makedirs(self.data_dir, exist_ok=True)
    
    def add_deadline(self, task_id: str, deadline: str, assignee: str, 
                    project_id: str, priority: str = "medium") -> Dict[str, Any]:
        """
        Добавляет дедлайн для задачи
        
        Args:
            task_id: ID задачи
            deadline: Дедлайн (ISO format)
            assignee: Исполнитель
            project_id: ID проекта
            priority: Приоритет
            
        Returns:
            Информация о дедлайне
        """
        deadlines = self._load_deadlines()
        
        deadline_info = {
            "deadline_id": f"DL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "task_id": task_id,
            "deadline": deadline,
            "assignee": assignee,
            "project_id": project_id,
            "priority": priority,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "reminders_sent": [],
            "completed_at": None
        }
        
        deadlines.append(deadline_info)
        self._save_deadlines(deadlines)
        return deadline_info
    
    def check_deadlines(self, days_ahead: int = 7) -> Dict[str, Any]:
        """
        Проверяет дедлайны на ближайшие дни
        
        Args:
            days_ahead: Количество дней вперёд для проверки
            
        Returns:
            Информация о дедлайнах и рисках
        """
        deadlines = self._load_deadlines()
        now = datetime.now()
        end_date = now + timedelta(days=days_ahead)
        
        upcoming = []
        overdue = []
        at_risk = []
        
        for deadline_info in deadlines:
            if deadline_info.get("status") != "active":
                continue
            
            deadline_date = datetime.fromisoformat(deadline_info["deadline"])
            
            if deadline_date < now:
                overdue.append(deadline_info)
            elif deadline_date <= end_date:
                days_left = (deadline_date - now).days
                upcoming.append(deadline_info)
                
                # Риск срыва если осталось мало времени
                if days_left <= 2 and deadline_info.get("priority") == "high":
                    at_risk.append(deadline_info)
        
        return {
            "upcoming": upcoming,
            "overdue": overdue,
            "at_risk": at_risk,
            "checked_at": now.isoformat()
        }
    
    def get_reminders(self, assignee: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Получает напоминания для пользователя или всех
        
        Args:
            assignee: Имя пользователя (опционально)
            
        Returns:
            Список напоминаний
        """
        deadlines = self._load_deadlines()
        now = datetime.now()
        reminders = []
        
        for deadline_info in deadlines:
            if deadline_info.get("status") != "active":
                continue
            
            if assignee and deadline_info.get("assignee") != assignee:
                continue
            
            deadline_date = datetime.fromisoformat(deadline_info["deadline"])
            days_left = (deadline_date - now).days
            
            # Напоминания за 7, 3, 1 день и в день дедлайна
            reminder_days = [7, 3, 1, 0]
            if days_left in reminder_days:
                reminder_id = f"REM-{deadline_info['deadline_id']}-{days_left}"
                
                # Проверяем, не отправляли ли уже это напоминание
                if reminder_id not in deadline_info.get("reminders_sent", []):
                    reminders.append({
                        "reminder_id": reminder_id,
                        "deadline_info": deadline_info,
                        "days_left": days_left,
                        "urgency": "high" if days_left <= 1 else "medium" if days_left <= 3 else "low"
                    })
        
        return reminders
    
    def mark_completed(self, deadline_id: str, on_time: bool = True):
        """Отмечает дедлайн как выполненный"""
        deadlines = self._load_deadlines()
        now = datetime.now()
        
        for deadline_info in deadlines:
            if deadline_info["deadline_id"] == deadline_id:
                deadline_info["status"] = "completed"
                deadline_info["completed_at"] = now.isoformat()
                deadline_info["completed_on_time"] = on_time
                
                # Сохраняем в историю
                self._save_to_history(deadline_info)
                break
        
        self._save_deadlines(deadlines)
    
    def analyze_risks(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Анализирует риски срыва дедлайнов
        
        Args:
            project_id: ID проекта (опционально)
            
        Returns:
            Анализ рисков
        """
        deadlines = self._load_deadlines()
        now = datetime.now()
        
        project_deadlines = [d for d in deadlines if d.get("status") == "active"]
        if project_id:
            project_deadlines = [d for d in project_deadlines if d.get("project_id") == project_id]
        
        risks = []
        cascade_risks = []
        
        for deadline_info in project_deadlines:
            deadline_date = datetime.fromisoformat(deadline_info["deadline"])
            days_left = (deadline_date - now).days
            
            # Риск срыва
            if days_left < 0:
                risks.append({
                    "deadline_id": deadline_info["deadline_id"],
                    "task_id": deadline_info["task_id"],
                    "severity": "critical",
                    "days_overdue": abs(days_left),
                    "impact": "high"
                })
            elif days_left <= 1:
                risks.append({
                    "deadline_id": deadline_info["deadline_id"],
                    "task_id": deadline_info["task_id"],
                    "severity": "high",
                    "days_left": days_left,
                    "impact": "high"
                })
            elif days_left <= 3:
                risks.append({
                    "deadline_id": deadline_info["deadline_id"],
                    "task_id": deadline_info["task_id"],
                    "severity": "medium",
                    "days_left": days_left,
                    "impact": "medium"
                })
        
        return {
            "risks": risks,
            "cascade_risks": cascade_risks,
            "total_risks": len(risks),
            "analyzed_at": now.isoformat()
        }
    
    def get_statistics(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Получает статистику по дедлайнам"""
        history = self._load_history()
        
        if project_id:
            history = [h for h in history if h.get("project_id") == project_id]
        
        total = len(history)
        on_time = len([h for h in history if h.get("completed_on_time", False)])
        overdue = len([h for h in history if not h.get("completed_on_time", False)])
        
        return {
            "total_completed": total,
            "completed_on_time": on_time,
            "completed_overdue": overdue,
            "on_time_percentage": (on_time / total * 100) if total > 0 else 0,
            "overdue_percentage": (overdue / total * 100) if total > 0 else 0
        }
    
    def _load_deadlines(self) -> List[Dict[str, Any]]:
        """Загружает дедлайны"""
        if os.path.exists(self.deadlines_file):
            try:
                with open(self.deadlines_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_deadlines(self, deadlines: List[Dict[str, Any]]):
        """Сохраняет дедлайны"""
        with open(self.deadlines_file, 'w', encoding='utf-8') as f:
            json.dump(deadlines, f, ensure_ascii=False, indent=2)
    
    def _load_history(self) -> List[Dict[str, Any]]:
        """Загружает историю"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_to_history(self, deadline_info: Dict[str, Any]):
        """Сохраняет в историю"""
        history = self._load_history()
        history.append(deadline_info)
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)


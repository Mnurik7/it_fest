"""
Модуль создания задач из текста (ТЗ, описание, переписка, встречи)
"""
import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import google.generativeai as genai


class TaskCreator:
    """Создание задач из текста с автоматической декомпозицией"""
    
    def __init__(self, gemini_model):
        self.model = gemini_model
    
    def create_tasks_from_text(self, text: str, project_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Создаёт задачи из текста (ТЗ, описание, переписка)
        
        Args:
            text: Текст для анализа
            project_id: ID проекта
            context: Контекст (команда, дедлайны, приоритеты)
            
        Returns:
            Структурированные задачи (Epic, User Stories, Tasks)
        """
        prompt = f"""Ты AI-Scrum Master для банка. Проанализируй следующий текст и создай структурированные задачи.

Текст для анализа:
{text}

{f'Контекст проекта: {json.dumps(context, ensure_ascii=False, indent=2)}' if context else ''}

Создай структуру задач в формате JSON:

{{
    "epic": {{
        "title": "название Epic",
        "description": "описание Epic",
        "business_value": "бизнес-ценность",
        "priority": "high/medium/low",
        "deadline": "дедлайн если указан"
    }},
    "user_stories": [
        {{
            "title": "название User Story",
            "description": "как [роль], я хочу [действие], чтобы [результат]",
            "acceptance_criteria": ["критерий 1", "критерий 2"],
            "priority": "high/medium/low",
            "story_points": 1-13,
            "dependencies": ["ID другой задачи"],
            "deadline": "дедлайн если указан"
        }}
    ],
    "tasks": [
        {{
            "title": "название задачи",
            "description": "детальное описание",
            "type": "development/testing/documentation/design/other",
            "priority": "high/medium/low",
            "story_points": 1-8,
            "estimated_hours": 1-40,
            "complexity": "low/medium/high",
            "dependencies": ["ID другой задачи"],
            "assignee": "имя исполнителя или null",
            "deadline": "дедлайн если указан",
            "definition_of_done": ["критерий 1", "критерий 2"]
        }}
    ],
    "subtasks": [
        {{
            "title": "название подзадачи",
            "parent_task_id": "ID родительской задачи",
            "description": "описание",
            "estimated_hours": 1-8,
            "assignee": "имя исполнителя или null"
        }}
    ],
    "insights": {{
        "total_estimated_hours": 0,
        "critical_path": ["ID задач"],
        "risks": ["риск 1", "риск 2"],
        "recommendations": ["рекомендация 1", "рекомендация 2"]
    }}
}}

Верни ТОЛЬКО валидный JSON без дополнительных комментариев."""

        try:
            response = self.model.generate_content(prompt)
            if hasattr(response, 'text'):
                text_response = response.text.strip()
                
                # Извлекаем JSON
                text_response = self._extract_json(text_response)
                
                try:
                    result = json.loads(text_response)
                    # Добавляем метаданные
                    result["created_at"] = datetime.now().isoformat()
                    result["project_id"] = project_id
                    result["source_text"] = text[:500]  # Первые 500 символов для справки
                    
                    # Генерируем ID для всех задач
                    result = self._assign_task_ids(result)
                    
                    return result
                except json.JSONDecodeError as e:
                    print(f"Ошибка парсинга JSON при создании задач: {e}")
                    return self._fallback_task_creation(text, project_id)
            else:
                return self._fallback_task_creation(text, project_id)
        except Exception as e:
            print(f"Ошибка при создании задач: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_task_creation(text, project_id)
    
    def _extract_json(self, text: str) -> str:
        """Извлекает JSON из текста ответа"""
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
        
        # Исправляем частые ошибки JSON
        text = re.sub(r"'(\w+)':", r'"\1":', text)
        text = re.sub(r":\s*'([^']*)'", r': "\1"', text)
        
        return text
    
    def _assign_task_ids(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Назначает уникальные ID всем задачам"""
        task_counter = 1
        
        # ID для Epic
        if "epic" in result:
            result["epic"]["epic_id"] = f"EPIC-{task_counter}"
            task_counter += 1
        
        # ID для User Stories
        if "user_stories" in result:
            for story in result["user_stories"]:
                story["story_id"] = f"US-{task_counter}"
                task_counter += 1
        
        # ID для Tasks
        if "tasks" in result:
            for task in result["tasks"]:
                task["task_id"] = f"TASK-{task_counter}"
                task_counter += 1
        
        # ID для Subtasks
        if "subtasks" in result:
            for subtask in result["subtasks"]:
                subtask["subtask_id"] = f"SUB-{task_counter}"
                task_counter += 1
        
        return result
    
    def _fallback_task_creation(self, text: str, project_id: str) -> Dict[str, Any]:
        """Простое создание задач если AI не сработал"""
        return {
            "epic": {
                "epic_id": "EPIC-1",
                "title": "Задача из текста",
                "description": text[:200],
                "business_value": "Требуется уточнение",
                "priority": "medium",
                "deadline": None
            },
            "user_stories": [],
            "tasks": [
                {
                    "task_id": "TASK-1",
                    "title": "Проанализировать требования",
                    "description": text[:500],
                    "type": "analysis",
                    "priority": "high",
                    "story_points": 3,
                    "estimated_hours": 8,
                    "complexity": "medium",
                    "dependencies": [],
                    "assignee": None,
                    "deadline": None,
                    "definition_of_done": ["Требования проанализированы", "Задачи декомпозированы"]
                }
            ],
            "subtasks": [],
            "insights": {
                "total_estimated_hours": 8,
                "critical_path": ["TASK-1"],
                "risks": ["Требуется дополнительная информация"],
                "recommendations": ["Уточнить требования", "Провести встречу с заказчиком"]
            },
            "created_at": datetime.now().isoformat(),
            "project_id": project_id,
            "source_text": text[:500]
        }
    
    def fill_task_fields(self, text: str, project_id: str = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Заполняет поля задачи на основе текста через AI
        
        Args:
            text: Текст для анализа (ТЗ, описание, переписка)
            project_id: ID проекта (опционально)
            context: Контекст проекта (опционально)
            
        Returns:
            Словарь с заполненными полями задачи
        """
        prompt = f"""Ты AI-Scrum Master для банка. Проанализируй следующий текст и заполни поля задачи.

Текст для анализа:
{text}

{f'Контекст проекта: {json.dumps(context, ensure_ascii=False, indent=2)}' if context else ''}

Заполни все поля задачи в формате JSON:

{{
    "title": "краткое и понятное название задачи",
    "description": "детальное описание задачи с контекстом и требованиями",
    "type": "development/testing/documentation/design/other",
    "priority": "high/medium/low",
    "story_points": 1-13,
    "estimated_hours": 1-40,
    "complexity": "low/medium/high",
    "assignee": "имя исполнителя или null если не указан",
    "deadline": "дедлайн в формате YYYY-MM-DD или null если не указан",
    "dependencies": ["ID другой задачи или пустой массив"],
    "definition_of_done": ["критерий 1", "критерий 2", "критерий 3"],
    "acceptance_criteria": ["критерий приёмки 1", "критерий приёмки 2"],
    "tags": ["тег1", "тег2"],
    "notes": "дополнительные заметки и комментарии"
}}

Верни ТОЛЬКО валидный JSON без дополнительных комментариев."""

        try:
            response = self.model.generate_content(prompt)
            if hasattr(response, 'text'):
                text_response = response.text.strip()
                
                # Извлекаем JSON
                text_response = self._extract_json(text_response)
                
                try:
                    result = json.loads(text_response)
                    
                    # Добавляем метаданные
                    result["source_text"] = text[:500]  # Первые 500 символов для справки
                    if project_id:
                        result["project_id"] = project_id
                    
                    return result
                except json.JSONDecodeError as e:
                    print(f"Ошибка парсинга JSON при заполнении полей задачи: {e}")
                    return self._fallback_task_fields(text)
            else:
                return self._fallback_task_fields(text)
        except Exception as e:
            print(f"Ошибка при заполнении полей задачи: {e}")
            return self._fallback_task_fields(text)
    
    def _fallback_task_fields(self, text: str) -> Dict[str, Any]:
        """Простое заполнение полей если AI не сработал"""
        return {
            "title": text[:100] if len(text) > 100 else text,
            "description": text[:1000] if len(text) > 1000 else text,
            "type": "other",
            "priority": "medium",
            "story_points": 3,
            "estimated_hours": 8,
            "complexity": "medium",
            "assignee": None,
            "deadline": None,
            "dependencies": [],
            "definition_of_done": ["Задача выполнена", "Код проверен", "Документация обновлена"],
            "acceptance_criteria": [],
            "tags": [],
            "notes": ""
        }
    
    def confirm_and_save_tasks(self, tasks_data: Dict[str, Any], save_to_jira: bool = False) -> Dict[str, Any]:
        """
        Подтверждает и сохраняет задачи
        
        Args:
            tasks_data: Данные задач для сохранения
            save_to_jira: Не используется (Jira интеграция удалена)
            
        Returns:
            Результат сохранения
        """
        import os
        import json
        
        project_id = tasks_data.get("project_id")
        tasks_file = os.path.join("data", "scrum_tasks.json")
        
        # Загружаем существующие задачи
        all_tasks = []
        if os.path.exists(tasks_file):
            try:
                with open(tasks_file, 'r', encoding='utf-8') as f:
                    all_tasks = json.load(f)
            except:
                all_tasks = []
        
        # Добавляем project_id ко всем задачам и сохраняем
        saved_tasks = []
        
        # Сохраняем Epic как задачу
        if tasks_data.get("epic"):
            epic = tasks_data["epic"]
            epic_task = {
                "task_id": epic.get("epic_id", f"EPIC-{datetime.now().strftime('%Y%m%d%H%M%S')}"),
                "project_id": project_id,
                "title": epic.get("title", ""),
                "description": epic.get("description", ""),
                "type": "epic",
                "priority": epic.get("priority", "medium"),
                "status": "planned",
                "created_at": datetime.now().isoformat()
            }
            all_tasks.append(epic_task)
            saved_tasks.append(epic_task["task_id"])
        
        # Сохраняем User Stories
        for story in tasks_data.get("user_stories", []):
            story_task = {
                "task_id": story.get("story_id", f"US-{datetime.now().strftime('%Y%m%d%H%M%S')}"),
                "project_id": project_id,
                "title": story.get("title", ""),
                "description": story.get("description", ""),
                "type": "user_story",
                "priority": story.get("priority", "medium"),
                "story_points": story.get("story_points", 0),
                "status": "planned",
                "created_at": datetime.now().isoformat()
            }
            all_tasks.append(story_task)
            saved_tasks.append(story_task["task_id"])
        
        # Сохраняем Tasks
        for task in tasks_data.get("tasks", []):
            task["project_id"] = project_id
            task["status"] = task.get("status", "planned")
            task["created_at"] = datetime.now().isoformat()
            all_tasks.append(task)
            saved_tasks.append(task.get("task_id"))
            
            # Автоматически создаём дедлайн если указан в задаче
            if task.get("deadline"):
                try:
                    from scrum_models.deadline_tracker import DeadlineTracker
                    deadline_tracker = DeadlineTracker()
                    deadline_tracker.add_deadline(
                        task_id=task.get("task_id"),
                        deadline=task.get("deadline"),
                        assignee=task.get("assignee") or "",
                        project_id=project_id,
                        priority=task.get("priority", "medium")
                    )
                except Exception as e:
                    print(f"Ошибка при создании дедлайна для задачи {task.get('task_id')}: {e}")
        
        # Сохраняем Subtasks
        for subtask in tasks_data.get("subtasks", []):
            subtask["project_id"] = project_id
            subtask["status"] = subtask.get("status", "planned")
            subtask["created_at"] = datetime.now().isoformat()
            all_tasks.append(subtask)
            saved_tasks.append(subtask.get("subtask_id"))
        
        # Сохраняем в файл
        os.makedirs(os.path.dirname(tasks_file), exist_ok=True)
        with open(tasks_file, 'w', encoding='utf-8') as f:
            json.dump(all_tasks, f, ensure_ascii=False, indent=2)
        
        result = {
            "saved": True,
            "epic_id": tasks_data.get("epic", {}).get("epic_id"),
            "tasks_count": len(tasks_data.get("tasks", [])),
            "user_stories_count": len(tasks_data.get("user_stories", [])),
            "saved_tasks": saved_tasks,
            "jira_synced": False,
            "saved_at": datetime.now().isoformat()
        }
        
        return result


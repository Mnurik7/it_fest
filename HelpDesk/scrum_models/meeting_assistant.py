"""
Модуль AI-ассистента встреч (Stand-up, Grooming, Demo)
"""
import json
import re
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import google.generativeai as genai


class MeetingAssistant:
    """Ассистент для встреч: анализ транскриптов, выявление задач, генерация отчётов"""
    
    def __init__(self, gemini_model, data_dir: str = "data"):
        self.model = gemini_model
        self.data_dir = data_dir
        self.meetings_file = os.path.join(data_dir, "scrum_meetings.json")
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """Создаёт директорию для данных"""
        import os
        os.makedirs(self.data_dir, exist_ok=True)
    
    def analyze_meeting_transcript(self, transcript: str, meeting_type: str, 
                                  project_id: str, participants: List[str]) -> Dict[str, Any]:
        """
        Анализирует транскрипт встречи
        
        Args:
            transcript: Транскрипт встречи
            meeting_type: Тип встречи (standup, grooming, demo, planning, retrospective)
            project_id: ID проекта
            participants: Список участников
            
        Returns:
            Анализ встречи с выявленными задачами и решениями
        """
        prompt = f"""Ты AI-Scrum Master. Проанализируй транскрипт встречи и выяви все важные моменты.

Тип встречи: {meeting_type}
Участники: {', '.join(participants)}
Проект: {project_id}

Транскрипт:
{transcript}

Проанализируй и верни результат в формате JSON:

{{
    "meeting_summary": {{
        "type": "{meeting_type}",
        "date": "{datetime.now().isoformat()}",
        "participants": {json.dumps(participants)},
        "duration_minutes": 0,
        "key_topics": ["тема 1", "тема 2"]
    }},
    "discussions": [
        {{
            "topic": "тема обсуждения",
            "participants": ["участник 1"],
            "summary": "краткое резюме",
            "decisions": ["решение 1", "решение 2"],
            "action_items": ["действие 1", "действие 2"]
        }}
    ],
    "new_tasks": [
        {{
            "title": "название задачи",
            "description": "описание из обсуждения",
            "assignee": "имя исполнителя",
            "priority": "high/medium/low",
            "deadline": "дедлайн если указан",
            "source_discussion": "из какого обсуждения"
        }}
    ],
    "updated_tasks": [
        {{
            "task_id": "ID задачи",
            "updates": {{
                "status": "новый статус",
                "comments": "комментарий",
                "deadline": "новый дедлайн",
                "assignee": "новый исполнитель"
            }}
        }}
    ],
    "dependencies_identified": [
        {{
            "task1": "ID задачи 1",
            "task2": "ID задачи 2",
            "dependency_type": "blocks/is_blocked_by/related_to"
        }}
    ],
    "problems_identified": [
        {{
            "problem": "описание проблемы",
            "severity": "low/medium/high",
            "impact": "влияние на проект",
            "suggested_solutions": ["решение 1", "решение 2"]
        }}
    ],
    "follow_up_questions": [
        "вопрос для уточнения 1",
        "вопрос для уточнения 2"
    ],
    "meeting_report": {{
        "what_was_discussed": "что обсуждали",
        "what_was_decided": "что решили",
        "who_is_responsible": [
            {{
                "person": "имя",
                "responsibilities": ["ответственность 1", "ответственность 2"],
                "deadlines": ["дедлайн 1"]
            }}
        ],
        "next_steps": ["шаг 1", "шаг 2"]
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
                    result["analyzed_at"] = datetime.now().isoformat()
                    result["project_id"] = project_id
                    result["meeting_id"] = f"MEET-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    result["transcript"] = transcript[:1000]  # Сохраняем первые 1000 символов транскрипта
                    
                    # Сохраняем результат анализа
                    self._save_meeting(result)
                    
                    return result
                except json.JSONDecodeError:
                    return self._fallback_analysis(transcript, meeting_type, project_id, participants)
            else:
                return self._fallback_analysis(transcript, meeting_type, project_id, participants)
        except Exception as e:
            print(f"Ошибка при анализе встречи: {e}")
            return self._fallback_analysis(transcript, meeting_type, project_id, participants)
    
    def generate_meeting_report(self, analysis: Dict[str, Any]) -> str:
        """
        Генерирует текстовый отчёт о встрече
        
        Args:
            analysis: Результат анализа встречи
            
        Returns:
            Текстовый отчёт
        """
        report = f"""# Отчёт о встрече: {analysis.get('meeting_summary', {}).get('type', 'Встреча').upper()}

**Дата:** {analysis.get('meeting_summary', {}).get('date', 'N/A')}
**Участники:** {', '.join(analysis.get('meeting_summary', {}).get('participants', []))}

## Что обсуждали
{analysis.get('meeting_report', {}).get('what_was_discussed', 'N/A')}

## Что решили
{analysis.get('meeting_report', {}).get('what_was_decided', 'N/A')}

## Ответственность и дедлайны
"""
        for person in analysis.get('meeting_report', {}).get('who_is_responsible', []):
            report += f"\n**{person.get('person', 'N/A')}:**\n"
            for resp in person.get('responsibilities', []):
                report += f"- {resp}\n"
        
        report += "\n## Следующие шаги\n"
        for step in analysis.get('meeting_report', {}).get('next_steps', []):
            report += f"- {step}\n"
        
        if analysis.get('new_tasks'):
            report += "\n## Новые задачи\n"
            for task in analysis.get('new_tasks', []):
                report += f"- **{task.get('title', 'N/A')}** (Исполнитель: {task.get('assignee', 'Не назначен')})\n"
        
        if analysis.get('problems_identified'):
            report += "\n## Выявленные проблемы\n"
            for problem in analysis.get('problems_identified', []):
                report += f"- **{problem.get('problem', 'N/A')}** (Серьёзность: {problem.get('severity', 'N/A')})\n"
        
        return report
    
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
    
    def _save_meeting(self, meeting_data: Dict[str, Any]):
        """Сохраняет результат анализа встречи"""
        meetings = self._load_meetings()
        meetings.append(meeting_data)
        self._save_meetings(meetings)
    
    def _load_meetings(self) -> List[Dict[str, Any]]:
        """Загружает сохранённые встречи"""
        if os.path.exists(self.meetings_file):
            try:
                with open(self.meetings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_meetings(self, meetings: List[Dict[str, Any]]):
        """Сохраняет встречи в файл"""
        with open(self.meetings_file, 'w', encoding='utf-8') as f:
            json.dump(meetings, f, ensure_ascii=False, indent=2)
    
    def get_meetings(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Получает список встреч (опционально фильтр по проекту)"""
        meetings = self._load_meetings()
        if project_id:
            return [m for m in meetings if m.get("project_id") == project_id]
        return meetings
    
    def _fallback_analysis(self, transcript: str, meeting_type: str, 
                          project_id: str, participants: List[str]) -> Dict[str, Any]:
        """Простой анализ если AI не сработал"""
        result = {
            "meeting_summary": {
                "type": meeting_type,
                "date": datetime.now().isoformat(),
                "participants": participants,
                "duration_minutes": 0,
                "key_topics": []
            },
            "discussions": [],
            "new_tasks": [],
            "updated_tasks": [],
            "dependencies_identified": [],
            "problems_identified": [],
            "follow_up_questions": ["Требуется дополнительный анализ"],
            "meeting_report": {
                "what_was_discussed": transcript[:200],
                "what_was_decided": "Требуется уточнение",
                "who_is_responsible": [],
                "next_steps": ["Проанализировать транскрипт вручную"]
            },
            "analyzed_at": datetime.now().isoformat(),
            "project_id": project_id,
            "meeting_id": f"MEET-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "transcript": transcript[:1000]
        }
        
        # Сохраняем даже fallback результат
        self._save_meeting(result)
        
        return result
    
    def sync_to_jira(self, analysis: Dict[str, Any], 
                    integration_manager=None,
                    project_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Jira интеграция удалена
        
        Args:
            analysis: Результат анализа встречи
            integration_manager: Не используется
            project_key: Не используется
            
        Returns:
            Результат (всегда False, так как интеграция удалена)
        """
        return {
            'success': False,
            'error': 'Jira интеграция удалена',
            'synced': False
        }


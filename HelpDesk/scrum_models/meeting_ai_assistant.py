"""
AI-ассистент во время звонков
Генерация вопросов, ответы на вопросы участников, отслеживание прогресса
"""
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import google.generativeai as genai


class MeetingAIAssistant:
    """AI-ассистент для работы во время встреч"""
    
    def __init__(self, gemini_model):
        """
        Инициализация AI-ассистента
        
        Args:
            gemini_model: Модель Gemini для генерации
        """
        self.model = gemini_model
        self.meeting_context: Dict[str, Any] = {}
        self.transcript_history: List[Dict[str, Any]] = []
        self.generated_questions: List[str] = []
        self.answered_questions: List[Dict[str, Any]] = []
        self.action_items: List[Dict[str, Any]] = []
    
    def initialize_meeting(self, meeting_type: str, project_id: str, 
                          participants: List[str], meeting_goal: Optional[str] = None):
        """
        Инициализирует контекст встречи
        
        Args:
            meeting_type: Тип встречи (standup, grooming, demo, planning, retrospective)
            project_id: ID проекта
            participants: Список участников
            meeting_goal: Цель встречи
        """
        self.meeting_context = {
            'meeting_type': meeting_type,
            'project_id': project_id,
            'participants': participants,
            'meeting_goal': meeting_goal,
            'started_at': datetime.now().isoformat(),
            'status': 'active'
        }
        self.transcript_history = []
        self.generated_questions = []
        self.answered_questions = []
        self.action_items = []
    
    def add_transcript_chunk(self, text: str, speaker: str, timestamp: Optional[str] = None):
        """
        Добавляет фрагмент транскрипта для анализа
        
        Args:
            text: Текст транскрипта
            speaker: Имя говорящего
            timestamp: Временная метка
        """
        chunk = {
            'text': text,
            'speaker': speaker,
            'timestamp': timestamp or datetime.now().isoformat()
        }
        self.transcript_history.append(chunk)
    
    def generate_contextual_question(self) -> Optional[str]:
        """
        Генерирует контекстуальный вопрос на основе текущего обсуждения
        
        Returns:
            Вопрос для уточнения или None если вопрос не нужен
        """
        if len(self.transcript_history) < 3:
            return None  # Недостаточно контекста
        
        # Последние несколько фрагментов транскрипта
        recent_transcript = "\n".join([
            f"{chunk['speaker']}: {chunk['text']}"
            for chunk in self.transcript_history[-5:]
        ])
        
        prompt = f"""Ты AI-Scrum Master, который помогает на встрече. На основе текущего обсуждения сгенерируй уточняющий вопрос, который поможет:
1. Уточнить детали задачи или требования
2. Выявить потенциальные проблемы или риски
3. Уточнить дедлайны или приоритеты
4. Прояснить ответственность или зависимости

Тип встречи: {self.meeting_context.get('meeting_type', 'standup')}
Проект: {self.meeting_context.get('project_id', 'N/A')}

Текущее обсуждение:
{recent_transcript}

Сгенерируй ОДИН краткий уточняющий вопрос на русском языке. Если вопрос не нужен (всё понятно), верни только слово "НЕТ".

Вопрос:"""

        try:
            response = self.model.generate_content(prompt)
            if hasattr(response, 'text'):
                question = response.text.strip()
                
                # Проверяем, не является ли это отказом
                if question.upper() in ['НЕТ', 'NO', 'N/A', '']:
                    return None
                
                # Убираем кавычки если есть
                question = question.strip('"\'')
                
                if question and question not in self.generated_questions:
                    self.generated_questions.append(question)
                    return question
        except Exception as e:
            print(f"Ошибка генерации вопроса: {e}")
        
        return None
    
    def answer_question(self, question: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Отвечает на вопрос участника встречи
        
        Args:
            question: Вопрос от участника
            context: Дополнительный контекст (опционально)
            
        Returns:
            Ответ на вопрос
        """
        # Собираем контекст встречи
        meeting_type = self.meeting_context.get('meeting_type', 'standup')
        project_id = self.meeting_context.get('project_id', 'N/A')
        participants = ', '.join(self.meeting_context.get('participants', []))
        
        # Последние фрагменты транскрипта для контекста
        recent_context = "\n".join([
            f"{chunk['speaker']}: {chunk['text']}"
            for chunk in self.transcript_history[-10:]
        ])
        
        prompt = f"""Ты AI-Scrum Master, который помогает команде на встрече. Ответь на вопрос участника, используя контекст встречи.

Тип встречи: {meeting_type}
Проект: {project_id}
Участники: {participants}

Контекст встречи:
{recent_context}

{f'Дополнительный контекст: {context}' if context else ''}

Вопрос участника: {question}

Дай краткий, полезный ответ на русском языке. Если информация недоступна в контексте, так и скажи.

Ответ:"""

        try:
            response = self.model.generate_content(prompt)
            if hasattr(response, 'text'):
                answer = response.text.strip()
                
                answer_data = {
                    'question': question,
                    'answer': answer,
                    'answered_at': datetime.now().isoformat(),
                    'context_used': len(self.transcript_history)
                }
                
                self.answered_questions.append(answer_data)
                return {
                    'success': True,
                    'answer': answer,
                    'answer_data': answer_data
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка генерации ответа: {str(e)}'
            }
        
        return {
            'success': False,
            'error': 'Не удалось сгенерировать ответ'
        }
    
    def track_progress(self) -> Dict[str, Any]:
        """
        Отслеживает прогресс встречи и выявляет проблемы
        
        Returns:
            Анализ прогресса встречи
        """
        if len(self.transcript_history) < 5:
            return {
                'progress': 'insufficient_data',
                'message': 'Недостаточно данных для анализа прогресса'
            }
        
        meeting_type = self.meeting_context.get('meeting_type', 'standup')
        meeting_goal = self.meeting_context.get('meeting_goal', '')
        
        # Полный транскрипт для анализа
        full_transcript = "\n".join([
            f"{chunk['speaker']}: {chunk['text']}"
            for chunk in self.transcript_history
        ])
        
        prompt = f"""Ты AI-Scrum Master. Проанализируй прогресс встречи и верни JSON:

Тип встречи: {meeting_type}
Цель встречи: {meeting_goal}

Транскрипт встречи:
{full_transcript}

Проанализируй и верни JSON:
{{
    "progress_status": "on_track/behind/ahead/blocked",
    "progress_percentage": 0-100,
    "key_topics_covered": ["тема 1", "тема 2"],
    "blockers_identified": ["блокер 1", "блокер 2"],
    "action_items_identified": [
        {{
            "action": "действие",
            "assignee": "исполнитель",
            "deadline": "дедлайн"
        }}
    ],
    "next_steps_suggested": ["шаг 1", "шаг 2"],
    "recommendations": ["рекомендация 1", "рекомендация 2"]
}}

Верни ТОЛЬКО валидный JSON."""

        try:
            response = self.model.generate_content(prompt)
            if hasattr(response, 'text'):
                text_response = response.text.strip()
                
                # Извлекаем JSON
                if '```json' in text_response:
                    text_response = text_response.split('```json')[1].split('```')[0].strip()
                elif '```' in text_response:
                    parts = text_response.split('```')
                    for part in parts:
                        part = part.strip()
                        if part.startswith('{'):
                            text_response = part
                            break
                
                try:
                    progress_data = json.loads(text_response)
                    
                    # Обновляем action items если есть
                    if 'action_items_identified' in progress_data:
                        for item in progress_data['action_items_identified']:
                            if item not in self.action_items:
                                self.action_items.append(item)
                    
                    return {
                        'success': True,
                        'progress': progress_data
                    }
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            print(f"Ошибка анализа прогресса: {e}")
        
        return {
            'success': False,
            'progress': {
                'progress_status': 'unknown',
                'message': 'Не удалось проанализировать прогресс'
            }
        }
    
    def generate_reminder(self, context: Optional[str] = None) -> Optional[str]:
        """
        Генерирует напоминание о дедлайнах или важных моментах
        
        Args:
            context: Дополнительный контекст
            
        Returns:
            Текст напоминания или None
        """
        prompt = f"""Ты AI-Scrum Master. На основе текущего обсуждения сгенерируй краткое напоминание о:
1. Ближайших дедлайнах
2. Важных задачах, которые могут быть забыты
3. Зависимостях между задачами
4. Регулярных процессах (stand-up, review, etc.)

Тип встречи: {self.meeting_context.get('meeting_type', 'standup')}
Проект: {self.meeting_context.get('project_id', 'N/A')}

{f'Контекст: {context}' if context else 'Используй контекст встречи'}

Если напоминание не нужно, верни "НЕТ".
Если нужно, верни краткий текст напоминания (1-2 предложения).

Напоминание:"""

        try:
            response = self.model.generate_content(prompt)
            if hasattr(response, 'text'):
                reminder = response.text.strip()
                
                if reminder.upper() in ['НЕТ', 'NO', 'N/A', '']:
                    return None
                
                return reminder.strip('"\'')
        except Exception as e:
            print(f"Ошибка генерации напоминания: {e}")
        
        return None
    
    def get_meeting_summary(self) -> Dict[str, Any]:
        """
        Получает краткую сводку встречи
        
        Returns:
            Сводка встречи
        """
        full_transcript = self.get_full_transcript()
        
        return {
            'meeting_context': self.meeting_context,
            'transcript_length': len(self.transcript_history),
            'questions_generated': len(self.generated_questions),
            'questions_answered': len(self.answered_questions),
            'action_items': len(self.action_items),
            'generated_questions': self.generated_questions,
            'answered_questions': self.answered_questions,
            'action_items_list': self.action_items,
            'full_transcript': full_transcript
        }
    
    def get_full_transcript(self) -> str:
        """Получает полный транскрипт встречи"""
        return "\n".join([
            f"[{chunk.get('timestamp', '')}] {chunk.get('speaker', 'Unknown')}: {chunk.get('text', '')}"
            for chunk in self.transcript_history
        ])
    
    def end_meeting(self):
        """Завершает встречу и очищает данные"""
        self.meeting_context['status'] = 'ended'
        self.meeting_context['ended_at'] = datetime.now().isoformat()
        
        # Можно сохранить сводку если нужно
        return self.get_meeting_summary()


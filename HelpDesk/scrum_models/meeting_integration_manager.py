"""
Менеджер интеграции встреч
Объединяет Google Meet, транскрибацию и AI-ассистента
"""
from typing import Dict, Optional, Any
from scrum_models.google_meet_integration import GoogleMeetIntegration
from scrum_models.real_time_transcription import RealTimeTranscriber
from scrum_models.meeting_ai_assistant import MeetingAIAssistant


class MeetingIntegrationManager:
    """Менеджер интеграции встреч с транскрибацией и AI-ассистентом"""
    
    def __init__(self, gemini_model):
        """
        Инициализация менеджера
        
        Args:
            gemini_model: Модель Gemini для AI-ассистента
        """
        self.gemini_model = gemini_model
        
        # Интеграции
        self.google_meet: Optional[GoogleMeetIntegration] = None
        
        # Активные встречи с полной интеграцией
        self.active_meetings: Dict[str, Dict[str, Any]] = {}
    
    def initialize_google_meet(self, client_id: str, client_secret: str, redirect_uri: str):
        """Инициализирует Google Meet интеграцию"""
        self.google_meet = GoogleMeetIntegration(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri
        )
        return self.google_meet
    
    def start_meeting_with_ai(self, 
                              meeting_id: str,
                              meeting_type: str,
                              project_id: str,
                              participants: list,
                              provider: str = 'google',
                              transcription_provider: str = 'local',
                              meeting_goal: Optional[str] = None) -> Dict[str, Any]:
        """
        Запускает встречу с полной интеграцией: подключение, транскрибация, AI-ассистент
        
        Args:
            meeting_id: ID встречи или ссылка
            meeting_type: Тип встречи (standup, grooming, etc.)
            project_id: ID проекта
            participants: Список участников
            provider: Провайдер ('google' или 'teams')
            transcription_provider: Провайдер транскрибации ('google', 'azure', 'local')
            meeting_goal: Цель встречи
            
        Returns:
            Результат запуска встречи
        """
        # 1. Инициализируем AI-ассистента
        ai_assistant = MeetingAIAssistant(self.gemini_model)
        ai_assistant.initialize_meeting(
            meeting_type=meeting_type,
            project_id=project_id,
            participants=participants,
            meeting_goal=meeting_goal
        )
        
        # 2. Инициализируем транскрибера
        transcriber = RealTimeTranscriber(
            provider=transcription_provider,
            language='ru-RU',
            on_transcript_chunk=lambda chunk: self._handle_transcript_chunk(meeting_id, chunk, ai_assistant)
        )
        
        # 3. Подключаемся к встрече
        meeting_data = None
        if provider == 'google' and self.google_meet:
            result = self.google_meet.join_meeting(meeting_id, project_id)
            if result.get('success'):
                meeting_data = self.google_meet.active_meetings.get(result.get('meeting_id'))
        else:
            return {
                'success': False,
                'error': f'Провайдер {provider} не настроен'
            }
        
        if not meeting_data:
            return {
                'success': False,
                'error': 'Не удалось подключиться к встрече'
            }
        
        # 4. Сохраняем полную интеграцию
        integration_data = {
            'meeting_id': meeting_id,
            'meeting_data': meeting_data,
            'ai_assistant': ai_assistant,
            'transcriber': transcriber,
            'provider': provider,
            'started_at': ai_assistant.meeting_context.get('started_at'),
            'status': 'active'
        }
        
        self.active_meetings[meeting_id] = integration_data
        
        # 5. Запускаем транскрибацию (в реальной системе это будет через аудио поток)
        # Пока только инициализируем
        
        return {
            'success': True,
            'meeting_id': meeting_id,
            'message': 'Встреча запущена с полной интеграцией',
            'transcription_ready': True,
            'ai_assistant_ready': True
        }
    
    def _handle_transcript_chunk(self, meeting_id: str, chunk: Dict[str, Any], ai_assistant: MeetingAIAssistant):
        """Обрабатывает фрагмент транскрипта"""
        # Добавляем в AI-ассистента
        ai_assistant.add_transcript_chunk(
            text=chunk.get('text', ''),
            speaker=chunk.get('speaker', 'Unknown'),
            timestamp=chunk.get('timestamp')
        )
        
        # Добавляем в интеграцию встречи
        if meeting_id in self.active_meetings:
            integration = self.active_meetings[meeting_id]
            
            # Добавляем в транскрипт встречи
            if 'google_meet' in integration.get('provider', ''):
                if self.google_meet and meeting_id in self.google_meet.active_meetings:
                    self.google_meet.add_transcription_chunk(
                        meeting_id=meeting_id,
                        text=chunk.get('text', ''),
                        speaker=chunk.get('speaker', 'Unknown'),
                        timestamp=chunk.get('timestamp')
                    )
    
    def generate_ai_question(self, meeting_id: str) -> Optional[str]:
        """Генерирует вопрос AI-ассистента для встречи"""
        if meeting_id not in self.active_meetings:
            return None
        
        integration = self.active_meetings[meeting_id]
        ai_assistant = integration.get('ai_assistant')
        
        if not ai_assistant:
            return None
        
        return ai_assistant.generate_contextual_question()
    
    def answer_question(self, meeting_id: str, question: str) -> Dict[str, Any]:
        """Отвечает на вопрос участника встречи"""
        if meeting_id not in self.active_meetings:
            return {
                'success': False,
                'error': 'Встреча не найдена'
            }
        
        integration = self.active_meetings[meeting_id]
        ai_assistant = integration.get('ai_assistant')
        
        if not ai_assistant:
            return {
                'success': False,
                'error': 'AI-ассистент не инициализирован'
            }
        
        return ai_assistant.answer_question(question)
    
    def get_meeting_progress(self, meeting_id: str) -> Dict[str, Any]:
        """Получает прогресс встречи"""
        if meeting_id not in self.active_meetings:
            return {
                'success': False,
                'error': 'Встреча не найдена'
            }
        
        integration = self.active_meetings[meeting_id]
        ai_assistant = integration.get('ai_assistant')
        
        if not ai_assistant:
            return {
                'success': False,
                'error': 'AI-ассистент не инициализирован'
            }
        
        return ai_assistant.track_progress()
    
    def end_meeting(self, meeting_id: str) -> Dict[str, Any]:
        """Завершает встречу и возвращает сводку"""
        if meeting_id not in self.active_meetings:
            return {
                'success': False,
                'error': 'Встреча не найдена'
            }
        
        integration = self.active_meetings[meeting_id]
        
        # Завершаем транскрибацию
        transcriber = integration.get('transcriber')
        if transcriber and transcriber.is_transcribing:
            transcriber.stop_transcription()
        
        # Завершаем AI-ассистента
        ai_assistant = integration.get('ai_assistant')
        summary = None
        if ai_assistant:
            summary = ai_assistant.end_meeting()
        
        # Покидаем встречу
        provider = integration.get('provider', '')
        if provider == 'google' and self.google_meet:
            self.google_meet.leave_meeting(meeting_id)
        
        # Удаляем из активных встреч
        del self.active_meetings[meeting_id]
        
        return {
            'success': True,
            'summary': summary,
            'message': 'Встреча завершена'
        }


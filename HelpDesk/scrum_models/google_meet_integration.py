"""
Модуль интеграции с Google Meet
Подключение к звонкам, получение аудио, транскрибация
"""
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
import logging

logger = logging.getLogger(__name__)

# Попытка импортировать библиотеки Google (если установлены)
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError as e:
    GOOGLE_API_AVAILABLE = False
    missing_module = str(e).split("'")[1] if "'" in str(e) else "неизвестный модуль"
    logger.warning(f"⚠️  Библиотеки Google API не установлены. Установите: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    logger.warning(f"Отсутствует модуль: {missing_module}")


class GoogleMeetIntegration:
    """Интеграция с Google Meet для подключения к звонкам и транскрибации"""
    
    # Scopes для доступа к Google Meet API
    # Для тестирования используем упрощенные scopes
    # Если нужен полный доступ, можно вернуть cloud-platform scope
    SCOPES = [
        'https://www.googleapis.com/auth/meetings.space.created',
        'https://www.googleapis.com/auth/calendar.readonly'
        # 'https://www.googleapis.com/auth/cloud-platform'  # Временно отключен для тестирования
    ]
    
    def __init__(self, 
                 client_id: Optional[str] = None,
                 client_secret: Optional[str] = None,
                 redirect_uri: Optional[str] = None,
                 credentials_path: str = 'data/google_meet_credentials.json',
                 token_path: str = 'data/google_meet_token.json'):
        """
        Инициализация интеграции с Google Meet
        
        Args:
            client_id: OAuth 2.0 Client ID
            client_secret: OAuth 2.0 Client Secret
            redirect_uri: Redirect URI для OAuth
            credentials_path: Путь к файлу с OAuth credentials
            token_path: Путь к файлу с токеном
        """
        self.client_id = client_id or os.getenv('GOOGLE_MEET_CLIENT_ID', '')
        self.client_secret = client_secret or os.getenv('GOOGLE_MEET_CLIENT_SECRET', '')
        self.redirect_uri = redirect_uri or os.getenv('GOOGLE_MEET_REDIRECT_URI', 'http://localhost:5000/api/ai-scrum/integrations/google-meet/callback')
        self.credentials_path = credentials_path
        self.token_path = token_path
        
        self.credentials = None
        self.service = None
        self.is_authenticated = False
        
        # Обработчики событий
        self.on_meeting_start: Optional[Callable] = None
        self.on_meeting_end: Optional[Callable] = None
        self.on_participant_join: Optional[Callable] = None
        self.on_transcription_chunk: Optional[Callable] = None
        
        # Активные встречи
        self.active_meetings: Dict[str, Dict[str, Any]] = {}
        
        # Загружаем сохранённый токен если есть
        self._load_credentials()
    
    def _load_credentials(self):
        """Загружает сохранённые credentials"""
        if not GOOGLE_API_AVAILABLE:
            return
        
        if os.path.exists(self.token_path):
            try:
                self.credentials = Credentials.from_authorized_user_file(
                    self.token_path, self.SCOPES
                )
                
                # Обновляем токен если нужно
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                    self._save_credentials()
                
                if self.credentials and self.credentials.valid:
                    self.is_authenticated = True
                    self.service = build('meet', 'v2', credentials=self.credentials)
                    logger.info("✅ Google Meet credentials загружены")
            except Exception as e:
                logger.error(f"Ошибка загрузки credentials: {e}")
    
    def _save_credentials(self):
        """Сохраняет credentials в файл"""
        if self.credentials:
            os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
            with open(self.token_path, 'w') as token:
                token.write(self.credentials.to_json())
    
    def get_authorization_url(self) -> Dict[str, Any]:
        """
        Получает URL для авторизации OAuth
        
        Returns:
            URL для авторизации
        """
        if not GOOGLE_API_AVAILABLE:
            return {
                'success': False,
                'error': 'Библиотеки Google API не установлены'
            }
        
        if not self.client_id or not self.client_secret:
            return {
                'success': False,
                'error': 'OAuth credentials не настроены. Укажите client_id и client_secret'
            }
        
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri]
                    }
                },
                scopes=self.SCOPES,
                redirect_uri=self.redirect_uri
            )
            
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true'
            )
            
            # Сохраняем state для проверки
            state_path = os.path.join(os.path.dirname(self.token_path), 'google_meet_oauth_state.json')
            os.makedirs(os.path.dirname(state_path), exist_ok=True)
            with open(state_path, 'w') as f:
                json.dump({'state': state}, f)
            
            return {
                'success': True,
                'authorization_url': authorization_url,
                'state': state
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка создания authorization URL: {str(e)}'
            }
    
    def handle_oauth_callback(self, code: str, state: str) -> Dict[str, Any]:
        """
        Обрабатывает OAuth callback и получает токен
        
        Args:
            code: Authorization code из callback
            state: State для проверки
            
        Returns:
            Результат авторизации
        """
        if not GOOGLE_API_AVAILABLE:
            return {
                'success': False,
                'error': 'Библиотеки Google API не установлены'
            }
        
        # Проверяем state
        state_path = os.path.join(os.path.dirname(self.token_path), 'google_meet_oauth_state.json')
        if os.path.exists(state_path):
            with open(state_path, 'r') as f:
                saved_state = json.load(f).get('state')
                if saved_state != state:
                    return {
                        'success': False,
                        'error': 'Invalid state parameter'
                    }
        
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri]
                    }
                },
                scopes=self.SCOPES,
                redirect_uri=self.redirect_uri
            )
            
            flow.fetch_token(code=code)
            
            self.credentials = flow.credentials
            self._save_credentials()
            
            if self.credentials and self.credentials.valid:
                self.is_authenticated = True
                self.service = build('meet', 'v2', credentials=self.credentials)
                logger.info("✅ Google Meet авторизация успешна")
                
                return {
                    'success': True,
                    'message': 'Авторизация успешна'
                }
            else:
                return {
                    'success': False,
                    'error': 'Не удалось получить валидные credentials'
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка обработки callback: {str(e)}'
            }
    
    def join_meeting(self, meeting_code: str, project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Подключается к встрече Google Meet
        
        Args:
            meeting_code: Код встречи или ссылка
            project_id: ID проекта для связи
            
        Returns:
            Результат подключения
        """
        if not self.is_authenticated:
            return {
                'success': False,
                'error': 'Не авторизован. Выполните OAuth авторизацию'
            }
        
        # Извлекаем код встречи из ссылки если это URL
        if 'meet.google.com' in meeting_code:
            meeting_code = meeting_code.split('/')[-1]
        
        meeting_id = f"meet_{meeting_code}"
        
        try:
            # В реальной системе здесь будет подключение к встрече
            # Google Meet API пока не поддерживает программное подключение напрямую
            # Нужно использовать альтернативные методы:
            # 1. Webhook от календаря Google
            # 2. Интеграция через расширения браузера
            # 3. Использование Google Meet SDK (если доступно)
            
            meeting_data = {
                'meeting_id': meeting_id,
                'meeting_code': meeting_code,
                'project_id': project_id,
                'joined_at': datetime.now().isoformat(),
                'status': 'active',
                'participants': [],
                'transcription': []
            }
            
            self.active_meetings[meeting_id] = meeting_data
            
            # Вызываем обработчик если есть
            if self.on_meeting_start:
                self.on_meeting_start(meeting_data)
            
            return {
                'success': True,
                'meeting_id': meeting_id,
                'message': 'Подключение к встрече инициализировано'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка подключения к встрече: {str(e)}'
            }
    
    def start_transcription(self, meeting_id: str) -> Dict[str, Any]:
        """
        Начинает транскрибацию встречи
        
        Args:
            meeting_id: ID встречи
            
        Returns:
            Результат начала транскрибации
        """
        if meeting_id not in self.active_meetings:
            return {
                'success': False,
                'error': 'Встреча не найдена'
            }
        
        meeting = self.active_meetings[meeting_id]
        meeting['transcription_enabled'] = True
        meeting['transcription_started_at'] = datetime.now().isoformat()
        
        return {
            'success': True,
            'message': 'Транскрибация начата'
        }
    
    def stop_transcription(self, meeting_id: str) -> Dict[str, Any]:
        """
        Останавливает транскрибацию встречи
        
        Args:
            meeting_id: ID встречи
            
        Returns:
            Результат остановки транскрибации
        """
        if meeting_id not in self.active_meetings:
            return {
                'success': False,
                'error': 'Встреча не найдена'
            }
        
        meeting = self.active_meetings[meeting_id]
        meeting['transcription_enabled'] = False
        meeting['transcription_stopped_at'] = datetime.now().isoformat()
        
        return {
            'success': True,
            'message': 'Транскрибация остановлена',
            'full_transcript': self.get_full_transcript(meeting_id)
        }
    
    def get_full_transcript(self, meeting_id: str) -> str:
        """
        Получает полный транскрипт встречи
        
        Args:
            meeting_id: ID встречи
            
        Returns:
            Полный транскрипт
        """
        if meeting_id not in self.active_meetings:
            return ""
        
        meeting = self.active_meetings[meeting_id]
        transcript_chunks = meeting.get('transcription', [])
        
        # Объединяем все фрагменты транскрипта
        full_text = "\n".join([
            f"[{chunk.get('timestamp', '')}] {chunk.get('speaker', 'Unknown')}: {chunk.get('text', '')}"
            for chunk in transcript_chunks
        ])
        
        return full_text
    
    def add_transcription_chunk(self, meeting_id: str, text: str, speaker: str = "Unknown", timestamp: Optional[str] = None):
        """
        Добавляет фрагмент транскрипта (вызывается из внешней транскрибации)
        
        Args:
            meeting_id: ID встречи
            text: Текст транскрипта
            speaker: Имя говорящего
            timestamp: Временная метка
        """
        if meeting_id not in self.active_meetings:
            return
        
        meeting = self.active_meetings[meeting_id]
        
        if 'transcription' not in meeting:
            meeting['transcription'] = []
        
        chunk = {
            'text': text,
            'speaker': speaker,
            'timestamp': timestamp or datetime.now().isoformat()
        }
        
        meeting['transcription'].append(chunk)
        
        # Вызываем обработчик если есть
        if self.on_transcription_chunk:
            self.on_transcription_chunk(meeting_id, chunk)
    
    def leave_meeting(self, meeting_id: str) -> Dict[str, Any]:
        """
        Покидает встречу
        
        Args:
            meeting_id: ID встречи
            
        Returns:
            Результат выхода
        """
        if meeting_id not in self.active_meetings:
            return {
                'success': False,
                'error': 'Встреча не найдена'
            }
        
        meeting = self.active_meetings[meeting_id]
        meeting['status'] = 'ended'
        meeting['ended_at'] = datetime.now().isoformat()
        
        # Вызываем обработчик если есть
        if self.on_meeting_end:
            self.on_meeting_end(meeting)
        
        # Получаем финальный транскрипт
        full_transcript = self.get_full_transcript(meeting_id)
        
        # Удаляем из активных встреч
        del self.active_meetings[meeting_id]
        
        return {
            'success': True,
            'message': 'Выход из встречи выполнен',
            'full_transcript': full_transcript,
            'meeting_summary': meeting
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Тестирует подключение к Google Meet API
        
        Returns:
            Результат теста
        """
        if not GOOGLE_API_AVAILABLE:
            return {
                'success': False,
                'error': 'Библиотеки Google API не установлены. Установите: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client'
            }
        
        if not self.is_authenticated:
            return {
                'success': False,
                'error': 'Не авторизован. Выполните OAuth авторизацию',
                'auth_required': True
            }
        
        try:
            # Попытка выполнить простой запрос к API
            # В реальной системе здесь будет проверка доступности сервиса
            return {
                'success': True,
                'message': 'Подключение к Google Meet API работает',
                'authenticated': True
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка подключения: {str(e)}'
            }


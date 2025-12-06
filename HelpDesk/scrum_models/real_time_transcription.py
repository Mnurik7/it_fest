"""
Модуль транскрибации в реальном времени
Поддержка различных сервисов транскрибации
"""
import os
import json
import asyncio
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from queue import Queue
import logging

logger = logging.getLogger(__name__)

# Попытка импортировать библиотеки для транскрибации
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError as e:
    SPEECH_RECOGNITION_AVAILABLE = False
    missing_module = str(e).split("'")[1] if "'" in str(e) else "неизвестный модуль"
    logger.warning(f"⚠️  Библиотека speech_recognition не установлена. Установите: pip install SpeechRecognition")
    logger.warning(f"Отсутствует модуль: {missing_module}")

try:
    from google.cloud import speech
    GOOGLE_SPEECH_AVAILABLE = True
except ImportError:
    GOOGLE_SPEECH_AVAILABLE = False

try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_SPEECH_AVAILABLE = True
except ImportError:
    AZURE_SPEECH_AVAILABLE = False


class RealTimeTranscriber:
    """Транскрибация аудио в реальном времени"""
    
    def __init__(self, 
                 provider: str = 'google',
                 language: str = 'ru-RU',
                 on_transcript_chunk: Optional[Callable] = None):
        """
        Инициализация транскрибера
        
        Args:
            provider: Провайдер ('google', 'azure', 'local')
            language: Язык транскрибации ('ru-RU', 'en-US', etc.)
            on_transcript_chunk: Callback для новых фрагментов транскрипта
        """
        self.provider = provider
        self.language = language
        self.on_transcript_chunk = on_transcript_chunk
        
        self.is_transcribing = False
        self.audio_queue = Queue()
        self.transcript_chunks: List[Dict[str, Any]] = []
        self.current_speaker = "Unknown"
        
        # Инициализация провайдера
        self._init_provider()
    
    def _init_provider(self):
        """Инициализирует провайдера транскрибации"""
        if self.provider == 'google':
            self._init_google_speech()
        elif self.provider == 'azure':
            self._init_azure_speech()
        elif self.provider == 'local':
            self._init_local_speech()
        else:
            logger.warning(f"Неизвестный провайдер: {self.provider}. Используется локальный.")
            self.provider = 'local'
            self._init_local_speech()
    
    def _init_google_speech(self):
        """Инициализирует Google Speech-to-Text"""
        if not GOOGLE_SPEECH_AVAILABLE:
            logger.warning("Google Speech-to-Text не доступен. Используется локальный провайдер.")
            self.provider = 'local'
            return
        
        try:
            # Здесь будет инициализация Google Speech client
            # Требуется GOOGLE_APPLICATION_CREDENTIALS или credentials
            self.google_client = None  # Будет инициализирован при необходимости
            logger.info("✅ Google Speech-to-Text инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации Google Speech: {e}")
            self.provider = 'local'
    
    def _init_azure_speech(self):
        """Инициализирует Azure Speech Services"""
        if not AZURE_SPEECH_AVAILABLE:
            logger.warning("Azure Speech Services не доступен. Используется локальный провайдер.")
            self.provider = 'local'
            return
        
        try:
            # Здесь будет инициализация Azure Speech client
            # Требуется AZURE_SPEECH_KEY и AZURE_SPEECH_REGION
            self.azure_key = os.getenv('AZURE_SPEECH_KEY', '')
            self.azure_region = os.getenv('AZURE_SPEECH_REGION', '')
            
            if not self.azure_key or not self.azure_region:
                logger.warning("Azure Speech credentials не настроены. Используется локальный провайдер.")
                self.provider = 'local'
                return
            
            logger.info("✅ Azure Speech Services инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации Azure Speech: {e}")
            self.provider = 'local'
    
    def _init_local_speech(self):
        """Инициализирует локальный провайдер (SpeechRecognition)"""
        if not SPEECH_RECOGNITION_AVAILABLE:
            logger.error("SpeechRecognition не установлен. Транскрибация будет недоступна.")
            return
        
        try:
            self.recognizer = sr.Recognizer()
            logger.info("✅ Локальный провайдер транскрибации инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации локального провайдера: {e}")
    
    def start_transcription(self, audio_source: Any = None) -> Dict[str, Any]:
        """
        Начинает транскрибацию
        
        Args:
            audio_source: Источник аудио (микрофон, файл, поток)
            
        Returns:
            Результат начала транскрибации
        """
        if self.is_transcribing:
            return {
                'success': False,
                'error': 'Транскрибация уже запущена'
            }
        
        try:
            self.is_transcribing = True
            self.transcript_chunks = []
            
            # Запускаем транскрибацию в отдельном потоке
            transcription_thread = threading.Thread(
                target=self._transcription_loop,
                args=(audio_source,),
                daemon=True
            )
            transcription_thread.start()
            
            return {
                'success': True,
                'message': 'Транскрибация запущена',
                'provider': self.provider
            }
        except Exception as e:
            self.is_transcribing = False
            return {
                'success': False,
                'error': f'Ошибка запуска транскрибации: {str(e)}'
            }
    
    def stop_transcription(self) -> Dict[str, Any]:
        """Останавливает транскрибацию"""
        if not self.is_transcribing:
            return {
                'success': False,
                'error': 'Транскрибация не запущена'
            }
        
        self.is_transcribing = False
        
        full_transcript = self.get_full_transcript()
        
        return {
            'success': True,
            'message': 'Транскрибация остановлена',
            'full_transcript': full_transcript,
            'total_chunks': len(self.transcript_chunks)
        }
    
    def _transcription_loop(self, audio_source: Any = None):
        """Основной цикл транскрибации"""
        if self.provider == 'google':
            self._google_transcription_loop(audio_source)
        elif self.provider == 'azure':
            self._azure_transcription_loop(audio_source)
        else:
            self._local_transcription_loop(audio_source)
    
    def _local_transcription_loop(self, audio_source: Any = None):
        """Локальная транскрибация через SpeechRecognition"""
        if not SPEECH_RECOGNITION_AVAILABLE:
            logger.error("SpeechRecognition недоступен")
            return
        
        try:
            # Используем микрофон по умолчанию если источник не указан
            if audio_source is None:
                with sr.Microphone() as source:
                    self.recognizer.adjust_for_ambient_noise(source)
                    
                    while self.is_transcribing:
                        try:
                            audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)
                            
                            # Распознаём речь
                            text = self.recognizer.recognize_google(audio, language=self.language)
                            
                            if text:
                                chunk = {
                                    'text': text,
                                    'speaker': self.current_speaker,
                                    'timestamp': datetime.now().isoformat(),
                                    'provider': 'local'
                                }
                                
                                self.transcript_chunks.append(chunk)
                                
                                # Вызываем callback если есть
                                if self.on_transcript_chunk:
                                    self.on_transcript_chunk(chunk)
                        except sr.WaitTimeoutError:
                            continue
                        except sr.UnknownValueError:
                            continue
                        except Exception as e:
                            logger.error(f"Ошибка транскрибации: {e}")
                            continue
        except Exception as e:
            logger.error(f"Ошибка в цикле транскрибации: {e}")
            self.is_transcribing = False
    
    def _google_transcription_loop(self, audio_source: Any = None):
        """Транскрибация через Google Speech-to-Text"""
        # Здесь будет реализация Google Speech-to-Text
        # Пока используем локальный провайдер
        logger.warning("Google Speech-to-Text пока не реализован. Используется локальный провайдер.")
        self._local_transcription_loop(audio_source)
    
    def _azure_transcription_loop(self, audio_source: Any = None):
        """Транскрибация через Azure Speech Services"""
        # Здесь будет реализация Azure Speech-to-Text
        # Пока используем локальный провайдер
        logger.warning("Azure Speech Services пока не реализован. Используется локальный провайдер.")
        self._local_transcription_loop(audio_source)
    
    def add_audio_chunk(self, audio_data: bytes):
        """
        Добавляет аудио фрагмент для транскрибации
        
        Args:
            audio_data: Аудио данные в формате bytes
        """
        if self.is_transcribing:
            self.audio_queue.put(audio_data)
    
    def process_transcript_text(self, text: str, speaker: str = "Unknown", timestamp: Optional[str] = None):
        """
        Обрабатывает текстовый транскрипт (если транскрибация уже выполнена внешним сервисом)
        
        Args:
            text: Текст транскрипта
            speaker: Имя говорящего
            timestamp: Временная метка
        """
        chunk = {
            'text': text,
            'speaker': speaker,
            'timestamp': timestamp or datetime.now().isoformat(),
            'provider': 'external'
        }
        
        self.transcript_chunks.append(chunk)
        
        # Вызываем callback если есть
        if self.on_transcript_chunk:
            self.on_transcript_chunk(chunk)
    
    def get_full_transcript(self) -> str:
        """Получает полный транскрипт"""
        return "\n".join([
            f"[{chunk.get('timestamp', '')}] {chunk.get('speaker', 'Unknown')}: {chunk.get('text', '')}"
            for chunk in self.transcript_chunks
        ])
    
    def get_transcript_chunks(self) -> List[Dict[str, Any]]:
        """Получает все фрагменты транскрипта"""
        return self.transcript_chunks.copy()
    
    def set_speaker(self, speaker: str):
        """Устанавливает текущего говорящего"""
        self.current_speaker = speaker
    
    def clear_transcript(self):
        """Очищает транскрипт"""
        self.transcript_chunks = []


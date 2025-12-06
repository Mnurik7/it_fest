"""
Модуль для управления структурированным диалогом со сбором информации
"""
from typing import Dict, List, Optional, Tuple
from enum import Enum
import json
import time

try:
    from .smart_answer_analyzer import SmartAnswerAnalyzer
except ImportError:
    SmartAnswerAnalyzer = None


class DialogStage(Enum):
    """Этапы структурированного диалога"""
    INITIAL = "initial"  # Начало диалога
    PROJECT_NAME = "project_name"  # Сбор названия проекта
    PROJECT_GOAL = "project_goal"  # Сбор цели проекта
    PROJECT_DESCRIPTION = "project_description"  # Описание проекта
    SCOPE_IN = "scope_in"  # Что входит в scope
    SCOPE_OUT = "scope_out"  # Что не входит в scope
    BUSINESS_RULES = "business_rules"  # Бизнес-правила
    KPI = "kpi"  # KPI метрики
    LEADING_INDICATORS = "leading_indicators"  # Лидирующие индикаторы
    STAKEHOLDERS = "stakeholders"  # Заинтересованные стороны
    CONSTRAINTS = "constraints"  # Ограничения
    DEPENDENCIES = "dependencies"  # Зависимости
    REVIEW = "review"  # Проверка собранной информации
    COMPLETE = "complete"  # Диалог завершен, готов к генерации


class StructuredDialogManager:
    """Менеджер структурированного диалога для сбора требований"""
    
    # Порядок этапов диалога (PROJECT_NAME исключен, так как собирается на INITIAL)
    STAGES_ORDER = [
        DialogStage.INITIAL,
        DialogStage.PROJECT_GOAL,
        DialogStage.PROJECT_DESCRIPTION,
        DialogStage.SCOPE_IN,
        DialogStage.SCOPE_OUT,
        DialogStage.BUSINESS_RULES,
        DialogStage.KPI,
        DialogStage.LEADING_INDICATORS,
        DialogStage.STAKEHOLDERS,
        DialogStage.CONSTRAINTS,
        DialogStage.DEPENDENCIES,
        DialogStage.REVIEW,
        DialogStage.COMPLETE
    ]
    
    # Вопросы для каждого этапа
    STAGE_QUESTIONS = {
        DialogStage.INITIAL: "Здравствуйте! Я AI Business Analyst. Давайте начнём сбор требований для вашего проекта. Начнём с названия проекта - как называется ваш проект?",
        DialogStage.PROJECT_GOAL: "Отлично! Теперь расскажите, какова основная цель вашего проекта? Что вы хотите достичь?",
        DialogStage.PROJECT_DESCRIPTION: "Хорошо! Теперь давайте определим область применения. Что конкретно входит в scope (область охвата) вашего проекта? Перечислите основные компоненты или функции.",
        DialogStage.SCOPE_IN: "Понятно! А что явно НЕ входит в scope вашего проекта? Что мы не будем реализовывать в рамках этого проекта?",
        DialogStage.SCOPE_OUT: "Спасибо! Какие бизнес-правила должны соблюдаться в вашем проекте? Есть ли какие-то особые условия или ограничения?",
        DialogStage.BUSINESS_RULES: "Хорошо! Какие ключевые метрики (KPI) будут использоваться для оценки успеха проекта? Какие показатели вы хотите отслеживать?",
        DialogStage.KPI: "Отлично! Какие лидирующие индикаторы (прогнозные метрики) помогут предсказать успех проекта до его завершения?",
        DialogStage.LEADING_INDICATORS: "Хорошо! Кто является заинтересованными сторонами (stakeholders) проекта? Кто будет использовать систему или заинтересован в результатах?",
        DialogStage.STAKEHOLDERS: "Понятно! Есть ли какие-то ограничения у проекта? Технические, временные, ресурсные или другие?",
        DialogStage.CONSTRAINTS: "Спасибо! Есть ли зависимости от других проектов, систем или процессов? От чего зависит успешная реализация?",
        DialogStage.DEPENDENCIES: "Отлично! Давайте проверим собранную информацию. Вот краткое резюме:"
    }
    
    def __init__(self, session_id: str = None, model=None):
        """
        Инициализация менеджера диалога
        
        Args:
            session_id: Уникальный идентификатор сессии
            model: AI модель для умного анализа (опционально)
        """
        self.session_id = session_id or f"dialog_{int(time.time())}"
        self.current_stage = DialogStage.INITIAL
        self.collected_data = {}
        self.stage_start_time = time.time()
        self.total_start_time = time.time()
        self.conversation_history = []
        
        # Инициализируем умный анализатор, если модель доступна
        self.smart_analyzer = None
        if model and SmartAnswerAnalyzer:
            try:
                self.smart_analyzer = SmartAnswerAnalyzer(model)
            except:
                pass
        
    def get_current_question(self) -> str:
        """Получить текущий вопрос на основе этапа"""
        return self.STAGE_QUESTIONS.get(self.current_stage, "Продолжаем сбор информации.")
    
    def process_answer(self, answer: str, model=None) -> Tuple[str, bool]:
        """
        Обработать ответ пользователя с умным анализом
        
        Args:
            answer: Ответ пользователя
            model: Модель AI для анализа ответа (опционально)
        
        Returns:
            Tuple[ответ_ассистента, завершен_ли_диалог]
        """
        # Сохраняем ответ в историю
        self.conversation_history.append({
            'stage': self.current_stage.value,
            'user_answer': answer,
            'timestamp': time.time()
        })
        
        # Если доступен умный анализатор, используем его
        if self.smart_analyzer or (model and SmartAnswerAnalyzer):
            if not self.smart_analyzer and model:
                try:
                    self.smart_analyzer = SmartAnswerAnalyzer(model)
                except:
                    pass
            
            if self.smart_analyzer:
                # Умный анализ ответа
                context = {
                    'collected_data': self.collected_data,
                    'current_stage': self.current_stage.value,
                    'conversation_history': self.conversation_history[-3:]
                }
                
                analysis = self.smart_analyzer.analyze_answer(
                    answer, 
                    self.current_stage.value, 
                    context
                )
                
                # Извлекаем данные из умного анализа
                extracted_data = analysis.get('extracted_data', {})
                self.collected_data.update(extracted_data)
                
                # Проверяем, нужно ли уточнение
                needs_clarification = analysis.get('needs_clarification', False)
                confidence = analysis.get('confidence', 0.7)
                
                # Определяем следующий этап
                if not needs_clarification and confidence > 0.5:
                    next_stage = self._get_next_stage(answer, model)
                else:
                    next_stage = self.current_stage  # Остаемся на текущем этапе
                
                # Генерируем ответ
                if needs_clarification:
                    clarification = analysis.get('suggested_clarification', '')
                    response = f"{clarification}" if clarification else self._generate_response(next_stage, answer, model)
                else:
                    response = self._generate_response(next_stage, answer, model)
                
                # Переходим к следующему этапу
                if next_stage != self.current_stage:
                    self.current_stage = next_stage
                
                is_complete = (self.current_stage == DialogStage.COMPLETE)
                return response, is_complete
        
        # Fallback на обычную обработку
        extracted_data = self._extract_data_from_answer(answer, model)
        self.collected_data.update(extracted_data)
        
        next_stage = self._get_next_stage(answer, model)
        response = self._generate_response(next_stage, answer, model)
        
        if next_stage != self.current_stage:
            self.current_stage = next_stage
        
        is_complete = (self.current_stage == DialogStage.COMPLETE)
        return response, is_complete
    
    def _extract_data_from_answer(self, answer: str, model=None) -> Dict:
        """Извлечь данные из ответа пользователя"""
        data = {}
        
        # Обрабатываем INITIAL этап - первый ответ считается названием проекта
        if self.current_stage == DialogStage.INITIAL:
            data['project_name'] = answer.strip()
        elif self.current_stage == DialogStage.PROJECT_NAME:
            data['project_name'] = answer.strip()
        elif self.current_stage == DialogStage.PROJECT_GOAL:
            data['project_goal'] = answer.strip()
        elif self.current_stage == DialogStage.PROJECT_DESCRIPTION:
            data['project_description'] = answer.strip()
        elif self.current_stage == DialogStage.SCOPE_IN:
            # Парсим список элементов scope
            scope_items = [item.strip() for item in answer.replace('\n', ',').split(',') if item.strip()]
            if 'scope_in' not in self.collected_data:
                self.collected_data['scope_in'] = []
            self.collected_data['scope_in'].extend(scope_items)
            data['scope_in'] = self.collected_data['scope_in']
        elif self.current_stage == DialogStage.SCOPE_OUT:
            scope_out_items = [item.strip() for item in answer.replace('\n', ',').split(',') if item.strip()]
            data['scope_out'] = scope_out_items
        elif self.current_stage == DialogStage.BUSINESS_RULES:
            rules = [item.strip() for item in answer.replace('\n', ',').split(',') if item.strip()]
            data['business_rules'] = rules
        elif self.current_stage == DialogStage.KPI:
            # Парсим KPI (формат: название: цель, текущее значение)
            kpi_items = []
            for line in answer.split('\n'):
                line = line.strip()
                if line and ':' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        kpi_items.append({
                            'label': parts[0].strip(),
                            'goal': parts[1].strip() if len(parts) > 1 else '',
                            'current': parts[2].strip() if len(parts) > 2 else ''
                        })
            if kpi_items:
                data['kpi'] = kpi_items
        elif self.current_stage == DialogStage.LEADING_INDICATORS:
            indicators = [item.strip() for item in answer.replace('\n', ',').split(',') if item.strip()]
            data['leading_indicators'] = indicators
        
        return data
    
    def _get_next_stage(self, answer: str, model=None) -> DialogStage:
        """Определить следующий этап диалога"""
        # Если мы на этапе REVIEW, переходим к COMPLETE
        if self.current_stage == DialogStage.REVIEW:
            return DialogStage.COMPLETE
        
        # Если мы на этапе COMPLETE, остаемся там
        if self.current_stage == DialogStage.COMPLETE:
            return DialogStage.COMPLETE
        
        # Проверяем, достаточно ли данных для перехода к следующему этапу
        if not self._has_sufficient_data(self.current_stage, answer):
            # Если данных недостаточно, остаемся на текущем этапе
            return self.current_stage
        
        # Данных достаточно, переходим к следующему этапу
        try:
            current_index = self.STAGES_ORDER.index(self.current_stage)
        except ValueError:
            # Если текущий этап не в списке (например, PROJECT_NAME), ищем ближайший
            return self.current_stage
        
        # Переходим к следующему этапу
        if current_index < len(self.STAGES_ORDER) - 1:
            next_stage = self.STAGES_ORDER[current_index + 1]
            return next_stage
        
        # Если это последний этап в порядке, проверяем, нужно ли переходить к REVIEW
        if self.current_stage not in [DialogStage.REVIEW, DialogStage.COMPLETE]:
            # Проверяем, собрана ли достаточно информации для REVIEW
            if self._is_ready_for_review():
                return DialogStage.REVIEW
        
        return self.current_stage
    
    def _has_sufficient_data(self, stage: DialogStage, answer: str) -> bool:
        """Проверить, достаточно ли данных для перехода к следующему этапу"""
        if not answer or len(answer.strip()) < 3:
            return False
        
        # Для INITIAL этапа достаточно минимум 3 символов
        if stage == DialogStage.INITIAL:
            return len(answer.strip()) >= 3
        
        # Для обязательных этапов требуется минимум 5 символов (снижено с 10)
        required_stages = [
            DialogStage.PROJECT_NAME,
            DialogStage.PROJECT_GOAL,
            DialogStage.PROJECT_DESCRIPTION
        ]
        
        if stage in required_stages:
            return len(answer.strip()) >= 5
        
        return True
    
    def _is_ready_for_review(self) -> bool:
        """Проверить, достаточно ли данных для перехода к этапу REVIEW"""
        # Минимальные требования: название проекта, цель, scope
        has_name = bool(self.collected_data.get('project_name'))
        has_goal = bool(self.collected_data.get('project_goal'))
        has_scope = bool(self.collected_data.get('scope_in')) or bool(self.collected_data.get('scope'))
        
        return has_name and has_goal and has_scope
    
    def _generate_response(self, next_stage: DialogStage, answer: str, model=None) -> str:
        """Сгенерировать умный ответ ассистента"""
        # Если переходим к следующему этапу
        if next_stage != self.current_stage:
            # Используем умную генерацию подтверждения, если доступен анализатор
            if self.smart_analyzer:
                confirmation = self._generate_smart_confirmation(answer, model)
            else:
                confirmation = self._generate_confirmation()
            
            # Задаем следующий вопрос
            next_question = self.STAGE_QUESTIONS.get(next_stage, "Продолжаем сбор информации.")
            
            # Формируем контекстуальный переход
            if self.smart_analyzer and model:
                transition = self._generate_smart_transition(answer, next_stage, model)
                if transition:
                    return f"{confirmation}\n\n{transition}\n\n{next_question}"
            
            return f"{confirmation}\n\n{next_question}"
        
        # Если остаемся на том же этапе, просим уточнить умно
        if self.smart_analyzer and model:
            clarification = self._generate_smart_clarification(answer, model)
            if clarification:
                return clarification
        
        return "Пожалуйста, уточните ваш ответ или предоставьте более подробную информацию."
    
    def _generate_confirmation(self) -> str:
        """Сгенерировать подтверждение получения информации"""
        confirmations = [
            "Понятно, спасибо!",
            "Отлично, принято!",
            "Хорошо, записал!",
            "Спасибо за информацию!",
            "Понял, продолжаем!",
            "Отлично, понял!",
            "Спасибо, записал!"
        ]
        import random
        return random.choice(confirmations)
    
    def _generate_smart_confirmation(self, answer: str, model=None) -> str:
        """Генерирует умное подтверждение с учетом ответа"""
        if not model or not self.smart_analyzer:
            return self._generate_confirmation()
        
        try:
            prompt = f"""Пользователь дал ответ на вопрос бизнес-аналитика.

Ответ пользователя: "{answer}"

Сгенерируй короткое (1-2 предложения) дружелюбное подтверждение, которое:
1. Показывает, что ты понял ответ
2. Коротко резюмирует ключевую мысль (если возможно)
3. Будет естественным и профессиональным

Примеры:
- "Понятно, спасибо! Вижу, что вы хотите создать систему автоматизации."
- "Отлично! Ваш проект направлен на улучшение клиентского сервиса."
- "Хорошо, записал! Цель проекта - оптимизация процессов."

Только подтверждение, без вопросов:"""
            
            response = model.generate_content(prompt)
            confirmation = response.text.strip() if hasattr(response, 'text') else ''
            
            if confirmation and len(confirmation) < 200:
                return confirmation
        except:
            pass
        
        return self._generate_confirmation()
    
    def _generate_smart_transition(self, answer: str, next_stage: DialogStage, model=None) -> str:
        """Генерирует умный переход между этапами"""
        if not model:
            return None
        
        try:
            current_stage_name = self.current_stage.value
            next_stage_name = next_stage.value
            
            prompt = f"""Ты бизнес-аналитик, ведешь структурированный диалог с пользователем.

Пользователь только что ответил на вопрос о {current_stage_name}.
Теперь переходим к вопросу о {next_stage_name}.

Ответ пользователя: "{answer}"

Сгенерируй короткое (1 предложение) связующее предложение для плавного перехода к следующему вопросу.

Примеры:
- "Теперь давайте определим основные требования..."
- "Хорошо, теперь перейдем к деталям..."
- "Отлично, теперь обсудим область применения..."

Только одно короткое предложение для плавного перехода:"""
            
            response = model.generate_content(prompt)
            transition = response.text.strip() if hasattr(response, 'text') else ''
            
            if transition and 10 < len(transition) < 150:
                return transition
        except:
            pass
        
        return None
    
    def _generate_smart_clarification(self, answer: str, model=None) -> str:
        """Генерирует умный вопрос для уточнения"""
        if not model or not self.smart_analyzer:
            return None
        
        try:
            current_question = self.STAGE_QUESTIONS.get(self.current_stage, '')
            context = {
                'collected_data': self.collected_data,
                'current_stage': self.current_stage.value
            }
            
            clarification = self.smart_analyzer.suggest_followup_question(
                answer, 
                self.current_stage.value, 
                context
            )
            
            if clarification:
                return clarification
        except:
            pass
        
        return None
    
    def generate_summary(self) -> str:
        """Сгенерировать резюме собранной информации"""
        summary = "## Краткое резюме собранной информации:\n\n"
        
        if self.collected_data.get('project_name'):
            summary += f"**Название проекта:** {self.collected_data['project_name']}\n\n"
        
        if self.collected_data.get('project_goal'):
            summary += f"**Цель проекта:** {self.collected_data['project_goal']}\n\n"
        
        if self.collected_data.get('scope_in'):
            summary += "**Scope (входит):**\n"
            for item in self.collected_data['scope_in']:
                summary += f"- {item}\n"
            summary += "\n"
        
        if self.collected_data.get('scope_out'):
            summary += "**Scope (не входит):**\n"
            for item in self.collected_data['scope_out']:
                summary += f"- {item}\n"
            summary += "\n"
        
        if self.collected_data.get('kpi'):
            summary += "**KPI метрики:**\n"
            for kpi in self.collected_data['kpi']:
                summary += f"- {kpi.get('label', '')}: {kpi.get('goal', '')}\n"
            summary += "\n"
        
        summary += "\nВсё верно? Могу ли я приступить к генерации документов?"
        
        return summary
    
    def get_collected_data_for_brd(self) -> Dict:
        """Получить собранные данные в формате для генерации BRD"""
        return {
            'project_name': self.collected_data.get('project_name', ''),
            'project_description': self.collected_data.get('project_description', ''),
            'project_goal': self.collected_data.get('project_goal', ''),
            'scope': self.collected_data.get('scope_in', []),
            'scope_out': self.collected_data.get('scope_out', []),
            'business_rules': self.collected_data.get('business_rules', []),
            'kpi': self.collected_data.get('kpi', []),
            'leading_indicators': self.collected_data.get('leading_indicators', []),
            'constraints': self.collected_data.get('constraints', []),
            'dependencies': self.collected_data.get('dependencies', [])
        }
    
    def get_dialog_stats(self) -> Dict:
        """Получить статистику диалога"""
        duration = time.time() - self.total_start_time
        return {
            'session_id': self.session_id,
            'current_stage': self.current_stage.value,
            'stages_completed': self.STAGES_ORDER.index(self.current_stage),
            'total_stages': len(self.STAGES_ORDER),
            'duration_seconds': duration,
            'data_fields_collected': len([k for k, v in self.collected_data.items() if v]),
            'messages_count': len(self.conversation_history)
        }
    
    def to_dict(self) -> Dict:
        """Преобразовать состояние диалога в словарь для сохранения"""
        return {
            'session_id': self.session_id,
            'current_stage': self.current_stage.value,
            'collected_data': self.collected_data,
            'conversation_history': self.conversation_history,
            'start_time': self.total_start_time
        }
    
    @classmethod
    def from_dict(cls, data: Dict, model=None) -> 'StructuredDialogManager':
        """Восстановить состояние диалога из словаря"""
        manager = cls(data.get('session_id'), model=model)
        manager.current_stage = DialogStage(data.get('current_stage', DialogStage.INITIAL.value))
        manager.collected_data = data.get('collected_data', {})
        manager.conversation_history = data.get('conversation_history', [])
        manager.total_start_time = data.get('start_time', time.time())
        return manager


"""
Умный анализатор ответов пользователя с использованием AI
"""
from typing import Dict, List, Optional, Tuple
import json
import re


class SmartAnswerAnalyzer:
    """Умный анализатор ответов с пониманием контекста и намерений"""
    
    def __init__(self, model):
        self.model = model
    
    def analyze_answer(self, answer: str, current_stage: str, context: Dict = None) -> Dict:
        """
        Интеллектуальный анализ ответа пользователя
        
        Args:
            answer: Ответ пользователя
            current_stage: Текущий этап диалога
            context: Контекст (собранные данные, история)
        
        Returns:
            Словарь с извлеченными данными и анализом
        """
        if not answer or len(answer.strip()) < 1:
            return {
                'extracted_data': {},
                'confidence': 0.0,
                'is_complete': False,
                'needs_clarification': True,
                'suggested_clarification': 'Пожалуйста, предоставьте более подробную информацию.'
            }
        
        # Определяем тип ответа и извлекаем данные
        analysis_result = self._intelligent_extraction(answer, current_stage, context)
        
        return analysis_result
    
    def _intelligent_extraction(self, answer: str, stage: str, context: Dict = None) -> Dict:
        """Интеллектуальное извлечение данных с использованием AI"""
        
        # Формируем контекст для AI
        context_info = ""
        if context:
            collected = context.get('collected_data', {})
            if collected:
                context_info = "\nУже собранные данные:\n"
                for key, value in collected.items():
                    if value:
                        context_info += f"- {key}: {value}\n"
        
        # Создаем промпт для анализа ответа
        stage_descriptions = {
            'INITIAL': 'название проекта',
            'PROJECT_GOAL': 'цель проекта - что пользователь хочет достичь',
            'PROJECT_DESCRIPTION': 'подробное описание проекта',
            'SCOPE_IN': 'что входит в область проекта (scope in)',
            'SCOPE_OUT': 'что не входит в область проекта (scope out)',
            'BUSINESS_RULES': 'бизнес-правила и условия',
            'KPI': 'ключевые показатели эффективности (KPI)',
            'LEADING_INDICATORS': 'лидирующие индикаторы (прогнозные метрики)',
            'STAKEHOLDERS': 'заинтересованные стороны проекта',
            'CONSTRAINTS': 'ограничения проекта',
            'DEPENDENCIES': 'зависимости проекта'
        }
        
        stage_description = stage_descriptions.get(stage, stage)
        
        prompt = f"""Ты умный ассистент бизнес-аналитика. Проанализируй ответ пользователя и извлеки нужную информацию.

Текущий этап диалога: {stage}
Что нужно извлечь: {stage_description}

Ответ пользователя:
"{answer}"
{context_info}

Твоя задача:
1. Понять намерение пользователя (даже если ответ неформальный или неполный)
2. Извлечь релевантную информацию
3. Определить, достаточно ли информации
4. Если информации недостаточно, предложить уточнение

Верни ответ в формате JSON:
{{
    "extracted_data": {{
        "value": "извлеченное значение",
        "items": ["список элементов, если есть"],
        "confidence": 0.0-1.0
    }},
    "is_complete": true/false,
    "needs_clarification": true/false,
    "suggested_clarification": "вопрос для уточнения, если нужен",
    "understanding": "краткое понимание ответа пользователя"
}}

ВАЖНО:
- Если пользователь дал неполный ответ, но из него можно что-то извлечь - извлеки
- Если пользователь отвечает на другой вопрос - попробуй понять и использовать
- Если пользователь дает несколько ответов сразу - извлеки все
- Будь гибким и понимай контекст
- Если ответ очень короткий ("да", "нет", "ок"), попроси уточнение"""
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text if hasattr(response, 'text') else str(response)
            
            # Парсим JSON ответ
            analysis = self._parse_ai_response(response_text, answer, stage)
            return analysis
            
        except Exception as e:
            # Fallback на простое извлечение
            return self._simple_extraction(answer, stage)
    
    def _parse_ai_response(self, response_text: str, original_answer: str, stage: str) -> Dict:
        """Парсит ответ AI и извлекает структурированные данные"""
        try:
            # Пытаемся найти JSON в ответе
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)
                
                extracted_data = {}
                extracted_value = parsed.get('extracted_data', {}).get('value', original_answer.strip())
                extracted_items = parsed.get('extracted_data', {}).get('items', [])
                
                # Формируем данные в зависимости от этапа
                if stage in ['INITIAL', 'PROJECT_NAME']:
                    extracted_data['project_name'] = extracted_value
                elif stage == 'PROJECT_GOAL':
                    extracted_data['project_goal'] = extracted_value
                elif stage == 'PROJECT_DESCRIPTION':
                    extracted_data['project_description'] = extracted_value
                elif stage == 'SCOPE_IN':
                    items = extracted_items if extracted_items else [extracted_value]
                    extracted_data['scope_in'] = items
                elif stage == 'SCOPE_OUT':
                    items = extracted_items if extracted_items else [extracted_value]
                    extracted_data['scope_out'] = items
                elif stage == 'BUSINESS_RULES':
                    items = extracted_items if extracted_items else [extracted_value]
                    extracted_data['business_rules'] = items
                elif stage == 'KPI':
                    # Пытаемся извлечь KPI в структурированном виде
                    extracted_data['kpi'] = self._parse_kpi_from_answer(original_answer, extracted_items)
                elif stage == 'LEADING_INDICATORS':
                    items = extracted_items if extracted_items else [extracted_value]
                    extracted_data['leading_indicators'] = items
                
                return {
                    'extracted_data': extracted_data,
                    'confidence': parsed.get('extracted_data', {}).get('confidence', 0.7),
                    'is_complete': parsed.get('is_complete', True),
                    'needs_clarification': parsed.get('needs_clarification', False),
                    'suggested_clarification': parsed.get('suggested_clarification', ''),
                    'understanding': parsed.get('understanding', '')
                }
        except:
            pass
        
        # Fallback
        return self._simple_extraction(original_answer, stage)
    
    def _simple_extraction(self, answer: str, stage: str) -> Dict:
        """Простое извлечение данных без AI (fallback)"""
        answer = answer.strip()
        extracted_data = {}
        
        if stage in ['INITIAL', 'PROJECT_NAME']:
            extracted_data['project_name'] = answer
        elif stage == 'PROJECT_GOAL':
            extracted_data['project_goal'] = answer
        elif stage == 'PROJECT_DESCRIPTION':
            extracted_data['project_description'] = answer
        elif stage == 'SCOPE_IN':
            items = [item.strip() for item in answer.replace('\n', ',').split(',') if item.strip()]
            extracted_data['scope_in'] = items if items else [answer]
        elif stage == 'SCOPE_OUT':
            items = [item.strip() for item in answer.replace('\n', ',').split(',') if item.strip()]
            extracted_data['scope_out'] = items if items else [answer]
        elif stage == 'BUSINESS_RULES':
            items = [item.strip() for item in answer.replace('\n', ',').split(',') if item.strip()]
            extracted_data['business_rules'] = items if items else [answer]
        elif stage == 'KPI':
            extracted_data['kpi'] = self._parse_kpi_from_answer(answer)
        elif stage == 'LEADING_INDICATORS':
            items = [item.strip() for item in answer.replace('\n', ',').split(',') if item.strip()]
            extracted_data['leading_indicators'] = items if items else [answer]
        
        confidence = 0.8 if len(answer) >= 5 else 0.5
        needs_clarification = len(answer) < 5
        
        return {
            'extracted_data': extracted_data,
            'confidence': confidence,
            'is_complete': not needs_clarification,
            'needs_clarification': needs_clarification,
            'suggested_clarification': 'Пожалуйста, уточните ваш ответ.' if needs_clarification else ''
        }
    
    def _parse_kpi_from_answer(self, answer: str, items: List = None) -> List[Dict]:
        """Парсит KPI из ответа"""
        kpi_items = []
        
        if items:
            for item in items:
                if isinstance(item, dict):
                    kpi_items.append(item)
                elif isinstance(item, str) and ':' in item:
                    parts = item.split(':')
                    kpi_items.append({
                        'label': parts[0].strip(),
                        'goal': parts[1].strip() if len(parts) > 1 else '',
                        'current': parts[2].strip() if len(parts) > 2 else ''
                    })
        
        # Если items нет, пытаемся парсить из текста
        if not kpi_items:
            lines = answer.split('\n')
            for line in lines:
                line = line.strip()
                if ':' in line:
                    parts = line.split(':')
                    kpi_items.append({
                        'label': parts[0].strip(),
                        'goal': parts[1].strip() if len(parts) > 1 else '',
                        'current': ''
                    })
        
        # Если ничего не нашли, создаем один KPI из всего ответа
        if not kpi_items:
            kpi_items.append({
                'label': answer[:50] if len(answer) > 50 else answer,
                'goal': '',
                'current': ''
            })
        
        return kpi_items
    
    def understand_intent(self, message: str, context: Dict = None) -> Dict:
        """
        Понимает намерение пользователя из сообщения
        
        Args:
            message: Сообщение пользователя
            context: Контекст диалога
        
        Returns:
            Словарь с пониманием намерения
        """
        prompt = f"""Проанализируй сообщение пользователя и определи его намерение.

Сообщение: "{message}"
{self._format_context(context)}

Определи:
1. Что хочет пользователь?
2. Отвечает ли он на текущий вопрос?
3. Задает ли он новый вопрос?
4. Нужна ли дополнительная информация?

Ответ в формате JSON:
{{
    "intent": "answer|question|clarification|skip|other",
    "is_relevant": true/false,
    "confidence": 0.0-1.0,
    "summary": "краткое понимание намерения"
}}"""
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text if hasattr(response, 'text') else str(response)
            
            # Парсим ответ
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                return {
                    'intent': parsed.get('intent', 'answer'),
                    'is_relevant': parsed.get('is_relevant', True),
                    'confidence': parsed.get('confidence', 0.7),
                    'summary': parsed.get('summary', '')
                }
        except:
            pass
        
        # Fallback
        return {
            'intent': 'answer',
            'is_relevant': True,
            'confidence': 0.6,
            'summary': 'Пользователь отвечает на вопрос'
        }
    
    def _format_context(self, context: Dict = None) -> str:
        """Форматирует контекст для промпта"""
        if not context:
            return ""
        
        context_str = "\nКонтекст:\n"
        
        if context.get('collected_data'):
            context_str += "Уже собрано:\n"
            for key, value in context['collected_data'].items():
                if value:
                    context_str += f"- {key}: {value}\n"
        
        if context.get('current_stage'):
            context_str += f"\nТекущий этап: {context['current_stage']}\n"
        
        return context_str
    
    def suggest_followup_question(self, answer: str, stage: str, context: Dict = None) -> str:
        """
        Предлагает следующий вопрос на основе ответа пользователя
        
        Args:
            answer: Ответ пользователя
            stage: Текущий этап
            context: Контекст
        
        Returns:
            Предложенный вопрос для уточнения (если нужен)
        """
        prompt = f"""На основе ответа пользователя предложи уточняющий вопрос, если ответ неполный или неясный.

Текущий этап: {stage}
Ответ пользователя: "{answer}"
{self._format_context(context)}

Если ответ полный и ясный - верни пустую строку.
Если нужен уточняющий вопрос - верни его (коротко и по делу).

Ответ (только вопрос, без лишнего):"""
        
        try:
            response = self.model.generate_content(prompt)
            question = response.text.strip() if hasattr(response, 'text') else ''
            return question if question and len(question) > 10 else ''
        except:
            return ''


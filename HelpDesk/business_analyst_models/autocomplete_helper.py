"""
Модуль для автозаполнения полей через AI
"""
from typing import Dict, List, Optional
import json
import re


class AutocompleteHelper:
    """Помощник для автозаполнения через AI"""
    
    def __init__(self, model):
        self.model = model
    
    def suggest_answer_options(self, question: str, context: Dict = None) -> List[str]:
        """
        Предлагает варианты ответов на вопрос
        
        Args:
            question: Вопрос, на который нужно предложить варианты
            context: Контекст (история, собранные данные)
        
        Returns:
            Список вариантов ответов (3-5 вариантов)
        """
        context_info = ""
        if context:
            collected = context.get('collected_data', {})
            if collected:
                context_info = "\nУже собрано:\n"
                for key, value in collected.items():
                    if value:
                        context_info += f"- {key}: {value}\n"
        
        prompt = f"""Ты умный помощник бизнес-аналитика. Предложи 3-5 вариантов ответа на вопрос пользователя.

Вопрос: "{question}"
{context_info}

Предложи 3-5 коротких, конкретных вариантов ответа. Варианты должны быть:
- Краткими (1-2 предложения каждый)
- Конкретными и полезными
- Разнообразными (покрывать разные аспекты)
- Релевантными для банковской сферы

Верни только варианты, каждый с новой строки, без нумерации.
Формат:
Вариант 1
Вариант 2
Вариант 3"""
        
        try:
            response = self.model.generate_content(prompt)
            suggestions_text = response.text if hasattr(response, 'text') else str(response)
            
            # Парсим варианты
            suggestions = []
            for line in suggestions_text.split('\n'):
                line = line.strip()
                # Убираем нумерацию и маркеры
                line = re.sub(r'^[\d\-•\*]\s*', '', line)
                if line and len(line) > 5 and len(line) < 200:
                    suggestions.append(line)
            
            return suggestions[:5] if suggestions else []
        except Exception as e:
            return []
    
    def autofill_fields_from_chat(self, chat_history: List, collected_data: Dict = None) -> Dict:
        """
        Автоматически заполняет поля BRD на основе истории чата
        
        Args:
            chat_history: История диалога
            collected_data: Уже собранные данные
        
        Returns:
            Словарь с заполненными полями
        """
        if not chat_history:
            return {}
        
        # Формируем контекст из истории
        conversation_text = ""
        for msg in chat_history:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            conversation_text += f"{'Пользователь' if role == 'user' else 'Ассистент'}: {content}\n"
        
        existing_data = ""
        if collected_data:
            existing_data = "\nУже заполнено:\n"
            for key, value in collected_data.items():
                if value:
                    existing_data += f"- {key}: {value}\n"
        
        prompt = f"""Ты бизнес-аналитик. Извлеки информацию из диалога и заполни поля BRD.

Диалог:
{conversation_text}
{existing_data}

Извлеки и заполни следующие поля:
1. project_name - название проекта
2. project_goal - цель проекта
3. project_description - описание проекта
4. scope - список элементов scope (массив строк)
5. scope_out - что не входит в scope (массив строк)
6. business_rules - бизнес-правила (массив строк)
7. kpi - метрики KPI (массив объектов: {{label, goal, current}})
8. leading_indicators - лидирующие индикаторы (массив строк)

Верни результат в формате JSON:
{{
    "project_name": "название",
    "project_goal": "цель",
    "project_description": "описание",
    "scope": ["элемент1", "элемент2"],
    "scope_out": ["элемент1"],
    "business_rules": ["правило1"],
    "kpi": [{{"label": "метрика", "goal": "цель", "current": "текущее"}}],
    "leading_indicators": ["индикатор1"]
}}

Если какое-то поле не найдено в диалоге, верни пустое значение (null, [], {{}})."""
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text if hasattr(response, 'text') else str(response)
            
            # Парсим JSON
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                return parsed
        except Exception as e:
            pass
        
        return {}
    
    def autofill_field(self, field_name: str, partial_value: str, context: Dict = None) -> List[str]:
        """
        Автозаполнение конкретного поля на основе частичного ввода
        
        Args:
            field_name: Название поля (project_name, scope, kpi, etc.)
            partial_value: Частично введенное значение
            context: Контекст (собранные данные, история)
        
        Returns:
            Список предложений для автозаполнения
        """
        field_descriptions = {
            'project_name': 'название проекта (краткое, понятное)',
            'project_goal': 'цель проекта (что хотим достичь)',
            'scope': 'элемент области проекта (scope)',
            'kpi': 'название KPI метрики',
            'business_rule': 'бизнес-правило',
            'leading_indicator': 'лидирующий индикатор'
        }
        
        field_desc = field_descriptions.get(field_name, field_name)
        
        context_info = ""
        if context:
            collected = context.get('collected_data', {})
            if collected.get('project_name'):
                context_info = f"\nНазвание проекта: {collected['project_name']}\n"
        
        prompt = f"""Предложи 3 варианта автозаполнения для поля: {field_desc}

Частично введено: "{partial_value}"
{context_info}

Предложи 3 коротких варианта (максимум 10-15 слов каждый), которые:
- Начинаются с введенного текста (если есть)
- Релевантны для банковского проекта
- Конкретны и полезны

Верни только варианты, каждый с новой строки:"""
        
        try:
            response = self.model.generate_content(prompt)
            suggestions_text = response.text if hasattr(response, 'text') else str(response)
            
            suggestions = []
            for line in suggestions_text.split('\n'):
                line = line.strip()
                line = re.sub(r'^[\d\-•\*]\s*', '', line)
                if line and len(line) > 3 and len(line) < 100:
                    suggestions.append(line)
            
            return suggestions[:3] if suggestions else []
        except:
            return []
    
    def suggest_scope_items(self, project_description: str, existing_scope: List[str] = None) -> List[str]:
        """
        Предлагает элементы scope для проекта
        
        Args:
            project_description: Описание проекта
            existing_scope: Уже добавленные элементы
        
        Returns:
            Список предложенных элементов scope
        """
        existing_info = ""
        if existing_scope:
            existing_info = f"\nУже добавлено:\n" + "\n".join([f"- {item}" for item in existing_scope])
        
        prompt = f"""Предложи 5-7 элементов scope (области проекта) для следующего проекта:

Описание проекта: {project_description}
{existing_info}

Предложи элементы, которые:
- Входят в область проекта
- Конкретны и измеримы
- Релевантны для банковской сферы
- Не дублируют уже добавленные

Верни только элементы, каждый с новой строки, коротко (3-7 слов):"""
        
        try:
            response = self.model.generate_content(prompt)
            suggestions_text = response.text if hasattr(response, 'text') else str(response)
            
            suggestions = []
            for line in suggestions_text.split('\n'):
                line = line.strip()
                line = re.sub(r'^[\d\-•\*]\s*', '', line)
                if line and len(line) > 5 and len(line) < 80:
                    # Проверяем, нет ли дубликатов
                    if not existing_scope or line.lower() not in [s.lower() for s in existing_scope]:
                        suggestions.append(line)
            
            return suggestions[:7] if suggestions else []
        except:
            return []
    
    def suggest_kpi_metrics(self, project_description: str, existing_kpi: List[Dict] = None) -> List[Dict]:
        """
        Предлагает KPI метрики для проекта
        
        Args:
            project_description: Описание проекта
            existing_kpi: Уже добавленные KPI
        
        Returns:
            Список предложенных KPI
        """
        existing_info = ""
        if existing_kpi:
            existing_info = "\nУже добавлено:\n"
            for kpi in existing_kpi:
                existing_info += f"- {kpi.get('label', '')}\n"
        
        prompt = f"""Предложи 5-7 KPI метрик для следующего проекта:

Описание проекта: {project_description}
{existing_info}

Предложи метрики в формате JSON массива:
[
    {{"label": "название метрики", "goal": "целевое значение", "current": "текущее значение"}},
    ...
]

Примеры:
- Время обработки заявки
- Процент автоматического одобрения
- Удовлетворенность клиентов
- Количество обработанных заявок
- Точность принятия решений

Верни только JSON массив:"""
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text if hasattr(response, 'text') else str(response)
            
            # Парсим JSON
            json_match = re.search(r'\[[^\]]*\]', response_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                if isinstance(parsed, list):
                    # Фильтруем дубликаты
                    existing_labels = [k.get('label', '').lower() for k in (existing_kpi or [])]
                    filtered = [k for k in parsed if k.get('label', '').lower() not in existing_labels]
                    return filtered[:7]
        except:
            pass
        
        return []
    
    def smart_fill_from_text(self, text: str) -> Dict:
        """
        Умное заполнение всех полей из текста
        
        Args:
            text: Текст с описанием проекта/требований
        
        Returns:
            Словарь с заполненными полями
        """
        prompt = f"""Извлеки информацию из текста и заполни поля BRD.

Текст:
{text}

Извлеки:
1. Название проекта
2. Цель проекта
3. Описание проекта
4. Scope (что входит)
5. Scope out (что не входит)
6. Бизнес-правила
7. KPI метрики

Верни в формате JSON:
{{
    "project_name": "...",
    "project_goal": "...",
    "project_description": "...",
    "scope": ["..."],
    "scope_out": ["..."],
    "business_rules": ["..."],
    "kpi": [{{"label": "...", "goal": "...", "current": "..."}}]
}}"""
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text if hasattr(response, 'text') else str(response)
            
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                return parsed
        except:
            pass
        
        return {}


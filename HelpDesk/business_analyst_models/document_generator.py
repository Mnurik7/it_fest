"""
Модуль для генерации документов (BRD, Use Case, User Stories)
"""
from typing import Dict, List, Optional


class DocumentGenerator:
    """Генератор документов для бизнес-аналитики"""
    
    def __init__(self, model):
        self.model = model
    
    def generate_brd(self, analysis: Dict, context: Optional[Dict] = None) -> Dict:
        """
        Генерирует BRD (Business Requirements Document)
        
        Args:
            analysis: Результат анализа документа или данные пользователя
            context: Дополнительный контекст
        
        Returns:
            BRD документ
        """
        # Извлекаем данные пользователя
        project_name = analysis.get('project_name', '') or analysis.get('project_description', '').split('\n')[0] if analysis.get('project_description') else ''
        project_description = analysis.get('project_description', '')
        scope_items = analysis.get('scope', [])
        kpi_items = analysis.get('kpi', [])
        
        # Формируем детальное описание проекта на основе данных пользователя
        user_data_section = f"""ДАННЫЕ ПРОЕКТА ОТ ПОЛЬЗОВАТЕЛЯ:

Название проекта: {project_name if project_name else 'Не указано'}

Описание проекта:
{project_description if project_description else 'Описание не предоставлено'}

Scope (Область охвата):
"""
        if scope_items:
            for i, item in enumerate(scope_items, 1):
                user_data_section += f"{i}. {item}\n"
        else:
            user_data_section += "Не указано\n"
        
        user_data_section += "\nKPI метрики:\n"
        if kpi_items:
            for kpi in kpi_items:
                label = kpi.get('label', '') if isinstance(kpi, dict) else str(kpi)
                goal = kpi.get('goal', '') if isinstance(kpi, dict) else ''
                current = kpi.get('current', '') if isinstance(kpi, dict) else ''
                user_data_section += f"- {label}"
                if goal:
                    user_data_section += f" | Цель: {goal}"
                if current:
                    user_data_section += f" | Текущее значение: {current}"
                user_data_section += "\n"
        else:
            user_data_section += "Не указано\n"
        
        context_str = ""
        if context:
            context_str = f"""
Контекст:
- Заказчик: {context.get('customer', 'не указан')}
- Проект: {context.get('project', project_name or 'не указан')}
"""
        
        prompt = f"""Ты бизнес-аналитик в банке. Создай BRD (Business Requirements Document) ИСКЛЮЧИТЕЛЬНО на основе данных, предоставленных пользователем ниже.

ВАЖНО: Используй ТОЛЬКО данные пользователя. НЕ придумывай свой проект. Если пользователь указал название проекта, Scope и KPI - используй именно их. Дополняй и структурируй эти данные, но не заменяй их на другие.

{context_str}

{user_data_section}

На основе ЭТИХ данных пользователя создай полный BRD по следующему шаблону:

# BUSINESS REQUIREMENTS DOCUMENT (BRD)

## Название проекта
{project_name if project_name else '[Укажи название проекта на основе описания]'}

## 1. ЦЕЛЬ
[Сформулируй цель проекта на основе описания и данных пользователя. Если пользователь не указал цель явно, выведи логичную цель на основе названия и описания проекта]

## 2. ПРОБЛЕМА
[Опиши проблему, которую решает этот проект. Используй данные пользователя, если они есть]

## 3. SCOPE (ОБЛАСТЬ ПРИМЕНЕНИЯ)

### Входит в Scope (In Scope):
{chr(10).join([f"- {item}" for item in scope_items]) if scope_items else "- [Укажи на основе описания проекта]"}

### Не входит в Scope (Out of Scope):
[Укажи, что явно не входит в проект]

## 4. ТРЕБОВАНИЯ

### 4.1. Функциональные требования
[Сформулируй функциональные требования на основе Scope и описания проекта]

### 4.2. Нефункциональные требования
[Производительность, безопасность, масштабируемость и т.д. - стандартные для банковских проектов]

### 4.3. Бизнес-требования
[Бизнес-правила и ограничения на основе данных проекта]

## 5. БИЗНЕС-ПРАВИЛА
[Детальное описание бизнес-правил для данного проекта]

## 6. KPI И МЕТРИКИ
{chr(10).join([f"**{kpi.get('label', '') if isinstance(kpi, dict) else str(kpi)}:** {'Цель: ' + kpi.get('goal', '') + '. ' if isinstance(kpi, dict) and kpi.get('goal') else ''}{'Текущее значение: ' + kpi.get('current', '') if isinstance(kpi, dict) and kpi.get('current') else ''}" for kpi in kpi_items]) if kpi_items else "[Укажи KPI метрики на основе описания проекта]"}

## 7. РИСКИ
[Идентифицированные риски и митигация для данного проекта]

## 8. ЗАВИСИМОСТИ
[Зависимости от других проектов/систем]

## 9. ОГРАНИЧЕНИЯ
[Технические и бизнес-ограничения]

ПОМНИ: Используй данные пользователя как основу. Название проекта, Scope и KPI должны точно соответствовать тому, что указал пользователь. Дополняй только недостающие разделы."""
        
        try:
            response = self.model.generate_content(prompt)
            brd_text = response.text if hasattr(response, 'text') else str(response)
            
            return {
                'type': 'BRD',
                'content': brd_text,
                'formatted_for_confluence': self._format_for_confluence(brd_text)
            }
        except Exception as e:
            return {
                'type': 'BRD',
                'error': str(e),
                'content': None
            }
    
    def generate_use_case(self, requirement: str, actor: str, context: Optional[Dict] = None) -> Dict:
        """
        Генерирует Use Case
        
        Args:
            requirement: Описание требования
            actor: Актор (роль пользователя)
            context: Дополнительный контекст
        
        Returns:
            Use Case документ
        """
        prompt = f"""Ты бизнес-аналитик. Создай Use Case на основе следующего требования.

Актор: {actor}
Требование: {requirement}

Создай Use Case в следующем формате:

# USE CASE: [Название]

## АКТОР
[Описание актора]

## ПРЕДУСЛОВИЯ
[Что должно быть выполнено до начала сценария]

## ОСНОВНОЙ СЦЕНАРИЙ
1. [Шаг 1]
2. [Шаг 2]
3. [Шаг 3]

## АЛЬТЕРНАТИВНЫЕ СЦЕНАРИИ
[Описание альтернативных путей]

## ПОСТУСЛОВИЯ
[Состояние системы после выполнения]

## РЕЗУЛЬТАТ
[Ожидаемый результат]

Используй формат Markdown."""
        
        try:
            response = self.model.generate_content(prompt)
            use_case_text = response.text if hasattr(response, 'text') else str(response)
            
            return {
                'type': 'Use Case',
                'actor': actor,
                'requirement': requirement,
                'content': use_case_text,
                'formatted_for_confluence': self._format_for_confluence(use_case_text)
            }
        except Exception as e:
            return {
                'type': 'Use Case',
                'error': str(e),
                'content': None
            }
    
    def generate_user_stories(self, requirements: List[str], roles: Optional[List[str]] = None) -> List[Dict]:
        """
        Генерирует User Stories
        
        Args:
            requirements: Список требований
            roles: Список ролей пользователей
        
        Returns:
            Список User Stories
        """
        if not roles:
            roles = ['Пользователь', 'Администратор', 'Менеджер']
        
        requirements_text = '\n'.join([f"- {req}" for req in requirements])
        roles_text = ', '.join(roles)
        
        prompt = f"""Ты бизнес-аналитик. Создай User Stories на основе следующих требований.

Роли: {roles_text}

Требования:
{requirements_text}

Создай User Stories в формате:
Как <роль>, я хочу <действие>, чтобы <результат>.

Для каждого требования создай 1-3 User Stories с разными ролями, если это уместно.

Формат вывода:
## USER STORY 1
**Как** [роль], **я хочу** [действие], **чтобы** [результат].

**Критерии приемки:**
- [Критерий 1]
- [Критерий 2]

**Приоритет:** [Высокий/Средний/Низкий]

Используй формат Markdown."""
        
        try:
            response = self.model.generate_content(prompt)
            stories_text = response.text if hasattr(response, 'text') else str(response)
            
            # Парсим User Stories
            stories = self._parse_user_stories(stories_text)
            
            return stories
        except Exception as e:
            return [{
                'error': str(e),
                'content': None
            }]
    
    def _format_analysis_for_prompt(self, analysis: Dict) -> str:
        """Форматирует анализ для использования в промпте"""
        text = f"""
Тип документа: {analysis.get('document_type', 'неизвестный')}

Цель: {analysis.get('goal', 'не указана')}

Требования: {', '.join(analysis.get('requirements', []))}

Бизнес-правила: {', '.join(analysis.get('business_rules', []))}

Метрики: {', '.join(analysis.get('metrics', []))}

Ограничения: {', '.join(analysis.get('constraints', []))}

Резюме: {analysis.get('summary', 'не указано')}
"""
        return text
    
    def _parse_user_stories(self, stories_text: str) -> List[Dict]:
        """Парсит User Stories из текста"""
        stories = []
        lines = stories_text.split('\n')
        
        current_story = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if 'USER STORY' in line.upper() or 'СТОРИЯ' in line.upper():
                if current_story:
                    stories.append(current_story)
                current_story = {
                    'content': '',
                    'acceptance_criteria': [],
                    'priority': 'Средний'
                }
            elif 'КАК' in line.upper() and current_story:
                current_story['content'] = line
            elif 'КРИТЕРИИ' in line.upper() or 'ACCEPTANCE' in line.upper():
                continue
            elif 'ПРИОРИТЕТ' in line.upper() and current_story:
                if 'высокий' in line.lower() or 'high' in line.lower():
                    current_story['priority'] = 'Высокий'
                elif 'низкий' in line.lower() or 'low' in line.lower():
                    current_story['priority'] = 'Низкий'
            elif line.startswith('-') or line.startswith('•') or line.startswith('*'):
                if current_story:
                    current_story['acceptance_criteria'].append(line.lstrip('-•* ').strip())
            elif current_story and len(line) > 10:
                if not current_story['content']:
                    current_story['content'] = line
        
        if current_story:
            stories.append(current_story)
        
        return stories if stories else [{'content': stories_text, 'acceptance_criteria': [], 'priority': 'Средний'}]
    
    def _format_for_confluence(self, text: str) -> str:
        """Форматирует текст для Confluence (Markdown совместимый)"""
        # Confluence поддерживает Markdown, так что просто возвращаем как есть
        # Можно добавить дополнительные преобразования при необходимости
        return text
    
    def generate_confluence_page(self, documents: List[Dict], title: str = "Бизнес-анализ") -> str:
        """
        Генерирует страницу для Confluence со всеми документами
        
        Args:
            documents: Список документов (BRD, Use Cases, User Stories)
            title: Заголовок страницы
        
        Returns:
            Markdown текст для Confluence
        """
        confluence_content = f"# {title}\n\n"
        confluence_content += f"*Сгенерировано автоматически*\n\n"
        confluence_content += "---\n\n"
        
        for doc in documents:
            doc_type = doc.get('type', 'Документ')
            content = doc.get('content') or doc.get('formatted_for_confluence', '')
            
            if content:
                confluence_content += f"## {doc_type}\n\n"
                confluence_content += f"{content}\n\n"
                confluence_content += "---\n\n"
        
        return confluence_content
    
    def generate_leading_indicators(self, project_data: Dict, kpi_data: Optional[List[Dict]] = None) -> Dict:
        """
        Генерирует лидирующие индикаторы (прогнозные метрики)
        
        Args:
            project_data: Данные проекта
            kpi_data: Список KPI метрик
        
        Returns:
            Документ с лидирующими индикаторами
        """
        project_name = project_data.get('project_name', 'Проект')
        project_description = project_data.get('project_description', '')
        
        kpi_section = ""
        if kpi_data:
            kpi_section = "\nТекущие KPI метрики:\n"
            for kpi in kpi_data:
                label = kpi.get('label', '') if isinstance(kpi, dict) else str(kpi)
                kpi_section += f"- {label}\n"
        
        prompt = f"""Ты бизнес-аналитик в банке. Создай лидирующие индикаторы (leading indicators) для проекта.

Лидирующие индикаторы - это прогнозные метрики, которые помогают предсказать успех проекта ДО его завершения. Они показывают ранние признаки успеха или проблем.

Проект: {project_name}
Описание: {project_description}
{kpi_section}

Создай лидирующие индикаторы в следующем формате:

# ЛИДИРУЮЩИЕ ИНДИКАТОРЫ

## 1. ИНДИКАТОР: [Название индикатора]
- **Описание:** [Что измеряет этот индикатор]
- **Как измеряется:** [Метод измерения]
- **Целевое значение:** [Ожидаемое значение]
- **Частота измерения:** [Как часто отслеживается - ежедневно/еженедельно/ежемесячно]
- **Связь с KPI:** [Какой KPI предсказывает]
- **Ранние признаки успеха:** [Что указывает на успех]
- **Ранние признаки проблем:** [Что указывает на проблемы]

## 2. ИНДИКАТОР: [Следующий индикатор]
...

Создай 5-7 лидирующих индикаторов, которые помогут предсказать успех проекта. Каждый индикатор должен быть:
- Измеримым
- Ранним признаком (измеряется до достижения финального KPI)
- Релевантным для проекта
- Понятным для stakeholders

Используй формат Markdown."""
        
        try:
            response = self.model.generate_content(prompt)
            indicators_text = response.text if hasattr(response, 'text') else str(response)
            
            return {
                'type': 'Leading Indicators',
                'content': indicators_text,
                'formatted_for_confluence': self._format_for_confluence(indicators_text)
            }
        except Exception as e:
            return {
                'type': 'Leading Indicators',
                'error': str(e),
                'content': None
            }
    
    def suggest_process_improvements(self, current_process: str, business_rules: Optional[List[str]] = None) -> Dict:
        """
        Предлагает улучшения бизнес-процессов
        
        Args:
            current_process: Описание текущего процесса
            business_rules: Список бизнес-правил
        
        Returns:
            Документ с предложениями по улучшению
        """
        rules_section = ""
        if business_rules:
            rules_section = "\nТекущие бизнес-правила:\n"
            for rule in business_rules:
                rules_section += f"- {rule}\n"
        
        prompt = f"""Ты бизнес-аналитик, специализирующийся на совершенствовании бизнес-процессов в банке. 

Проанализируй текущий процесс и предложи улучшения:

Текущий процесс:
{current_process}
{rules_section}

Создай документ с предложениями по улучшению в следующем формате:

# ПРЕДЛОЖЕНИЯ ПО СОВЕРШЕНСТВОВАНИЮ БИЗНЕС-ПРОЦЕССОВ

## ТЕКУЩЕЕ СОСТОЯНИЕ
[Краткое описание текущего процесса и выявленных проблем]

## ПРЕДЛОЖЕНИЯ ПО УЛУЧШЕНИЮ

### 1. УЛУЧШЕНИЕ: [Название]
- **Область применения:** [Где применяется]
- **Текущая проблема:** [Какая проблема решается]
- **Предлагаемое решение:** [Описание улучшения]
- **Ожидаемый эффект:** [Что это даст]
- **Сложность внедрения:** [Низкая/Средняя/Высокая]
- **Приоритет:** [Высокий/Средний/Низкий]
- **Зависимости:** [От чего зависит]

### 2. УЛУЧШЕНИЕ: [Следующее улучшение]
...

## BEST PRACTICES
[Рекомендации на основе лучших практик в банковской отрасли]

## МЕТРИКИ УЛУЧШЕНИЯ
[Какие метрики помогут измерить эффективность улучшений]

## ПЛАН ВНЕДРЕНИЯ
[Предлагаемые шаги по внедрению улучшений]

Проанализируй процесс с точки зрения:
- Эффективности (скорость, время выполнения)
- Качества (точность, ошибки)
- Затрат ресурсов
- Удовлетворенности пользователей
- Соответствия регуляторным требованиям
- Масштабируемости

Используй формат Markdown."""
        
        try:
            response = self.model.generate_content(prompt)
            improvements_text = response.text if hasattr(response, 'text') else str(response)
            
            return {
                'type': 'Process Improvements',
                'content': improvements_text,
                'formatted_for_confluence': self._format_for_confluence(improvements_text)
            }
        except Exception as e:
            return {
                'type': 'Process Improvements',
                'error': str(e),
                'content': None
            }


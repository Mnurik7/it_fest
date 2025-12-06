"""
Модуль для анализа и совершенствования бизнес-процессов
"""
from typing import Dict, List, Optional


class ProcessImprover:
    """Анализатор и улучшатель бизнес-процессов"""
    
    def __init__(self, model):
        self.model = model
    
    def analyze_process(self, process_description: str, current_metrics: Optional[Dict] = None) -> Dict:
        """
        Анализирует текущий бизнес-процесс
        
        Args:
            process_description: Описание процесса
            current_metrics: Текущие метрики процесса (опционально)
        
        Returns:
            Результат анализа процесса
        """
        metrics_section = ""
        if current_metrics:
            metrics_section = "\nТекущие метрики процесса:\n"
            for key, value in current_metrics.items():
                metrics_section += f"- {key}: {value}\n"
        
        prompt = f"""Ты бизнес-аналитик, специализирующийся на анализе бизнес-процессов в банке.

Проанализируй следующий бизнес-процесс:

Описание процесса:
{process_description}
{metrics_section}

Проведи комплексный анализ и предоставь результат в следующей структуре:

# АНАЛИЗ БИЗНЕС-ПРОЦЕССА

## 1. ОБЩЕЕ ОПИСАНИЕ
- Краткое описание процесса
- Основные участники (акторы)
- Цели процесса

## 2. ВЫЯВЛЕННЫЕ ПРОБЛЕМЫ
- Проблемы эффективности
- Проблемы качества
- Узкие места (bottlenecks)
- Избыточные шаги
- Риски

## 3. ОЦЕНКА ЭФФЕКТИВНОСТИ
- Время выполнения процесса
- Использование ресурсов
- Процент успешных завершений
- Уровень автоматизации

## 4. СООТВЕТСТВИЕ ТРЕБОВАНИЯМ
- Соответствие регуляторным требованиям
- Соответствие внутренним стандартам
- Соблюдение бизнес-правил

## 5. ВОЗМОЖНОСТИ ДЛЯ УЛУЧШЕНИЯ
- Области для оптимизации
- Потенциал автоматизации
- Возможности для стандартизации

Используй формат Markdown."""
        
        try:
            response = self.model.generate_content(prompt)
            analysis_text = response.text if hasattr(response, 'text') else str(response)
            
            return {
                'type': 'Process Analysis',
                'content': analysis_text,
                'process_description': process_description,
                'has_improvements': True
            }
        except Exception as e:
            return {
                'type': 'Process Analysis',
                'error': str(e),
                'content': None
            }
    
    def suggest_improvements(self, analysis: Dict, priority: str = 'high') -> List[Dict]:
        """
        Предлагает конкретные улучшения на основе анализа
        
        Args:
            analysis: Результат анализа процесса
            priority: Приоритет улучшений (high/medium/low/all)
        
        Returns:
            Список предложений по улучшению
        """
        analysis_content = analysis.get('content', '')
        
        priority_filter = {
            'high': 'Высокий',
            'medium': 'Средний',
            'low': 'Низкий',
            'all': 'Все'
        }.get(priority, 'Все')
        
        prompt = f"""На основе анализа бизнес-процесса предложи конкретные улучшения.

Анализ процесса:
{analysis_content}

Создай список конкретных предложений по улучшению. Для каждого предложения укажи:

1. **Название улучшения**
2. **Проблема, которую решает**
3. **Описание улучшения**
4. **Ожидаемый эффект** (в числовых показателях, если возможно)
5. **Сложность внедрения** (Низкая/Средняя/Высокая)
6. **Приоритет** (Высокий/Средний/Низкий)
7. **Зависимости** (от чего зависит внедрение)
8. **Рекомендуемые шаги** (как внедрить)

Приоритет предложений: {priority_filter}

Формат вывода:
## ПРЕДЛОЖЕНИЕ 1: [Название]
[Описание в структурированном виде]

## ПРЕДЛОЖЕНИЕ 2: [Название]
...

Используй формат Markdown."""
        
        try:
            response = self.model.generate_content(prompt)
            improvements_text = response.text if hasattr(response, 'text') else str(response)
            
            # Парсим предложения
            improvements = self._parse_improvements(improvements_text)
            
            return improvements
        except Exception as e:
            return [{
                'error': str(e),
                'content': None
            }]
    
    def _parse_improvements(self, text: str) -> List[Dict]:
        """Парсит предложения по улучшению из текста"""
        improvements = []
        lines = text.split('\n')
        
        current_improvement = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('## ПРЕДЛОЖЕНИЕ') or line.startswith('## ПРЕДЛОЖЕНИЕ'):
                if current_improvement:
                    improvements.append(current_improvement)
                
                # Извлекаем название из заголовка
                title = line.split(':', 1)[1].strip() if ':' in line else 'Улучшение'
                current_improvement = {
                    'title': title,
                    'content': '',
                    'priority': 'Средний',
                    'complexity': 'Средняя'
                }
            elif current_improvement:
                current_improvement['content'] += line + '\n'
                
                # Извлекаем приоритет и сложность
                if 'Приоритет' in line:
                    if 'Высокий' in line or 'High' in line.upper():
                        current_improvement['priority'] = 'Высокий'
                    elif 'Низкий' in line or 'Low' in line.upper():
                        current_improvement['priority'] = 'Низкий'
                
                if 'Сложность' in line or 'Complexity' in line:
                    if 'Низкая' in line or 'Low' in line.upper():
                        current_improvement['complexity'] = 'Низкая'
                    elif 'Высокая' in line or 'High' in line.upper():
                        current_improvement['complexity'] = 'Высокая'
        
        if current_improvement:
            improvements.append(current_improvement)
        
        return improvements if improvements else [{
            'title': 'Улучшение процесса',
            'content': text,
            'priority': 'Средний',
            'complexity': 'Средняя'
        }]
    
    def compare_with_best_practices(self, process_description: str, industry: str = 'banking') -> Dict:
        """
        Сравнивает процесс с лучшими практиками
        
        Args:
            process_description: Описание процесса
            industry: Отрасль (по умолчанию банковская)
        
        Returns:
            Сравнение с best practices
        """
        prompt = f"""Ты бизнес-аналитик. Сравни следующий процесс с лучшими практиками в {industry} отрасли.

Описание процесса:
{process_description}

Сравни процесс с best practices и предоставь:

1. **Соответствие best practices** - что уже соответствует
2. **Отклонения от best practices** - что нужно улучшить
3. **Рекомендации** - конкретные рекомендации по приведению к best practices
4. **Примеры из практики** - как это делают лидеры отрасли

Используй формат Markdown."""
        
        try:
            response = self.model.generate_content(prompt)
            comparison_text = response.text if hasattr(response, 'text') else str(response)
            
            return {
                'type': 'Best Practices Comparison',
                'content': comparison_text,
                'industry': industry
            }
        except Exception as e:
            return {
                'type': 'Best Practices Comparison',
                'error': str(e),
                'content': None
            }


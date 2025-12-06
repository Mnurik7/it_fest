"""
Модуль для генерации рекомендаций по ревью кода
"""
from typing import Dict, List, Optional, Any


class ReviewGenerator:
    """Генератор рекомендаций по ревью кода"""
    
    def __init__(self, model):
        self.model = model
    
    def generate_recommendations(self, analysis: Dict[str, Any], 
                                review_scope: str = 'file') -> Dict[str, Any]:
        """
        Генерирует рекомендации на основе анализа
        
        Args:
            analysis: Результат анализа кода
            review_scope: Область ревью ('file' или 'project')
        
        Returns:
            Словарь с рекомендациями
        """
        if analysis.get('error'):
            return analysis
        
        analysis_text = analysis.get('analysis', '')
        
        prompt = f"""Краткие рекомендации с улучшенным кодом.

Область: {review_scope}

Анализ:
{analysis_text[:5000]}

Формат:

**КРИТИЧНО:**
- [Строка] [Проблема: кратко]
  ```python
  # Исправленный код
  ```

**ВАЖНО:**
- [Строка] [Проблема: кратко]
  ```python
  # Исправленный код
  ```

**УЛУЧШЕНИЯ:**
- [Строка] [Рекомендация: кратко]
  ```python
  # Улучшенный код
  ```

Для каждого пункта: краткое описание (1 предложение) + исправленный код."""
        
        try:
            response = self.model.generate_content(prompt)
            recommendations_text = response.text if hasattr(response, 'text') else str(response)
            
            return {
                'recommendations': recommendations_text,
                'review_scope': review_scope,
                'success': True
            }
        except Exception as e:
            return {
                'error': f'Ошибка при генерации рекомендаций: {str(e)}',
                'review_scope': review_scope
            }
    
    def generate_code_fixes(self, analysis: Dict[str, Any], original_code: str, 
                           file_path: str = '') -> Dict[str, Any]:
        """
        Генерирует исправленный код с объяснениями
        
        Args:
            analysis: Результат анализа кода
            original_code: Исходный код
            file_path: Путь к файлу
        
        Returns:
            Словарь с исправленным кодом и объяснениями
        """
        if analysis.get('error'):
            return analysis
        
        analysis_text = analysis.get('analysis', '')
        recommendations_text = analysis.get('recommendations', '')
        
        prompt = f"""Проанализируй код и предоставь полный исправленный вариант с объяснениями.

Исходный код:
```python
{original_code[:5000]}
```

Анализ проблем:
{analysis_text[:3000]}

Рекомендации:
{recommendations_text[:2000]}

Предоставь ответ в строгом JSON формате:
{{
    "fixed_code": "полный исправленный код",
    "changes": [
        {{
            "line_start": номер_строки,
            "line_end": номер_строки,
            "original": "старый код",
            "fixed": "новый код",
            "reason": "объяснение почему это изменение нужно",
            "priority": "critical|important|suggestion"
        }}
    ],
    "summary": "краткое резюме всех изменений"
}}

ВАЖНО: Возвращай ТОЛЬКО валидный JSON, без дополнительного текста."""
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text if hasattr(response, 'text') else str(response)
            
            # Пытаемся извлечь JSON из ответа
            import json
            import re
            
            # Ищем JSON в ответе
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                json_str = json_match.group(0)
                fix_data = json.loads(json_str)
                
                return {
                    'fixed_code': fix_data.get('fixed_code', original_code),
                    'changes': fix_data.get('changes', []),
                    'summary': fix_data.get('summary', 'Код был улучшен на основе анализа'),
                    'success': True
                }
            else:
                # Если не удалось извлечь JSON, возвращаем улучшенный код на основе рекомендаций
                return {
                    'fixed_code': original_code,  # В этом случае нужно будет улучшить логику
                    'changes': [],
                    'summary': 'Не удалось автоматически сгенерировать исправления. См. рекомендации выше.',
                    'success': False
                }
                
        except Exception as e:
            return {
                'error': f'Ошибка при генерации исправлений: {str(e)}',
                'success': False
            }
    
    def generate_educational_hints(self, issue: str, developer_level: str = 'junior') -> Dict[str, Any]:
        """
        Генерирует обучающие подсказки для разработчиков
        
        Args:
            issue: Проблема в коде
            developer_level: Уровень разработчика (junior/middle/senior)
        
        Returns:
            Обучающие подсказки
        """
        prompt = f"""Ты ментор для разработчиков. Объясни следующую проблему в коде для разработчика уровня {developer_level}.

Проблема:
{issue}

Предоставь объяснение в следующем формате:

1. ЧТО НЕ ТАК:
   - [Простое объяснение проблемы]

2. ПОЧЕМУ ЭТО ПРОБЛЕМА:
   - [Объяснение последствий]
   - [Примеры когда это может вызвать проблемы]

3. КАК ИСПРАВИТЬ:
   - [Пошаговое объяснение]
   - [Пример правильного кода]

4. BEST PRACTICES:
   - [Рекомендации как избежать в будущем]
   - [Полезные ресурсы для изучения]

5. ПРОВЕРЬ СЕБЯ:
   - [Вопросы для самопроверки]

Будь дружелюбным и понятным. Используй простой язык для junior разработчиков."""
        
        try:
            response = self.model.generate_content(prompt)
            hints_text = response.text if hasattr(response, 'text') else str(response)
            
            return {
                'hints': hints_text,
                'developer_level': developer_level,
                'success': True
            }
        except Exception as e:
            return {
                'error': f'Ошибка при генерации подсказок: {str(e)}',
                'developer_level': developer_level
            }
    
    def generate_commit_message(self, file_path: str, changes: List[Dict[str, Any]], 
                               summary: str = '') -> Dict[str, Any]:
        """
        Генерирует имя и описание коммита через ИИ
        
        Args:
            file_path: Путь к файлу
            changes: Список изменений
            summary: Краткое резюме изменений
        
        Returns:
            Словарь с именем и описанием коммита
        """
        changes_text = ""
        if changes:
            for change in changes[:5]:  # Ограничиваем количество изменений
                changes_text += f"- {change.get('reason', 'Изменение')} (приоритет: {change.get('priority', 'suggestion')})\n"
        
        prompt = f"""Создай профессиональное имя и описание коммита для изменений в файле.

Файл: {file_path}

Изменения:
{changes_text}

Резюме:
{summary}

Формат ответа (строгий JSON):
{{
    "title": "краткое имя коммита (до 50 символов)",
    "description": "подробное описание изменений (2-3 предложения)"
}}

ВАЖНО: Возвращай ТОЛЬКО валидный JSON, без дополнительного текста."""
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text if hasattr(response, 'text') else str(response)
            
            import json
            import re
            
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                json_str = json_match.group(0)
                commit_data = json.loads(json_str)
                
                return {
                    'title': commit_data.get('title', 'AI: Исправления кода'),
                    'description': commit_data.get('description', summary or 'Применены исправления на основе AI-анализа'),
                    'success': True
                }
            else:
                return {
                    'title': f'AI: Исправления в {file_path.split("/")[-1]}',
                    'description': summary or 'Применены исправления кода на основе AI-анализа',
                    'success': True
                }
        except Exception as e:
            return {
                'title': f'AI: Исправления в {file_path.split("/")[-1]}',
                'description': summary or 'Применены исправления кода на основе AI-анализа',
                'success': True
            }


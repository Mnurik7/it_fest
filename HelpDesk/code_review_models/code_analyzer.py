"""
Модуль для анализа кода и diff
"""
import re
import json
from typing import Dict, List, Optional, Any
import difflib


class CodeAnalyzer:
    """Анализатор кода и изменений"""
    
    def __init__(self, model):
        self.model = model
    
    def analyze_code(self, code: str, language: str, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Анализирует код на соответствие стандартам
        
        Args:
            code: Исходный код
            language: Язык программирования
            file_path: Путь к файлу (опционально)
        
        Returns:
            Результат анализа кода
        """
        prompt = f"""Проведи краткое ревью кода на {language}. Для каждой проблемы сразу давай улучшенный код.

{'Файл: ' + file_path if file_path else ''}

Код:
```{language}
{code}
```

Формат ответа:

**КРИТИЧНО:**
- [Строка X] Проблема: [краткое описание]
  ```{language}
  // Исправленный код
  ```

**ВАЖНО:**
- [Строка Y] Проблема: [краткое описание]
  ```{language}
  // Исправленный код
  ```

**УЛУЧШЕНИЯ:**
- [Строка Z] Рекомендация: [краткое описание]
  ```{language}
  // Улучшенный код
  ```

**БЕЗОПАСНОСТЬ:**
- [Строка N] Уязвимость: [тип]
  ```{language}
  // Безопасный код
  ```

**ПРОИЗВОДИТЕЛЬНОСТЬ:**
- [Строка M] Проблема: [краткое описание]
  ```{language}
  // Оптимизированный код
  ```

Для каждой проблемы: краткое описание (1 предложение) + исправленный код. Без лишних слов."""
        
        try:
            response = self.model.generate_content(prompt)
            analysis_text = response.text if hasattr(response, 'text') else str(response)
            
            # Извлекаем проблемы
            issues = self._extract_issues(analysis_text)
            
            return {
                'analysis': analysis_text,
                'issues': issues,
                'file_path': file_path,
                'language': language,
                'success': True
            }
        except Exception as e:
            return {
                'error': f'Ошибка при анализе кода: {str(e)}',
                'file_path': file_path,
                'language': language
            }
    
    def analyze_diff(self, diff_text: str, base_code: Optional[str] = None, 
                     new_code: Optional[str] = None, description: Optional[str] = None,
                     mr_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Анализирует diff изменений и проверяет корректность реализации функционала
        
        Args:
            diff_text: Текст diff
            base_code: Исходный код (опционально)
            new_code: Новый код (опционально)
            description: Описание функционала/требований (опционально)
            mr_id: ID Merge Request (опционально)
        
        Returns:
            Результат анализа diff
        """
        description_section = ""
        if description:
            description_section = f"""
**ТРЕБУЕМЫЙ ФУНКЦИОНАЛ:**
{description}

Проверь, что реализация СООТВЕТСТВУЕТ описанному функционалу. Укажи, если что-то не реализовано или реализовано неправильно.

"""
        
        prompt = f"""Краткий анализ diff для Merge Request. Для каждой проблемы давай улучшенный код.
{description_section}
Diff:
```
{diff_text}
```

{f'Исходный код:\n```\n{base_code}\n```' if base_code else ''}
{f'Новый код:\n```\n{new_code}\n```' if new_code else ''}

Формат:

**ОЦЕНКА КОРРЕКТНОСТИ РЕАЛИЗАЦИИ:**
{'- [✓/✗] Соответствие функционалу: [описание того, что должно быть реализовано и что реализовано]' if description else '- [✓/✗] Общая оценка: [кратко]'}

**КРИТИЧНО:**
- [Строка] Проблема: [кратко]
  ```python
  # Исправленный код
  ```

**ВАЖНО:**
- [Строка] Проблема: [кратко]
  ```python
  # Исправленный код
  ```

**РЕКОМЕНДАЦИИ:**
- [Строка] Улучшение: [кратко]
  ```python
  # Улучшенный код
  ```

**КОММЕНТАРИИ:**
- Предложения по улучшению и исправлению

**СТАТУС:** ready-for-merge / needs-fixes / reject

Для каждой проблемы: описание + исправленный код."""
        
        try:
            response = self.model.generate_content(prompt)
            analysis_text = response.text if hasattr(response, 'text') else str(response)
            
            # Извлекаем рекомендацию по merge
            merge_recommendation = self._extract_merge_recommendation(analysis_text)
            
            return {
                'analysis': analysis_text,
                'merge_recommendation': merge_recommendation,
                'success': True
            }
        except Exception as e:
            return {
                'error': f'Ошибка при анализе diff: {str(e)}'
            }
    
    def analyze_project(self, files: List[Dict[str, str]], architecture: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Анализирует весь проект
        
        Args:
            files: Список файлов с кодом [{'path': '...', 'code': '...', 'language': '...'}]
            architecture: Информация об архитектуре (опционально)
        
        Returns:
            Результат анализа проекта
        """
        files_summary = []
        for file_info in files[:20]:  # Ограничиваем количество файлов
            files_summary.append({
                'path': file_info.get('path', 'unknown'),
                'language': file_info.get('language', 'unknown'),
                'size': len(file_info.get('code', ''))
            })
        
        architecture_info = ""
        if architecture:
            architecture_info = f"\n\nИнформация об архитектуре:\n{architecture.get('analysis', '')[:2000]}"
        
        prompt = f"""Краткий анализ проекта. Для каждой проблемы давай улучшенный код.

Файлы ({len(files)}):
{json.dumps(files_summary, ensure_ascii=False, indent=2)}{architecture_info}

Формат:

**АРХИТЕКТУРА:**
- Проблема: [кратко]
  ```python
  # Исправление
  ```

**ФАЙЛЫ:**
- [Файл:Строка] Проблема: [кратко]
  ```python
  # Исправленный код
  ```

**ОБЩИЕ ПРОБЛЕМЫ:**
- [Проблема]: [кратко]
  ```python
  # Решение
  ```

**ПРИОРИТЕТЫ:**
1. [Критично] → [код исправления]
2. [Важно] → [код исправления]
3. [Улучшить] → [код улучшения]

Для каждой проблемы: краткое описание + исправленный код."""
        
        try:
            response = self.model.generate_content(prompt)
            analysis_text = response.text if hasattr(response, 'text') else str(response)
            
            return {
                'analysis': analysis_text,
                'files_analyzed': len(files),
                'success': True
            }
        except Exception as e:
            return {
                'error': f'Ошибка при анализе проекта: {str(e)}',
                'files_analyzed': len(files)
            }
    
    def generate_code_from_description(self, description: str, language: str = "Python", file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Генерирует код на основе описания через AI
        
        Args:
            description: Описание того, что должен делать код
            language: Язык программирования
            file_path: Путь к файлу (опционально)
            
        Returns:
            Сгенерированный код
        """
        prompt = f"""Ты эксперт-разработчик на {language}. Создай ПОЛНЫЙ, ДЕТАЛЬНЫЙ и РАБОТАЮЩИЙ код на основе следующего описания.

Описание:
{description}

{f'Путь к файлу: {file_path}' if file_path else ''}

ВАЖНЫЕ ТРЕБОВАНИЯ:
1. Код должен быть ПОЛНЫМ и ЗАВЕРШЁННЫМ - не сокращай, не используй "..." или "// TODO"
2. Включи ВСЕ необходимые импорты и зависимости
3. Добавь обработку ошибок (try-except, проверки и т.д.)
4. Добавь валидацию входных данных где необходимо
5. Включи документацию (docstrings, комментарии)
6. Используй правильные паттерны и идиомы для {language}
7. Код должен быть готов к использованию БЕЗ дополнительных изменений
8. Если описание подразумевает несколько функций/методов - создай ВСЕ
9. Если нужны классы - создай ПОЛНЫЕ классы с методами
10. Добавь примеры использования если это уместно

Создай РАЗВЁРНУТЫЙ код, который можно сразу использовать. Не сокращай код!

Верни ТОЛЬКО полный код без дополнительных объяснений."""

        try:
            response = self.model.generate_content(prompt)
            code = response.text if hasattr(response, 'text') else str(response)
            
            # Очищаем код от markdown форматирования и лишнего текста
            original_code = code
            
            # Убираем markdown блоки кода
            if '```' in code:
                # Ищем блоки кода
                import re
                code_blocks = re.findall(r'```(?:' + language.lower() + r'|' + language + r'|python|javascript|typescript|java|cpp|csharp|go|rust)?\n?(.*?)```', code, re.DOTALL)
                if code_blocks:
                    # Берём самый большой блок кода (обычно это основной код)
                    code = max(code_blocks, key=len)[0].strip()
                else:
                    # Если не нашли блоки, просто убираем markdown
                    parts = code.split('```')
                    for part in parts:
                        part = part.strip()
                        # Пропускаем части с названием языка
                        if language.lower() in part.lower() and len(part) < 50:
                            continue
                        # Берём первую значимую часть с кодом
                        if len(part) > 50 and ('def ' in part or 'function ' in part or 'class ' in part or 'import ' in part or '{' in part or '(' in part):
                            code = part
                            break
                    else:
                        # Если ничего не нашли, берём самую большую часть
                        code = max(parts, key=len).strip()
                        # Убираем название языка если есть
                        if code.startswith(language.lower()) or code.startswith(language):
                            code = code[len(language):].strip()
            
            # Убираем лишний текст в начале и конце
            lines = code.split('\n')
            # Убираем пустые строки в начале
            while lines and not lines[0].strip():
                lines.pop(0)
            # Убираем пустые строки в конце
            while lines and not lines[-1].strip():
                lines.pop()
            code = '\n'.join(lines)
            
            # Если код слишком короткий, используем оригинальный ответ
            if len(code.strip()) < 50:
                code = original_code
                # Пробуем извлечь код более агрессивно
                if '```' in code:
                    # Берём всё между первыми и последними ```
                    start = code.find('```')
                    end = code.rfind('```')
                    if start != -1 and end != -1 and end > start:
                        code = code[start+3:end].strip()
                        # Убираем название языка
                        if '\n' in code:
                            first_line = code.split('\n')[0]
                            if language.lower() in first_line.lower() and len(first_line) < 30:
                                code = '\n'.join(code.split('\n')[1:])
            
            return {
                'code': code.strip(),
                'language': language,
                'file_path': file_path,
                'success': True
            }
        except Exception as e:
            return {
                'error': f'Ошибка при генерации кода: {str(e)}',
                'language': language,
                'file_path': file_path
            }
    
    def generate_diff_from_description(self, description: str, base_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Генерирует diff на основе описания изменений
        
        Args:
            description: Описание изменений, которые нужно сделать
            base_code: Исходный код (опционально)
            
        Returns:
            Сгенерированный diff и новый код
        """
        if base_code:
            prompt = f"""Ты эксперт по коду. На основе следующего описания изменений создай diff для исходного кода.

Исходный код:
```python
{base_code}
```

Описание изменений:
{description}

Верни результат в формате:
1. Новый код (полный исправленный код)
2. Diff в формате unified diff (если возможно)

Формат:
НОВЫЙ_КОД:
```python
[новый код здесь]
```

DIFF:
```
[diff здесь]
```"""
        else:
            prompt = f"""Ты эксперт по коду. На основе следующего описания создай пример diff изменений.

Описание изменений:
{description}

Создай пример diff в формате unified diff, показывающий типичные изменения для такого описания."""

        try:
            response = self.model.generate_content(prompt)
            result_text = response.text if hasattr(response, 'text') else str(response)
            
            # Извлекаем новый код и diff
            new_code = None
            diff_text = None
            
            if 'НОВЫЙ_КОД:' in result_text:
                new_code_part = result_text.split('НОВЫЙ_КОД:')[1]
                if 'DIFF:' in new_code_part:
                    new_code_part = new_code_part.split('DIFF:')[0]
                # Извлекаем код из markdown
                if '```' in new_code_part:
                    code_parts = new_code_part.split('```')
                    for i, part in enumerate(code_parts):
                        if i > 0 and ('python' in part.lower() or 'javascript' in part.lower() or 'typescript' in part.lower()):
                            new_code = part.split('\n', 1)[1] if '\n' in part else part
                            break
            
            if 'DIFF:' in result_text:
                diff_part = result_text.split('DIFF:')[1]
                if '```' in diff_part:
                    diff_parts = diff_part.split('```')
                    for part in diff_parts:
                        if part.strip() and not part.strip().startswith('diff'):
                            diff_text = part.strip()
                            break
                else:
                    diff_text = diff_part.strip()
            
            return {
                'new_code': new_code,
                'diff_text': diff_text or result_text,
                'success': True
            }
        except Exception as e:
            return {
                'error': f'Ошибка при генерации diff: {str(e)}'
            }
    
    def improve_issue_description(self, description: str, code_snippet: Optional[str] = None) -> Dict[str, Any]:
        """
        Улучшает описание проблемы для обучающей поддержки
        
        Args:
            description: Краткое описание проблемы
            code_snippet: Фрагмент кода с проблемой (опционально)
            
        Returns:
            Улучшенное описание проблемы
        """
        prompt = f"""Ты эксперт по программированию и обучению. Улучши следующее описание проблемы в коде, сделав его более детальным и полезным для обучения.

Исходное описание:
{description}

{f'Проблемный код:\n```\n{code_snippet}\n```' if code_snippet else ''}

Создай улучшенное описание, которое включает:
- Чёткое описание проблемы
- Контекст, где возникает проблема
- Почему это проблема
- Что должно быть вместо этого
- Примеры (если применимо)

Верни только улучшенное описание без дополнительных комментариев."""

        try:
            response = self.model.generate_content(prompt)
            improved_description = response.text if hasattr(response, 'text') else str(response)
            
            return {
                'improved_description': improved_description.strip(),
                'success': True
            }
        except Exception as e:
            return {
                'error': f'Ошибка при улучшении описания: {str(e)}'
            }
    
    def _extract_issues(self, analysis_text: str) -> List[Dict[str, Any]]:
        """Извлекает конкретные проблемы из анализа"""
        issues = []
        # Простой парсинг для извлечения проблем
        lines = analysis_text.split('\n')
        current_issue = None
        
        for line in lines:
            if re.match(r'^\d+\.', line) or ':' in line:
                if current_issue:
                    issues.append(current_issue)
                current_issue = {'title': line.strip(), 'details': []}
            elif current_issue and line.strip():
                current_issue['details'].append(line.strip())
        
        if current_issue:
            issues.append(current_issue)
        
        return issues[:10]  # Ограничиваем количество
    
    def _extract_merge_recommendation(self, analysis_text: str) -> str:
        """Извлекает рекомендацию по merge из анализа"""
        text_lower = analysis_text.lower()
        
        if 'reject' in text_lower or 'отклонить' in text_lower:
            return 'reject'
        elif 'needs-fixes' in text_lower or 'требует исправлений' in text_lower or 'нужны исправления' in text_lower:
            return 'needs-fixes'
        elif 'ready' in text_lower or 'готов' in text_lower or 'merge' in text_lower:
            return 'ready-for-merge'
        else:
            return 'needs-review'


"""
Модуль для обучающей поддержки команды
"""
from typing import Dict, List, Optional, Any
import json
import os
from datetime import datetime


class EducationalSupport:
    """Обучающая поддержка для разработчиков"""
    
    def __init__(self, model):
        self.model = model
        self.learning_data_file = 'data/code_review_learning.json'
        self._ensure_data_file()
    
    def _ensure_data_file(self):
        """Создаёт файл для хранения данных обучения если его нет"""
        os.makedirs(os.path.dirname(self.learning_data_file), exist_ok=True)
        if not os.path.exists(self.learning_data_file):
            with open(self.learning_data_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'developers': {},
                    'common_issues': [],
                    'learning_resources': []
                }, f, ensure_ascii=False, indent=2)
    
    def generate_explanation(self, issue: str, code_snippet: str, 
                            developer_level: str = 'junior') -> Dict[str, Any]:
        """
        Генерирует объяснение проблемы для разработчика
        
        Args:
            issue: Описание проблемы
            code_snippet: Фрагмент кода с проблемой
            developer_level: Уровень разработчика
        
        Returns:
            Объяснение с обучающими материалами
        """
        prompt = f"""Ты ментор для разработчиков уровня {developer_level}. Объясни проблему в коде и научи как её исправить.

Проблема:
{issue}

Проблемный код:
```python
{code_snippet}
```

Предоставь объяснение в следующем формате:

1. ЧТО НЕ ТАК:
   - [Простое объяснение проблемы]

2. ПОЧЕМУ ЭТО ПРОБЛЕМА:
   - [Объяснение последствий]
   - [Примеры когда это может вызвать проблемы]

3. КАК ИСПРАВИТЬ:
   - [Пошаговое объяснение]
   - [Пример правильного кода]

4. ПОЧЕМУ ПРАВИЛЬНОЕ РЕШЕНИЕ ЛУЧШЕ:
   - [Преимущества правильного подхода]

5. BEST PRACTICES:
   - [Рекомендации как избежать в будущем]
   - [Полезные ресурсы для изучения]

6. ПРОВЕРЬ СЕБЯ:
   - [Вопросы для самопроверки]
   - [Упражнения]

Будь дружелюбным, понятным и мотивирующим. Используй простой язык."""
        
        try:
            response = self.model.generate_content(prompt)
            explanation_text = response.text if hasattr(response, 'text') else str(response)
            
            return {
                'explanation': explanation_text,
                'developer_level': developer_level,
                'success': True
            }
        except Exception as e:
            return {
                'error': f'Ошибка при генерации объяснения: {str(e)}',
                'developer_level': developer_level
            }
    
    def track_developer_progress(self, developer_id: str, issue_type: str, 
                                 resolved: bool) -> Dict[str, Any]:
        """
        Отслеживает прогресс разработчика
        
        Args:
            developer_id: ID разработчика
            issue_type: Тип проблемы
            resolved: Решена ли проблема
        
        Returns:
            Информация о прогрессе
        """
        try:
            with open(self.learning_data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if developer_id not in data['developers']:
                data['developers'][developer_id] = {
                    'issues_encountered': {},
                    'issues_resolved': {},
                    'total_issues': 0,
                    'resolved_count': 0,
                    'created_at': datetime.now().isoformat()
                }
            
            dev_data = data['developers'][developer_id]
            
            # Обновляем статистику
            if issue_type not in dev_data['issues_encountered']:
                dev_data['issues_encountered'][issue_type] = 0
            dev_data['issues_encountered'][issue_type] += 1
            
            if resolved:
                if issue_type not in dev_data['issues_resolved']:
                    dev_data['issues_resolved'][issue_type] = 0
                dev_data['issues_resolved'][issue_type] += 1
                dev_data['resolved_count'] += 1
            
            dev_data['total_issues'] += 1
            dev_data['updated_at'] = datetime.now().isoformat()
            
            # Сохраняем
            with open(self.learning_data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # Вычисляем прогресс
            progress = (dev_data['resolved_count'] / dev_data['total_issues'] * 100) if dev_data['total_issues'] > 0 else 0
            
            return {
                'developer_id': developer_id,
                'progress': progress,
                'total_issues': dev_data['total_issues'],
                'resolved_count': dev_data['resolved_count'],
                'success': True
            }
        except Exception as e:
            return {'error': f'Ошибка при отслеживании прогресса: {str(e)}'}
    
    def get_developer_stats(self, developer_id: str) -> Dict[str, Any]:
        """
        Получает статистику разработчика
        
        Args:
            developer_id: ID разработчика
        
        Returns:
            Статистика разработчика
        """
        try:
            with open(self.learning_data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if developer_id not in data['developers']:
                return {
                    'developer_id': developer_id,
                    'message': 'Статистика не найдена',
                    'total_issues': 0,
                    'resolved_count': 0,
                    'progress': 0
                }
            
            dev_data = data['developers'][developer_id]
            progress = (dev_data['resolved_count'] / dev_data['total_issues'] * 100) if dev_data['total_issues'] > 0 else 0
            
            return {
                'developer_id': developer_id,
                'total_issues': dev_data['total_issues'],
                'resolved_count': dev_data['resolved_count'],
                'progress': progress,
                'issues_encountered': dev_data['issues_encountered'],
                'issues_resolved': dev_data['issues_resolved'],
                'created_at': dev_data.get('created_at'),
                'updated_at': dev_data.get('updated_at')
            }
        except Exception as e:
            return {'error': f'Ошибка при получении статистики: {str(e)}'}
    
    def get_common_issues(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получает список наиболее частых проблем
        
        Args:
            limit: Количество проблем
        
        Returns:
            Список частых проблем
        """
        try:
            with open(self.learning_data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Собираем статистику по всем разработчикам
            issue_counts = {}
            for dev_id, dev_data in data['developers'].items():
                for issue_type, count in dev_data.get('issues_encountered', {}).items():
                    if issue_type not in issue_counts:
                        issue_counts[issue_type] = 0
                    issue_counts[issue_type] += count
            
            # Сортируем по частоте
            sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
            
            return [
                {'issue_type': issue_type, 'count': count}
                for issue_type, count in sorted_issues[:limit]
            ]
        except Exception as e:
            return [{'error': f'Ошибка при получении частых проблем: {str(e)}'}]


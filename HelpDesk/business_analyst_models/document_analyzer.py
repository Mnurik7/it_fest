"""
Модуль для анализа документов бизнес-аналитиком
"""
import json
import os
from typing import Dict, List, Optional


class DocumentAnalyzer:
    """Анализатор документов для извлечения бизнес-информации"""
    
    def __init__(self, model):
        self.model = model
    
    def analyze_document(self, document_text: str, document_type: Optional[str] = None) -> Dict:
        """
        Анализирует документ и извлекает ключевую информацию
        
        Args:
            document_text: Текст документа
            document_type: Тип документа (ТЗ, регламент, письмо и т.п.)
        
        Returns:
            Словарь с результатами анализа
        """
        # Определяем тип документа, если не указан
        if not document_type:
            document_type = self._detect_document_type(document_text)
        
        prompt = f"""Ты бизнес-аналитик в банке. Проанализируй следующий документ и извлеки ключевую информацию.

Тип документа: {document_type}

Текст документа:
{document_text}

Проведи анализ и предоставь результат в следующей структуре:

1. ТИП ДОКУМЕНТА: {document_type}

2. ЦЕЛЬ:
   - Основная цель документа
   - Бизнес-цели

3. ТРЕБОВАНИЯ:
   - Функциональные требования
   - Нефункциональные требования
   - Технические требования

4. БИЗНЕС-ПРАВИЛА:
   - Правила обработки
   - Ограничения
   - Условия

5. МЕТРИКИ И KPI:
   - Ключевые показатели
   - Метрики успеха

6. ОГРАНИЧЕНИЯ:
   - Технические ограничения
   - Бизнес-ограничения
   - Временные ограничения

7. КРАТКОЕ РЕЗЮМЕ:
   - Основные моменты документа

8. ПРОТИВОРЕЧИЯ И ПРОБЕЛЫ:
   - Найденные противоречия
   - Пробелы в информации
   - Неясности

9. ВОПРОСЫ ДЛЯ УТОЧНЕНИЯ:
   - Список вопросов для уточнения требований

Будь конкретным и структурированным. Используй формат с четкими заголовками и списками."""
        
        try:
            response = self.model.generate_content(prompt)
            analysis_text = response.text if hasattr(response, 'text') else str(response)
            
            # Парсим структурированный ответ
            structured_analysis = self._parse_analysis(analysis_text)
            structured_analysis['raw_analysis'] = analysis_text
            structured_analysis['document_type'] = document_type
            
            return structured_analysis
        except Exception as e:
            return {
                'error': str(e),
                'document_type': document_type,
                'raw_analysis': None
            }
    
    def _detect_document_type(self, text: str) -> str:
        """Определяет тип документа по содержимому"""
        text_lower = text.lower()
        
        type_keywords = {
            'ТЗ': ['техническое задание', 'тз', 'технические требования', 'спецификация'],
            'регламент': ['регламент', 'процедура', 'правила', 'инструкция'],
            'бизнес-описание': ['бизнес-процесс', 'бизнес-описание', 'описание процесса'],
            'письмо': ['уважаемый', 'письмо', 'обращение', 'просьба'],
            'требования': ['требования', 'requirements', 'требование'],
            'проект': ['проект', 'инициатива', 'задача']
        }
        
        for doc_type, keywords in type_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return doc_type
        
        return 'неизвестный'
    
    def _parse_analysis(self, analysis_text: str) -> Dict:
        """Парсит структурированный анализ из текста"""
        result = {
            'goal': '',
            'requirements': [],
            'business_rules': [],
            'metrics': [],
            'constraints': [],
            'summary': '',
            'contradictions': [],
            'gaps': [],
            'questions': []
        }
        
        # Простой парсинг по заголовкам
        lines = analysis_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Определяем секцию
            if 'ЦЕЛЬ' in line.upper() or 'ЦЕЛИ' in line.upper():
                current_section = 'goal'
            elif 'ТРЕБОВАНИЯ' in line.upper():
                current_section = 'requirements'
            elif 'БИЗНЕС-ПРАВИЛА' in line.upper() or 'ПРАВИЛА' in line.upper():
                current_section = 'business_rules'
            elif 'МЕТРИКИ' in line.upper() or 'KPI' in line.upper():
                current_section = 'metrics'
            elif 'ОГРАНИЧЕНИЯ' in line.upper():
                current_section = 'constraints'
            elif 'РЕЗЮМЕ' in line.upper():
                current_section = 'summary'
            elif 'ПРОТИВОРЕЧИЯ' in line.upper():
                current_section = 'contradictions'
            elif 'ПРОБЕЛЫ' in line.upper():
                current_section = 'gaps'
            elif 'ВОПРОСЫ' in line.upper():
                current_section = 'questions'
            else:
                # Добавляем содержимое в текущую секцию
                if current_section and line and not line.startswith('#'):
                    if current_section == 'goal':
                        result['goal'] += line + ' '
                    elif current_section == 'summary':
                        result['summary'] += line + ' '
                    elif current_section in ['requirements', 'business_rules', 'metrics', 
                                            'constraints', 'contradictions', 'gaps', 'questions']:
                        if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                            result[current_section].append(line.lstrip('-•* ').strip())
                        elif line and len(line) > 10:  # Не слишком короткие строки
                            result[current_section].append(line)
        
        # Очистка
        result['goal'] = result['goal'].strip()
        result['summary'] = result['summary'].strip()
        
        return result
    
    def find_contradictions(self, analysis: Dict) -> List[str]:
        """Находит противоречия в анализе"""
        contradictions = []
        
        # Проверяем требования на противоречия
        requirements = analysis.get('requirements', [])
        constraints = analysis.get('constraints', [])
        
        # Простая проверка на ключевые слова противоречий
        contradiction_keywords = ['противоречие', 'конфликт', 'несовместимо', 'невозможно']
        
        for req in requirements:
            if any(keyword in req.lower() for keyword in contradiction_keywords):
                contradictions.append(req)
        
        return contradictions or analysis.get('contradictions', [])


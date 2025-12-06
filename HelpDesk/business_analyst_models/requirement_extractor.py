"""
Модуль для извлечения требований из документов
"""
from typing import Dict, List, Optional


class RequirementExtractor:
    """Извлекает требования из документов"""
    
    def __init__(self, model):
        self.model = model
    
    def extract_requirements(self, document_text: str, context: Optional[Dict] = None) -> Dict:
        """
        Извлекает требования из документа
        
        Args:
            document_text: Текст документа
            context: Дополнительный контекст (заказчик, цель и т.д.)
        
        Returns:
            Словарь с извлеченными требованиями
        """
        context_str = ""
        if context:
            context_str = f"""
Контекст:
- Заказчик: {context.get('customer', 'не указан')}
- Цель использования: {context.get('purpose', 'не указана')}
- Для Confluence: {context.get('for_confluence', False)}
"""
        
        prompt = f"""Ты бизнес-аналитик. Извлеки требования из следующего документа.

{context_str}

Текст документа:
{document_text}

Извлеки и структурируй требования в следующем формате:

1. ФУНКЦИОНАЛЬНЫЕ ТРЕБОВАНИЯ:
   - [Список функциональных требований]

2. НЕФУНКЦИОНАЛЬНЫЕ ТРЕБОВАНИЯ:
   - Производительность
   - Безопасность
   - Масштабируемость
   - Надежность

3. БИЗНЕС-ТРЕБОВАНИЯ:
   - Бизнес-правила
   - Ограничения
   - Условия

4. ТЕХНИЧЕСКИЕ ТРЕБОВАНИЯ:
   - Технологии
   - Интеграции
   - Инфраструктура

Будь конкретным. Каждое требование должно быть четко сформулировано."""
        
        try:
            response = self.model.generate_content(prompt)
            requirements_text = response.text if hasattr(response, 'text') else str(response)
            
            # Парсим требования
            structured_requirements = self._parse_requirements(requirements_text)
            structured_requirements['raw_requirements'] = requirements_text
            
            return structured_requirements
        except Exception as e:
            return {
                'error': str(e),
                'functional': [],
                'non_functional': {},
                'business': [],
                'technical': []
            }
    
    def _parse_requirements(self, requirements_text: str) -> Dict:
        """Парсит требования из текста"""
        result = {
            'functional': [],
            'non_functional': {
                'performance': [],
                'security': [],
                'scalability': [],
                'reliability': []
            },
            'business': [],
            'technical': []
        }
        
        lines = requirements_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Определяем секцию
            if 'ФУНКЦИОНАЛЬНЫЕ' in line.upper():
                current_section = 'functional'
            elif 'НЕФУНКЦИОНАЛЬНЫЕ' in line.upper():
                current_section = 'non_functional'
            elif 'БИЗНЕС-ТРЕБОВАНИЯ' in line.upper() or 'БИЗНЕС' in line.upper():
                current_section = 'business'
            elif 'ТЕХНИЧЕСКИЕ' in line.upper():
                current_section = 'technical'
            elif 'ПРОИЗВОДИТЕЛЬНОСТЬ' in line.upper():
                current_section = 'performance'
            elif 'БЕЗОПАСНОСТЬ' in line.upper():
                current_section = 'security'
            elif 'МАСШТАБИРУЕМОСТЬ' in line.upper():
                current_section = 'scalability'
            elif 'НАДЕЖНОСТЬ' in line.upper():
                current_section = 'reliability'
            else:
                # Добавляем требование
                if current_section and line and not line.startswith('#'):
                    if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                        req_text = line.lstrip('-•* ').strip()
                    else:
                        req_text = line
                    
                    if req_text and len(req_text) > 5:
                        if current_section == 'functional':
                            result['functional'].append(req_text)
                        elif current_section == 'business':
                            result['business'].append(req_text)
                        elif current_section == 'technical':
                            result['technical'].append(req_text)
                        elif current_section in ['performance', 'security', 'scalability', 'reliability']:
                            result['non_functional'][current_section].append(req_text)
        
        return result
    
    def identify_gaps(self, requirements: Dict, analysis: Dict) -> List[str]:
        """Идентифицирует пробелы в требованиях"""
        gaps = []
        
        # Проверяем наличие обязательных разделов
        if not requirements.get('functional'):
            gaps.append("Отсутствуют функциональные требования")
        
        if not requirements.get('non_functional', {}).get('security'):
            gaps.append("Не указаны требования по безопасности")
        
        # Добавляем пробелы из анализа
        gaps.extend(analysis.get('gaps', []))
        
        return gaps


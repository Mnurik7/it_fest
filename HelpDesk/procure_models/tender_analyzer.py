"""
Модуль для анализа тендеров и извлечения ключевых параметров
"""
import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import google.generativeai as genai


class TenderAnalyzer:
    """Анализатор тендеров для извлечения структурированных данных"""
    
    def __init__(self, gemini_model):
        self.model = gemini_model
        
    def extract_tender_params(self, tender_text: str, source_type: str = "text") -> Dict[str, Any]:
        """
        Извлекает ключевые параметры тендера из текста
        
        Args:
            tender_text: Текст тендера (из PDF, веб-сайта, документа)
            source_type: Тип источника (text, pdf, web)
            
        Returns:
            Словарь с извлеченными параметрами
        """
        prompt = f"""Ты эксперт по анализу тендеров и закупок. Извлеки из следующего текста все ключевые параметры тендера.

Текст тендера:
{tender_text}

Извлеки и структурируй следующие параметры в формате JSON:

{{
    "customer": {{
        "name": "название заказчика",
        "type": "госструктура/компания/организация",
        "inn": "ИНН если указан",
        "address": "адрес"
    }},
    "subject": {{
        "description": "детальное описание предмета закупки",
        "quantity": "количество",
        "quality_requirements": "требования к качеству",
        "delivery_terms": "условия поставки",
        "deadlines": "сроки выполнения"
    }},
    "budget": {{
        "amount": "сумма бюджета",
        "currency": "валюта",
        "price_type": "лимит/диапазон/скрытая",
        "vat_included": true/false
    }},
    "participation_requirements": {{
        "licenses": ["список необходимых лицензий"],
        "experience": "требования к опыту",
        "certificates": ["список сертификатов"],
        "min_turnover": "минимальный оборот",
        "other_requirements": "другие требования"
    }},
    "timeline": {{
        "publication_date": "дата публикации",
        "application_start": "начало приема заявок",
        "application_end": "конец приема заявок",
        "evaluation_period": "период оценки",
        "contract_signing": "срок подписания договора"
    }},
    "application_requirements": {{
        "price": "требования к цене",
        "description": "требования к описанию",
        "documents": ["список необходимых документов"],
        "guarantee": "требования к гарантии",
        "delivery_time": "требования к срокам поставки"
    }},
    "evaluation_criteria": {{
        "price_weight": "вес цены в оценке",
        "quality_weight": "вес качества",
        "experience_weight": "вес опыта",
        "delivery_weight": "вес сроков",
        "guarantee_weight": "вес гарантии",
        "tz_compliance_weight": "вес соответствия ТЗ"
    }},
    "process": {{
        "selection_method": "метод выбора победителя",
        "commission": "информация о комиссии",
        "evaluation_process": "процесс оценки"
    }},
    "execution": {{
        "obligations": "обязательства по исполнению",
        "control": "контроль исполнения",
        "penalties": "штрафы и санкции",
        "acceptance": "процедура приемки"
    }},
    "metadata": {{
        "tender_id": "ID тендера если указан",
        "tender_number": "номер тендера",
        "source": "{source_type}",
        "extraction_date": "{datetime.now().isoformat()}"
    }}
}}

Верни ТОЛЬКО валидный JSON без дополнительных комментариев. Если какой-то параметр не найден, укажи null или пустую строку."""

        try:
            response = self.model.generate_content(prompt)
            if hasattr(response, 'text'):
                # Извлекаем JSON из ответа
                text = response.text.strip()
                
                # Убираем markdown форматирование
                if '```json' in text:
                    text = text.split('```json')[1].split('```')[0].strip()
                elif '```' in text:
                    parts = text.split('```')
                    for part in parts:
                        part = part.strip()
                        if part.startswith('{') or part.startswith('['):
                            text = part
                            break
                
                text = text.strip()
                
                # Пытаемся найти JSON в тексте
                if not text.startswith('{') and not text.startswith('['):
                    start_idx = text.find('{')
                    if start_idx == -1:
                        start_idx = text.find('[')
                    if start_idx != -1:
                        text = text[start_idx:]
                    end_idx = text.rfind('}')
                    if end_idx == -1:
                        end_idx = text.rfind(']')
                    if end_idx != -1:
                        text = text[:end_idx + 1]
                
                try:
                    result = json.loads(text)
                    return result
                except json.JSONDecodeError as json_err:
                    print(f"Ошибка парсинга JSON при извлечении параметров: {json_err}")
                    print(f"Текст ответа (первые 500 символов): {text[:500]}")
                    # Пытаемся исправить частые ошибки JSON
                    try:
                        import re
                        text = re.sub(r"'(\w+)':", r'"\1":', text)
                        text = re.sub(r":\s*'([^']*)'", r': "\1"', text)
                        result = json.loads(text)
                        return result
                    except:
                        return self._fallback_extraction(tender_text)
            else:
                return self._fallback_extraction(tender_text)
        except Exception as e:
            print(f"Ошибка при извлечении параметров: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_extraction(tender_text)
    
    def generate_tender_text(self, description: str) -> str:
        """
        Генерирует структурированный текст тендера на основе краткого описания
        
        Args:
            description: Краткое описание тендера или его параметров
            
        Returns:
            Структурированный текст тендера
        """
        prompt = f"""Ты эксперт по составлению текстов тендеров. На основе следующего описания создай полный, структурированный текст тендера.

Описание:
{description}

Создай детальный текст тендера, который включает:
- Название заказчика и его реквизиты
- Детальное описание предмета закупки
- Бюджет и условия оплаты
- Сроки подачи заявок и выполнения работ
- Требования к поставщику (лицензии, опыт, сертификаты)
- Критерии оценки заявок
- Условия поставки и гарантии
- Другие важные детали

Текст должен быть профессиональным, структурированным и содержать всю необходимую информацию для участия в тендере. Верни только текст тендера без дополнительных комментариев."""

        try:
            response = self.model.generate_content(prompt)
            if hasattr(response, 'text'):
                return response.text.strip()
            else:
                return self._fallback_tender_text(description)
        except Exception as e:
            print(f"Ошибка при генерации текста тендера: {e}")
            return self._fallback_tender_text(description)
    
    def improve_company_description(self, description: str) -> str:
        """
        Улучшает и расширяет описание компании для поиска партнёрств
        
        Args:
            description: Краткое описание компании
            
        Returns:
            Улучшенное и структурированное описание компании
        """
        prompt = f"""Ты эксперт по составлению описаний компаний для тендеров и партнёрств. Улучши и расширь следующее описание компании, сделав его профессиональным и привлекательным для потенциальных партнёров.

Исходное описание:
{description}

Создай улучшенное описание, которое включает:
- Название компании и её специализацию
- Опыт работы и достижения
- Сильные стороны и конкурентные преимущества
- Ключевые компетенции
- Примеры успешных проектов (если применимо)
- Готовность к партнёрству и сотрудничеству

Описание должно быть профессиональным, структурированным и убедительным. Верни только улучшенное описание без дополнительных комментариев."""

        try:
            response = self.model.generate_content(prompt)
            if hasattr(response, 'text'):
                return response.text.strip()
            else:
                return self._fallback_company_description(description)
        except Exception as e:
            print(f"Ошибка при улучшении описания компании: {e}")
            return self._fallback_company_description(description)
    
    def _fallback_company_description(self, description: str) -> str:
        """Простое улучшение описания если AI не сработал"""
        return f"""{description}

НАША КОМПАНИЯ:
- Опыт работы на рынке
- Профессиональная команда
- Качественное выполнение проектов
- Соблюдение сроков
- Гибкий подход к клиентам

МЫ ПРЕДЛАГАЕМ:
- Высокое качество услуг
- Конкурентные цены
- Надёжность и ответственность
- Индивидуальный подход

ГОТОВЫ К ПАРТНЁРСТВУ:
Мы открыты к сотрудничеству и совместным проектам."""
    
    def _fallback_tender_text(self, description: str) -> str:
        """Простой шаблон текста тендера если AI не сработал"""
        return f"""ТЕНДЕРНАЯ ДОКУМЕНТАЦИЯ

{description}

ОБЩАЯ ИНФОРМАЦИЯ О ЗАКАЗЧИКЕ:
[Укажите название, ИНН, адрес заказчика]

ПРЕДМЕТ ЗАКУПКИ:
[Детальное описание предмета закупки]

БЮДЖЕТ:
[Укажите сумму и валюту]

СРОКИ:
- Публикация: [дата]
- Начало приема заявок: [дата]
- Окончание приема заявок: [дата]
- Срок выполнения: [срок]

ТРЕБОВАНИЯ К УЧАСТНИКАМ:
- Лицензии: [требования]
- Опыт работы: [требования]
- Сертификаты: [требования]

КРИТЕРИИ ОЦЕНКИ:
- Цена: [вес]
- Качество: [вес]
- Опыт: [вес]

ДОКУМЕНТЫ ДЛЯ ПОДАЧИ:
[Список необходимых документов]

КОНТАКТНАЯ ИНФОРМАЦИЯ:
[Контактные данные для вопросов]"""
    
    def _fallback_extraction(self, tender_text: str) -> Dict[str, Any]:
        """Простое извлечение параметров через регулярные выражения если AI не сработал"""
        result = {
            "customer": {"name": "", "type": "", "inn": "", "address": ""},
            "subject": {"description": tender_text[:500], "quantity": "", "quality_requirements": "", "delivery_terms": "", "deadlines": ""},
            "budget": {"amount": "", "currency": "KZT", "price_type": "", "vat_included": False},
            "participation_requirements": {"licenses": [], "experience": "", "certificates": [], "min_turnover": "", "other_requirements": ""},
            "timeline": {"publication_date": "", "application_start": "", "application_end": "", "evaluation_period": "", "contract_signing": ""},
            "application_requirements": {"price": "", "description": "", "documents": [], "guarantee": "", "delivery_time": ""},
            "evaluation_criteria": {"price_weight": "", "quality_weight": "", "experience_weight": "", "delivery_weight": "", "guarantee_weight": "", "tz_compliance_weight": ""},
            "process": {"selection_method": "", "commission": "", "evaluation_process": ""},
            "execution": {"obligations": "", "control": "", "penalties": "", "acceptance": ""},
            "metadata": {"tender_id": "", "tender_number": "", "source": "text", "extraction_date": datetime.now().isoformat()}
        }
        
        # Простое извлечение через regex
        amount_match = re.search(r'(\d+[\s,.]?\d*)\s*(тенге|KZT|₸|руб|RUB|USD|доллар)', tender_text, re.IGNORECASE)
        if amount_match:
            result["budget"]["amount"] = amount_match.group(1)
            result["budget"]["currency"] = amount_match.group(2).upper()
        
        date_match = re.search(r'(\d{1,2}[./]\d{1,2}[./]\d{2,4})', tender_text)
        if date_match:
            result["timeline"]["application_end"] = date_match.group(1)
        
        return result
    
    def analyze_tender_completeness(self, tender_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Анализирует полноту информации о тендере
        
        Returns:
            Словарь с оценкой полноты и рекомендациями
        """
        required_fields = [
            ("customer.name", "Название заказчика"),
            ("subject.description", "Описание предмета закупки"),
            ("budget.amount", "Бюджет"),
            ("timeline.application_end", "Срок подачи заявок"),
            ("participation_requirements", "Требования к участию")
        ]
        
        missing_fields = []
        for field_path, field_name in required_fields:
            keys = field_path.split('.')
            value = tender_params
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    missing_fields.append(field_name)
                    break
                if not value or (isinstance(value, str) and not value.strip()):
                    missing_fields.append(field_name)
                    break
        
        completeness = (len(required_fields) - len(missing_fields)) / len(required_fields) * 100
        
        return {
            "completeness_percentage": round(completeness, 2),
            "missing_fields": list(set(missing_fields)),
            "status": "complete" if completeness >= 80 else "incomplete" if completeness >= 50 else "critical"
        }


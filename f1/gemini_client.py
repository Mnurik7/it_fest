import os
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Optional, Dict, List

load_dotenv()

class GeminiClient:
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        model_name = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
        api_version = os.getenv('GEMINI_API_VERSION', 'v1beta')
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY не найден в переменных окружения")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.api_version = api_version
    
    def detect_language(self, text: str) -> str:
        """Определение языка сообщения (казахский/русский)"""
        kazakh_chars = ['ә', 'ғ', 'қ', 'ң', 'ө', 'ұ', 'ү', 'һ', 'і']
        kazakh_words = ['жоқ', 'бар', 'жұмыс', 'жұмыс істемейді', 'қосылмайды', 'қате', 'көмек']
        
        text_lower = text.lower()
        kazakh_count = sum(1 for char in kazakh_chars if char in text_lower)
        kazakh_word_count = sum(1 for word in kazakh_words if word in text_lower)
        
        if kazakh_count > 0 or kazakh_word_count > 0:
            return 'kk'  # Казахский
        return 'ru'  # Русский
    
    def analyze_problem(self, user_message: str, conversation_history: Optional[List[Dict]] = None,
                       client_info: Optional[Dict] = None, outage_info: Optional[Dict] = None,
                       services_info: Optional[List[Dict]] = None) -> Dict:
        """
        Анализирует проблему пользователя и определяет:
        - тип проблемы
        - услугу (интернет/ТВ/телефон)
        - срочность
        - регион
        - может ли решить сам
        """
        # Определяем язык
        language = self.detect_language(user_message)
        
        # Формируем контекст из истории диалога
        context = ""
        if conversation_history:
            context = "\nИстория диалога:\n"
            for msg in reversed(conversation_history[-5:]):  # Последние 5 сообщений
                role = "Пользователь" if msg['is_user'] else "Бот"
                context += f"{role}: {msg['message']}\n"
        # Формируем контекст из истории диалога
        context = ""
        if conversation_history:
            context = "\nИстория диалога:\n"
            for msg in reversed(conversation_history[-5:]):  # Последние 5 сообщений
                role = "Пользователь" if msg['is_user'] else "Бот"
                context += f"{role}: {msg['message']}\n"
        
        # Формируем информацию о клиенте
        client_context = ""
        if client_info:
            client_context = f"""
Информация о клиенте:
- ФИО: {client_info.get('full_name', 'не указано')}
- Адрес: {client_info.get('city', '')}, {client_info.get('street', '')}, д. {client_info.get('house_number', '')}
- Номер договора: {client_info.get('contract_number', 'не указан')}
- Телефон: {client_info.get('phone_number', 'не указан')}
"""
            
            if services_info:
                client_context += "\nУслуги клиента:\n"
                for service in services_info:
                    status = "активна" if service.get('is_active') else "неактивна"
                    blocked = " (заблокирована" if service.get('is_blocked') else ""
                    debt = f", долг: {service.get('debt_amount', 0)} тг)" if service.get('is_blocked') else ""
                    client_context += f"- {service.get('tariff_name', 'не указан')}: {status}{blocked}{debt}\n"
        
        # Информация об аварии
        outage_context = ""
        if outage_info:
            from datetime import datetime
            estimated_end = outage_info.get('estimated_end', '')
            if estimated_end:
                try:
                    if isinstance(estimated_end, str):
                        estimated_end = datetime.fromisoformat(estimated_end.replace('Z', '+00:00'))
                    estimated_str = estimated_end.strftime('%H:%M')
                except:
                    estimated_str = str(estimated_end)
            else:
                estimated_str = "уточняется"
            
            outage_context = f"""
⚠️ ВАЖНО: В районе клиента активна авария!
- Причина: {outage_info.get('reason', 'не указана')}
- Начало: {outage_info.get('started_at', 'не указано')}
- Планируемое восстановление: до {estimated_str}
- Узел: {outage_info.get('node_name', 'не указан')}

Если клиент жалуется на отсутствие интернета/ТВ/телефонии, это скорее всего связано с аварией.
"""
        
        # Определяем язык для ответа
        lang_prompt = "Отвечай на казахском языке." if language == 'kk' else "Отвечай на русском языке."
        
        prompt = f"""Ты - умный помощник службы поддержки Казахтелекома. 
{lang_prompt}

Твоя задача - проанализировать обращение клиента и определить:

1. **Тип проблемы**: авария / техническая проблема / настройка / оплата / другое
2. **Услуга**: интернет / телевидение / телефония / все услуги
3. **Срочность**: низкая / средняя / высокая / критическая
4. **Регион/город**: извлеки название города из сообщения (если указан)
5. **Может ли решить сам**: true/false (может ли клиент решить проблему самостоятельно)
6. **Нужен ли инженер**: true/false

{client_context}
{outage_context}
{context}

Обращение клиента: {user_message}

ВАЖНО: Если в районе клиента есть активная авария (указано выше), и проблема связана с отсутствием услуги - 
это скорее всего связано с аварией. В этом случае НЕ создавай заявку, а сообщи об аварии.

Ответь в формате JSON:
{{
    "problem_type": "тип проблемы (авария/техническая/настройка/оплата/другое)",
    "service": "услуга (интернет/телевидение/телефония/все)",
    "urgency": "срочность (низкая/средняя/высокая/критическая)",
    "city": "город из сообщения или null",
    "can_solve_self": true/false,
    "needs_engineer": true/false,
    "category": "категория (интернет/телефония/телевидение/оборудование/оплата/другое)",
    "solution": "подробное решение или инструкция",
    "engineer_specialization": "специализация инженера (если needs_engineer = true, иначе null)",
    "diagnostic_steps": ["шаг 1", "шаг 2", "шаг 3"] - пошаговые действия для диагностики (если can_solve_self = true)
}}

Если проблема простая и может быть решена самостоятельно, предложи пошаговое решение.
Если проблема сложная или требует вмешательства инженера, укажи needs_engineer = true."""
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Пытаемся извлечь JSON из ответа
            import json
            import re
            
            # Ищем JSON в ответе (поддерживаем вложенные объекты)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group()
                    # Очищаем от markdown форматирования если есть
                    json_str = json_str.replace('```json', '').replace('```', '').strip()
                    result = json.loads(json_str)
                    # Проверяем наличие обязательных полей
                    if 'problem_type' not in result:
                        result['problem_type'] = 'другое'
                    if 'service' not in result:
                        result['service'] = 'интернет'
                    if 'urgency' not in result:
                        result['urgency'] = 'средняя'
                    if 'city' not in result:
                        result['city'] = None
                    if 'can_solve_self' not in result:
                        result['can_solve_self'] = False
                    if 'category' not in result:
                        result['category'] = result.get('problem_type', 'другое')
                    if 'solution' not in result:
                        result['solution'] = response_text
                    if 'needs_engineer' not in result:
                        result['needs_engineer'] = True
                    if 'engineer_specialization' not in result:
                        result['engineer_specialization'] = 'общая поддержка'
                    if 'diagnostic_steps' not in result:
                        result['diagnostic_steps'] = []
                    
                    # Добавляем язык
                    result['language'] = language
                except json.JSONDecodeError:
                    # Если JSON невалидный, создаем структурированный ответ
                    result = {
                        "category": "другое",
                        "solution": response_text,
                        "needs_engineer": True,
                        "engineer_specialization": "общая поддержка"
                    }
            else:
                # Если JSON не найден, создаем структурированный ответ
                result = {
                    "category": "другое",
                    "solution": response_text,
                    "needs_engineer": True,
                    "engineer_specialization": "общая поддержка"
                }
            
            return result
        except Exception as e:
            print(f"Ошибка при обращении к Gemini API: {e}")
            return {
                "category": "другое",
                "solution": "Извините, произошла ошибка при обработке вашего запроса. Обращение передано инженеру.",
                "needs_engineer": True,
                "engineer_specialization": "общая поддержка"
            }
    
    def generate_response(self, user_message: str, context: Optional[str] = None) -> str:
        """
        Генерирует ответ пользователю на основе его сообщения
        """
        system_prompt = """Ты - вежливый и профессиональный помощник службы поддержки Казахтелекома.
Отвечай кратко, по делу, на русском языке. Будь дружелюбным и готовым помочь."""
        
        if context:
            prompt = f"{system_prompt}\n\nКонтекст: {context}\n\nВопрос клиента: {user_message}\n\nОтвет:"
        else:
            prompt = f"{system_prompt}\n\nВопрос клиента: {user_message}\n\nОтвет:"
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Ошибка при генерации ответа: {e}")
            return "Извините, произошла ошибка. Пожалуйста, попробуйте еще раз или обратитесь к инженеру."


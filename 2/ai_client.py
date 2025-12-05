import os
import json
import logging
import requests
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Настройки из переменных окружения
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
GEMINI_API_VERSION = os.getenv('GEMINI_API_VERSION', 'v1beta')

# Формируем URL для Gemini API
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/{GEMINI_API_VERSION}/models/{GEMINI_MODEL}:generateContent"


def analyze_ticket(text: str) -> Dict:
    """
    Анализирует текст обращения через Gemini API.
    Возвращает структурированный ответ с категоризацией.
    
    Args:
        text: Текст обращения пользователя
        
    Returns:
        dict с полями:
        - language: ru/kk
        - summary: краткое резюме
        - category: категория проблемы
        - priority: LOW/MEDIUM/HIGH/CRITICAL
        - type: INCIDENT/REQUEST/QUESTION/COMPLAINT
        - department: предлагаемый отдел
        - auto_resolve: можно ли закрыть автоматически
        - auto_response: текст автоответа (если auto_resolve=True)
        - error: сообщение об ошибке (если была)
    """
    
    # Если API ключ не задан, возвращаем fallback
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set, using fallback response")
        return _get_fallback_response(text)
    
    # Формируем промпт для Gemini
    prompt = f"""Ты — AI-ассистент для Help Desk системы. Проанализируй следующее обращение пользователя и верни ответ в формате JSON.

Обращение пользователя:
{text}

Верни JSON со следующими полями:
{{
  "language": "ru" или "kk" (определи язык обращения),
  "summary": "краткое резюме обращения на языке пользователя (1-2 предложения)",
  "category": "одна из категорий: доступ, почта, сеть, ПО, оборудование, учетные записи, безопасность, другое",
  "priority": "LOW" или "MEDIUM" или "HIGH" или "CRITICAL" (оцени критичность),
  "type": "INCIDENT" или "REQUEST" или "QUESTION" или "COMPLAINT",
  "department": "IT" или "Security" или "HR" или "Finance" или "Other",
  "auto_resolve": true или false (можно ли ответить автоматически на типовой вопрос),
  "auto_response": "текст ответа на языке пользователя, если auto_resolve=true, иначе пустая строка",
  "advice": "подробный совет или инструкция как решить проблему на языке пользователя (даже если auto_resolve=false, дай полезный совет)"
}}

Правила:
- Если это простой вопрос (например, "как сбросить пароль?", "где найти инструкцию?"), то auto_resolve=true
- Если это инцидент, требующий действий (например, "не работает почта", "заблокирован доступ"), то auto_resolve=false
- В поле "advice" ВСЕГДА дай полезный совет или инструкцию, как можно решить проблему самостоятельно (даже если требуется помощь специалиста)
- Ответ должен быть на том же языке, что и обращение
- Будь точным в определении приоритета: критический только для серьезных сбоев, влияющих на работу многих пользователей
- В поле "advice" дай конкретные шаги, что можно попробовать сделать самостоятельно
"""
    
    try:
        # Формируем запрос к Gemini API
        headers = {
            'Content-Type': 'application/json',
        }
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 1024,
            }
        }
        
        url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
        
        # Отправляем запрос с таймаутом
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Извлекаем текст ответа из структуры Gemini
        if 'candidates' in data and len(data['candidates']) > 0:
            content = data['candidates'][0].get('content', {})
            parts = content.get('parts', [])
            if parts and 'text' in parts[0]:
                ai_text = parts[0]['text'].strip()
                
                # Пытаемся извлечь JSON из ответа
                # Gemini может вернуть JSON в markdown блоках или просто текст
                json_text = _extract_json_from_text(ai_text)
                
                if json_text:
                    result = json.loads(json_text)
                    result['ai_raw_response'] = ai_text
                    return result
                else:
                    logger.error(f"Could not parse JSON from Gemini response: {ai_text}")
                    return _get_fallback_response(text, error="Could not parse AI response")
        
        logger.error(f"Unexpected Gemini API response structure: {data}")
        return _get_fallback_response(text, error="Unexpected API response")
        
    except requests.exceptions.Timeout:
        logger.error("Gemini API request timeout")
        return _get_fallback_response(text, error="API timeout")
    except requests.exceptions.RequestException as e:
        logger.error(f"Gemini API request failed: {e}")
        return _get_fallback_response(text, error=f"API error: {str(e)}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return _get_fallback_response(text, error="JSON parse error")
    except Exception as e:
        logger.error(f"Unexpected error in analyze_ticket: {e}")
        return _get_fallback_response(text, error=f"Unexpected error: {str(e)}")


def _extract_json_from_text(text: str) -> Optional[str]:
    """Извлекает JSON из текста ответа (может быть в markdown блоках)"""
    import re
    
    # Пытаемся найти JSON в markdown блоках ```json ... ```
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        return json_match.group(1)
    
    # Пытаемся найти JSON объект напрямую
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        return json_match.group(0)
    
    return None


def _get_fallback_response(text: str, error: Optional[str] = None) -> Dict:
    """
    Возвращает fallback ответ, если AI недоступен.
    Простая эвристика для базовой категоризации.
    """
    text_lower = text.lower()
    
    # Определяем язык (простая эвристика)
    language = "ru"
    if any(word in text_lower for word in ["қалай", "қандай", "не", "керек"]):
        language = "kk"
    
    # Определяем категорию
    category = "другое"
    if any(word in text_lower for word in ["пароль", "доступ", "логин", "аккаунт"]):
        category = "учетные записи"
    elif any(word in text_lower for word in ["почта", "email", "электрон"]):
        category = "почта"
    elif any(word in text_lower for word in ["сеть", "интернет", "подключ"]):
        category = "сеть"
    elif any(word in text_lower for word in ["программа", "приложение", "софт"]):
        category = "ПО"
    
    # Определяем тип
    ticket_type = "QUESTION"
    if any(word in text_lower for word in ["не работает", "сломал", "ошибка", "проблема"]):
        ticket_type = "INCIDENT"
    elif any(word in text_lower for word in ["нужно", "требуется", "запрос"]):
        ticket_type = "REQUEST"
    elif any(word in text_lower for word in ["жалоба", "недоволен"]):
        ticket_type = "COMPLAINT"
    
    # Определяем приоритет
    priority = "MEDIUM"
    if any(word in text_lower for word in ["срочно", "критично", "не работает", "все"]):
        priority = "HIGH"
    elif any(word in text_lower for word in ["вопрос", "как", "где"]):
        priority = "LOW"
    
    # Определяем отдел
    department = "IT"
    if any(word in text_lower for word in ["безопасность", "security"]):
        department = "Security"
    
    # Простые вопросы можно авто-решить
    auto_resolve = False
    auto_response = ""
    advice = ""
    
    if any(word in text_lower for word in ["как", "где", "инструкция", "помощь"]):
        auto_resolve = True
        if language == "ru":
            auto_response = "Спасибо за обращение! Мы получили ваш запрос и обработаем его в ближайшее время. Если это срочный вопрос, пожалуйста, свяжитесь с поддержкой по телефону."
            advice = "Попробуйте найти ответ в базе знаний или документации. Если проблема не решается, обратитесь к специалисту."
        else:
            auto_response = "Сіздің сұрауыңызды алдық. Біз оны жақын арада өңдейміз. Шұғыл сұрау болса, қолдау қызметіне телефон арқылы хабарласыңыз."
            advice = "Білім базасында немесе құжаттамада жауапты табуға тырысыңыз. Мәселе шешілмесе, маманға хабарласыңыз."
    else:
        if language == "ru":
            advice = "Попробуйте перезагрузить систему, проверить подключение к интернету или перезапустить приложение. Если проблема сохраняется, обратитесь к специалисту."
        else:
            advice = "Жүйені қайта жүктеуге, интернет байланысын тексеруге немесе қолданбаны қайта іске қосуға тырысыңыз. Мәселе сақталса, маманға хабарласыңыз."
    
    result = {
        "language": language,
        "summary": text[:200] + "..." if len(text) > 200 else text,
        "category": category,
        "priority": priority,
        "type": ticket_type,
        "department": department,
        "auto_resolve": auto_resolve,
        "auto_response": auto_response,
        "advice": advice,
    }
    
    if error:
        result["error"] = error
    
    return result


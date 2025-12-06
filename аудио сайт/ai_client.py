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
    prompt = f"""Ты — AI-ассистент для Help Desk системы. Твоя главная задача — ВСЕГДА находить решение проблемы пользователя, независимо от сложности и типа проблемы.

Обращение пользователя:
{text}

ВАЖНО: Проблема может быть ЛЮБОЙ - IT-проблема, вопрос о здоровье, бытовой вопрос, вопрос о работе и т.д. 
Для ЛЮБОЙ проблемы дай полезный совет и решение, даже если это не IT-проблема.

Верни JSON со следующими полями:
{{
  "language": "ru" или "kk" (определи язык обращения),
  "summary": "краткое резюме обращения на языке пользователя (1-2 предложения)",
  "category": "одна из категорий: доступ, почта, сеть, ПО, оборудование, учетные записи, безопасность, здоровье, быт, работа, другое (выбери наиболее подходящую)",
  "priority": "LOW" или "MEDIUM" или "HIGH" или "CRITICAL" (оцени критичность - для проблем со здоровьем обычно HIGH или CRITICAL),
  "type": "INCIDENT" или "REQUEST" или "QUESTION" или "COMPLAINT",
  "department": "IT" или "Security" или "HR" или "Finance" или "Medical" или "Other" (выбери наиболее подходящий отдел),
  "auto_resolve": true или false (можно ли ответить автоматически на типовой вопрос),
  "auto_response": "текст ответа на языке пользователя, если auto_resolve=true, иначе пустая строка",
  "advice": "ОБЯЗАТЕЛЬНО: подробное пошаговое решение проблемы на языке пользователя. Дай КОНКРЕТНОЕ решение, даже если проблема сложная. НИКОГДА не оставляй это поле пустым! Для проблем со здоровьем дай конкретные рекомендации (что делать, когда обратиться к врачу, какие симптомы опасны). Для IT-проблем - технические шаги. Для любых других проблем - соответствующие рекомендации."
}}

КРИТИЧЕСКИ ВАЖНЫЕ ПРАВИЛА ДЛЯ ПОЛЯ "advice" (РЕШЕНИЕ ПРОБЛЕМЫ):

1. ОБЯЗАТЕЛЬНО дай УНИКАЛЬНОЕ решение для ЭТОЙ конкретной проблемы - НЕ используй шаблонные ответы
2. Внимательно прочитай описание проблемы и дай решение, специфичное именно для этой ситуации
3. НИКОГДА не используй готовые шаблоны - каждая проблема уникальна и требует индивидуального подхода
4. НИКОГДА не пиши "обратитесь к специалисту" или "нужна помощь IT" - дай максимально конкретные шаги
5. Для ЛЮБОЙ проблемы дай пошаговую инструкцию с нумерованными шагами, адаптированную под описанную ситуацию
6. Если проблема требует диагностики - дай ПОЛНУЮ инструкцию диагностики с конкретными командами/действиями для ЭТОЙ проблемы
7. Если проблема требует доступа к системам - опиши КАК получить доступ и ЧТО делать дальше в контексте описанной проблемы
8. Если проблема с оборудованием - дай ТОЧНЫЕ шаги для ЭТОГО конкретного оборудования: какие кнопки, какие индикаторы, какие настройки
9. Если проблема с ПО - дай ТОЧНЫЕ шаги для ЭТОЙ конкретной программы: какие команды, какие настройки, куда зайти, что изменить
10. Если проблема с сетью - дай КОНКРЕТНЫЕ команды для ЭТОЙ сетевой проблемы: ping, ipconfig, route, и т.д. с примерами
11. Если проблема с доступом - опиши КАК восстановить доступ для ЭТОЙ конкретной ситуации, КУДА обратиться, ЧТО проверить
12. Используй нумерованные списки (1., 2., 3., ...) для всех шагов
13. Будь максимально конкретным - указывай точные пути, команды, названия кнопок, меню, специфичные для описанной проблемы
14. Если проблема может иметь несколько причин - опиши диагностику для каждой причины, упомянутой в описании
15. Дай решение на том же языке, что и обращение пользователя
16. ВАЖНО: анализируй КАЖДУЮ проблему индивидуально - одинаковые проблемы могут иметь разные решения в зависимости от контекста

ВАЖНО: НЕ используй эти примеры как шаблоны! Каждая проблема уникальна и требует индивидуального анализа.

ПРИМЕРЫ ПРАВИЛЬНОГО ПОДХОДА (НЕ шаблоны!):

Проблема: "Не работает интернет"
ПЛОХО (шаблонный ответ): "Проверьте подключение к интернету. Если не поможет, обратитесь к IT."
ПЛОХО (готовый шаблон): "1. Откройте командную строку. 2. Выполните ping 8.8.8.8. 3. Выполните ipconfig /release..."
ХОРОШО (уникальное решение): Анализируй КОНКРЕТНУЮ ситуацию: какой тип подключения (Wi-Fi/Ethernet), какая ОС, какие ошибки видны, когда началась проблема, что изменилось. Дай решение для ЭТОЙ конкретной ситуации.

Проблема: "Не включается ноутбук"
ПЛОХО (шаблонный ответ): "Попробуйте перезагрузить ноутбук."
ПЛОХО (готовый шаблон): "1. Проверьте индикатор питания. 2. Нажмите кнопку питания..."
ХОРОШО (уникальное решение): Анализируй КОНКРЕТНУЮ ситуацию: какая модель ноутбука, что происходит при нажатии кнопки питания (ничего/мигает индикатор/звук), когда последний раз работал, что делали перед этим. Дай решение для ЭТОЙ конкретной модели и ситуации.

ПРАВИЛО: ВСЕГДА анализируй описание проблемы и давай решение, специфичное для описанной ситуации. НЕ используй готовые шаблоны!

Правила для других полей:
- Если это простой вопрос (например, "как сбросить пароль?", "где найти инструкцию?"), то auto_resolve=true
- Если это инцидент, требующий действий (например, "не работает почта", "заблокирован доступ"), то auto_resolve=false
- Ответ должен быть на том же языке, что и обращение
- Будь точным в определении приоритета: критический только для серьезных сбоев, влияющих на работу многих пользователей
- В поле "auto_response" (если auto_resolve=true) дай КОНКРЕТНЫЙ ответ на вопрос, а не общие слова
- ПОМНИ: поле "advice" должно ВСЕГДА содержать решение, даже если проблема очень сложная - дай хотя бы начальные шаги диагностики и решения
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
                "maxOutputTokens": 4096,
                "topP": 0.95,
                "topK": 40,
            }
        }
        
        url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
        
        # Отправляем запрос с таймаутом
        logger.info(f"Sending request to Gemini API for text: {text[:100]}...")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Gemini API response received, status: {response.status_code}")
        
        # Извлекаем текст ответа из структуры Gemini
        if 'candidates' in data and len(data['candidates']) > 0:
            content = data['candidates'][0].get('content', {})
            parts = content.get('parts', [])
            if parts and 'text' in parts[0]:
                ai_text = parts[0]['text'].strip()
                logger.info(f"Gemini response text length: {len(ai_text)}")
                
                # Пытаемся извлечь JSON из ответа
                # Gemini может вернуть JSON в markdown блоках или просто текст
                json_text = _extract_json_from_text(ai_text)
                
                if json_text:
                    result = json.loads(json_text)
                    result['ai_raw_response'] = ai_text
                    logger.info(f"Successfully parsed Gemini response, advice length: {len(result.get('advice', ''))}")
                    return result
                else:
                    logger.error(f"Could not parse JSON from Gemini response. Response text: {ai_text[:500]}")
                    return _get_fallback_response(text, error="Could not parse AI response")
        
        logger.error(f"Unexpected Gemini API response structure: {data}")
        return _get_fallback_response(text, error="Unexpected API response")
        
    except requests.exceptions.Timeout:
        logger.error("Gemini API request timeout")
        return _get_fallback_response(text, error="API timeout")
    except requests.exceptions.RequestException as e:
        logger.error(f"Gemini API request failed: {e}")
        logger.error(f"Response status: {e.response.status_code if hasattr(e, 'response') and e.response else 'N/A'}")
        logger.error(f"Response text: {e.response.text[:500] if hasattr(e, 'response') and e.response else 'N/A'}")
        return _get_fallback_response(text, error=f"API error: {str(e)}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return _get_fallback_response(text, error="JSON parse error")
    except Exception as e:
        logger.error(f"Unexpected error in analyze_ticket: {e}", exc_info=True)
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
    
    # Даем базовый полезный совет даже в fallback режиме
    auto_resolve = False
    auto_response = ""
    advice = ""
    
    # Анализируем проблему и даем базовый совет
    text_lower = text.lower()
    
    if any(word in text_lower for word in ["болит", "боль", "голова", "головная", "ауру", "сыздау"]):
        if language == "ru":
            advice = """1. Измерьте температуру тела - если выше 38°C, это может быть признаком инфекции.
2. Примите обезболивающее (парацетамол или ибупрофен) согласно инструкции, если нет противопоказаний.
3. Обеспечьте покой: прилягте в темной тихой комнате, закройте глаза.
4. Приложите холодный компресс ко лбу или затылку на 15-20 минут.
5. Выпейте воды - обезвоживание может усиливать головную боль.
6. Если боль сильная, не проходит более 24 часов, сопровождается тошнотой, рвотой, нарушением зрения или высокой температурой - НЕМЕДЛЕННО обратитесь к врачу или вызовите скорую помощь.
7. Если это повторяющаяся проблема - запишитесь на прием к неврологу или терапевту."""
        else:
            advice = """1. Дене температурасын өлшеңіз - егер 38°C-дан жоғары болса, бұл инфекция белгісі болуы мүмкін.
2. Егер қарсы көрсеткіштер болмаса, нұсқау бойынша ауруды басатын дәрі (парацетамол немесе ибупрофен) қабылдаңыз.
3. Демалуды қамтамасыз етіңіз: қараңғы, тыныш бөлмеде жатқызып, көздерді жұмыңыз.
4. Маңдайға немесе затылқаға 15-20 минутқа салқын компресс қойыңыз.
5. Су ішіңіз - сусыздану бас ауруыңызды күшейте алады.
6. Егер ауру күшті болса, 24 сағаттан астам өтпейді, жүрек айну, құсу, көру бұзылуы немесе жоғары температурамен бірге болса - ДЕРТЕЗЕ дәрігерге хабарласыңыз немесе жедел жәрдем шақырыңыз.
7. Егер бұл қайталанатын мәселе болса - невролог немесе терапевтке жаздырыңыз."""
    elif any(word in text_lower for word in ["не работает", "ошибка", "проблема", "не могу"]):
        if language == "ru":
            advice = f"Проблема требует детального анализа. Категория: {category}. Приоритет: {priority}. Опишите проблему подробнее: что именно не работает, когда началось, какие ошибки видите, что пробовали сделать. Это поможет быстрее найти решение."
        else:
            advice = f"Мәселе толық талдауды талап етеді. Категория: {category}. Басымдық: {priority}. Мәселені толығырақ сипаттаңыз: нақты не жұмыс істемейді, қашан басталды, қандай қателер көрінеді, не істеуге тырыстыңыз. Бұл шешімді тезірек табуға көмектеседі."
    else:
        if language == "ru":
            advice = f"Спасибо за обращение! Ваш запрос получен. Категория: {category}. Приоритет: {priority}. Специалист проанализирует вашу проблему и предоставит решение. Если это срочно - опишите проблему подробнее или свяжитесь с поддержкой."
        else:
            advice = f"Сіздің сұрауыңызды алдық! Рахмет. Категория: {category}. Басымдық: {priority}. Маман сіздің мәселеңізді талдап, шешім ұсынады. Егер бұл шұғыл болса - мәселені толығырақ сипаттаңыз немесе қолдау қызметіне хабарласыңыз."
    
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


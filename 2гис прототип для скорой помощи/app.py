from flask import Flask, render_template, jsonify, request
import os
from dotenv import load_dotenv
import requests
import math

load_dotenv()

app = Flask(__name__)

# Загружаем API ключи из .env
DGIS_API_KEY = os.getenv('DGIS_API_KEY', '')
TGIS_API_KEY = os.getenv('TGIS_API_KEY', '')
YANDEX_MAPS_API_KEY = os.getenv('YANDEX_MAPS_API_KEY', '95e511f0-870b-4635-8470-a1b3b77b614b')  # Для карты
YANDEX_SEARCH_API_KEY = os.getenv('YANDEX_SEARCH_API_KEY', 'cf74351f-8cd8-4d19-864b-be2bd33c9b2c')  # Для поиска организаций
YANDEX_GEOCODER_API_KEY = os.getenv('YANDEX_GEOCODER_API_KEY', '34b963ab-0af1-475f-967e-36a9c7687d9e')  # Для геокодирования и маршрутов
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

# Настройка Gemini AI (условный импорт из-за проблем совместимости с Python 3.14)
GEMINI_AVAILABLE = False
genai = None

if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        GEMINI_AVAILABLE = True
        print("[INFO] Gemini AI успешно инициализирован")
    except ImportError as e:
        print(f"[WARNING] Библиотека google-generativeai не установлена или несовместима: {e}")
        print("[INFO] Чат-бот будет работать без AI (с простыми ответами)")
        GEMINI_AVAILABLE = False
    except Exception as e:
        print(f"[WARNING] Ошибка настройки Gemini AI: {e}")
        print("[INFO] Чат-бот будет работать без AI (с простыми ответами)")
        GEMINI_AVAILABLE = False
else:
    print("[INFO] GEMINI_API_KEY не настроен. Чат-бот будет работать без AI")

@app.route('/')
def index():
    """Главная страница с картой"""
    return render_template('index.html', yandex_maps_api_key=YANDEX_MAPS_API_KEY)

@app.route('/api/search')
def search():
    """API endpoint для поиска объектов на карте"""
    query = request.args.get('q', '')
    type_filter = request.args.get('type', '')
    city = request.args.get('city', 'Алматы')
    
    # Используем Yandex Search API для поиска организаций
    yandex_search_key = YANDEX_SEARCH_API_KEY
    dgis_key = DGIS_API_KEY or TGIS_API_KEY
    
    # Приоритет Yandex Search API, если есть ключ
    use_yandex_search = bool(yandex_search_key)
    
    if not yandex_search_key and not dgis_key:
        return jsonify({'error': 'API ключ не настроен. Проверьте файл .env'}), 500
    
    # Маппинг типов на поисковые запросы
    # Используем текстовый поиск, так как rubric_id могут отличаться в разных регионах
    type_queries = {
        'hospital': 'больница',
        'pharmacy': 'аптека',
        'clinic': 'клиника',
        'ambulance': 'скорая помощь',
        'dentist': 'стоматология',
        'veterinary': 'ветеринарная клиника'
    }
    
    # Формируем поисковый запрос
    search_query = query
    if not search_query and type_filter:
        search_query = type_queries.get(type_filter, type_filter)
    if not search_query:
        search_query = 'медицинские учреждения'
    
    # Координаты центра Алматы
    almaty_center = {'lat': 43.2220, 'lon': 76.8512}
    
    # Пробуем несколько вариантов API
    urls_to_try = []
    
    # Если есть Yandex Search API ключ, используем его в первую очередь
    if yandex_search_key:
        # Yandex Search API для поиска организаций
        urls_to_try.append({
            'url': 'https://search-maps.yandex.ru/v1/',
            'params': {
                'apikey': yandex_search_key,
                'text': f"{search_query}, Алматы",
                'type': 'biz',
                'll': f"{almaty_center['lon']},{almaty_center['lat']}",
                'spn': '0.3,0.3',  # Область поиска
                'results': 50,
                'lang': 'ru_RU',
                'format': 'json'
            },
            'api_type': 'yandex'
        })
        
        # Альтернативный вариант Yandex - без указания координат
        urls_to_try.append({
            'url': 'https://search-maps.yandex.ru/v1/',
            'params': {
                'apikey': yandex_search_key,
                'text': f"{search_query}, Алматы, Казахстан",
                'type': 'biz',
                'results': 50,
                'lang': 'ru_RU',
                'format': 'json'
            },
            'api_type': 'yandex'
        })
    
    # Если есть 2GIS ключ, добавляем варианты с 2GIS как запасной вариант
    if dgis_key:
        # Вариант 1: Поиск по текстовому запросу с region_id (основной)
        urls_to_try.append({
            'url': 'https://catalog.api.2gis.ru/3.0/items',
            'params': {
                'q': search_query,
                'key': dgis_key,
                'region_id': 64,  # Алматы
                'fields': 'items.point,items.name,items.type,items.address_name,items.rubrics',
                'page_size': 50,
                'locale': 'ru_RU'
            },
            'api_type': '2gis'
        })
        
        # Вариант 2: Поиск по координатам и радиусу
        urls_to_try.append({
            'url': 'https://catalog.api.2gis.ru/3.0/items',
            'params': {
                'q': search_query,
                'key': dgis_key,
                'point': f"{almaty_center['lon']},{almaty_center['lat']}",
                'radius': 20000,  # 20 км
                'fields': 'items.point,items.name,items.type,items.address_name,items.rubrics',
                'page_size': 50,
                'locale': 'ru_RU'
            },
            'api_type': '2gis'
        })
    
    last_error = None
    
    for attempt, api_config in enumerate(urls_to_try):
        url = api_config['url']
        params = api_config['params']
        api_type = api_config.get('api_type', '2gis')
        
        try:
            print(f"[DEBUG] Попытка {attempt + 1}: {url} ({api_type})")
            print(f"[DEBUG] Параметры: {params}")
            
            response = requests.get(url, params=params, timeout=10)
            print(f"[DEBUG] Статус: {response.status_code}")
            
            # Выводим первые 500 символов ответа для отладки
            response_text = response.text[:500]
            print(f"[DEBUG] Ответ (первые 500 символов): {response_text}")
            
            response.raise_for_status()
            data = response.json()
            
            print(f"[DEBUG] Структура ответа: {list(data.keys())}")
            
            # Обрабатываем результаты
            results = []
            items = []
            
            # Обработка ответа Yandex Search API
            if api_type == 'yandex':
                if 'features' in data:
                    items = data['features']
                elif 'results' in data:
                    items = data['results']
                
                for item in items:
                    # Yandex API структура
                    geometry = item.get('geometry', {})
                    properties = item.get('properties', {})
                    company_meta = properties.get('CompanyMetaData', {})
                    
                    # Получаем координаты
                    if geometry.get('type') == 'Point' and 'coordinates' in geometry:
                        coords = geometry['coordinates']
                        lon, lat = coords[0], coords[1]
                        
                        # Получаем название
                        name = properties.get('name', company_meta.get('name', 'Без названия'))
                        
                        # Получаем адрес
                        address = company_meta.get('address', '')
                        if not address:
                            address = properties.get('description', 'Адрес не указан')
                        
                        # Получаем категорию
                        item_type = ''
                        if 'Categories' in company_meta and company_meta['Categories']:
                            item_type = company_meta['Categories'][0].get('name', '')
                        
                        results.append({
                            'name': name,
                            'address': address,
                            'type': item_type,
                            'lat': float(lat),
                            'lon': float(lon)
                        })
            
            # Обработка ответа 2GIS API
            else:
                if 'result' in data:
                    if 'items' in data['result']:
                        items = data['result']['items']
                    elif 'data' in data['result']:
                        items = data['result']['data']
                elif 'items' in data:
                    items = data['items']
                elif 'data' in data:
                    items = data['data']
                elif 'results' in data:
                    items = data['results']
                
                for item in items:
                    # Проверяем наличие координат
                    point = None
                    if 'point' in item:
                        point = item['point']
                    elif 'geometry' in item and 'coordinates' in item['geometry']:
                        coords = item['geometry']['coordinates']
                        point = {'lon': coords[0], 'lat': coords[1]}
                    
                    if point and point.get('lat') and point.get('lon'):
                        # Получаем тип из рубрик
                        item_type = ''
                        if 'rubrics' in item and item['rubrics']:
                            if isinstance(item['rubrics'], list) and len(item['rubrics']) > 0:
                                item_type = item['rubrics'][0].get('name', '')
                            elif isinstance(item['rubrics'], dict):
                                item_type = item['rubrics'].get('name', '')
                        elif 'type' in item:
                            item_type = item.get('type', '')
                        
                        # Получаем адрес
                        address = item.get('address_name', '')
                        if not address and 'address' in item:
                            address = item['address'].get('name', '')
                        
                        results.append({
                            'name': item.get('name', 'Без названия'),
                            'address': address or 'Адрес не указан',
                            'type': item_type,
                            'lat': float(point['lat']),
                            'lon': float(point['lon'])
                        })
            
            print(f"[DEBUG] Найдено элементов: {len(items)}, обработано: {len(results)}")
            
            # Если items пустой, выводим полную структуру для отладки
            if not items:
                print(f"[DEBUG] Полная структура ответа: {data}")
                if 'result' in data:
                    print(f"[DEBUG] Содержимое result: {data['result']}")
            
            print(f"[DEBUG] Обработано результатов: {len(results)}")
            
            if results:
                return jsonify({'results': results})
            else:
                print(f"[DEBUG] Нет результатов, пробуем следующий вариант...")
                continue
                
        except requests.exceptions.HTTPError as e:
            last_error = e
            error_code = e.response.status_code
            print(f"[DEBUG] HTTP ошибка {error_code}, пробуем следующий вариант...")
            
            # Если 403 (Forbidden) или 401 (Unauthorized), пропускаем этот API
            if error_code in [401, 403]:
                print(f"[DEBUG] Пропускаем этот API из-за ошибки авторизации")
                continue
            continue
        except Exception as e:
            last_error = e
            print(f"[DEBUG] Ошибка: {e}, пробуем следующий вариант...")
            continue
    
    # Если все попытки не удались
    if last_error:
        if isinstance(last_error, requests.exceptions.HTTPError):
            error_msg = f'Ошибка API: {last_error.response.status_code}'
            try:
                error_data = last_error.response.json()
                print(f"[DEBUG] Ошибка API: {error_data}")
                if 'error' in error_data:
                    error_msg = error_data['error'].get('message', error_msg)
                elif 'meta' in error_data and 'error' in error_data['meta']:
                    error_msg = error_data['meta']['error'].get('message', error_msg)
            except:
                error_msg = f'HTTP {last_error.response.status_code}: {last_error.response.text[:200]}'
            return jsonify({'error': error_msg}), last_error.response.status_code
        else:
            return jsonify({'error': f'Ошибка: {str(last_error)}'}), 500
    
    return jsonify({'results': []})

@app.route('/api/test')
def test_api():
    """Тестовый endpoint для проверки API ключа"""
    api_key = DGIS_API_KEY or TGIS_API_KEY
    
    if not api_key:
        return jsonify({'error': 'API ключ не настроен'}), 500
    
    # Простой тестовый запрос
    test_url = 'https://catalog.api.2gis.ru/3.0/items'
    test_params = {
        'q': 'аптека',
        'key': api_key,
        'region_id': 64,
        'page_size': 5
    }
    
    try:
        response = requests.get(test_url, params=test_params, timeout=10)
        return jsonify({
            'status_code': response.status_code,
            'response_preview': response.text[:500],
            'api_key_preview': api_key[:10] + '...' if len(api_key) > 10 else api_key
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/types')
def get_types():
    """API endpoint для получения списка типов объектов"""
    types = [
        {'id': 'hospital', 'name': 'Больницы', 'icon': '🏥'},
        {'id': 'pharmacy', 'name': 'Аптеки', 'icon': '💊'},
        {'id': 'clinic', 'name': 'Клиники', 'icon': '🏥'},
        {'id': 'ambulance', 'name': 'Скорая помощь', 'icon': '🚑'},
        {'id': 'dentist', 'name': 'Стоматологии', 'icon': '🦷'},
        {'id': 'veterinary', 'name': 'Ветеринарные клиники', 'icon': '🐾'}
    ]
    return jsonify({'types': types})

@app.route('/api/chatbot', methods=['POST'])
def chatbot():
    """API endpoint для чат-бота с Gemini AI"""
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({'error': 'Сообщение не может быть пустым'}), 400
    
    # Координаты центра Алматы (по умолчанию)
    almaty_center = {'lat': 43.2220, 'lon': 76.8512}
    
    try:
        # Пытаемся извлечь адрес из сообщения и геокодировать его
        user_location = extract_and_geocode_address(user_message, almaty_center)
        
        # Ищем ближайшие больницы к местоположению пользователя
        hospitals = find_nearest_hospitals(user_location)
        
        if not hospitals:
            return jsonify({
                'response': 'Извините, не удалось найти больницы поблизости. Попробуйте позже.',
                'ambulance_sent': False
            })
        
        # Используем Gemini AI для обработки запроса
        ai_response = ""
        if GEMINI_AVAILABLE and GEMINI_API_KEY and genai is not None:
            try:
                model = genai.GenerativeModel('gemini-pro')
                prompt = f"""Ты - помощник службы скорой помощи. Пользователь написал: "{user_message}"

Найденные больницы:
{format_hospitals_for_ai(hospitals[:3])}

Ответь кратко и профессионально. Если ситуация требует скорой помощи, подтверди отправку скорой от ближайшей больницы."""
                
                response = model.generate_content(prompt)
                ai_response = response.text
            except Exception as e:
                print(f"[DEBUG] Ошибка Gemini AI: {e}")
                ai_response = f"Понял вашу ситуацию. Отправляю скорую помощь от ближайшей больницы."
        else:
            # Если Gemini API ключ не настроен или недоступен, используем умный ответ на основе ключевых слов
            ai_response = generate_smart_response(user_message, hospitals)
        
        # Выбираем ближайшую больницу
        nearest_hospital = hospitals[0]
        
        # Рассчитываем расстояние и ETA
        distance_km = calculate_distance(
            user_location['lat'], user_location['lon'],
            nearest_hospital['lat'], nearest_hospital['lon']
        )
        
        # Рассчитываем ETA на основе расстояния (примерно 60 км/ч средняя скорость)
        estimated_minutes = max(3, int(distance_km * 1.2))  # Минимум 3 минуты
        eta_text = f"{estimated_minutes}-{estimated_minutes + 5} минут"
        eta_seconds = estimated_minutes * 60  # Для анимации
        
        # Получаем маршрут от больницы к адресу пользователя
        route_data = None
        try:
            # Вызываем функцию получения маршрута напрямую
            route_result = get_route_internal(
                {
                    'lat': nearest_hospital['lat'],
                    'lon': nearest_hospital['lon']
                },
                user_location
            )
            if route_result and route_result.get('success'):
                route_data = route_result
                # Обновляем ETA на основе реального маршрута
                if route_data.get('duration_seconds'):
                    eta_seconds = route_data['duration_seconds']
                    estimated_minutes = max(3, int(eta_seconds / 60))
                    eta_text = f"{estimated_minutes}-{estimated_minutes + 2} минут"
        except Exception as e:
            print(f"[DEBUG] Ошибка получения маршрута: {e}")
        
        return jsonify({
            'response': ai_response,
            'ambulance_sent': True,
            'hospital': {
                'name': nearest_hospital['name'],
                'address': nearest_hospital['address']
            },
            'hospital_location': {
                'lat': nearest_hospital['lat'],
                'lon': nearest_hospital['lon']
            },
            'user_location': user_location,
            'eta': eta_text,
            'eta_seconds': eta_seconds,
            'distance_km': round(distance_km, 2),
            'route_points': route_data.get('points', []) if route_data else []
        })
        
    except Exception as e:
        print(f"[DEBUG] Ошибка чат-бота: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'response': 'Извините, произошла ошибка при обработке запроса.'
        }), 500

def find_nearest_hospitals(location, limit=5):
    """Находит ближайшие больницы к указанному местоположению"""
    try:
        # Используем Yandex Search API или 2GIS для поиска больниц
        if YANDEX_SEARCH_API_KEY:
            url = 'https://search-maps.yandex.ru/v1/'
            params = {
                'apikey': YANDEX_SEARCH_API_KEY,
                'text': 'больница, Алматы',
                'type': 'biz',
                'll': f"{location['lon']},{location['lat']}",
                'spn': '0.3,0.3',
                'results': limit,
                'lang': 'ru_RU',
                'format': 'json'
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                hospitals = []
                
                if 'features' in data:
                    for item in data['features']:
                        geometry = item.get('geometry', {})
                        properties = item.get('properties', {})
                        company_meta = properties.get('CompanyMetaData', {})
                        
                        if geometry.get('type') == 'Point' and 'coordinates' in geometry:
                            coords = geometry['coordinates']
                            name = properties.get('name', company_meta.get('name', 'Больница'))
                            address = company_meta.get('address', 'Адрес не указан')
                            
                            hospitals.append({
                                'name': name,
                                'address': address,
                                'lat': coords[1],
                                'lon': coords[0],
                                'distance': calculate_distance(
                                    location['lat'], location['lon'],
                                    coords[1], coords[0]
                                )
                            })
                
                # Сортируем по расстоянию
                hospitals.sort(key=lambda x: x['distance'])
                return hospitals[:limit]
        
        # Fallback на 2GIS
        dgis_key = DGIS_API_KEY or TGIS_API_KEY
        if dgis_key:
            url = 'https://catalog.api.2gis.ru/3.0/items'
            params = {
                'q': 'больница',
                'key': dgis_key,
                'point': f"{location['lon']},{location['lat']}",
                'radius': 20000,
                'page_size': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                hospitals = []
                
                items = []
                if 'result' in data and 'items' in data['result']:
                    items = data['result']['items']
                
                for item in items:
                    if 'point' in item and item['point']:
                        hospitals.append({
                            'name': item.get('name', 'Больница'),
                            'address': item.get('address_name', 'Адрес не указан'),
                            'lat': item['point'].get('lat', 0),
                            'lon': item['point'].get('lon', 0),
                            'distance': calculate_distance(
                                location['lat'], location['lon'],
                                item['point'].get('lat', 0),
                                item['point'].get('lon', 0)
                            )
                        })
                
                hospitals.sort(key=lambda x: x['distance'])
                return hospitals[:limit]
        
        return []
        
    except Exception as e:
        print(f"[DEBUG] Ошибка поиска больниц: {e}")
        return []

def calculate_distance(lat1, lon1, lat2, lon2):
    """Вычисляет расстояние между двумя точками в километрах (формула гаверсинуса)"""
    R = 6371  # Радиус Земли в километрах
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def format_hospitals_for_ai(hospitals):
    """Форматирует список больниц для передачи в AI"""
    result = []
    for i, hospital in enumerate(hospitals, 1):
        result.append(f"{i}. {hospital['name']} - {hospital['address']} (расстояние: {hospital['distance']:.2f} км)")
    return "\n".join(result)

def extract_and_geocode_address(message, default_location):
    """Извлекает адрес из сообщения и геокодирует его"""
    import re
    
    # Сначала пытаемся геокодировать все сообщение (если это адрес)
    # Пробуем геокодировать с добавлением "Алматы"
    full_address = f"{message}, Алматы, Казахстан"
    geocoded = geocode_address(full_address)
    if geocoded:
        return geocoded
    
    # Если не получилось, пытаемся найти адрес по паттернам
    address_patterns = [
        r'(?:улица|ул\.?|проспект|пр\.?|бульвар|б-р|переулок|пер\.?)\s+[\w\s\-]+(?:\s+\d+)?',
        r'[\w\s\-]+(?:\s+улица|ул\.?|проспект|пр\.?|бульвар|б-р)',
        r'район\s+[\w\s\-]+',
        r'мкр\.?\s+[\w\s\-]+',
        r'микрорайон\s+[\w\s\-]+',
        r'[\w\s\-]+\s+\d+',  # Просто название + номер дома
    ]
    
    address_found = None
    for pattern in address_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            address_found = match.group(0)
            # Пробуем геокодировать найденный адрес
            full_address = f"{address_found}, Алматы, Казахстан"
            geocoded = geocode_address(full_address)
            if geocoded:
                return geocoded
    
    # Если ничего не найдено, используем центр Алматы
    return default_location

def geocode_address(address):
    """Геокодирует адрес через Yandex Geocoder API"""
    try:
        # Используем Yandex Geocoder API с ключом геокодера
        api_key = YANDEX_GEOCODER_API_KEY or YANDEX_MAPS_API_KEY
        url = 'https://geocode-maps.yandex.ru/1.x/'
        params = {
            'apikey': api_key,
            'geocode': address,
            'format': 'json',
            'results': 1,
            'lang': 'ru_RU'
        }
        
        print(f"[DEBUG] Геокодирование адреса: {address}")
        response = requests.get(url, params=params, timeout=10)
        print(f"[DEBUG] Статус геокодирования: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if 'response' in data and 'GeoObjectCollection' in data['response']:
                features = data['response']['GeoObjectCollection'].get('featureMember', [])
                if features:
                    coords = features[0]['GeoObject']['Point']['pos'].split()
                    result = {
                        'lat': float(coords[1]),
                        'lon': float(coords[0])
                    }
                    print(f"[DEBUG] Геокодирование успешно: {result}")
                    return result
                else:
                    print(f"[DEBUG] Геокодирование: адрес не найден")
            else:
                print(f"[DEBUG] Неожиданная структура ответа геокодера")
    except Exception as e:
        print(f"[DEBUG] Ошибка геокодирования адреса '{address}': {e}")
        import traceback
        traceback.print_exc()
    
    return None

def get_route_internal(from_location, to_location):
    """Внутренняя функция для получения маршрута между двумя точками"""
    try:
        # Используем Yandex Router API для построения маршрута
        api_key = YANDEX_GEOCODER_API_KEY or YANDEX_MAPS_API_KEY
        
        # Пробуем разные варианты Router API
        urls_to_try = [
            {
                'url': 'https://api.routing.yandex.net/v2/route',
                'params': {
                    'apikey': api_key,
                    'waypoints': f"{from_location['lon']},{from_location['lat']}|{to_location['lon']},{to_location['lat']}",
                    'mode': 'driving',
                    'lang': 'ru_RU'
                }
            },
            {
                'url': 'https://router.project-osrm.org/route/v1/driving/' + 
                       f"{from_location['lon']},{from_location['lat']};{to_location['lon']},{to_location['lat']}",
                'params': {
                    'overview': 'full',
                    'geometries': 'geojson'
                }
            }
        ]
        
        for route_config in urls_to_try:
            url = route_config['url']
            params = route_config['params']
        
            print(f"[DEBUG] Построение маршрута: {from_location} -> {to_location}")
            print(f"[DEBUG] URL: {url}")
            response = requests.get(url, params=params, timeout=10)
            print(f"[DEBUG] Статус маршрута: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"[DEBUG] Структура ответа маршрута: {list(data.keys())}")
                
                # Извлекаем точки маршрута
                route_points = []
                duration_seconds = 300
                distance_meters = 0
                
                # Обработка Yandex Router API
                if 'route' in data and len(data['route']) > 0:
                    route = data['route'][0]
                    
                    # Получаем время и расстояние
                    if 'duration' in route:
                        duration_seconds = int(route['duration'])
                    if 'distance' in route:
                        distance_meters = int(route['distance'])
                    
                    # Извлекаем точки из geometry
                    if 'geometry' in route:
                        geometry = route['geometry']
                        if isinstance(geometry, list):
                            for point in geometry:
                                if isinstance(point, list) and len(point) >= 2:
                                    route_points.append({
                                        'lat': point[1],
                                        'lon': point[0]
                                    })
                        elif isinstance(geometry, dict):
                            if 'coordinates' in geometry:
                                for point in geometry['coordinates']:
                                    route_points.append({
                                        'lat': point[1],
                                        'lon': point[0]
                                    })
                    
                    # Альтернативный способ - из legs
                    if not route_points and 'legs' in route:
                        for leg in route['legs']:
                            if 'steps' in leg:
                                for step in leg['steps']:
                                    if 'geometry' in step:
                                        geom = step['geometry']
                                        if isinstance(geom, list):
                                            for point in geom:
                                                if isinstance(point, list) and len(point) >= 2:
                                                    route_points.append({
                                                        'lat': point[1],
                                                        'lon': point[0]
                                                    })
                
                # Обработка OSRM API (альтернатива)
                elif 'routes' in data and len(data['routes']) > 0:
                    route = data['routes'][0]
                    if 'geometry' in route:
                        geom = route['geometry']
                        # OSRM может возвращать GeoJSON или закодированную полилинию
                        if isinstance(geom, dict) and 'coordinates' in geom:
                            # GeoJSON формат
                            for point in geom['coordinates']:
                                route_points.append({
                                    'lat': point[1],
                                    'lon': point[0]
                                })
                        elif isinstance(geom, str):
                            # Закодированная полилиния - пропускаем, используем интерполяцию
                            pass
                    
                    if 'duration' in route:
                        duration_seconds = int(route['duration'])
                    if 'distance' in route:
                        distance_meters = int(route['distance'])
                
                # Если точек все еще нет, создаем интерполированный маршрут
                if not route_points:
                    print("[DEBUG] Точки маршрута не найдены, создаем интерполированный маршрут")
                    steps = 100  # Больше точек для плавности
                    for i in range(steps + 1):
                        t = i / steps
                        lat = from_location['lat'] + (to_location['lat'] - from_location['lat']) * t
                        lon = from_location['lon'] + (to_location['lon'] - from_location['lon']) * t
                        route_points.append({'lat': lat, 'lon': lon})
                
                if route_points:
                    print(f"[DEBUG] Получено точек маршрута: {len(route_points)}, время: {duration_seconds}с")
                    return {
                        'success': True,
                        'points': route_points,
                        'duration_seconds': duration_seconds,
                        'distance_meters': distance_meters
                    }
            
            # Пробуем следующий вариант
            continue
            
    except Exception as e:
        print(f"[DEBUG] Ошибка получения маршрута: {e}")
        import traceback
        traceback.print_exc()
        return None

@app.route('/api/route', methods=['POST'])
def get_route():
    """API endpoint для получения маршрута между двумя точками"""
    data = request.json
    from_location = data.get('from')
    to_location = data.get('to')
    
    if not from_location or not to_location:
        return jsonify({'error': 'Не указаны точки маршрута'}), 400
    
    route_result = get_route_internal(from_location, to_location)
    if route_result:
        return jsonify(route_result)
    else:
        return jsonify({'error': 'Не удалось построить маршрут'}), 500

def generate_smart_response(user_message, hospitals):
    """Генерирует умный ответ без AI на основе ключевых слов"""
    message_lower = user_message.lower()
    
    # Определяем срочность по ключевым словам
    urgent_keywords = ['боль', 'травма', 'ранен', 'кровь', 'несчастный', 'авария', 'упал', 'упала', 
                      'сердце', 'инфаркт', 'инсульт', 'одышка', 'задыхаюсь', 'срочно', 'экстренно']
    
    is_urgent = any(keyword in message_lower for keyword in urgent_keywords)
    
    if is_urgent:
        return f"Понял, ситуация требует срочного вмешательства. Немедленно отправляю скорую помощь от ближайшей больницы \"{hospitals[0]['name']}\" (расстояние: {hospitals[0]['distance']:.2f} км)."
    else:
        return f"Понял вашу ситуацию. Отправляю скорую помощь от ближайшей больницы \"{hospitals[0]['name']}\" (расстояние: {hospitals[0]['distance']:.2f} км)."

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

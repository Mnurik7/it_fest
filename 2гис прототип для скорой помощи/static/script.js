// Глобальные переменные
let map;
let markers = [];
let currentType = '';
let searchQuery = '';

// Инициализация карты при загрузке страницы
window.addEventListener('load', function() {
    // Ждем загрузки Yandex Maps API
    if (typeof ymaps !== 'undefined') {
        ymaps.ready(initMap);
    } else {
        // Если API еще не загружен, ждем его загрузки
        const checkYMaps = setInterval(function() {
            if (typeof ymaps !== 'undefined') {
                clearInterval(checkYMaps);
                ymaps.ready(initMap);
            }
        }, 100);
        
        // Таймаут на случай, если API не загрузится
        setTimeout(function() {
            if (typeof ymaps === 'undefined') {
                clearInterval(checkYMaps);
                console.error('Yandex Maps API не загружен. Проверьте подключение к интернету и API ключ.');
                document.getElementById('map').innerHTML = 
                    '<div style="padding: 20px; text-align: center; color: #c62828;">' +
                    'Ошибка загрузки карты. Проверьте подключение к интернету и API ключ в .env файле.' +
                    '</div>';
            }
        }, 10000);
    }
    
    // Загружаем типы и настраиваем обработчики
    setTimeout(function() {
        loadTypes();
        setupEventListeners();
        
        // Автоматически загружаем больницы при открытии
        setTimeout(() => {
            filterByType('hospital');
        }, 2000);
    }, 500);
});

// Инициализация карты Yandex Maps
function initMap() {
    try {
        map = new ymaps.Map('map', {
            center: [43.2220, 76.8512], // Координаты Алматы [широта, долгота]
            zoom: 13,
            controls: ['zoomControl', 'fullscreenControl', 'geolocationControl']
        });
        
        console.log('Yandex карта инициализирована');
    } catch (error) {
        console.error('Ошибка инициализации карты:', error);
        document.getElementById('map').innerHTML = 
            '<div style="padding: 20px; text-align: center; color: #c62828;">' +
            'Ошибка инициализации карты: ' + error.message +
            '</div>';
    }
}

// Загрузка типов объектов
async function loadTypes() {
    try {
        const response = await fetch('/api/types');
        const data = await response.json();
        
        const typeButtons = document.getElementById('typeButtons');
        const typeFilter = document.getElementById('typeFilter');
        
        data.types.forEach(type => {
            // Кнопки в сайдбаре
            const btn = document.createElement('button');
            btn.className = 'type-btn';
            btn.innerHTML = `${type.icon} ${type.name}`;
            btn.dataset.type = type.id;
            btn.addEventListener('click', () => filterByType(type.id));
            typeButtons.appendChild(btn);
            
            // Опции в селекте
            const option = document.createElement('option');
            option.value = type.id;
            option.textContent = `${type.icon} ${type.name}`;
            typeFilter.appendChild(option);
        });
        
        typeFilter.addEventListener('change', (e) => {
            filterByType(e.target.value);
        });
        
    } catch (error) {
        console.error('Ошибка загрузки типов:', error);
    }
}

// Настройка обработчиков событий
function setupEventListeners() {
    const searchBtn = document.getElementById('searchBtn');
    const searchInput = document.getElementById('searchInput');
    
    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
}

// Поиск объектов
async function performSearch() {
    const query = document.getElementById('searchInput').value.trim();
    if (!query) return;
    
    searchQuery = query;
    await searchObjects(query, currentType);
}

// Фильтрация по типу
async function filterByType(type) {
    currentType = type;
    
    // Обновляем активную кнопку
    document.querySelectorAll('.type-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.type === type) {
            btn.classList.add('active');
        }
    });
    
    // Обновляем селект
    document.getElementById('typeFilter').value = type;
    
    // Выполняем поиск
    const query = searchQuery || getTypeQuery(type);
    await searchObjects(query, type);
}

// Получить поисковый запрос для типа
function getTypeQuery(type) {
    const typeQueries = {
        'hospital': 'больница',
        'pharmacy': 'аптека',
        'clinic': 'клиника',
        'ambulance': 'скорая помощь',
        'dentist': 'стоматология',
        'veterinary': 'ветеринарная клиника'
    };
    return typeQueries[type] || '';
}

// Поиск объектов на карте
async function searchObjects(query, type = '') {
    const resultsList = document.getElementById('resultsList');
    resultsList.innerHTML = '<div class="loading">Загрузка...</div>';
    
    try {
        const params = new URLSearchParams({
            q: query,
            city: 'Алматы'
        });
        
        if (type) {
            params.append('type', type);
        }
        
        const response = await fetch(`/api/search?${params}`);
        const data = await response.json();
        
        if (data.error) {
            resultsList.innerHTML = `<div class="error">Ошибка: ${data.error}</div>`;
            console.error('API Error:', data.error);
            return;
        }
        
        if (!data.results || data.results.length === 0) {
            resultsList.innerHTML = '<div class="loading">Ничего не найдено. Попробуйте другой запрос.</div>';
            clearMarkers();
            return;
        }
        
        displayResults(data.results);
        displayMarkers(data.results);
        
    } catch (error) {
        console.error('Ошибка поиска:', error);
        resultsList.innerHTML = `<div class="error">Ошибка при выполнении поиска: ${error.message}</div>`;
    }
}

// Отображение результатов в списке
function displayResults(results) {
    const resultsList = document.getElementById('resultsList');
    
    if (!results || results.length === 0) {
        resultsList.innerHTML = '<div class="loading">Ничего не найдено</div>';
        return;
    }
    
    resultsList.innerHTML = '';
    
    results.forEach((item, index) => {
        const div = document.createElement('div');
        div.className = 'result-item';
        div.innerHTML = `
            <h4>${item.name || 'Без названия'}</h4>
            <p>📍 ${item.address || 'Адрес не указан'}</p>
            <p>🏷️ ${item.type || 'Тип не указан'}</p>
        `;
        
        div.addEventListener('click', () => {
            centerMapOnMarker(item.lat, item.lon);
            highlightMarker(index);
        });
        
        resultsList.appendChild(div);
    });
}

// Отображение маркеров на карте
function displayMarkers(results) {
    // Удаляем старые маркеры
    clearMarkers();
    
    if (!results || results.length === 0) return;
    
    if (typeof ymaps === 'undefined' || !map) {
        console.error('Карта не инициализирована');
        return;
    }
    
    try {
        results.forEach((item, index) => {
            if (item.lat && item.lon) {
                // Создаем маркер Yandex Maps
                const marker = new ymaps.Placemark(
                    [item.lat, item.lon], // Координаты [широта, долгота]
                    {
                        balloonContentHeader: `<strong>${item.name || 'Без названия'}</strong>`,
                        balloonContentBody: `${item.address || 'Адрес не указан'}<br><small>${item.type || ''}</small>`,
                        balloonContentFooter: '',
                        hintContent: item.name || 'Без названия'
                    },
                    {
                        preset: 'islands#blueMedicalIcon' // Иконка для медицинских учреждений
                    }
                );
                
                // Добавляем обработчик клика
                marker.events.add('click', function() {
                    map.balloon.open([item.lat, item.lon], {
                        contentHeader: `<strong>${item.name || 'Без названия'}</strong>`,
                        contentBody: `${item.address || 'Адрес не указан'}<br><small>${item.type || ''}</small>`
                    });
                });
                
                map.geoObjects.add(marker);
                markers.push(marker);
            }
        });
        
        // Центрируем карту на всех маркерах
        if (markers.length > 0) {
            const bounds = map.geoObjects.getBounds();
            if (bounds) {
                map.setBounds(bounds, {
                    checkZoomRange: true,
                    duration: 300
                });
            }
        }
    } catch (error) {
        console.error('Ошибка отображения маркеров:', error);
    }
}

// Очистка маркеров
function clearMarkers() {
    if (!map) return;
    markers.forEach(marker => {
        try {
            map.geoObjects.remove(marker);
        } catch (error) {
            console.error('Ошибка удаления маркера:', error);
        }
    });
    markers = [];
}

// Центрирование карты на маркере
function centerMapOnMarker(lat, lon) {
    if (map && typeof ymaps !== 'undefined') {
        try {
            map.setCenter([lat, lon], 16, {
                duration: 300
            });
            
            // Открываем балун для этого маркера
            const marker = markers.find(m => {
                const coords = m.geometry.getCoordinates();
                return Math.abs(coords[0] - lat) < 0.0001 && Math.abs(coords[1] - lon) < 0.0001;
            });
            
            if (marker) {
                map.balloon.open([lat, lon], {
                    contentHeader: marker.properties.get('balloonContentHeader'),
                    contentBody: marker.properties.get('balloonContentBody')
                });
            }
        } catch (error) {
            console.error('Ошибка центрирования карты:', error);
        }
    }
}

// Подсветка маркера
function highlightMarker(index) {
    if (markers[index]) {
        const marker = markers[index];
        const coords = marker.geometry.getCoordinates();
        map.balloon.open(coords, {
            contentHeader: marker.properties.get('balloonContentHeader'),
            contentBody: marker.properties.get('balloonContentBody')
        });
    }
}

// ========== ЧАТ-БОТ СКОРОЙ ПОМОЩИ ==========

let ambulanceMarker = null;
let ambulanceRoute = null;

// Инициализация чат-бота
document.addEventListener('DOMContentLoaded', function() {
    const chatBotBtn = document.getElementById('chatBotBtn');
    const chatBotModal = document.getElementById('chatBotModal');
    const closeChatBot = document.getElementById('closeChatBot');
    const sendChatBotBtn = document.getElementById('sendChatBotBtn');
    const chatBotInput = document.getElementById('chatBotInput');
    
    if (chatBotBtn) {
        chatBotBtn.addEventListener('click', () => {
            chatBotModal.classList.add('active');
            chatBotInput.focus();
        });
    }
    
    if (closeChatBot) {
        closeChatBot.addEventListener('click', () => {
            chatBotModal.classList.remove('active');
        });
    }
    
    if (sendChatBotBtn) {
        sendChatBotBtn.addEventListener('click', sendChatMessage);
    }
    
    if (chatBotInput) {
        chatBotInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendChatMessage();
            }
        });
    }
    
    // Закрытие по клику вне модального окна
    chatBotModal.addEventListener('click', (e) => {
        if (e.target === chatBotModal) {
            chatBotModal.classList.remove('active');
        }
    });
});

// Отправка сообщения в чат-бот
async function sendChatMessage() {
    const chatBotInput = document.getElementById('chatBotInput');
    const chatBotMessages = document.getElementById('chatBotMessages');
    const sendChatBotBtn = document.getElementById('sendChatBotBtn');
    
    const message = chatBotInput.value.trim();
    if (!message) return;
    
    // Добавляем сообщение пользователя
    addChatMessage(message, 'user');
    chatBotInput.value = '';
    sendChatBotBtn.disabled = true;
    
    try {
        // Отправляем запрос к API
        const response = await fetch('/api/chatbot', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message })
        });
        
        const data = await response.json();
        
        if (data.error) {
            addChatMessage('Извините, произошла ошибка: ' + data.error, 'bot');
        } else {
            // Добавляем ответ бота
            addChatMessage(data.response, 'bot');
            
            // Если бот нашел больницу и отправил скорую
            if (data.hospital && data.ambulance_sent) {
                addChatMessage(
                    `✅ Скорая помощь отправлена от больницы "${data.hospital.name}" (${data.hospital.address}). ` +
                    `Ожидаемое время прибытия: ${data.eta || '5-10 минут'}. ` +
                    (data.distance_km ? `Расстояние: ${data.distance_km} км.` : ''),
                    'bot'
                );
                
                // Показываем анимацию движения скорой помощи
                if (data.hospital_location && data.user_location) {
                    animateAmbulance(
                        data.hospital_location,
                        data.user_location,
                        data.hospital.name,
                        data.eta_seconds || 300,  // По умолчанию 5 минут
                        data.route_points || []  // Точки маршрута от Router API
                    );
                }
            }
        }
    } catch (error) {
        console.error('Ошибка чат-бота:', error);
        addChatMessage('Извините, произошла ошибка при обработке запроса.', 'bot');
    } finally {
        sendChatBotBtn.disabled = false;
        chatBotInput.focus();
    }
}

// Добавление сообщения в чат
function addChatMessage(text, type) {
    const chatBotMessages = document.getElementById('chatBotMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chatbot-message ${type}-message`;
    
    const p = document.createElement('p');
    p.textContent = text;
    messageDiv.appendChild(p);
    
    chatBotMessages.appendChild(messageDiv);
    chatBotMessages.scrollTop = chatBotMessages.scrollHeight;
}

// Анимация движения скорой помощи
function animateAmbulance(fromLocation, toLocation, hospitalName, etaSeconds = 300, routePoints = []) {
    if (typeof ymaps === 'undefined' || !map) {
        console.error('Карта не инициализирована');
        return;
    }
    
    // Удаляем предыдущую скорую помощь, если есть
    if (ambulanceMarker) {
        map.geoObjects.remove(ambulanceMarker);
    }
    if (ambulanceRoute) {
        map.geoObjects.remove(ambulanceRoute);
    }
    
    const from = [fromLocation.lat, fromLocation.lon];
    const to = [toLocation.lat, toLocation.lon];
    
    // Создаем маркер больницы (точка отправления)
    const hospitalMarker = new ymaps.Placemark(
        from,
        {
            balloonContent: `Больница: ${hospitalName}`,
            hintContent: 'Больница'
        },
        {
            preset: 'islands#blueHospitalIcon',
            iconColor: '#0066cc'
        }
    );
    map.geoObjects.add(hospitalMarker);
    
    // Создаем маркер скорой помощи (начинаем от больницы)
    ambulanceMarker = new ymaps.Placemark(
        from,  // Начинаем от больницы
        {
            balloonContent: '🚑 Скорая помощь выезжает',
            hintContent: 'Скорая помощь'
        },
        {
            preset: 'islands#redAutoIcon',
            iconColor: '#ff0000'
        }
    );
    map.geoObjects.add(ambulanceMarker);
    
    // Создаем маркер места назначения
    const destinationMarker = new ymaps.Placemark(
        to,
        {
            balloonContent: '📍 Место вызова',
            hintContent: 'Место вызова'
        },
        {
            preset: 'islands#redDotIcon'
        }
    );
    map.geoObjects.add(destinationMarker);
    
    // Если есть точки маршрута от Router API, используем их
    if (routePoints && routePoints.length > 0) {
        console.log(`Используем маршрут от Router API: ${routePoints.length} точек`);
        
        // Создаем полилинию маршрута
        const routeCoordinates = routePoints.map(point => [point.lat, point.lon]);
        ambulanceRoute = new ymaps.Polyline(routeCoordinates, {}, {
            strokeColor: '#FF0000',
            strokeWidth: 4,
            strokeStyle: 'solid'
        });
        map.geoObjects.add(ambulanceRoute);
        
        // Конвертируем точки маршрута в формат [lat, lon]
        const allWayPoints = routePoints.map(point => [point.lat, point.lon]);
        
        // Рассчитываем скорость анимации на основе ETA
        const totalSteps = allWayPoints.length;
        const totalTimeMs = etaSeconds * 1000;
        const animationSpeed = Math.max(30, Math.floor(totalTimeMs / totalSteps));
        
        console.log(`Анимация: ${totalSteps} шагов, ${etaSeconds} секунд, скорость: ${animationSpeed}мс/шаг`);
        
        // Центрируем карту на маршруте
        const bounds = ambulanceRoute.geometry.getBounds();
        if (bounds) {
            map.setBounds(bounds, {
                checkZoomRange: true,
                duration: 500
            });
        }
        
        // Анимируем движение скорой помощи
        let currentIndex = 0;
        
        function animateStep() {
            if (currentIndex < allWayPoints.length) {
                const nextPoint = allWayPoints[currentIndex];
                ambulanceMarker.geometry.setCoordinates(nextPoint);
                ambulanceMarker.properties.set('balloonContent', '🚑 Скорая помощь в пути');
                currentIndex++;
                setTimeout(animateStep, animationSpeed);
            } else {
                // Скорая прибыла
                ambulanceMarker.properties.set('balloonContent', '✅ Скорая помощь прибыла!');
                map.balloon.open(to, {
                    contentHeader: '✅ Скорая помощь прибыла!',
                    contentBody: 'Медицинская бригада на месте.'
                });
            }
        }
        
        // Небольшая задержка перед началом движения
        setTimeout(() => {
            ambulanceMarker.properties.set('balloonContent', '🚑 Скорая помощь выезжает');
            setTimeout(animateStep, 500);
        }, 1000);
        
    } else {
        // Если точек маршрута нет, строим маршрут через Yandex Maps JavaScript API
        console.log('Строим маршрут через Yandex Maps JavaScript API');
        
        // Используем MultiRoute для построения автомобильного маршрута
        const multiRoute = new ymaps.multiRouter.MultiRoute({
            referencePoints: [from, to],
            params: {
                routingMode: 'auto'  // Автомобильный маршрут
            }
        }, {
            boundsAutoApply: true
        });
        
        map.geoObjects.add(multiRoute);
        ambulanceRoute = multiRoute;
        
        // Ждем построения маршрута
        multiRoute.model.events.add('requestsuccess', function() {
            const activeRoute = multiRoute.getActiveRoute();
            if (activeRoute) {
                // Получаем все точки маршрута
                let allWayPoints = [];
                const paths = activeRoute.getPaths();
                
                paths.each(function(path) {
                    const segments = path.getSegments();
                    segments.each(function(segment) {
                        const coordinates = segment.getCoordinates();
                        allWayPoints = allWayPoints.concat(coordinates);
                    });
                });
                
                // Если точек маршрута нет, используем прямую линию
                if (allWayPoints.length === 0) {
                    allWayPoints = [from, to];
                }
                
                // Рассчитываем скорость анимации на основе ETA
                const totalSteps = allWayPoints.length;
                const totalTimeMs = etaSeconds * 1000;
                const animationSpeed = Math.max(30, Math.floor(totalTimeMs / totalSteps));
                
                console.log(`Анимация: ${totalSteps} шагов, ${etaSeconds} секунд, скорость: ${animationSpeed}мс/шаг`);
                
                // Анимируем движение скорой помощи
                let currentIndex = 0;
                
                function animateStep() {
                    if (currentIndex < allWayPoints.length) {
                        const nextPoint = allWayPoints[currentIndex];
                        ambulanceMarker.geometry.setCoordinates(nextPoint);
                        ambulanceMarker.properties.set('balloonContent', '🚑 Скорая помощь в пути');
                        currentIndex++;
                        setTimeout(animateStep, animationSpeed);
                    } else {
                        // Скорая прибыла
                        ambulanceMarker.properties.set('balloonContent', '✅ Скорая помощь прибыла!');
                        map.balloon.open(to, {
                            contentHeader: '✅ Скорая помощь прибыла!',
                            contentBody: 'Медицинская бригада на месте.'
                        });
                    }
                }
                
                // Центрируем карту на маршруте
                const bounds = activeRoute.getBounds();
                if (bounds) {
                    map.setBounds(bounds, {
                        checkZoomRange: true,
                        duration: 500
                    });
                }
                
                // Небольшая задержка перед началом движения
                setTimeout(() => {
                    ambulanceMarker.properties.set('balloonContent', '🚑 Скорая помощь выезжает');
                    setTimeout(animateStep, 500);
                }, 1000);
            } else {
                console.error('Активный маршрут не найден');
                animateStraightLine(from, to, etaSeconds);
            }
        });
        
        multiRoute.model.events.add('requestfail', function() {
            console.error('Ошибка построения маршрута');
            animateStraightLine(from, to, etaSeconds);
        });
    }
}

// Простая анимация по прямой линии (если маршрут не построен)
function animateStraightLine(from, to, etaSeconds = 300) {
    const steps = 100; // Больше шагов для плавности
    let currentStep = 0;
    
    const totalTimeMs = etaSeconds * 1000;
    const animationSpeed = Math.max(50, Math.floor(totalTimeMs / steps));
    
    function animate() {
        if (currentStep <= steps) {
            const t = currentStep / steps;
            const lat = from[0] + (to[0] - from[0]) * t;
            const lon = from[1] + (to[1] - from[1]) * t;
            
            ambulanceMarker.geometry.setCoordinates([lat, lon]);
            ambulanceMarker.properties.set('balloonContent', '🚑 Скорая помощь в пути');
            currentStep++;
            setTimeout(animate, animationSpeed);
        } else {
            ambulanceMarker.properties.set('balloonContent', '✅ Скорая помощь прибыла!');
            map.balloon.open(to, {
                contentHeader: '✅ Скорая помощь прибыла!',
                contentBody: 'Медицинская бригада на месте.'
            });
        }
    }
    
    // Небольшая задержка перед началом
    setTimeout(() => {
        ambulanceMarker.properties.set('balloonContent', '🚑 Скорая помощь выезжает');
        setTimeout(animate, 500);
    }, 1000);
}

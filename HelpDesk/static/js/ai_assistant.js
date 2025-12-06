// AI Assistant JavaScript
let aiAssistantOpen = false;
let currentPage = 'index';
let conversationHistory = [];

// Определение текущей страницы
function detectCurrentPage() {
    const path = window.location.pathname;
    const pageMap = {
        '/': 'index',
        '/ai-procure': 'ai_procure',
        '/ai-scrum': 'ai_scrum',
        '/ai-business-analyst': 'ai_business_analyst',
        '/ai-code-review': 'ai_code_review',
        '/fraud-detection': 'fraud_detection',
        '/it-help-desk': 'it_help_desk',
        '/retail-help-desk': 'retail_help_desk',
        '/medical-help-desk': 'medical_help_desk',
        '/legal-help-desk': 'legal_help_desk',
        '/telecom-help-desk': 'telecom_help_desk',
        '/auto-help-desk': 'auto_help_desk',
        '/help-desk': 'general_help_desk'
    };
    
    return pageMap[path] || 'index';
}

// Переключение ассистента
function toggleAIAssistant() {
    const panel = document.getElementById('aiAssistantPanel');
    const badge = document.getElementById('aiAssistantBadge');
    
    aiAssistantOpen = !aiAssistantOpen;
    
    if (aiAssistantOpen) {
        panel.classList.add('active');
        badge.style.display = 'none';
        loadAIAssistantGreeting();
    } else {
        panel.classList.remove('active');
    }
}

// Загрузка приветствия
function loadAIAssistantGreeting() {
    currentPage = detectCurrentPage();
    const content = document.getElementById('aiAssistantContent');
    
    content.innerHTML = '<div class="ai-assistant-loading">Загрузка...</div>';
    
    fetch(`/api/ai-assistant/greeting?page=${currentPage}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayMessage('assistant', data.greeting);
                addQuickActions();
            } else {
                displayMessage('assistant', 'Привет! Я твой AI-ассистент. Чем могу помочь?');
            }
        })
        .catch(error => {
            displayMessage('assistant', 'Привет! Я твой AI-ассистент. Чем могу помочь?');
        });
}

// Добавление быстрых действий
function addQuickActions() {
    const content = document.getElementById('aiAssistantContent');
    const quickActions = document.createElement('div');
    quickActions.className = 'ai-assistant-quick-actions';
    
    const actions = getQuickActionsForPage(currentPage);
    
    actions.forEach(action => {
        const button = document.createElement('button');
        button.className = 'ai-assistant-quick-action';
        button.textContent = action.text;
        button.onclick = () => sendQuickQuestion(action.question);
        quickActions.appendChild(button);
    });
    
    content.appendChild(quickActions);
}

// Получение быстрых действий для страницы
function getQuickActionsForPage(page) {
    const actions = {
        'index': [
            { text: 'Как работает AI-Procure?', question: 'Как работает модуль AI-Procure?' },
            { text: 'Что может AI-Scrum Master?', question: 'Что может делать AI-Scrum Master?' }
        ],
        'ai_procure': [
            { text: 'Как извлечь параметры?', question: 'Как извлечь параметры тендера?' },
            { text: 'Как подобрать поставщиков?', question: 'Как подобрать подходящих поставщиков?' }
        ],
        'ai_scrum': [
            { text: 'Как создать проект?', question: 'Как создать новый проект?' },
            { text: 'Как создать задачи?', question: 'Как создать задачи из текста?' },
            { text: 'Как настроить Jira?', question: 'Как настроить интеграцию с Jira?' },
            { text: 'Как подключить Google Meet?', question: 'Как настроить интеграцию с Google Meet?' },
            { text: 'Как подключить Teams?', question: 'Как настроить интеграцию с Microsoft Teams?' },
            { text: 'Как работает AI-ассистент во время звонка?', question: 'Как работает AI-ассистент во время звонка?' }
        ],
        'ai_business_analyst': [
            { text: 'Как анализировать документы?', question: 'Как проанализировать документ?' },
            { text: 'Как извлечь требования?', question: 'Как извлечь требования из документа?' }
        ],
        'ai_code_review': [
            { text: 'Как провести ревью?', question: 'Как провести ревью кода?' },
            { text: 'Как загрузить архитектуру?', question: 'Как загрузить архитектуру проекта?' }
        ],
        'fraud_detection': [
            { text: 'Как проверить транзакции?', question: 'Как проверить транзакции на мошенничество?' },
            { text: 'Как настроить порог?', question: 'Как настроить порог детекции мошенничества?' },
            { text: 'Что показывает статистика?', question: 'Что показывает статистика по транзакциям?' }
        ],
        'it_help_desk': [
            { text: 'Как решить проблему с принтером?', question: 'Как решить проблему с принтером?' },
            { text: 'Как настроить VPN?', question: 'Как настроить VPN?' },
            { text: 'Проблемы с сетью', question: 'Помогите с сетевыми проблемами' },
            { text: 'Настройка безопасности', question: 'Как настроить безопасность IT?' }
        ],
        'retail_help_desk': [
            { text: 'Вернуть товар', question: 'Хочу вернуть товар' },
            { text: 'Консультация по товару', question: 'Нужна консультация по товару' },
            { text: 'Подать жалобу', question: 'Хочу подать жалобу' },
            { text: 'Поддержка продаж', question: 'Нужна поддержка продаж' }
        ],
        'medical_help_desk': [
            { text: 'Записаться на приём', question: 'Хочу записаться на приём к врачу' },
            { text: 'Медицинская консультация', question: 'Нужна медицинская консультация' },
            { text: 'Экстренная помощь', question: 'Нужна экстренная медицинская помощь' },
            { text: 'Помощь пациенту', question: 'Нужна помощь пациенту' }
        ],
        'legal_help_desk': [
            { text: 'Юридическая консультация', question: 'Нужна юридическая консультация' },
            { text: 'Обработка правового запроса', question: 'Нужна обработка правового запроса' },
            { text: 'Документооборот', question: 'Помощь с документооборотом' },
            { text: 'Срочный юридический вопрос', question: 'Срочный юридический вопрос' }
        ],
        'telecom_help_desk': [
            { text: 'Проблема с интернетом', question: 'Проблема с интернетом' },
            { text: 'Проблема с связью', question: 'Проблема с связью' },
            { text: 'Настройка оборудования', question: 'Нужна помощь с настройкой оборудования' },
            { text: 'Вопрос по биллингу', question: 'Вопрос по биллингу' }
        ],
        'auto_help_desk': [
            { text: 'Техническая помощь', question: 'Нужна техническая помощь с автомобилем' },
            { text: 'Запись на сервис', question: 'Хочу записаться на сервис' },
            { text: 'Консультация по ремонту', question: 'Нужна консультация по ремонту' },
            { text: 'Экстренная помощь', question: 'Нужна экстренная помощь на дороге' }
        ],
        'general_help_desk': [
            { text: 'Проблема с компьютером', question: 'У меня проблема с компьютером' },
            { text: 'Вернуть товар', question: 'Хочу вернуть товар' },
            { text: 'Медицинская консультация', question: 'Нужна медицинская консультация' },
            { text: 'Юридический вопрос', question: 'У меня юридический вопрос' }
        ]
    };
    
    return actions[page] || [];
}

// Отправка быстрого вопроса
function sendQuickQuestion(question) {
    const input = document.getElementById('aiAssistantInput');
    input.value = question;
    sendAIAssistantMessage();
}

// Отправка сообщения
function sendAIAssistantMessage() {
    const input = document.getElementById('aiAssistantInput');
    const question = input.value.trim();
    
    if (!question) return;
    
    // Очистка input
    input.value = '';
    
    // Отображение сообщения пользователя
    displayMessage('user', question);
    
    // Добавление в историю
    conversationHistory.push({
        role: 'user',
        content: question
    });
    
    // Показ индикатора печати
    showTypingIndicator();
    
    // Отправка запроса
    fetch('/api/ai-assistant/ask', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            page: currentPage,
            question: question,
            conversation_history: conversationHistory
        })
    })
    .then(response => response.json())
    .then(data => {
        hideTypingIndicator();
        
        if (data.success) {
            displayMessage('assistant', data.answer);
            
            // Добавление в историю
            conversationHistory.push({
                role: 'assistant',
                content: data.answer
            });
            
            // Ограничение истории (последние 10 сообщений)
            if (conversationHistory.length > 10) {
                conversationHistory = conversationHistory.slice(-10);
            }
        } else {
            displayMessage('assistant', 'Извините, произошла ошибка. Попробуйте позже.');
        }
    })
    .catch(error => {
        hideTypingIndicator();
        displayMessage('assistant', 'Извините, произошла ошибка при отправке запроса.');
    });
}

// Отображение сообщения
function displayMessage(role, content) {
    const contentDiv = document.getElementById('aiAssistantContent');
    const messageDiv = document.createElement('div');
    messageDiv.className = `ai-assistant-message ${role}`;
    
    const bubble = document.createElement('div');
    bubble.className = 'ai-assistant-message-bubble';
    
    // Преобразование markdown в HTML (простая версия)
    bubble.innerHTML = formatMessage(content);
    
    messageDiv.appendChild(bubble);
    contentDiv.appendChild(messageDiv);
    
    // Прокрутка вниз
    contentDiv.scrollTop = contentDiv.scrollHeight;
}

// Форматирование сообщения (простой markdown)
function formatMessage(text) {
    // Замена **текст** на <strong>текст</strong>
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Замена *текст* на <em>текст</em>
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Замена заголовков
    text = text.replace(/^### (.*$)/gm, '<h5>$1</h5>');
    text = text.replace(/^## (.*$)/gm, '<h4>$1</h4>');
    text = text.replace(/^# (.*$)/gm, '<h4>$1</h4>');
    
    // Замена списков
    text = text.replace(/^\- (.*$)/gm, '<li>$1</li>');
    text = text.replace(/^(\d+)\. (.*$)/gm, '<li>$2</li>');
    
    // Обёртка списков
    text = text.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    
    // Замена переносов строк на <br>
    text = text.replace(/\n/g, '<br>');
    
    // Замена кода
    text = text.replace(/`(.*?)`/g, '<code>$1</code>');
    
    return text;
}

// Показ индикатора печати
function showTypingIndicator() {
    const contentDiv = document.getElementById('aiAssistantContent');
    const typingDiv = document.createElement('div');
    typingDiv.className = 'ai-assistant-message assistant';
    typingDiv.id = 'typingIndicator';
    
    const bubble = document.createElement('div');
    bubble.className = 'ai-assistant-message-bubble';
    bubble.innerHTML = '<div class="ai-assistant-typing"><span></span><span></span><span></span></div>';
    
    typingDiv.appendChild(bubble);
    contentDiv.appendChild(typingDiv);
    contentDiv.scrollTop = contentDiv.scrollHeight;
}

// Скрытие индикатора печати
function hideTypingIndicator() {
    const typingDiv = document.getElementById('typingIndicator');
    if (typingDiv) {
        typingDiv.remove();
    }
}

// Обработка нажатия Enter
function handleAIAssistantKeyPress(event) {
    if (event.key === 'Enter') {
        sendAIAssistantMessage();
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    currentPage = detectCurrentPage();
    
    // Автоматическое открытие при первом посещении (можно настроить)
    // const hasSeenAssistant = localStorage.getItem('aiAssistantSeen');
    // if (!hasSeenAssistant) {
    //     setTimeout(() => {
    //         toggleAIAssistant();
    //         localStorage.setItem('aiAssistantSeen', 'true');
    //     }, 2000);
    // }
});


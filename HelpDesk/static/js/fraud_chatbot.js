// Чатбот о мошенничестве
let messageHistory = [];

// Инициализация
document.addEventListener('DOMContentLoaded', function() {
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    
    if (chatInput) {
        // Автоматическое изменение высоты textarea
        chatInput.addEventListener('input', function() {
            this.style.height = 'auto';
            const maxHeight = this.classList.contains('chat-input-compact') ? 100 : 150;
            this.style.height = (this.scrollHeight) + 'px';
            if (this.scrollHeight > maxHeight) {
                this.style.overflowY = 'auto';
                this.style.height = maxHeight + 'px';
            } else {
                this.style.overflowY = 'hidden';
            }
        });
        
        // Фокус на input при загрузке (только если не компактный)
        if (!chatInput.classList.contains('chat-input-compact')) {
            chatInput.focus();
        }
    }
});

// Обработка нажатия Enter
function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// Отправка предложенного вопроса
function sendSuggestedQuestion(question) {
    const chatInput = document.getElementById('chat-input');
    chatInput.value = question;
    sendMessage();
}

// Отправка сообщения
function sendMessage() {
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const message = chatInput.value.trim();
    
    if (!message) {
        return;
    }
    
    // Очищаем input
    chatInput.value = '';
    chatInput.style.height = 'auto';
    
    // Отключаем кнопку
    sendButton.disabled = true;
    
    // Скрываем предложенные вопросы после первого сообщения
    const suggestedQuestions = document.getElementById('suggested-questions');
    if (suggestedQuestions && messageHistory.length === 0) {
        suggestedQuestions.style.display = 'none';
    }
    
    // Добавляем сообщение пользователя
    addMessage('user', message);
    
    // Показываем индикатор загрузки
    const loadingId = addLoadingMessage();
    
    // Отправляем запрос на сервер
    fetch('/api/fraud-chatbot/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: message })
    })
    .then(async response => {
        const contentType = response.headers.get('content-type');
        let data;
        
        if (contentType && contentType.includes('application/json')) {
            data = await response.json();
        } else {
            const text = await response.text();
            throw new Error(`Неожиданный формат ответа: ${text}`);
        }
        
        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}`);
        }
        
        return data;
    })
    .then(data => {
        // Удаляем индикатор загрузки
        removeLoadingMessage(loadingId);
        
        if (data.success && data.response) {
            // Добавляем ответ бота
            addMessage('bot', data.response);
            
            // Сохраняем в историю
            messageHistory.push({
                user: message,
                bot: data.response,
                timestamp: data.timestamp || new Date().toISOString()
            });
        } else {
            throw new Error(data.error || 'Не удалось получить ответ');
        }
    })
    .catch(error => {
        console.error('Ошибка при отправке сообщения:', error);
        
        // Удаляем индикатор загрузки
        removeLoadingMessage(loadingId);
        
        // Показываем сообщение об ошибке
        addMessage('bot', `Извините, произошла ошибка: ${error.message}. Попробуйте еще раз или обратитесь к специалисту.`);
    })
    .finally(() => {
        // Включаем кнопку обратно
        sendButton.disabled = false;
        chatInput.focus();
    });
}

// Добавление сообщения в чат
function addMessage(type, text) {
    const chatMessages = document.getElementById('chat-messages');
    
    // Удаляем empty state если есть
    const emptyState = chatMessages.querySelector('.empty-state, .empty-state-compact');
    if (emptyState) {
        emptyState.remove();
    }
    
    const messageDiv = document.createElement('div');
    // Проверяем, есть ли компактный класс у контейнера
    const isCompact = chatMessages.classList.contains('chat-messages-compact');
    messageDiv.className = isCompact ? `message-compact ${type}` : `message ${type}`;
    
    const avatar = document.createElement('div');
    avatar.className = isCompact ? 'message-avatar-compact' : 'message-avatar';
    avatar.textContent = type === 'user' ? '👤' : '🤖';
    
    const content = document.createElement('div');
    content.className = isCompact ? 'message-content-compact' : 'message-content';
    
    // Форматируем текст (поддержка markdown-подобного форматирования)
    const formattedText = formatMessage(text);
    content.innerHTML = formattedText;
    
    const time = document.createElement('div');
    time.className = isCompact ? 'message-time-compact' : 'message-time';
    time.textContent = new Date().toLocaleTimeString('ru-RU', { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
    
    content.appendChild(time);
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    
    chatMessages.appendChild(messageDiv);
    
    // Прокрутка вниз
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageDiv;
}

// Форматирование сообщения
function formatMessage(text) {
    // Заменяем переносы строк на <br>
    let formatted = text.replace(/\n/g, '<br>');
    
    // Выделяем жирный текст **текст**
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Выделяем курсив *текст*
    formatted = formatted.replace(/(?<!\*)\*(?!\*)([^*]+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');
    
    // Создаем списки
    formatted = formatted.replace(/^[-•]\s+(.+)$/gm, '<li>$1</li>');
    formatted = formatted.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    
    // Выделяем код `код`
    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    return formatted;
}

// Добавление индикатора загрузки
function addLoadingMessage() {
    const chatMessages = document.getElementById('chat-messages');
    const isCompact = chatMessages.classList.contains('chat-messages-compact');
    
    const loadingId = 'loading-' + Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = isCompact ? 'message-compact bot' : 'message bot';
    messageDiv.id = loadingId;
    
    const avatar = document.createElement('div');
    avatar.className = isCompact ? 'message-avatar-compact' : 'message-avatar';
    avatar.textContent = '🤖';
    
    const content = document.createElement('div');
    content.className = isCompact ? 'message-content-compact' : 'message-content';
    content.innerHTML = `
        <div class="${isCompact ? 'loading-indicator-compact' : 'loading-indicator'}">
            <span>Бот печатает</span>
            <div class="${isCompact ? 'loading-dots-compact' : 'loading-dots'}">
                <div class="${isCompact ? 'loading-dot-compact' : 'loading-dot'}"></div>
                <div class="${isCompact ? 'loading-dot-compact' : 'loading-dot'}"></div>
                <div class="${isCompact ? 'loading-dot-compact' : 'loading-dot'}"></div>
            </div>
        </div>
    `;
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return loadingId;
}

// Удаление индикатора загрузки
function removeLoadingMessage(loadingId) {
    const loadingElement = document.getElementById(loadingId);
    if (loadingElement) {
        loadingElement.remove();
    }
}

// Экспорт функций для использования в HTML
window.sendMessage = sendMessage;
window.handleKeyPress = handleKeyPress;
window.sendSuggestedQuestion = sendSuggestedQuestion;


// Панель оператора: загрузка тикетов только своего отдела + приём звонков

let currentTicketId = null;
let currentChatId = null;
let chatPollInterval = null;
let aiAnalysisTimeout = null;
let analyzedMessageIds = new Set(); // Отслеживаем ID проанализированных сообщений

// Heartbeat для поддержания онлайн статуса
let heartbeatInterval = null;

async function updateOperatorActivity() {
    try {
        await fetch('/api/operators/heartbeat', {
            method: 'POST',
            credentials: 'same-origin'
        });
    } catch (error) {
        console.error('Error updating operator activity:', error);
    }
}

// Загрузка статуса оператора
async function loadOperatorStatus() {
    try {
        const response = await fetch('/api/operators/my-status', {
            credentials: 'same-origin'
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                updateOperatorStatusUI(data.is_online_manual);
            }
        }
    } catch (error) {
        console.error('Error loading operator status:', error);
    }
}

// Обновление UI статуса оператора
function updateOperatorStatusUI(isOnline) {
    const statusBtn = document.getElementById('operatorStatusBtn');
    const statusIcon = document.getElementById('operatorStatusIcon');
    const statusText = document.getElementById('operatorStatusText');
    
    if (statusBtn && statusIcon && statusText) {
        if (isOnline) {
            statusBtn.className = 'btn btn-status-online';
            statusIcon.textContent = '🟢';
            statusText.textContent = 'Онлайн';
        } else {
            statusBtn.className = 'btn btn-status-offline';
            statusIcon.textContent = '⚫';
            statusText.textContent = 'Офлайн';
        }
    }
}

// Переключение статуса оператора
async function toggleOperatorStatus() {
    const statusBtn = document.getElementById('operatorStatusBtn');
    if (statusBtn) {
        statusBtn.disabled = true;
    }
    
    try {
        const response = await fetch('/api/operators/toggle-status', {
            method: 'POST',
            credentials: 'same-origin'
        });
        
        if (response.status === 401 || response.status === 403) {
            alert('Ошибка доступа');
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            updateOperatorStatusUI(data.is_online);
            
            // Если переключились на онлайн, сразу обновляем активность
            if (data.is_online) {
                updateOperatorActivity();
            }
        } else {
            alert('Ошибка: ' + (data.error || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('Error toggling operator status:', error);
        alert('Произошла ошибка при переключении статуса');
    } finally {
        if (statusBtn) {
            statusBtn.disabled = false;
        }
    }
}

// Загрузка при открытии страницы
document.addEventListener('DOMContentLoaded', function() {
    // Загружаем текущий статус оператора
    loadOperatorStatus();
    
    // Сразу обновляем активность (если онлайн)
    updateOperatorActivity();
    
    // Обновляем активность каждые 2 минуты (чтобы оставаться онлайн, если статус онлайн)
    heartbeatInterval = setInterval(() => {
        // Проверяем статус перед обновлением активности
        const statusBtn = document.getElementById('operatorStatusBtn');
        if (statusBtn && statusBtn.classList.contains('btn-status-online')) {
            updateOperatorActivity();
        }
    }, 120000); // 2 минуты
    
    loadStats();
    loadTickets();
    loadWaitingChats();
    loadActiveChats();
    
    // Обработчики фильтров
    document.getElementById('filterStatus').addEventListener('change', loadTickets);
    document.getElementById('filterPriority').addEventListener('change', loadTickets);
    document.getElementById('filterSource').addEventListener('change', loadTickets);
    
    // Обработчик отправки сообщения в чате
    const operatorSendBtn = document.getElementById('operatorSendBtn');
    if (operatorSendBtn) {
        operatorSendBtn.addEventListener('click', sendOperatorMessage);
    }
    
    const operatorMessageInput = document.getElementById('operatorMessageInput');
    if (operatorMessageInput) {
        operatorMessageInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendOperatorMessage();
            }
        });
    }
    
    // Функции будут присвоены в window в конце файла после их определения
    
    // Автоматическое обновление тикетов каждые 30 секунд
    setInterval(function() {
        loadTickets(false); // Не показываем лоадер при автообновлении
        loadStats();
        if (!currentChatId) {
            loadWaitingChats();
            loadActiveChats();
        }
    }, 30000); // 30 секунд
});

// Загрузка статистики
async function loadStats() {
    try {
        const response = await fetch('/api/tickets?operator_view=true', {
            credentials: 'same-origin'
        });
        
        if (response.status === 401 || response.status === 403) {
            window.location.href = '/login';
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            const tickets = data.tickets;
            
            const total = tickets.length;
            const open = tickets.filter(t => t.status === 'OPEN').length;
            const inProgress = tickets.filter(t => t.status === 'IN_PROGRESS').length;
            const resolved = tickets.filter(t => t.status === 'RESOLVED').length;
            
            document.getElementById('statTotal').textContent = total;
            document.getElementById('statOpen').textContent = open;
            document.getElementById('statInProgress').textContent = inProgress;
            document.getElementById('statResolved').textContent = resolved;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Загрузка списка тикетов
async function loadTickets(showLoader = true) {
    const status = document.getElementById('filterStatus').value;
    const priority = document.getElementById('filterPriority').value;
    const source = document.getElementById('filterSource').value;
    
    const params = new URLSearchParams();
    params.append('operator_view', 'true'); // Используем operator_view для операторов
    if (status) params.append('status', status);
    if (priority) params.append('priority', priority);
    if (source) params.append('source', source);
    
    const url = '/api/tickets?' + params.toString();
    
    const tbody = document.getElementById('ticketsTableBody');
    if (showLoader) {
        tbody.innerHTML = '<tr><td colspan="8" class="loading"><div class="loading-spinner"></div><div>Загрузка обращений...</div></td></tr>';
    }
    
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 секунд таймаут
        
        const response = await fetch(url, {
            credentials: 'same-origin',
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (response.status === 401 || response.status === 403) {
            window.location.href = '/login';
            return;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            const tickets = data.tickets;
            
            if (tickets.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" class="loading">Тикетов не найдено</td></tr>';
                return;
            }
            
            // Загружаем информацию о пользователях для всех тикетов (с таймаутом)
            const userIds = [...new Set(tickets.filter(t => t.user_id).map(t => t.user_id))];
            const usersMap = {};
            
            // Загружаем информацию о пользователях параллельно с таймаутом
            try {
                await Promise.race([
                    Promise.all(userIds.map(async (userId) => {
                        try {
                            const userInfo = await loadUserInfo(userId);
                            if (userInfo) {
                                usersMap[userId] = userInfo;
                            }
                        } catch (e) {
                            console.warn(`Failed to load user ${userId}:`, e);
                        }
                    })),
                    new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 5000))
                ]);
            } catch (e) {
                console.warn('Some user info failed to load, continuing...');
            }
            
            tbody.innerHTML = tickets.map(ticket => {
                let userDisplay = '-';
                if (ticket.user_id) {
                    const userInfo = usersMap[ticket.user_id];
                    if (userInfo) {
                        userDisplay = `${escapeHtml(userInfo.username)} (${escapeHtml(userInfo.email)})`;
                    }
                }
                
                return `
                <tr>
                    <td>#${ticket.id}</td>
                    <td>${userDisplay}</td>
                    <td>${getSourceLabel(ticket.source)}</td>
                    <td>${escapeHtml(ticket.category || '-')}</td>
                    <td>
                        <span class="badge badge-priority-${(ticket.priority || 'medium').toLowerCase()}">
                            ${ticket.priority || 'MEDIUM'}
                        </span>
                    </td>
                    <td>
                        <span class="badge badge-${ticket.status.toLowerCase().replace('_', '-')}">
                            ${getStatusLabel(ticket.status)}
                        </span>
                    </td>
                    <td>${formatDate(ticket.created_at)}</td>
                    <td>
                        <button class="btn btn-primary" style="padding: 0.25rem 0.75rem; font-size: 0.85rem;" 
                                onclick="viewTicket(${ticket.id})">
                            Просмотр
                        </button>
                    </td>
                </tr>
            `;
            }).join('');
            
            // Обновляем статистику после загрузки тикетов
            loadStats();
        } else {
            tbody.innerHTML = '<tr><td colspan="8" class="loading" style="color: var(--color-error);">Ошибка загрузки: ' + (data.error || 'Неизвестная ошибка') + '</td></tr>';
        }
    } catch (error) {
        console.error('Error loading tickets:', error);
        if (error.name === 'AbortError') {
            tbody.innerHTML = '<tr><td colspan="8" class="loading" style="color: var(--color-error);">Таймаут загрузки. Попробуйте обновить страницу.</td></tr>';
        } else {
            tbody.innerHTML = '<tr><td colspan="8" class="loading" style="color: var(--color-error);">Ошибка загрузки. Проверьте подключение к серверу.</td></tr>';
        }
    }
}

// Просмотр деталей тикета
async function viewTicket(ticketId) {
    currentTicketId = ticketId;
    
    try {
        const response = await fetch(`/api/tickets/${ticketId}`, {
            credentials: 'same-origin'
        });
        
        if (response.status === 401 || response.status === 403) {
            window.location.href = '/login';
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            const ticket = data.ticket;
            
            document.getElementById('modalTicketId').textContent = ticket.id;
            document.getElementById('modalSource').textContent = getSourceLabel(ticket.source);
            document.getElementById('modalLanguage').textContent = ticket.language || '-';
            document.getElementById('modalCategory').textContent = ticket.category || '-';
            document.getElementById('modalPriority').textContent = ticket.priority || '-';
            document.getElementById('modalType').textContent = ticket.type || '-';
            document.getElementById('modalStatus').textContent = getStatusLabel(ticket.status);
            document.getElementById('modalText').textContent = ticket.text;
            document.getElementById('modalSummary').textContent = ticket.summary || '-';
            document.getElementById('modalAutoResponse').textContent = ticket.auto_response || '-';
            document.getElementById('modalLastResponse').value = ticket.last_response || '';
            document.getElementById('modalStatusSelect').value = ticket.status;
            
            // Показываем информацию о пользователе, если есть
            if (ticket.user_id) {
                loadUserInfo(ticket.user_id).then(userInfo => {
                    if (userInfo) {
                        document.getElementById('modalUserName').textContent = `${userInfo.username} (${userInfo.email})`;
                        document.getElementById('userInfoRow').style.display = 'flex';
                    }
                });
            } else {
                document.getElementById('userInfoRow').style.display = 'none';
            }
            
            document.getElementById('ticketModal').style.display = 'block';
        } else {
            alert('Ошибка загрузки тикета: ' + (data.error || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('Error loading ticket:', error);
        alert('Произошла ошибка при загрузке тикета');
    }
}

// Закрытие модального окна
function closeTicketModal() {
    document.getElementById('ticketModal').style.display = 'none';
    currentTicketId = null;
}

// Сохранение изменений тикета
async function saveTicketChanges() {
    if (!currentTicketId) return;
    
    const status = document.getElementById('modalStatusSelect').value;
    const lastResponse = document.getElementById('modalLastResponse').value.trim();
    
    // Валидация
    if (!lastResponse && status !== 'RESOLVED') {
        if (!confirm('Вы не ввели ответ. Продолжить без ответа?')) {
            return;
        }
    }
    
    if (status === 'RESOLVED' && !lastResponse) {
        alert('Для закрытия обращения необходимо указать ответ пользователю');
        return;
    }
    
    // Показываем индикатор загрузки
    const saveBtnText = document.getElementById('saveBtnText');
    const saveBtnLoader = document.getElementById('saveBtnLoader');
    
    if (saveBtnText) saveBtnText.style.display = 'none';
    if (saveBtnLoader) saveBtnLoader.style.display = 'inline-block';
    
    try {
        const response = await fetch(`/api/tickets/${currentTicketId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
            body: JSON.stringify({
                status: status,
                last_response: lastResponse || ''
            })
        });
        
        if (response.status === 401 || response.status === 403) {
            alert('Сессия истекла. Пожалуйста, войдите в систему снова.');
            window.location.href = '/login';
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            const successMsg = status === 'RESOLVED' 
                ? 'Обращение успешно закрыто!' 
                : 'Ответ сохранен!';
            alert(successMsg);
            closeTicketModal();
            loadTickets();
            loadStats();
        } else {
            alert('Ошибка сохранения: ' + (data.error || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('Error saving ticket:', error);
        alert('Произошла ошибка при сохранении');
    } finally {
        if (saveBtnText) saveBtnText.style.display = 'inline';
        if (saveBtnLoader) saveBtnLoader.style.display = 'none';
    }
}

// Закрытие модального окна при клике вне его
window.onclick = function(event) {
    const modal = document.getElementById('ticketModal');
    if (event.target === modal) {
        closeTicketModal();
    }
}

// Загрузка информации о пользователе
async function loadUserInfo(userId) {
    if (!userId) {
        return null;
    }
    
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000); // 3 секунды таймаут
        
        const response = await fetch(`/api/users/${userId}`, {
            credentials: 'same-origin',
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (response.status === 404) {
            console.warn(`User ${userId} not found`);
            return null;
        }
        
        if (response.status === 401 || response.status === 403) {
            console.warn(`Access denied for user ${userId}`);
            return null;
        }
        
        if (response.ok) {
            const data = await response.json();
            if (data.success && data.user) {
                return data.user;
            }
        }
    } catch (error) {
        if (error.name !== 'AbortError') {
            console.error('Error loading user info:', error);
        }
    }
    return null;
}

// Вспомогательные функции
function getStatusLabel(status) {
    const labels = {
        'OPEN': 'Открыт',
        'AUTO_CLOSED': 'Авто-закрыт',
        'IN_PROGRESS': 'В работе',
        'RESOLVED': 'Решён'
    };
    return labels[status] || status;
}

function getSourceLabel(source) {
    const labels = {
        'portal': 'Портал',
        'chat': 'Чат',
        'email': 'Email',
        'phone': '📞 Звонок'
    };
    return labels[source] || source;
}

function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('ru-RU', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function escapeHtml(text) {
    if (!text) return '-';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


// ========== CHAT FUNCTIONS ==========

// Загрузка ожидающих чатов
async function loadWaitingChats() {
    const container = document.getElementById('waitingChatsList');
    if (!container) return;
    
    try {
        // Показываем индикатор загрузки
        container.innerHTML = '<div class="loading">Загрузка...</div>';
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 секунд таймаут
        
        const response = await fetch('/api/chats?status=WAITING', {
            credentials: 'same-origin',
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (response.status === 401 || response.status === 403) {
            container.innerHTML = '<div class="no-messages">Требуется авторизация</div>';
            return;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            if (data.chats.length === 0) {
                container.innerHTML = '<div class="no-messages">Нет ожидающих чатов</div>';
                return;
            }
            
            container.innerHTML = data.chats.map(chat => {
                const time = new Date(chat.created_at).toLocaleString('ru-RU', {
                    hour: '2-digit',
                    minute: '2-digit'
                });
                const preview = chat.ticket ? (chat.ticket.text || '').substring(0, 50) + '...' : '';
                
                return `
                    <div class="waiting-chat-item" onclick="acceptChat(${chat.id})">
                        <div class="chat-item-header">
                            <span class="chat-item-user">👤 ${chat.user ? chat.user.username : 'Пользователь'}</span>
                            <span class="chat-item-time">${time}</span>
                        </div>
                        <div class="chat-item-preview">${escapeHtml(preview)}</div>
                        <button class="btn btn-primary" style="margin-top: 0.5rem; width: 100%;" onclick="event.stopPropagation(); acceptChat(${chat.id})">
                            ✅ Принять чат
                        </button>
                    </div>
                `;
            }).join('');
        } else {
            container.innerHTML = '<div class="no-messages" style="color: var(--color-error);">Ошибка загрузки: ' + (data.error || 'Неизвестная ошибка') + '</div>';
        }
    } catch (error) {
        console.error('Error loading waiting chats:', error);
        if (error.name === 'AbortError') {
            container.innerHTML = '<div class="no-messages" style="color: var(--color-error);">Таймаут загрузки. Попробуйте обновить страницу.</div>';
        } else {
            container.innerHTML = '<div class="no-messages" style="color: var(--color-error);">Ошибка загрузки чатов. Проверьте подключение.</div>';
        }
    }
}

// Загрузка активных чатов
async function loadActiveChats() {
    const container = document.getElementById('activeChatsList');
    if (!container) return;
    
    try {
        // Показываем индикатор загрузки
        container.innerHTML = '<div class="loading">Загрузка...</div>';
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 секунд таймаут
        
        const response = await fetch('/api/chats?status=ACTIVE', {
            credentials: 'same-origin',
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (response.status === 401 || response.status === 403) {
            container.innerHTML = '<div class="no-messages">Требуется авторизация</div>';
            return;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            if (data.chats.length === 0) {
                container.innerHTML = '<div class="no-messages">Нет активных чатов</div>';
                return;
            }
            
            container.innerHTML = data.chats.map(chat => {
                const time = new Date(chat.updated_at).toLocaleString('ru-RU', {
                    hour: '2-digit',
                    minute: '2-digit'
                });
                
                return `
                    <div class="waiting-chat-item" onclick="openChat(${chat.id})">
                        <div class="chat-item-header">
                            <span class="chat-item-user">👤 ${chat.user ? chat.user.username : 'Пользователь'}</span>
                            <span class="chat-item-time">${time}</span>
                        </div>
                        <div class="chat-item-preview">Активный чат - нажмите чтобы открыть</div>
                    </div>
                `;
            }).join('');
        } else {
            container.innerHTML = '<div class="no-messages" style="color: var(--color-error);">Ошибка загрузки: ' + (data.error || 'Неизвестная ошибка') + '</div>';
        }
    } catch (error) {
        console.error('Error loading active chats:', error);
        if (error.name === 'AbortError') {
            container.innerHTML = '<div class="no-messages" style="color: var(--color-error);">Таймаут загрузки. Попробуйте обновить страницу.</div>';
        } else {
            container.innerHTML = '<div class="no-messages" style="color: var(--color-error);">Ошибка загрузки чатов. Проверьте подключение.</div>';
        }
    }
}

// Принятие чата
async function acceptChat(chatId) {
    try {
        const response = await fetch(`/api/chats/${chatId}/accept`, {
            method: 'POST',
            credentials: 'same-origin'
        });
        
        if (response.status === 401 || response.status === 403) {
            alert('Ошибка доступа');
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            openChat(chatId);
            loadWaitingChats();
            loadActiveChats();
        } else {
            alert('Ошибка: ' + (data.error || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('Error accepting chat:', error);
        alert('Произошла ошибка при принятии чата');
    }
}

// Открытие чата
async function openChat(chatId) {
    currentChatId = chatId;
    
    // Сбрасываем отслеживание проанализированных сообщений для нового чата
    analyzedMessageIds.clear();
    
    // Показываем контейнер чата
    const chatContainer = document.getElementById('chatContainer');
    if (chatContainer) {
        chatContainer.style.display = 'grid';
    }
    
    // Загружаем информацию о чате
    await loadChatInfo(chatId);
    
    // Загружаем сообщения
    loadChatMessages();
    
    // Начинаем polling
    if (chatPollInterval) {
        clearInterval(chatPollInterval);
    }
    chatPollInterval = setInterval(loadChatMessages, 2000);
    
    // Прокручиваем страницу к чату
    if (chatContainer) {
        chatContainer.scrollIntoView({ behavior: 'smooth' });
    }
}

// Загрузка информации о чате
async function loadChatInfo(chatId) {
    try {
        const response = await fetch(`/api/chats/${chatId}`, {
            credentials: 'same-origin'
        });
        
        if (response.status === 401 || response.status === 403) {
            return;
        }
        
        const data = await response.json();
        if (data.success && data.chat) {
            const chat = data.chat;
            const titleEl = document.getElementById('chatHeaderTitle');
            const statusEl = document.getElementById('chatStatus');
            const ratingSection = document.getElementById('chatRatingSection');
            const ratingDisplay = document.getElementById('chatRatingDisplay');
            const ratingInput = document.getElementById('chatRatingInput');
            const chatInputContainer = document.getElementById('operatorChatInputContainer');
            
            if (titleEl) titleEl.textContent = `Чат #${chat.id} - ${chat.user ? chat.user.username : 'Пользователь'}`;
            
            // Обновляем статус
            if (statusEl) {
                if (chat.status === 'ACTIVE') {
                    statusEl.innerHTML = '<span class="status-badge status-active">✅ Активен</span>';
                } else if (chat.status === 'CLOSED') {
                    statusEl.innerHTML = '<span class="status-badge status-closed">🔒 Закрыт</span>';
                } else {
                    statusEl.innerHTML = '<span class="status-badge status-waiting">⏳ Ожидает</span>';
                }
            }
            
            // Показываем/скрываем поле ввода в зависимости от статуса
            if (chatInputContainer) {
                if (chat.status === 'CLOSED') {
                    chatInputContainer.style.display = 'none';
                } else {
                    chatInputContainer.style.display = 'block';
                }
            }
            
            // Показываем/скрываем кнопку голосового звонка
            const operatorChatActions = document.getElementById('operatorChatActions');
            if (operatorChatActions) {
                if (chat.status === 'ACTIVE') {
                    operatorChatActions.style.display = 'flex';
                } else {
                    operatorChatActions.style.display = 'none';
                }
            }
            
            // Показываем секцию оценки для закрытых чатов
            if (ratingSection) {
                if (chat.status === 'CLOSED') {
                    ratingSection.style.display = 'block';
                    
                    if (chat.rating) {
                        // Показываем оценку
                        ratingDisplay.innerHTML = getRatingStars(chat.rating);
                        ratingInput.style.display = 'none';
                    } else {
                        // Показываем возможность поставить оценку
                        ratingDisplay.innerHTML = 'Не оценено';
                        ratingInput.style.display = 'flex';
                    }
                } else {
                    ratingSection.style.display = 'none';
                }
            }
        }
    } catch (error) {
        console.error('Error loading chat info:', error);
    }
}

// Функция для отображения звезд оценки
function getRatingStars(rating) {
    let stars = '';
    for (let i = 1; i <= 5; i++) {
        if (i <= rating) {
            stars += '⭐';
        } else {
            stars += '☆';
        }
    }
    return stars + ` (${rating}/5)`;
}

// Оценка чата
async function rateChat(rating) {
    if (!currentChatId) return;
    
    if (!confirm(`Вы уверены, что хотите поставить оценку ${rating} из 5?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/chats/${currentChatId}/rate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
            body: JSON.stringify({ rating })
        });
        
        if (response.status === 401 || response.status === 403) {
            alert('Ошибка доступа');
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            // Обновляем информацию о чате
            await loadChatInfo(currentChatId);
            alert('Оценка успешно сохранена');
        } else {
            alert('Ошибка: ' + (data.error || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('Error rating chat:', error);
        alert('Произошла ошибка при сохранении оценки');
    }
}

// Загрузка сообщений чата
async function loadChatMessages() {
    if (!currentChatId) return;
    
    // Загружаем информацию о чате для обновления статуса и оценки
    await loadChatInfo(currentChatId);
    
    try {
        const response = await fetch(`/api/chats/${currentChatId}/messages`, {
            credentials: 'same-origin'
        });
        
        if (response.status === 401 || response.status === 403) {
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            displayChatMessages(data.messages);
            
            // Анализируем все новые сообщения от клиента для AI
            const userMessages = data.messages.filter(m => m.is_from_user);
            for (const message of userMessages) {
                // Проверяем, не анализировали ли мы уже это сообщение
                if (!analyzedMessageIds.has(message.id)) {
                    analyzedMessageIds.add(message.id);
                    // Анализируем сразу, без задержки для более быстрого ответа
                    analyzeMessageForAI(message.message, message.id);
                }
            }
        }
    } catch (error) {
        console.error('Error loading chat messages:', error);
    }
}

// Отображение сообщений в чате оператора
function displayChatMessages(messages) {
    const container = document.getElementById('operatorChatMessages');
    if (!container) return;
    
    if (messages.length === 0) {
        container.innerHTML = '<div class="no-messages">Пока нет сообщений</div>';
        return;
    }
    
    container.innerHTML = messages.map(msg => {
        const isFromUser = msg.is_from_user;
        const time = new Date(msg.created_at).toLocaleTimeString('ru-RU', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        
        return `
            <div class="message ${isFromUser ? 'message-other' : 'message-own'}">
                <div class="message-content">
                    <div class="message-text">${escapeHtml(msg.message)}</div>
                    <div class="message-time">${time}</div>
                </div>
            </div>
        `;
    }).join('');
    
    container.scrollTop = container.scrollHeight;
}

// Отправка сообщения оператором
async function sendOperatorMessage(messageText = null) {
    if (!currentChatId) return;
    
    const input = document.getElementById('operatorMessageInput');
    if (!input) return;
    
    const message = messageText || input.value.trim();
    if (!message) return;
    
    const sendBtn = document.getElementById('operatorSendBtn');
    if (!sendBtn) return;
    
    sendBtn.disabled = true;
    sendBtn.textContent = 'Отправка...';
    
    try {
        const response = await fetch(`/api/chats/${currentChatId}/messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
            body: JSON.stringify({ message })
        });
        
        if (response.status === 401 || response.status === 403) {
            alert('Ошибка доступа');
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            if (!messageText) {
                input.value = '';
            }
            loadChatMessages();
        } else {
            alert('Ошибка отправки: ' + (data.error || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('Error sending message:', error);
        alert('Произошла ошибка при отправке сообщения');
    } finally {
        sendBtn.disabled = false;
        sendBtn.textContent = 'Отправить';
    }
}

// Анализ сообщения клиента для AI-помощника
async function analyzeMessageForAI(messageText, messageId = null) {
    if (!messageText || messageText.length < 3) return;
    
    const aiContainer = document.getElementById('aiAssistantContent');
    if (!aiContainer) return;
    
    // Показываем индикатор анализа
    aiContainer.innerHTML = `
        <div style="padding: 1rem; text-align: center; color: var(--color-text-light);">
            <div class="loading-spinner" style="margin: 0 auto 0.5rem;"></div>
            <div>AI анализирует сообщение клиента...</div>
        </div>
    `;
    
    // Очищаем предыдущий таймаут для этого сообщения
    if (aiAnalysisTimeout) {
        clearTimeout(aiAnalysisTimeout);
    }
    
    // Минимальная задержка для быстрого анализа (300мс вместо 1 секунды)
    aiAnalysisTimeout = setTimeout(async () => {
        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin',
                body: JSON.stringify({ text: messageText })
            });
            
            if (response.status === 401 || response.status === 403) {
                return;
            }
            
            const data = await response.json();
            
            if (data.success && data.analysis) {
                const analysis = data.analysis;
                
                // Формируем HTML с советами
                let adviceHTML = '<div style="line-height: 1.6;">';
                
                if (analysis.advice) {
                    const formattedAdvice = escapeHtml(analysis.advice)
                        .replace(/\n/g, '<br>')
                        .replace(/(\d+\.\s)/g, '<strong style="color: #27ae60; font-weight: 600;">$1</strong>');
                    adviceHTML += `<div style="background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); padding: 1rem; border-radius: 8px; margin-bottom: 0.75rem; border-left: 4px solid #27ae60; box-shadow: 0 2px 8px rgba(39, 174, 96, 0.15);">`;
                    adviceHTML += `<strong style="color: #27ae60; display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.75rem; font-size: 1rem; font-weight: 600;">💡 Рекомендуемый ответ</strong>`;
                    adviceHTML += `<div style="color: #2c3e50; white-space: pre-wrap; line-height: 1.8; font-size: 0.9375rem;">${formattedAdvice}</div>`;
                    adviceHTML += `</div>`;
                }
                
                if (analysis.summary) {
                    adviceHTML += `<div style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); padding: 1rem; border-radius: 8px; margin-bottom: 0.75rem; border-left: 4px solid #2196f3; box-shadow: 0 2px 8px rgba(33, 150, 243, 0.15);">`;
                    adviceHTML += `<strong style="color: #2196f3; display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.75rem; font-size: 1rem; font-weight: 600;">📋 Резюме</strong>`;
                    adviceHTML += `<div style="color: #2c3e50; line-height: 1.7; font-size: 0.9375rem;">${escapeHtml(analysis.summary)}</div>`;
                    adviceHTML += `</div>`;
                }
                
                if (analysis.category || analysis.priority) {
                    adviceHTML += `<div style="display: flex; gap: 0.75rem; flex-wrap: wrap; margin-top: 0.75rem; padding: 0.75rem; background: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0;">`;
                    if (analysis.category) {
                        adviceHTML += `<span style="background: linear-gradient(135deg, #fff3cd 0%, #ffe082 100%); padding: 0.5rem 1rem; border-radius: 20px; font-size: 0.875rem; font-weight: 500; color: #856404; box-shadow: 0 2px 4px rgba(255, 193, 7, 0.2);"><strong>📁</strong> ${escapeHtml(analysis.category)}</span>`;
                    }
                    if (analysis.priority) {
                        const priorityColors = {
                            'LOW': 'linear-gradient(135deg, #95a5a6 0%, #7f8c8d 100%)',
                            'MEDIUM': 'linear-gradient(135deg, #3498db 0%, #2980b9 100%)',
                            'HIGH': 'linear-gradient(135deg, #f39c12 0%, #e67e22 100%)',
                            'CRITICAL': 'linear-gradient(135deg, #e74c3c 0%, #c0392b 100%)'
                        };
                        const priorityColor = priorityColors[analysis.priority] || priorityColors['MEDIUM'];
                        adviceHTML += `<span style="background: ${priorityColor}; color: white; padding: 0.5rem 1rem; border-radius: 20px; font-size: 0.875rem; font-weight: 500; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);"><strong>⚡</strong> ${escapeHtml(analysis.priority)}</span>`;
                    }
                    adviceHTML += `</div>`;
                }
                
                adviceHTML += '</div>';
                aiContainer.innerHTML = adviceHTML;
            }
        } catch (error) {
            console.error('Error analyzing message:', error);
            aiContainer.innerHTML = '<div style="color: #e74c3c; padding: 1rem;">Ошибка при анализе</div>';
        }
    }, 300); // Уменьшена задержка до 300мс для более быстрого анализа
}

// Очистка при закрытии страницы
window.addEventListener('beforeunload', function() {
    if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
    }
    if (chatPollInterval) {
        clearInterval(chatPollInterval);
    }
});

// Переменные для карты выбора адреса
let addressMap = null;
let addressMarker = null;
let selectedLat = null;
let selectedLon = null;

// Открытие модального окна для выбора специалиста
async function openSpecialistModal() {
    if (!currentChatId) {
        alert('Сначала откройте чат');
        return;
    }
    
    const modal = document.getElementById('specialistModal');
    const specialistSelect = document.getElementById('specialistSelect');
    
    // Загружаем список онлайн специалистов
    specialistSelect.innerHTML = '<option value="">Загрузка...</option>';
    modal.style.display = 'block';
    
    // Инициализируем карту для выбора адреса
    setTimeout(() => {
        initAddressMap();
    }, 100);
    
    try {
        const response = await fetch('/api/specialists/online', {
            credentials: 'same-origin'
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success && data.specialists.length > 0) {
                specialistSelect.innerHTML = '<option value="">Выберите специалиста</option>';
                data.specialists.forEach(spec => {
                    const option = document.createElement('option');
                    option.value = spec.id;
                    option.textContent = `${spec.username}${spec.department ? ' - ' + spec.department : ''}`;
                    specialistSelect.appendChild(option);
                });
            } else {
                specialistSelect.innerHTML = '<option value="">Нет онлайн специалистов</option>';
            }
        } else {
            alert('Ошибка загрузки специалистов');
        }
    } catch (error) {
        console.error('Error loading specialists:', error);
        alert('Ошибка загрузки специалистов');
    }
}

// Закрытие модального окна
function closeSpecialistModal() {
    document.getElementById('specialistModal').style.display = 'none';
    document.getElementById('clientAddress').value = '';
    document.getElementById('specialistSelect').value = '';
    selectedLat = null;
    selectedLon = null;
    
    // Очищаем карту
    if (addressMarker && addressMap) {
        addressMap.removeLayer(addressMarker);
        addressMarker = null;
    }
}

// Инициализация карты для выбора адреса
function initAddressMap() {
    const mapContainer = document.getElementById('addressMapContainer');
    const placeholder = document.getElementById('addressMapPlaceholder');
    
    if (!mapContainer) return;
    
    // Проверяем, загружен ли 2GIS API
    if (typeof DG === 'undefined') {
        // Загружаем скрипт 2GIS
        const script = document.createElement('script');
        script.src = 'https://maps.api.2gis.ru/2.0/loader.js?pkg=full';
        script.async = true;
        script.onload = function() {
            setTimeout(() => {
                createAddressMap();
            }, 200);
        };
        script.onerror = function() {
            placeholder.innerHTML = '<div style="color: #e74c3c;">Ошибка загрузки карты</div>';
        };
        document.head.appendChild(script);
    } else {
        if (typeof DG.then === 'function') {
            DG.then(function() {
                createAddressMap();
            });
        } else {
            createAddressMap();
        }
    }
}

// Создание карты для выбора адреса
function createAddressMap() {
    const mapContainer = document.getElementById('addressMapContainer');
    const placeholder = document.getElementById('addressMapPlaceholder');
    
    if (!mapContainer || typeof DG === 'undefined') return;
    
    try {
        // Скрываем placeholder
        if (placeholder) placeholder.style.display = 'none';
        
        // Создаем карту с центром в Алматы
        addressMap = DG.map('addressMapContainer', {
            center: [51.1694, 71.4491],
            zoom: 13
        });
        
        // Обработчик клика на карте
        addressMap.on('click', async function(e) {
            const lat = e.latlng.lat;
            const lon = e.latlng.lng;
            
            selectedLat = lat;
            selectedLon = lon;
            
            // Удаляем предыдущий маркер
            if (addressMarker) {
                addressMap.removeLayer(addressMarker);
            }
            
            // Добавляем новый маркер
            addressMarker = DG.marker([lat, lon]);
            addressMarker.addTo(addressMap);
            addressMarker.bindPopup('Выбранная точка').openPopup();
            
            // Получаем адрес по координатам через геокодинг
            await geocodeAddress(lat, lon);
        });
        
        console.log('Address map initialized');
    } catch (error) {
        console.error('Error creating address map:', error);
        if (placeholder) {
            placeholder.innerHTML = '<div style="color: #e74c3c;">Ошибка создания карты</div>';
        }
    }
}

// Геокодинг - получение адреса по координатам
async function geocodeAddress(lat, lon) {
    const addressInput = document.getElementById('clientAddress');
    const coordinatesDiv = document.getElementById('selectedCoordinates');
    const latLonSpan = document.getElementById('selectedLatLon');
    const mapHint = document.getElementById('mapHint');
    
    if (!addressInput) return;
    
    // Показываем координаты
    if (latLonSpan) {
        latLonSpan.textContent = `${lat.toFixed(6)}, ${lon.toFixed(6)}`;
    }
    if (coordinatesDiv) {
        coordinatesDiv.style.display = 'block';
    }
    
    // Показываем загрузку
    addressInput.value = 'Получение адреса...';
    if (mapHint) {
        mapHint.textContent = 'Получение адреса...';
        mapHint.style.color = '#3b82f6';
    }
    
    try {
        // Используем 2GIS Geocoding API для получения адреса
        const apiKey = typeof TGIS_API_KEY !== 'undefined' ? TGIS_API_KEY : '';
        const geocodeUrl = 'https://catalog.api.2gis.com/geo/search';
        const params = new URLSearchParams({
            key: apiKey,
            q: `${lat},${lon}`,
            type: 'building',
            fields: 'items.full_name,items.point'
        });
        
        const response = await fetch(`${geocodeUrl}?${params.toString()}`);
        
        if (response.ok) {
            const data = await response.json();
            
            if (data.result && data.result.items && data.result.items.length > 0) {
                const address = data.result.items[0].full_name || data.result.items[0].name;
                addressInput.value = address;
                
                if (mapHint) {
                    mapHint.textContent = 'Адрес получен! Вы можете изменить его вручную';
                    mapHint.style.color = '#10b981';
                }
            } else {
                // Если не нашли адрес, используем координаты
                addressInput.value = `${lat.toFixed(6)}, ${lon.toFixed(6)}`;
                if (mapHint) {
                    mapHint.textContent = 'Адрес не найден, используются координаты';
                    mapHint.style.color = '#f59e0b';
                }
            }
        } else {
            // Если API не работает, используем координаты
            addressInput.value = `${lat.toFixed(6)}, ${lon.toFixed(6)}`;
            if (mapHint) {
                mapHint.textContent = 'Используются координаты (геокодинг недоступен)';
                mapHint.style.color = '#f59e0b';
            }
        }
    } catch (error) {
        console.error('Error geocoding address:', error);
        // В случае ошибки используем координаты
        addressInput.value = `${lat.toFixed(6)}, ${lon.toFixed(6)}`;
        if (mapHint) {
            mapHint.textContent = 'Ошибка получения адреса, используются координаты';
            mapHint.style.color = '#e74c3c';
        }
    }
}

// Отправка специалиста
async function sendSpecialist() {
    const chatId = currentChatId;
    const specialistId = document.getElementById('specialistSelect').value;
    const clientAddress = document.getElementById('clientAddress').value.trim();
    
    if (!specialistId) {
        alert('Выберите специалиста');
        return;
    }
    
    if (!clientAddress) {
        alert('Введите адрес клиента или выберите его на карте');
        return;
    }
    
    const sendBtnText = document.getElementById('sendSpecialistBtnText');
    const sendBtnLoader = document.getElementById('sendSpecialistBtnLoader');
    
    if (sendBtnText) sendBtnText.style.display = 'none';
    if (sendBtnLoader) sendBtnLoader.style.display = 'inline-block';
    
    // Формируем данные для отправки
    const dispatchData = {
        chat_id: chatId,
        specialist_id: parseInt(specialistId),
        client_address: clientAddress
    };
    
    // Если были выбраны координаты на карте, добавляем их
    if (selectedLat && selectedLon) {
        dispatchData.client_latitude = selectedLat.toString();
        dispatchData.client_longitude = selectedLon.toString();
    }
    
    try {
        const response = await fetch('/api/dispatches', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
            body: JSON.stringify(dispatchData)
        });
        
        if (response.status === 401 || response.status === 403) {
            alert('Ошибка доступа');
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            // Отправляем сообщение в чат о том, что специалист отправлен
            const routeUrl = `/route/${data.dispatch.id}`;
            const message = `👨‍🔧 Специалист ${data.dispatch.specialist.username} отправлен к вам по адресу: ${clientAddress}\n\n[ROUTE_BUTTON:${routeUrl}]`;
            await sendOperatorMessage(message);
            
            alert('Специалист успешно отправлен! Клиент получит уведомление с ссылкой на маршрут.');
            closeSpecialistModal();
            
            // Не открываем маршрут автоматически для оператора - клиент увидит кнопку в сообщении
        } else {
            alert('Ошибка: ' + (data.error || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('Error sending specialist:', error);
        alert('Произошла ошибка при отправке специалиста');
    } finally {
        if (sendBtnText) sendBtnText.style.display = 'inline';
        if (sendBtnLoader) sendBtnLoader.style.display = 'none';
    }
}

// Делаем функции глобальными для использования в onclick
// Присваиваем их в window после определения всех функций
// Все функции уже определены выше, теперь экспортируем их в window
window.loadWaitingChats = loadWaitingChats;
window.openSpecialistModal = openSpecialistModal;
window.closeSpecialistModal = closeSpecialistModal;
window.sendSpecialist = sendSpecialist;
window.loadActiveChats = loadActiveChats;
// Начало голосового звонка
function startVoiceCall() {
    if (!currentChatId) {
        alert('Выберите чат для звонка');
        return;
    }
    window.location.href = `/voice/call/${currentChatId}`;
}

window.acceptChat = acceptChat;
window.openChat = openChat;
window.rateChat = rateChat;
window.toggleOperatorStatus = toggleOperatorStatus;
window.startVoiceCall = startVoiceCall;
window.loadTickets = loadTickets;
window.loadStats = loadStats;
window.viewTicket = viewTicket;
window.closeTicketModal = closeTicketModal;
window.saveTicketChanges = saveTicketChanges;


// Панель специалиста: загрузка тикетов только своего отдела (без приёма звонков)

let currentTicketId = null;

// Heartbeat для поддержания онлайн статуса
let specialistHeartbeatInterval = null;

async function updateSpecialistActivity() {
    try {
        await fetch('/api/specialists/heartbeat', {
            method: 'POST',
            credentials: 'same-origin'
        });
    } catch (error) {
        console.error('Error updating specialist activity:', error);
    }
}

// Загрузка при открытии страницы
document.addEventListener('DOMContentLoaded', function() {
    // Сразу обновляем активность
    updateSpecialistActivity();
    
    // Обновляем активность каждые 2 минуты
    specialistHeartbeatInterval = setInterval(() => {
        updateSpecialistActivity();
    }, 120000); // 2 минуты
    
    loadStats();
    loadTickets();
    loadPendingDispatches();
    
    // Обработчики фильтров
    document.getElementById('filterStatus').addEventListener('change', loadTickets);
    document.getElementById('filterPriority').addEventListener('change', loadTickets);
    document.getElementById('filterSource').addEventListener('change', loadTickets);
    
    // Автоматическое обновление тикетов каждые 30 секунд
    setInterval(function() {
        loadTickets(false); // Не показываем лоадер при автообновлении
        loadStats();
        loadPendingDispatches();
    }, 30000); // 30 секунд
});

// Загрузка ожидающих запросов от операторов
async function loadPendingDispatches() {
    try {
        const response = await fetch('/api/dispatches/pending', {
            credentials: 'same-origin'
        });
        
        if (response.status === 401 || response.status === 403) {
            return;
        }
        
        if (response.ok) {
            const data = await response.json();
            const section = document.getElementById('pendingDispatchesSection');
            const list = document.getElementById('pendingDispatchesList');
            
            if (data.success && data.dispatches && data.dispatches.length > 0) {
                if (section) section.style.display = 'block';
                
                if (list) {
                    list.innerHTML = data.dispatches.map(dispatch => {
                        const time = new Date(dispatch.created_at).toLocaleString('ru-RU', {
                            day: '2-digit',
                            month: '2-digit',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                        });
                        
                        return `
                            <div class="pending-dispatch-card">
                                <div class="pending-dispatch-info">
                                    <div class="pending-dispatch-client">
                                        👤 Клиент: ${dispatch.user ? dispatch.user.username : 'Неизвестно'}
                                    </div>
                                    <div class="pending-dispatch-address">
                                        📍 Адрес: ${dispatch.client_address || 'Не указан'}
                                    </div>
                                    <div class="pending-dispatch-time">
                                        ⏰ ${time}
                                    </div>
                                </div>
                                <div class="pending-dispatch-actions">
                                    <button class="btn btn-success btn-sm" onclick="acceptDispatchFromList(${dispatch.id})">
                                        ✓ Принять
                                    </button>
                                    <a href="/route/${dispatch.id}" class="btn btn-primary btn-sm" style="text-decoration: none; color: white;">
                                        🗺️ Маршрут
                                    </a>
                                </div>
                            </div>
                        `;
                    }).join('');
                }
            } else {
                if (section) section.style.display = 'none';
                if (list) list.innerHTML = '';
            }
        }
    } catch (error) {
        console.error('Error loading pending dispatches:', error);
    }
}

// Принятие запроса из списка
async function acceptDispatchFromList(dispatchId) {
    if (!confirm('Принять этот запрос от оператора?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/dispatches/${dispatchId}/accept`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin'
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                alert('Запрос принят! Теперь клиент может видеть маршрут.');
                loadPendingDispatches();
                // Обновляем ссылку на маршрут в навигации
                const routeLink = document.getElementById('routeLink');
                if (routeLink) {
                    routeLink.href = `/route/${dispatchId}`;
                    routeLink.style.display = 'inline-block';
                }
            } else {
                alert('Ошибка: ' + (data.error || 'Неизвестная ошибка'));
            }
        } else {
            alert('Ошибка принятия запроса');
        }
    } catch (error) {
        console.error('Error accepting dispatch:', error);
        alert('Произошла ошибка при принятии запроса');
    }
}

// Экспортируем функции
window.acceptDispatchFromList = acceptDispatchFromList;

// Загрузка статистики
async function loadStats() {
    try {
        const response = await fetch('/api/tickets?specialist_view=true', {
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
    params.append('specialist_view', 'true'); // Используем specialist_view для специалистов
    if (status) params.append('status', status);
    if (priority) params.append('priority', priority);
    if (source) params.append('source', source);
    
    const url = '/api/tickets?' + params.toString();
    
    const tbody = document.getElementById('ticketsTableBody');
    if (showLoader) {
        tbody.innerHTML = '<tr><td colspan="8" class="loading"><div class="loading-spinner"></div><div>Загрузка обращений...</div></td></tr>';
    }
    
    try {
        const response = await fetch(url, {
            credentials: 'same-origin'
        });
        
        if (response.status === 401 || response.status === 403) {
            window.location.href = '/login';
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            const tickets = data.tickets;
            
            if (tickets.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" class="loading">Тикетов не найдено</td></tr>';
                return;
            }
            
            // Загружаем информацию о пользователях для всех тикетов
            const userIds = [...new Set(tickets.filter(t => t.user_id).map(t => t.user_id))];
            const usersMap = {};
            
            // Загружаем информацию о пользователях параллельно
            await Promise.all(userIds.map(async (userId) => {
                const userInfo = await loadUserInfo(userId);
                if (userInfo) {
                    usersMap[userId] = userInfo;
                }
            }));
            
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
            tbody.innerHTML = '<tr><td colspan="8" class="loading">Ошибка загрузки</td></tr>';
        }
    } catch (error) {
        console.error('Error loading tickets:', error);
        tbody.innerHTML = '<tr><td colspan="8" class="loading">Ошибка загрузки</td></tr>';
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
        const response = await fetch(`/api/users/${userId}`, {
            credentials: 'same-origin'
        });
        
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
        console.error('Error loading user info:', error);
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


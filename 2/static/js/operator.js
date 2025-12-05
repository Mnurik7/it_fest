// Панель оператора: загрузка тикетов только своего отдела + приём звонков

let currentTicketId = null;

// Загрузка при открытии страницы
document.addEventListener('DOMContentLoaded', function() {
    loadStats();
    loadTickets();
    
    // Обработчики фильтров
    document.getElementById('filterStatus').addEventListener('change', loadTickets);
    document.getElementById('filterPriority').addEventListener('change', loadTickets);
    document.getElementById('filterSource').addEventListener('change', loadTickets);
    
    // Обработчик формы приёма звонка
    const callForm = document.getElementById('callForm');
    if (callForm) {
        callForm.addEventListener('submit', handleCallSubmit);
    }
    
    // Делаем функции глобальными для использования в onclick
    window.startRealtimeCall = startRealtimeCall;
    window.endRealtimeCall = endRealtimeCall;
    window.saveRealtimeCall = saveRealtimeCall;
    
    // Автоматическое обновление тикетов каждые 30 секунд
    setInterval(function() {
        loadTickets(false); // Не показываем лоадер при автообновлении
        loadStats();
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

// Переменные для режима реального времени
let realtimeCallActive = false;
let aiAnalysisTimeout = null;
let lastAnalyzedText = '';

// Начало звонка в реальном времени
function startRealtimeCall() {
    const callerName = document.getElementById('callerName').value.trim();
    const callerPhone = document.getElementById('callerPhone').value.trim();
    
    if (!callerName || !callerPhone) {
        alert('Введите имя и телефон звонящего перед началом звонка');
        return;
    }
    
    // Переключаем режимы
    document.getElementById('quickCallMode').style.display = 'none';
    document.getElementById('realtimeCallMode').style.display = 'block';
    
    // Заполняем данные в режиме реального времени
    document.getElementById('callerNameRealtime').value = callerName;
    document.getElementById('callerPhoneRealtime').value = callerPhone;
    
    realtimeCallActive = true;
    lastAnalyzedText = '';
    
    // Добавляем обработчик для текстового поля
    const realtimeTextarea = document.getElementById('realtimeCallText');
    realtimeTextarea.addEventListener('input', handleRealtimeInput);
    realtimeTextarea.focus();
}

// Завершение звонка в реальном времени
function endRealtimeCall() {
    realtimeCallActive = false;
    if (aiAnalysisTimeout) {
        clearTimeout(aiAnalysisTimeout);
        aiAnalysisTimeout = null;
    }
    
    // Переключаем режимы
    document.getElementById('realtimeCallMode').style.display = 'none';
    document.getElementById('quickCallMode').style.display = 'block';
    
    // Очищаем поля
    document.getElementById('realtimeCallText').value = '';
    document.getElementById('aiAdviceRealtime').innerHTML = '<div class="empty-advice-message"><div class="empty-icon">🤖</div><div>Начните вводить текст звонка, и ИИ начнёт давать советы...</div></div>';
    document.getElementById('callForm').reset();
    lastAnalyzedText = '';
}

// Обработка ввода в реальном времени
function handleRealtimeInput() {
    if (!realtimeCallActive) return;
    
    const text = document.getElementById('realtimeCallText').value.trim();
    
    // Если текст слишком короткий, не анализируем
    if (text.length < 10) {
        return;
    }
    
    // Если текст не изменился, не анализируем повторно
    if (text === lastAnalyzedText) {
        return;
    }
    
    // Очищаем предыдущий таймаут
    if (aiAnalysisTimeout) {
        clearTimeout(aiAnalysisTimeout);
    }
    
    // Устанавливаем новый таймаут (анализ через 3 секунды после остановки ввода)
    aiAnalysisTimeout = setTimeout(() => {
        analyzeRealtimeCall(text);
    }, 3000);
}

// Анализ звонка в реальном времени
async function analyzeRealtimeCall(text) {
    if (!realtimeCallActive || text.length < 10) return;
    
    // Показываем индикатор анализа
    const analyzingEl = document.getElementById('aiAnalyzing');
    if (analyzingEl) analyzingEl.style.display = 'inline';
    const adviceContainer = document.getElementById('aiAdviceRealtime');
    
    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
            body: JSON.stringify({ text: text })
        });
        
        if (response.status === 401 || response.status === 403) {
            alert('Сессия истекла. Пожалуйста, войдите в систему снова.');
            window.location.href = '/login';
            return;
        }
        
        const data = await response.json();
        
        if (data.success && data.analysis) {
            const analysis = data.analysis;
            lastAnalyzedText = text;
            
            // Формируем HTML с советами
            let adviceHTML = '<div style="line-height: 1.6;">';
            
            if (analysis.advice) {
                adviceHTML += `<div style="background: #e8f5e9; padding: 0.75rem; border-radius: 4px; margin-bottom: 0.75rem; border-left: 4px solid #27ae60;">`;
                adviceHTML += `<strong style="color: #27ae60; display: block; margin-bottom: 0.5rem;">💡 Совет для оператора:</strong>`;
                adviceHTML += `<div style="color: #2c3e50;">${escapeHtml(analysis.advice)}</div>`;
                adviceHTML += `</div>`;
            }
            
            if (analysis.summary) {
                adviceHTML += `<div style="background: #e3f2fd; padding: 0.75rem; border-radius: 4px; margin-bottom: 0.75rem; border-left: 4px solid #2196f3;">`;
                adviceHTML += `<strong style="color: #2196f3; display: block; margin-bottom: 0.5rem;">📋 Резюме:</strong>`;
                adviceHTML += `<div style="color: #2c3e50;">${escapeHtml(analysis.summary)}</div>`;
                adviceHTML += `</div>`;
            }
            
            if (analysis.category) {
                adviceHTML += `<div style="display: flex; gap: 1rem; flex-wrap: wrap; margin-top: 0.75rem;">`;
                adviceHTML += `<span style="background: #fff3cd; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.85rem;"><strong>Категория:</strong> ${escapeHtml(analysis.category)}</span>`;
                if (analysis.priority) {
                    const priorityColors = {
                        'LOW': '#95a5a6',
                        'MEDIUM': '#3498db',
                        'HIGH': '#f39c12',
                        'CRITICAL': '#e74c3c'
                    };
                    const priorityColor = priorityColors[analysis.priority] || '#3498db';
                    adviceHTML += `<span style="background: ${priorityColor}; color: white; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.85rem;"><strong>Приоритет:</strong> ${escapeHtml(analysis.priority)}</span>`;
                }
                if (analysis.department) {
                    adviceHTML += `<span style="background: #667eea; color: white; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.85rem;"><strong>Отдел:</strong> ${escapeHtml(analysis.department)}</span>`;
                }
                adviceHTML += `</div>`;
            }
            
            adviceHTML += '</div>';
            
            adviceContainer.innerHTML = adviceHTML;
            adviceContainer.scrollTop = adviceContainer.scrollHeight;
        }
    } catch (error) {
        console.error('Error analyzing realtime call:', error);
        adviceContainer.innerHTML = '<div style="color: #e74c3c; padding: 1rem;">Ошибка при анализе. Попробуйте еще раз.</div>';
    } finally {
        if (analyzingEl) analyzingEl.style.display = 'none';
    }
}

// Сохранение звонка в реальном времени как тикет
async function saveRealtimeCall() {
    if (!realtimeCallActive) return;
    
    const callerName = document.getElementById('callerNameRealtime').value.trim();
    const callerPhone = document.getElementById('callerPhoneRealtime').value.trim();
    const callText = document.getElementById('realtimeCallText').value.trim();
    
    if (!callerName || !callerPhone || !callText) {
        alert('Заполните все поля');
        return;
    }
    
    // Формируем текст тикета с информацией о звонке
    const ticketText = `Звонок от: ${callerName}\nТелефон: ${callerPhone}\n\nТекст разговора:\n${callText}`;
    
    // Показываем индикатор загрузки
    const saveBtnText = document.getElementById('saveCallBtnText');
    const saveBtnLoader = document.getElementById('saveCallBtnLoader');
    
    if (saveBtnText) saveBtnText.style.display = 'none';
    if (saveBtnLoader) saveBtnLoader.style.display = 'inline-block';
    
    try {
        const response = await fetch('/api/tickets', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
            body: JSON.stringify({
                text: ticketText,
                source: 'phone'
            })
        });
        
        if (response.status === 401 || response.status === 403) {
            alert('Сессия истекла. Пожалуйста, войдите в систему снова.');
            window.location.href = '/login';
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            alert('Звонок успешно сохранён как тикет!');
            endRealtimeCall();
            loadTickets();
            loadStats();
        } else {
            alert('Ошибка при сохранении звонка: ' + (data.error || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('Error saving realtime call:', error);
        alert('Произошла ошибка при сохранении звонка');
    } finally {
        if (saveBtnText) saveBtnText.style.display = 'inline';
        if (saveBtnLoader) saveBtnLoader.style.display = 'none';
    }
}

// Обработка приёма звонка (быстрый режим)
async function handleCallSubmit(e) {
    e.preventDefault();
    
    const callerName = document.getElementById('callerName').value.trim();
    const callerPhone = document.getElementById('callerPhone').value.trim();
    const callText = document.getElementById('callText').value.trim();
    
    if (!callerName || !callerPhone || !callText) {
        alert('Заполните все поля');
        return;
    }
    
    // Формируем текст тикета с информацией о звонке
    const ticketText = `Звонок от: ${callerName}\nТелефон: ${callerPhone}\n\nСуть обращения:\n${callText}`;
    
    // Показываем индикатор загрузки
    const callBtnText = document.getElementById('callBtnText');
    const callBtnLoader = document.getElementById('callBtnLoader');
    
    if (callBtnText) callBtnText.style.display = 'none';
    if (callBtnLoader) callBtnLoader.style.display = 'inline-block';
    
    try {
        const response = await fetch('/api/tickets', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
            body: JSON.stringify({
                text: ticketText,
                source: 'phone'
            })
        });
        
        if (response.status === 401 || response.status === 403) {
            alert('Сессия истекла. Пожалуйста, войдите в систему снова.');
            window.location.href = '/login';
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            alert('Звонок успешно зарегистрирован!');
            document.getElementById('callForm').reset();
            loadTickets();
            loadStats();
        } else {
            alert('Ошибка при регистрации звонка: ' + (data.error || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('Error creating call ticket:', error);
        alert('Произошла ошибка при регистрации звонка');
    } finally {
        if (callBtnText) callBtnText.style.display = 'inline';
        if (callBtnLoader) callBtnLoader.style.display = 'none';
    }
}


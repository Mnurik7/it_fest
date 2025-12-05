// Админ-панель: загрузка тикетов, статистики, управление

let currentTicketId = null;

// Загрузка при открытии страницы
document.addEventListener('DOMContentLoaded', function() {
    loadStats();
    loadTickets();
    
    // Обработчики фильтров
    document.getElementById('filterStatus').addEventListener('change', loadTickets);
    document.getElementById('filterDepartment').addEventListener('change', loadTickets);
    document.getElementById('filterSource').addEventListener('change', loadTickets);
});

// Загрузка статистики
async function loadStats() {
    try {
        const response = await fetch('/api/stats', {
            credentials: 'same-origin'
        });
        
        if (response.status === 401 || response.status === 403) {
            window.location.href = '/login';
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            const stats = data.stats;
            
            document.getElementById('statTotal').textContent = stats.total;
            document.getElementById('statAutoClosed').textContent = stats.auto_closed;
            document.getElementById('statAutoPercent').textContent = stats.auto_closed_percent + '%';
            document.getElementById('statAvgTime').textContent = Math.round(stats.avg_response_time_seconds);
            
            // Обновляем список отделов в фильтре
            const deptSelect = document.getElementById('filterDepartment');
            const currentValue = deptSelect.value;
            deptSelect.innerHTML = '<option value="">Все</option>';
            
            for (const [dept, count] of Object.entries(stats.department_counts)) {
                const option = document.createElement('option');
                option.value = dept;
                option.textContent = `${dept} (${count})`;
                deptSelect.appendChild(option);
            }
            
            deptSelect.value = currentValue;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Загрузка списка тикетов
async function loadTickets() {
    const status = document.getElementById('filterStatus').value;
    const department = document.getElementById('filterDepartment').value;
    const source = document.getElementById('filterSource').value;
    
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (department) params.append('department', department);
    if (source) params.append('source', source);
    
    const url = '/api/tickets' + (params.toString() ? '?' + params.toString() : '');
    
    const tbody = document.getElementById('ticketsTableBody');
    tbody.innerHTML = '<tr><td colspan="9" class="loading">Загрузка...</td></tr>';
    
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
                tbody.innerHTML = '<tr><td colspan="9" class="loading">Тикетов не найдено</td></tr>';
                return;
            }
            
            tbody.innerHTML = tickets.map(ticket => `
                <tr>
                    <td>#${ticket.id}</td>
                    <td>${escapeHtml(ticket.source)}</td>
                    <td>${escapeHtml(ticket.category || '-')}</td>
                    <td>
                        <span class="badge badge-priority-${(ticket.priority || 'medium').toLowerCase()}">
                            ${ticket.priority || 'MEDIUM'}
                        </span>
                    </td>
                    <td>${escapeHtml(ticket.department || '-')}</td>
                    <td>
                        <span class="badge badge-${ticket.status.toLowerCase().replace('_', '-')}">
                            ${getStatusLabel(ticket.status)}
                        </span>
                    </td>
                    <td>
                        <span class="badge ${ticket.is_auto_closed ? 'badge-yes' : 'badge-no'}">
                            ${ticket.is_auto_closed ? 'Да' : 'Нет'}
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
            `).join('');
            
            // Обновляем статистику после загрузки тикетов
            loadStats();
        } else {
            tbody.innerHTML = '<tr><td colspan="9" class="loading">Ошибка загрузки</td></tr>';
        }
    } catch (error) {
        console.error('Error loading tickets:', error);
        tbody.innerHTML = '<tr><td colspan="9" class="loading">Ошибка загрузки</td></tr>';
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
            document.getElementById('modalSource').textContent = ticket.source;
            document.getElementById('modalLanguage').textContent = ticket.language || '-';
            document.getElementById('modalCategory').textContent = ticket.category || '-';
            document.getElementById('modalPriority').textContent = ticket.priority || '-';
            document.getElementById('modalType').textContent = ticket.type || '-';
            document.getElementById('modalDepartment').textContent = ticket.department || '-';
            document.getElementById('modalStatus').textContent = getStatusLabel(ticket.status);
            document.getElementById('modalText').textContent = ticket.text;
            document.getElementById('modalSummary').textContent = ticket.summary || '-';
            document.getElementById('modalAutoResponse').textContent = ticket.auto_response || '-';
            document.getElementById('modalLastResponse').value = ticket.last_response || '';
            document.getElementById('modalStatusSelect').value = ticket.status;
            
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
    const lastResponse = document.getElementById('modalLastResponse').value;
    
    try {
        const response = await fetch(`/api/tickets/${currentTicketId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
            body: JSON.stringify({
                status: status,
                last_response: lastResponse
            })
        });
        
        if (response.status === 401 || response.status === 403) {
            alert('Сессия истекла. Пожалуйста, войдите в систему снова.');
            window.location.href = '/login';
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            alert('Изменения сохранены');
            closeTicketModal();
            loadTickets();
            loadStats();
        } else {
            alert('Ошибка сохранения: ' + (data.error || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('Error saving ticket:', error);
        alert('Произошла ошибка при сохранении');
    }
}

// Закрытие модального окна при клике вне его
window.onclick = function(event) {
    const modal = document.getElementById('ticketModal');
    if (event.target === modal) {
        closeTicketModal();
    }
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


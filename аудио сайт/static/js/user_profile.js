// Профиль пользователя: просмотр своих обращений

let currentTicketId = null;

// Загрузка при открытии страницы
document.addEventListener('DOMContentLoaded', function() {
    loadStats();
    loadTickets();
    
    // Обработчик фильтра
    document.getElementById('filterStatus').addEventListener('change', loadTickets);
});

// Загрузка статистики
async function loadStats() {
    try {
        const response = await fetch('/api/tickets?my_tickets=true', {
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
            const resolved = tickets.filter(t => t.status === 'RESOLVED').length;
            const autoClosed = tickets.filter(t => t.status === 'AUTO_CLOSED').length;
            
            document.getElementById('statTotal').textContent = total;
            document.getElementById('statOpen').textContent = open;
            document.getElementById('statResolved').textContent = resolved;
            document.getElementById('statAutoClosed').textContent = autoClosed;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Загрузка списка тикетов
async function loadTickets() {
    const status = document.getElementById('filterStatus').value;
    
    const params = new URLSearchParams();
    params.append('my_tickets', 'true');
    if (status) params.append('status', status);
    
    const url = '/api/tickets?' + params.toString();
    
    const tbody = document.getElementById('ticketsTableBody');
    tbody.innerHTML = '<tr><td colspan="8" class="loading">Загрузка...</td></tr>';
    
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
                tbody.innerHTML = '<tr><td colspan="8" class="loading">У вас пока нет обращений</td></tr>';
                return;
            }
            
            tbody.innerHTML = tickets.map(ticket => {
                const textPreview = ticket.text.length > 50 ? ticket.text.substring(0, 50) + '...' : ticket.text;
                return `
                    <tr>
                        <td>#${ticket.id}</td>
                        <td>${escapeHtml(textPreview)}</td>
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
            
            // Обновляем статистику
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
            document.getElementById('modalStatus').innerHTML = `<span class="badge badge-${ticket.status.toLowerCase().replace('_', '-')}">${getStatusLabel(ticket.status)}</span>`;
            document.getElementById('modalCategory').textContent = ticket.category || '-';
            document.getElementById('modalPriority').textContent = ticket.priority || '-';
            document.getElementById('modalDepartment').textContent = ticket.department || '-';
            document.getElementById('modalText').textContent = ticket.text;
            document.getElementById('modalSummary').textContent = ticket.summary || '-';
            
            // Показываем совет от ИИ, если есть
            if (ticket.auto_response) {
                // Сохраняем форматирование (переносы строк, нумерацию)
                const formattedAdvice = escapeHtml(ticket.auto_response)
                    .replace(/\n/g, '<br>')
                    .replace(/(\d+\.\s)/g, '<strong>$1</strong>');
                document.getElementById('modalAdvice').innerHTML = formattedAdvice;
                document.getElementById('modalAdvice').style.whiteSpace = 'pre-wrap';
                document.getElementById('modalAdvice').style.lineHeight = '1.8';
                document.getElementById('adviceSection').style.display = 'block';
            } else {
                document.getElementById('adviceSection').style.display = 'none';
            }
            
            // Показываем ответ специалиста, если есть
            if (ticket.last_response) {
                document.getElementById('modalResponse').textContent = ticket.last_response;
                document.getElementById('responseSection').style.display = 'block';
            } else {
                document.getElementById('responseSection').style.display = 'none';
            }
            
            document.getElementById('ticketModal').style.display = 'block';
        } else {
            alert('Ошибка загрузки обращения: ' + (data.error || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('Error loading ticket:', error);
        alert('Произошла ошибка при загрузке обращения');
    }
}

// Закрытие модального окна
function closeTicketModal() {
    document.getElementById('ticketModal').style.display = 'none';
    currentTicketId = null;
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


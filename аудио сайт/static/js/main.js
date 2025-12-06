// ChatGPT-style interface for ticket creation and AI assistance

let currentAnalysis = null;
let currentText = '';
let currentSource = 'portal';
let selectedTicketId = null;
let selectedFiles = [];
let recognition = null;
let isRecording = false;
let userAvatar = null;

document.addEventListener('DOMContentLoaded', function() {
    loadTicketsHistory();
    setupChatInterface();
    setupVoiceRecognition();
    loadUserAvatar();
});

// Setup voice recognition
function setupVoiceRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.lang = 'ru-RU';
        recognition.continuous = false;
        recognition.interimResults = false;
        
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            const chatInput = document.getElementById('chatInput');
            const currentText = chatInput.value.trim();
            chatInput.value = currentText ? currentText + ' ' + transcript : transcript;
            chatInput.dispatchEvent(new Event('input'));
        };
        
        recognition.onerror = function(event) {
            console.error('Speech recognition error:', event.error);
            stopVoiceRecording();
            alert('Ошибка распознавания речи: ' + event.error);
        };
        
        recognition.onend = function() {
            stopVoiceRecording();
        };
    } else {
        // Браузер не поддерживает распознавание речи
        const voiceBtn = document.getElementById('voiceInputBtn');
        if (voiceBtn) {
            voiceBtn.style.display = 'none';
        }
    }
}

// Toggle voice input
function toggleVoiceInput() {
    if (!recognition) {
        alert('Ваш браузер не поддерживает голосовой ввод');
        return;
    }
    
    if (isRecording) {
        stopVoiceRecording();
    } else {
        startVoiceRecording();
    }
}

// Start voice recording
function startVoiceRecording() {
    if (!recognition) return;
    
    try {
        recognition.start();
        isRecording = true;
        
        const voiceBtn = document.getElementById('voiceInputBtn');
        const voiceStatus = document.getElementById('voiceStatus');
        
        if (voiceBtn) {
            voiceBtn.classList.add('active');
        }
        if (voiceStatus) {
            voiceStatus.classList.add('active');
        }
    } catch (error) {
        console.error('Error starting recognition:', error);
        isRecording = false;
    }
}

// Stop voice recording
function stopVoiceRecording() {
    if (recognition && isRecording) {
        try {
            recognition.stop();
        } catch (error) {
            console.error('Error stopping recognition:', error);
        }
    }
    
    isRecording = false;
    
    const voiceBtn = document.getElementById('voiceInputBtn');
    const voiceStatus = document.getElementById('voiceStatus');
    
    if (voiceBtn) {
        voiceBtn.classList.remove('active');
    }
    if (voiceStatus) {
        voiceStatus.classList.remove('active');
    }
}

// Handle file selection
function handleFileSelect(event) {
    const files = Array.from(event.target.files);
    
    files.forEach(file => {
        // Проверка размера (10MB max)
        if (file.size > 10 * 1024 * 1024) {
            alert(`Файл "${file.name}" слишком большой. Максимальный размер: 10MB`);
            return;
        }
        
        selectedFiles.push(file);
    });
    
    updateFileList();
}

// Update file list display
function updateFileList() {
    const fileList = document.getElementById('fileList');
    
    if (selectedFiles.length === 0) {
        fileList.style.display = 'none';
        fileList.innerHTML = '';
        return;
    }
    
    fileList.style.display = 'flex';
    fileList.innerHTML = selectedFiles.map((file, index) => {
        const fileSize = (file.size / 1024).toFixed(1);
        return `
            <div class="file-item">
                <span class="file-item-name" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</span>
                <span style="color: var(--color-text-light); font-size: 0.75rem;">(${fileSize} KB)</span>
                <button type="button" class="file-item-remove" onclick="removeFile(${index})" title="Удалить">×</button>
            </div>
        `;
    }).join('');
}

// Remove file
function removeFile(index) {
    selectedFiles.splice(index, 1);
    updateFileList();
    
    // Обновляем input
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.value = '';
    }
}

// Load tickets history for sidebar
async function loadTicketsHistory() {
    const ticketsList = document.getElementById('ticketsList');
    
    try {
        const params = new URLSearchParams();
        params.append('my_tickets', 'true');
        
        const response = await fetch('/api/tickets?' + params.toString(), {
            credentials: 'same-origin'
        });
        
        if (response.status === 401) {
            // Не авторизован - перенаправляем на логин
            window.location.href = '/login';
            return;
        }
        
        if (response.status === 403) {
            // Доступ запрещен - возможно, пользователь не имеет роли 'user'
            const errorData = await response.json().catch(() => ({ error: 'Доступ запрещен' }));
            ticketsList.innerHTML = `<div class="no-tickets">${escapeHtml(errorData.error || 'Доступ запрещен. Требуется роль пользователя.')}</div>`;
            return;
        }
        
        if (!response.ok) {
            ticketsList.innerHTML = '<div class="no-tickets">Ошибка загрузки тикетов</div>';
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            const tickets = data.tickets || [];
            
            if (tickets.length === 0) {
                ticketsList.innerHTML = '<div class="no-tickets">У вас пока нет тикетов</div>';
                return;
            }
            
            // Sort by created_at descending (newest first)
            tickets.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
            
            ticketsList.innerHTML = tickets.map(ticket => {
                const status = (ticket.status || 'OPEN').toLowerCase();
                const statusClass = status === 'in_progress' ? 'in_progress' : 
                                   status === 'resolved' ? 'resolved' :
                                   status === 'auto_closed' || status === 'closed' ? 'closed' : 'open';
                
                const statusLabel = status === 'in_progress' ? 'В работе' :
                                   status === 'resolved' ? 'Решён' :
                                   status === 'auto_closed' || status === 'closed' ? 'Закрыт' : 'Открыт';
                
                const date = new Date(ticket.created_at);
                const dateStr = date.toLocaleDateString('ru-RU', { 
                    day: '2-digit', 
                    month: '2-digit',
                    year: 'numeric'
                });
                
                const textPreview = ticket.text ? 
                    (ticket.text.length > 50 ? ticket.text.substring(0, 50) + '...' : ticket.text) : 
                    'Без описания';
                
                return `
                    <div class="ticket-item" data-ticket-id="${ticket.id}" onclick="selectTicket(${ticket.id})">
                        <div class="ticket-item-title">${escapeHtml(textPreview)}</div>
                        <div class="ticket-item-meta">
                            <span>#${ticket.id} • ${dateStr}</span>
                            <span class="ticket-item-status ${statusClass}">${statusLabel}</span>
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            ticketsList.innerHTML = '<div class="no-tickets">Ошибка загрузки тикетов</div>';
        }
    } catch (error) {
        console.error('Error loading tickets:', error);
        ticketsList.innerHTML = '<div class="no-tickets">Ошибка загрузки тикетов</div>';
    }
}

// Select ticket from sidebar
function selectTicket(ticketId) {
    // Remove active class from all items
    document.querySelectorAll('.ticket-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // Add active class to selected item
    const selectedItem = document.querySelector(`[data-ticket-id="${ticketId}"]`);
    if (selectedItem) {
        selectedItem.classList.add('active');
    }
    
    selectedTicketId = ticketId;
    
    // Load ticket details and show in chat
    loadTicketDetails(ticketId);
}

// Load ticket details
async function loadTicketDetails(ticketId) {
    try {
        const response = await fetch(`/api/tickets/${ticketId}`, {
            credentials: 'same-origin'
        });
        
        if (response.status === 401 || response.status === 403) {
            window.location.href = '/login';
            return;
        }
        
        const data = await response.json();
        
        if (data.success && data.ticket) {
            const ticket = data.ticket;
            
            // Clear chat and show ticket info
            const chatArea = document.getElementById('chatMessagesArea');
            chatArea.innerHTML = '';
            
            // Add user message
            addMessage('user', ticket.text || 'Тикет #' + ticket.id, ticket.attachments || []);
            
            // Add AI response if available
            if (ticket.ai_advice) {
                addMessage('assistant', ticket.ai_advice);
            } else {
                addMessage('assistant', 'Тикет #' + ticket.id + ' создан. Статус: ' + getStatusLabel(ticket.status));
            }
        }
    } catch (error) {
        console.error('Error loading ticket details:', error);
    }
}

// Setup chat interface
function setupChatInterface() {
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendChatBtn');
    
    // Auto-resize textarea
    chatInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 400) + 'px';
    });
    
    // Send message on button click
    sendBtn.addEventListener('click', sendMessage);
    
    // Send message on Enter (Shift+Enter for new line)
    chatInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

// Send message
async function sendMessage() {
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendChatBtn');
    const message = chatInput.value.trim();
    
    if (!message && selectedFiles.length === 0) return;
    
    // Stop voice recording if active
    if (isRecording) {
        stopVoiceRecording();
    }
    
    // Add user message to chat
    addMessage('user', message, selectedFiles);
    
    // Clear input and files
    chatInput.value = '';
    chatInput.style.height = 'auto';
    const filesToSend = [...selectedFiles];
    selectedFiles = [];
    updateFileList();
    
    // Disable input and show loading
    chatInput.disabled = true;
    sendBtn.disabled = true;
    sendBtn.textContent = 'Отправка...';
    
    // Show loading message
    const loadingId = addLoadingMessage();
    
    try {
        // Prepare form data for file upload
        const formData = new FormData();
        formData.append('text', message || '');
        formData.append('source', 'portal');
        
        filesToSend.forEach((file, index) => {
            formData.append(`file_${index}`, file);
        });
        
        // Request AI analysis and create ticket
        const response = await fetch('/api/tickets', {
            method: 'POST',
            credentials: 'same-origin',
            body: formData
        });
        
        if (response.status === 401) {
            alert('Сессия истекла. Пожалуйста, войдите в систему снова.');
            window.location.href = '/login';
            return;
        }
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: 'Ошибка сервера' }));
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Remove loading message
        removeLoadingMessage(loadingId);
        
        if (data.success) {
            const ticket = data.ticket;
            currentText = message;
            
            // Build AI response
            let aiResponse = '';
            
            if (ticket.summary) {
                aiResponse += `📋 ${ticket.summary}\n\n`;
            }
            
            if (ticket.auto_response) {
                aiResponse += `💡 ${ticket.auto_response}\n\n`;
            }
            
            // Add categorization info
            aiResponse += `📁 Категория: ${ticket.category || '-'}\n`;
            aiResponse += `⚡ Приоритет: ${ticket.priority || 'MEDIUM'}\n`;
            aiResponse += `🏢 Отдел: ${ticket.department || '-'}`;
            
            // Add assistant message
            addMessage('assistant', aiResponse);
            
            // If auto-resolved, show success message
            if (ticket.is_auto_closed) {
                setTimeout(() => {
                    if (confirm('Проблема решена? Если нет, вы можете обратиться к оператору.')) {
                        addMessage('assistant', 'Отлично! Рады, что смогли помочь. Если возникнут другие вопросы, обращайтесь!');
                    } else {
                        offerOperatorContact();
                    }
                }, 500);
            } else {
                // Offer to contact operator
                offerOperatorContact();
            }
            
            // Reload tickets history
            loadTicketsHistory();
            
        } else {
            addMessage('assistant', 'Ошибка при создании обращения: ' + (data.error || 'Неизвестная ошибка'));
        }
        
    } catch (error) {
        console.error('Error:', error);
        removeLoadingMessage(loadingId);
        
        if (error.message.includes('401') || error.message.includes('Authentication')) {
            alert('Требуется авторизация. Пожалуйста, войдите в систему.');
            window.location.href = '/login';
        } else {
            addMessage('assistant', 'Произошла ошибка: ' + error.message + '. Попробуйте еще раз.');
        }
    } finally {
        // Re-enable input
        chatInput.disabled = false;
        sendBtn.disabled = false;
        sendBtn.textContent = 'Отправить';
        chatInput.focus();
    }
}

// Offer to contact operator
function offerOperatorContact() {
    const chatArea = document.getElementById('chatMessagesArea');
    
    const offerDiv = document.createElement('div');
    offerDiv.className = 'chat-message assistant';
    offerDiv.innerHTML = `
        <div class="message-avatar assistant">🤖</div>
        <div class="message-content-wrapper">
            <div class="message-content">
                Хотите обратиться к оператору для более детальной помощи?
            </div>
            <div style="margin-top: var(--spacing-sm);">
                <button class="btn btn-primary btn-sm" onclick="contactOperator()" style="margin-right: var(--spacing-sm);">
                    👤 Обратиться к оператору
                </button>
                <button class="btn btn-secondary btn-sm" onclick="dismissOffer(this)">
                    Нет, спасибо
                </button>
            </div>
        </div>
    `;
    
    chatArea.appendChild(offerDiv);
    chatArea.scrollTop = chatArea.scrollHeight;
}

// Contact operator
async function contactOperator() {
    if (!currentText) {
        addMessage('assistant', 'Ошибка: данные не найдены. Пожалуйста, попробуйте еще раз.');
        return;
    }
    
    // Show loading
    const loadingId = addLoadingMessage();
    
    try {
        // Check for online operators
        const checkResponse = await fetch('/api/operators/online', {
            credentials: 'same-origin'
        });
        
        if (checkResponse.ok) {
            const checkData = await checkResponse.json();
            if (checkData.success && !checkData.has_online_operators) {
                removeLoadingMessage(loadingId);
                addMessage('assistant', 'Онлайн операторов сейчас нет. Пожалуйста, попробуйте позже.');
                return;
            }
        }
        
        // Create ticket/chat
        const response = await fetch('/api/tickets', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
            body: JSON.stringify({
                text: currentText,
                source: 'chat'
            })
        });
        
        if (response.status === 401) {
            alert('Сессия истекла. Пожалуйста, войдите в систему снова.');
            window.location.href = '/login';
            return;
        }
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: 'Ошибка сервера' }));
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        removeLoadingMessage(loadingId);
        
        if (data.no_online_operators) {
            addMessage('assistant', 'Онлайн операторов сейчас нет. Пожалуйста, попробуйте позже.');
            return;
        }
        
        if (data.success) {
            const ticket = data.ticket;
            
            // If chat created, redirect to chat
            if (data.chat) {
                addMessage('assistant', '✅ Ваше обращение создано! Перенаправление в чат...');
                setTimeout(() => {
                    window.location.href = `/chat/${data.chat.id}`;
                }, 1500);
                return;
            }
            
            // Show success message
            let message = '✅ Ваше обращение успешно создано!\n\n';
            message += `Номер тикета: #${ticket.id}\n`;
            message += `Статус: ${getStatusLabel(ticket.status)}\n`;
            message += `Отдел: ${ticket.department}\n`;
            message += `Приоритет: ${ticket.priority}`;
            
            if (ticket.is_auto_closed) {
                message += '\n\nТикет был автоматически обработан и закрыт.';
            } else {
                message += '\n\nСпециалисты обработают ваше обращение в ближайшее время.';
            }
            
            addMessage('assistant', message);
            
            // Reload tickets history
            loadTicketsHistory();
            
            // Reset
            currentText = '';
            
        } else {
            addMessage('assistant', 'Ошибка при создании тикета: ' + (data.error || 'Неизвестная ошибка'));
        }
        
    } catch (error) {
        console.error('Error:', error);
        removeLoadingMessage(loadingId);
        
        if (error.message.includes('401') || error.message.includes('Authentication')) {
            alert('Требуется авторизация. Пожалуйста, войдите в систему.');
            window.location.href = '/login';
        } else {
            addMessage('assistant', 'Произошла ошибка при создании тикета: ' + error.message);
        }
    }
}

// Dismiss offer
function dismissOffer(button) {
    button.closest('.chat-message').remove();
}

// Load user avatar
async function loadUserAvatar() {
    try {
        const response = await fetch('/api/user-info', {
            credentials: 'same-origin'
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success && data.user && data.user.avatar_url) {
                userAvatar = data.user.avatar_url;
            }
        }
    } catch (error) {
        console.error('Error loading user avatar:', error);
    }
}

// Add message to chat
function addMessage(role, text, attachments = []) {
    const chatArea = document.getElementById('chatMessagesArea');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}`;
    
    const time = new Date().toLocaleTimeString('ru-RU', { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
    
    // Use user avatar if available, otherwise use emoji
    let avatarHTML = '';
    const avatarClass = role === 'user' ? 'user' : 'assistant';
    
    if (role === 'user' && userAvatar) {
        avatarHTML = `<img src="${userAvatar}" alt="Avatar" class="message-avatar ${avatarClass}">`;
    } else {
        const avatar = role === 'user' ? '👤' : '🤖';
        avatarHTML = `<div class="message-avatar ${avatarClass}">${avatar}</div>`;
    }
    
    // Format text (preserve line breaks, but don't break words)
    let formattedText = escapeHtml(text || '').replace(/\n/g, '<br>');
    
    // Обрабатываем специальные кнопки в сообщениях
    let routeButton = '';
    const routeButtonMatch = formattedText.match(/\[ROUTE_BUTTON:(.+?)\]/);
    if (routeButtonMatch) {
        const routeUrl = routeButtonMatch[1];
        formattedText = formattedText.replace(/\[ROUTE_BUTTON:.+?\]/, '');
        routeButton = `<div style="margin-top: var(--spacing-sm);">
            <a href="${routeUrl}" class="btn btn-primary btn-sm" style="display: inline-block; text-decoration: none; color: white; padding: 0.5rem 1rem; border-radius: var(--radius-sm); background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); font-weight: 600; box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);">
                🗺️ Открыть маршрут
            </a>
        </div>`;
    }
    
    // Format attachments
    let attachmentsHTML = '';
    if (attachments && attachments.length > 0) {
        attachmentsHTML = '<div class="message-attachments">';
        attachments.forEach(att => {
            const fileName = att.name || att.filename || 'Файл';
            const fileUrl = att.url || att.path || '#';
            attachmentsHTML += `<a href="${fileUrl}" target="_blank" class="message-attachment">📎 ${escapeHtml(fileName)}</a>`;
        });
        attachmentsHTML += '</div>';
    }
    
    messageDiv.innerHTML = `
        ${avatarHTML}
        <div class="message-content-wrapper">
            <div class="message-content">${formattedText}${attachmentsHTML}${routeButton}</div>
            <div class="message-time">${time}</div>
        </div>
    `;
    
    chatArea.appendChild(messageDiv);
    chatArea.scrollTop = chatArea.scrollHeight;
}

// Add loading message
function addLoadingMessage() {
    const chatArea = document.getElementById('chatMessagesArea');
    const loadingId = 'loading-' + Date.now();
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'chat-message assistant';
    messageDiv.id = loadingId;
    
    messageDiv.innerHTML = `
        <div class="message-avatar assistant">🤖</div>
        <div class="message-content-wrapper">
            <div class="loading-message">
                <span>Думаю</span>
                <div class="loading-dots">
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                </div>
            </div>
        </div>
    `;
    
    chatArea.appendChild(messageDiv);
    chatArea.scrollTop = chatArea.scrollHeight;
    
    return loadingId;
}

// Remove loading message
function removeLoadingMessage(loadingId) {
    const loadingElement = document.getElementById(loadingId);
    if (loadingElement) {
        loadingElement.remove();
    }
}

// Utility functions
function getStatusLabel(status) {
    const labels = {
        'OPEN': 'Открыт',
        'AUTO_CLOSED': 'Авто-закрыт',
        'IN_PROGRESS': 'В работе',
        'RESOLVED': 'Решён'
    };
    return labels[status] || status;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

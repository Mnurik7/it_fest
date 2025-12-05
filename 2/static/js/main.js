// Обработка формы - сначала получаем совет от ИИ, потом можно создать тикет

let currentAnalysis = null;
let currentText = '';
let currentSource = 'portal';

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('ticketForm');
    const submitBtn = document.getElementById('submitBtn');
    const submitText = document.getElementById('submitText');
    const submitLoader = document.getElementById('submitLoader');
    const aiAdviceContainer = document.getElementById('aiAdvice');
    const aiAdviceContent = document.getElementById('aiAdviceContent');
    const satisfiedBtn = document.getElementById('satisfiedBtn');
    const contactSpecialistBtn = document.getElementById('contactSpecialistBtn');
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const text = document.getElementById('text').value.trim();
        
        if (!text) {
            alert('Пожалуйста, введите текст обращения');
            return;
        }
        
        currentText = text;
        
        // Показываем лоадер
        submitBtn.disabled = true;
        submitText.style.display = 'none';
        submitLoader.style.display = 'inline-block';
        aiAdviceContainer.style.display = 'none';
        
        try {
            // Сначала запрашиваем анализ и совет от ИИ
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    text: text
                })
            });
            
            // Проверяем статус ответа
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
            
            if (data.success) {
                currentAnalysis = data.analysis;
                
                // Формируем HTML с советом от ИИ
                let html = '';
                
                // Показываем совет
                if (data.analysis.advice) {
                    html += `
                        <div class="advice-section">
                            <h3>Рекомендации по решению проблемы:</h3>
                            <div class="advice-text">${escapeHtml(data.analysis.advice)}</div>
                        </div>
                    `;
                }
                
                // Если есть автоответ (для простых вопросов)
                if (data.analysis.auto_resolve && data.analysis.auto_response) {
                    html += `
                        <div class="auto-response-section">
                            <h3>Ответ:</h3>
                            <div class="auto-response-text">${escapeHtml(data.analysis.auto_response)}</div>
                        </div>
                    `;
                }
                
                // Показываем категоризацию
                html += `
                    <div class="analysis-info">
                        <div class="info-item">
                            <strong>Категория:</strong> ${escapeHtml(data.analysis.category || '-')}
                        </div>
                        <div class="info-item">
                            <strong>Приоритет:</strong> 
                            <span class="badge badge-priority-${(data.analysis.priority || 'medium').toLowerCase()}">
                                ${data.analysis.priority || 'MEDIUM'}
                            </span>
                        </div>
                        <div class="info-item">
                            <strong>Отдел:</strong> ${escapeHtml(data.analysis.department || '-')}
                        </div>
                    </div>
                `;
                
                aiAdviceContent.innerHTML = html;
                aiAdviceContainer.style.display = 'block';
                
                // Показываем кнопку "Проблема решена" только если есть автоответ
                if (data.analysis.auto_resolve && data.analysis.auto_response) {
                    satisfiedBtn.style.display = 'inline-block';
                } else {
                    satisfiedBtn.style.display = 'none';
                }
                
            } else {
                alert('Ошибка при получении совета: ' + (data.error || 'Неизвестная ошибка'));
            }
            
        } catch (error) {
            console.error('Error:', error);
            if (error.message.includes('401') || error.message.includes('Authentication')) {
                alert('Требуется авторизация. Пожалуйста, войдите в систему.');
                window.location.href = '/login';
            } else {
                alert('Произошла ошибка при получении совета: ' + error.message + '. Попробуйте еще раз.');
            }
        } finally {
            // Скрываем лоадер
            submitBtn.disabled = false;
            submitText.style.display = 'inline';
            submitLoader.style.display = 'none';
        }
    });
    
    // Обработчик кнопки "Проблема решена"
    satisfiedBtn.addEventListener('click', function() {
        alert('Отлично! Рады, что смогли помочь. Если возникнут другие вопросы, обращайтесь!');
        form.reset();
        aiAdviceContainer.style.display = 'none';
        currentAnalysis = null;
    });
    
    // Обработчик кнопки "Обратиться к специалисту"
    contactSpecialistBtn.addEventListener('click', async function() {
        if (!currentAnalysis || !currentText) {
            alert('Ошибка: данные не найдены. Пожалуйста, попробуйте еще раз.');
            return;
        }
        
        // Показываем подтверждение
        if (!confirm('Вы уверены, что хотите обратиться к специалисту? Будет создан тикет в системе поддержки.')) {
            return;
        }
        
        // Отключаем кнопки
        contactSpecialistBtn.disabled = true;
        satisfiedBtn.disabled = true;
        contactSpecialistBtn.textContent = 'Создание тикета...';
        
        try {
            const response = await fetch('/api/tickets', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    text: currentText,
                    source: currentSource
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
            
            if (data.success) {
                const ticket = data.ticket;
                
                // Показываем успешное сообщение
                let message = '✅ Ваше обращение успешно создано!\n\n';
                message += `Номер тикета: #${ticket.id}\n`;
                message += `Статус: ${getStatusLabel(ticket.status)}\n`;
                message += `Отдел: ${ticket.department}\n`;
                message += `Приоритет: ${ticket.priority}\n\n`;
                
                if (ticket.is_auto_closed) {
                    message += 'Тикет был автоматически обработан и закрыт.';
                } else {
                    message += 'Специалисты обработают ваше обращение в ближайшее время.';
                }
                
                alert(message);
                
                // Очищаем форму
                form.reset();
                aiAdviceContainer.style.display = 'none';
                currentAnalysis = null;
                currentText = '';
                
            } else {
                alert('Ошибка при создании тикета: ' + (data.error || 'Неизвестная ошибка'));
            }
            
        } catch (error) {
            console.error('Error:', error);
            if (error.message.includes('401') || error.message.includes('Authentication')) {
                alert('Требуется авторизация. Пожалуйста, войдите в систему.');
                window.location.href = '/login';
            } else {
                alert('Произошла ошибка при создании тикета: ' + error.message + '. Попробуйте еще раз.');
            }
        } finally {
            // Восстанавливаем кнопки
            contactSpecialistBtn.disabled = false;
            satisfiedBtn.disabled = false;
            contactSpecialistBtn.textContent = '👤 Обратиться к специалисту';
        }
    });
});

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

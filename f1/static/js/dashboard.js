// JavaScript для dashboard страницы

document.addEventListener('DOMContentLoaded', function() {
    const ticketForm = document.getElementById('ticket-form');
    const ticketResponse = document.getElementById('ticket-response');
    
    if (ticketForm) {
        ticketForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const message = document.getElementById('problem-message').value.trim();
            if (!message) {
                showAlert(ticketResponse, 'Пожалуйста, введите описание проблемы', 'error');
                return;
            }
            
            // Показываем загрузку
            const submitBtn = ticketForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="loading"></span> Отправка...';
            
            try {
                const response = await fetch('/create_ticket', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: message })
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.error || 'Ошибка при отправке обращения');
                }
                
                // Обработка результата
                handleTicketResponse(data);
                
            } catch (error) {
                showAlert(ticketResponse, `Ошибка: ${error.message}`, 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
        });
    }
});

function handleTicketResponse(data) {
    const ticketResponse = document.getElementById('ticket-response');
    const ticketForm = document.getElementById('ticket-form');
    const messageTextarea = document.getElementById('problem-message');
    
    let html = '';
    
    if (data.type === 'outage') {
        // Авария в районе
        html = `
            <div class="alert alert-warning">
                <div class="alert-icon">⚠️</div>
                <div class="alert-content">
                    <h3>В вашем районе ведутся восстановительные работы</h3>
                    <p><strong>Причина:</strong> ${data.outage.reason || 'не указана'}</p>
                    <p><strong>Восстановление:</strong> ${data.outage.estimated_end || 'уточняется'}</p>
                    <p>✅ Заявка не требуется - это районная проблема.</p>
                </div>
            </div>
        `;
        showAlert(ticketResponse, html, 'info');
        messageTextarea.value = '';
        
    } else if (data.type === 'diagnostic') {
        // Пошаговая диагностика
        const steps = data.diagnostic_steps || [];
        html = `
            <div class="alert alert-info">
                <div class="alert-icon">🔧</div>
                <div class="alert-content">
                    <h3>Давайте попробуем решить проблему</h3>
                    <div class="diagnostic-steps" id="diagnostic-steps">
                        ${renderDiagnosticStep(0, steps[0], data.ticket_id)}
                    </div>
                </div>
            </div>
        `;
        showAlert(ticketResponse, html, 'info');
        messageTextarea.value = '';
        
        // Сохраняем данные для следующих шагов
        window.diagnosticData = {
            ticketId: data.ticket_id,
            steps: steps,
            currentStep: 0
        };
        
    } else if (data.type === 'engineer') {
        // Нужен инженер
        html = `
            <div class="alert alert-success">
                <div class="alert-icon">✅</div>
                <div class="alert-content">
                    <h3>Заявка №${data.request_id} принята!</h3>
                    <p><strong>Инженер приедет:</strong> ${data.visit_time_start} - ${data.visit_time_end}</p>
                    <p>Мы уведомим вас о статусе заявки.</p>
                </div>
            </div>
        `;
        showAlert(ticketResponse, html, 'success');
        messageTextarea.value = '';
        
        // Обновляем страницу через 3 секунды для показа новой заявки
        setTimeout(() => {
            window.location.reload();
        }, 3000);
        
    } else if (data.type === 'normal') {
        // Обычный ответ
        html = `
            <div class="alert alert-info">
                <div class="alert-icon">✅</div>
                <div class="alert-content">
                    <h3>Решение:</h3>
                    <p>${data.analysis.solution || 'Решение в процессе'}</p>
                    <p style="margin-top: 12px; font-size: 14px; color: #666;">
                        Если проблема не решена, напишите нам еще раз.
                    </p>
                </div>
            </div>
        `;
        showAlert(ticketResponse, html, 'info');
        messageTextarea.value = '';
    }
}

function renderDiagnosticStep(stepIndex, stepText, ticketId) {
    return `
        <div class="diagnostic-step">
            <h4>Шаг ${stepIndex + 1}:</h4>
            <p>${stepText}</p>
            <div class="diagnostic-buttons">
                <button class="btn btn-primary" onclick="handleDiagnosticStep(${stepIndex}, true, ${ticketId})">
                    ✅ Помогло
                </button>
                <button class="btn btn-secondary" onclick="handleDiagnosticStep(${stepIndex}, false, ${ticketId})">
                    ❌ Не помогло
                </button>
            </div>
        </div>
    `;
}

async function handleDiagnosticStep(stepIndex, solved, ticketId) {
    const diagnosticSteps = document.getElementById('diagnostic-steps');
    
    if (solved) {
        // Проблема решена
        try {
            await fetch('/diagnostic_step', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ticket_id: ticketId,
                    step: stepIndex,
                    solved: true
                })
            });
            
            const ticketResponse = document.getElementById('ticket-response');
            showAlert(ticketResponse, `
                <div class="alert alert-success">
                    <div class="alert-icon">✅</div>
                    <div class="alert-content">
                        <h3>Отлично! Проблема решена!</h3>
                        <p>Если проблема возникнет снова, обращайтесь к нам.</p>
                    </div>
                </div>
            `, 'success');
            
            document.getElementById('problem-message').value = '';
            
        } catch (error) {
            console.error('Ошибка:', error);
        }
        return;
    }
    
    // Проблема не решена - переходим к следующему шагу
    if (window.diagnosticData && window.diagnosticData.steps) {
        const nextStep = stepIndex + 1;
        const steps = window.diagnosticData.steps;
        
        if (nextStep < steps.length) {
            // Есть следующий шаг
            diagnosticSteps.innerHTML = renderDiagnosticStep(nextStep, steps[nextStep], ticketId);
            window.diagnosticData.currentStep = nextStep;
        } else {
            // Все шаги пройдены - создаем заявку
            try {
                const response = await fetch('/create_ticket', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        message: 'Диагностика не помогла, требуется выезд инженера'
                    })
                });
                
                const data = await response.json();
                
                if (data.type === 'engineer') {
                    const ticketResponse = document.getElementById('ticket-response');
                    showAlert(ticketResponse, `
                        <div class="alert alert-success">
                            <div class="alert-icon">✅</div>
                            <div class="alert-content">
                                <h3>Заявка №${data.request_id} принята!</h3>
                                <p><strong>Инженер приедет:</strong> ${data.visit_time_start} - ${data.visit_time_end}</p>
                                <p>Диагностика не помогла, требуется выезд инженера.</p>
                            </div>
                        </div>
                    `, 'success');
                    
                    document.getElementById('problem-message').value = '';
                    
                    setTimeout(() => {
                        window.location.reload();
                    }, 3000);
                }
            } catch (error) {
                console.error('Ошибка:', error);
                showAlert(document.getElementById('ticket-response'), 
                    'Ошибка при создании заявки. Попробуйте еще раз.', 'error');
            }
        }
    }
}

function showAlert(element, message, type = 'info') {
    element.innerHTML = message;
    element.className = `ticket-response ${type} show`;
    element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}


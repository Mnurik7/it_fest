// Fraud Detection JavaScript - Enhanced UX Version
let currentThreshold = 0.3;
let fraudTransactions = [];
let statistics = null;
let allTransactions = []; // Для фильтрации

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    loadCurrentThreshold();
    loadModelInfo();
    initializeToastContainer();
});

// ==================== Toast Notifications ====================
function initializeToastContainer() {
    if (!document.getElementById('toastContainer')) {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
}

function showToast(message, type = 'info', duration = 5000) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
        success: '✓',
        error: '✗',
        warning: '⚠',
        info: 'ℹ'
    };

    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || 'ℹ'}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;

    container.appendChild(toast);

    // Автоматическое удаление
    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ==================== Threshold Management ====================
function updateThresholdValue(value) {
    const display = document.getElementById('threshold-value');
    const threshold = parseFloat(value);
    display.textContent = threshold.toFixed(2);
    currentThreshold = threshold;
    
    // Визуальная обратная связь
    display.style.transform = 'scale(1.1)';
    setTimeout(() => {
        display.style.transform = 'scale(1)';
    }, 200);
}

function updateThreshold() {
    const threshold = parseFloat(document.getElementById('threshold-slider').value);
    const btn = document.getElementById('threshold-btn');
    const progress = document.getElementById('threshold-progress');
    
    btn.disabled = true;
    progress.classList.add('active');
    
    fetch('/api/fraud-detection/threshold', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ threshold: threshold })
    })
    .then(response => response.json())
    .then(data => {
        progress.classList.remove('active');
        btn.disabled = false;
        
        if (data.success) {
            currentThreshold = threshold;
            showToast('Порог успешно обновлен', 'success');
        } else {
            showToast(data.error || 'Ошибка при обновлении порога', 'error');
        }
    })
    .catch(error => {
        progress.classList.remove('active');
        btn.disabled = false;
        showToast('Ошибка при обновлении порога: ' + error.message, 'error');
    });
}

function loadCurrentThreshold() {
    fetch('/api/fraud-detection/get-threshold')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.threshold !== undefined) {
                currentThreshold = data.threshold;
                const slider = document.getElementById('threshold-slider');
                const display = document.getElementById('threshold-value');
                if (slider) slider.value = currentThreshold;
                if (display) display.textContent = currentThreshold.toFixed(2);
            }
        })
        .catch(error => {
            console.error('Ошибка загрузки порога:', error);
        });
}

// ==================== Transaction Checking ====================
function checkAllTransactions() {
    const btn = document.getElementById('check-btn');
    const statusDiv = document.getElementById('check-status');
    const progress = document.getElementById('check-progress');
    const progressText = document.getElementById('progress-text');
    
    btn.disabled = true;
    statusDiv.innerHTML = '<div class="loading-spinner"></div> <span style="margin-left: 0.5rem;">Инициализация проверки...</span>';
    progress.classList.add('active');
    
    // Симуляция прогресса
    let progressValue = 0;
    const progressInterval = setInterval(() => {
        progressValue += Math.random() * 15;
        if (progressValue > 90) progressValue = 90;
        document.querySelector('#check-progress .progress-fill').style.width = progressValue + '%';
    }, 500);
    
    // Получаем настройку максимального количества транзакций (если есть)
    const maxTransactions = document.getElementById('max-transactions-input')?.value || null;
    
    fetch('/api/fraud-detection/check-all', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
            threshold: currentThreshold,
            max_transactions: maxTransactions ? parseInt(maxTransactions) : null
        })
    })
    .then(response => response.json())
    .then(data => {
        clearInterval(progressInterval);
        document.querySelector('#check-progress .progress-fill').style.width = '100%';
        
        setTimeout(() => {
            progress.classList.remove('active');
            btn.disabled = false;
        statusDiv.innerHTML = '';
        
        if (data.success) {
            fraudTransactions = data.fraud_transactions || [];
                allTransactions = [...fraudTransactions]; // Копия для фильтрации
            statistics = data.statistics || {};
            
            displayFraudList();
            displayStatistics();
                
                const total = statistics.total_checked || 0;
                const fraud = statistics.fraud_detected || 0;
                const totalInFile = statistics.total_in_file || total;
                
                let message = `Проверка завершена: ${total.toLocaleString()} транзакций, обнаружено ${fraud.toLocaleString()} подозрительных`;
                if (totalInFile > total) {
                    message += ` (из ${totalInFile.toLocaleString()} в файле)`;
                }
                
                showToast(message, 'success', 6000);
                
                // Показываем предупреждение если есть
                if (data.warning) {
                    showToast(data.warning, 'warning', 8000);
                }
        } else {
                showToast(data.error || 'Ошибка при проверке транзакций', 'error', 8000);
                
                // Показываем диагностику если есть
                if (data.diagnostics) {
                    console.error('Диагностика:', data.diagnostics);
                    let diagnosticMsg = 'Детали ошибки:\n';
                    if (data.diagnostics.available_columns_in_raw_data) {
                        diagnosticMsg += 'Доступные колонки: ' + data.diagnostics.available_columns_in_raw_data.join(', ') + '\n';
                    }
                    if (data.diagnostics.feature_names) {
                        diagnosticMsg += 'Признаки: ' + data.diagnostics.feature_names.slice(0, 5).join(', ') + '...';
                    }
                    showToast(diagnosticMsg, 'error', 10000);
                }
            }
        }, 500);
    })
    .catch(error => {
        clearInterval(progressInterval);
        progress.classList.remove('active');
        btn.disabled = false;
        statusDiv.innerHTML = '';
        showToast('Ошибка при проверке транзакций: ' + error.message, 'error');
    });
}

// ==================== Display Functions ====================
function displayFraudList() {
    const container = document.getElementById('fraud-list');
    const controls = document.getElementById('table-controls');
    
    if (!fraudTransactions || fraudTransactions.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">✅</div>
                <div class="empty-state-text">Мошеннические транзакции не обнаружены</div>
                <div class="empty-state-hint">Все транзакции выглядят безопасными</div>
            </div>
        `;
        if (controls) controls.style.display = 'none';
        return;
    }
    
    if (controls) controls.style.display = 'flex';
    
    let html = `
        <div class="fraud-table-container">
            <table class="fraud-table" id="fraud-table">
                <thead>
                    <tr>
                        <th onclick="sortTable(0)">ID ↕</th>
                        <th onclick="sortTable(1)">Клиент ID ↕</th>
                        <th onclick="sortTable(2)">Сумма ↕</th>
                        <th onclick="sortTable(3)">Дата ↕</th>
                        <th onclick="sortTable(4)">Вероятность ↕</th>
                        <th>Действие</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    fraudTransactions.forEach((txn, index) => {
        const probability = (txn.fraud_probability * 100).toFixed(2);
        const riskClass = txn.fraud_probability > 0.7 ? 'high-risk' : 
                         txn.fraud_probability > 0.4 ? 'medium-risk' : 'low-risk';
        
        html += `
            <tr class="fraud-row ${riskClass}" onclick="showTransactionDetail(${index})" data-index="${index}">
                <td>${txn.id || index + 1}</td>
                <td>${txn.customer_id || txn.cst_dim_id || 'N/A'}</td>
                <td>${formatAmount(txn.amount)}</td>
                <td>${formatDate(txn.date || txn.transdate || txn.transdatetime)}</td>
                <td>
                    <span class="probability-badge ${riskClass}">${probability}%</span>
                </td>
                <td>
                    <button class="btn btn-small btn-primary" onclick="event.stopPropagation(); showTransactionDetail(${index})">
                        👁️ Детали
                    </button>
                </td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
        <div style="margin-top: 1rem; text-align: center; color: var(--text-secondary); font-size: 0.875rem;">
            Показано: ${fraudTransactions.length} из ${fraudTransactions.length} транзакций
        </div>
    `;
    
    container.innerHTML = html;
}

function displayStatistics() {
    const container = document.getElementById('statistics');
    
    if (!statistics) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">Статистика недоступна</div></div>';
        return;
    }
    
    const fraudPercentage = statistics.fraud_percentage || 0;
    const totalChecked = statistics.total_checked || 0;
    const fraudDetected = statistics.fraud_detected || 0;
    const safeTransactions = statistics.safe_transactions || 0;
    const totalInFile = statistics.total_in_file || totalChecked;
    const probStats = statistics.probability_stats || {};
    
    let html = `
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-label">Всего проверено</div>
                <div class="stat-value">${totalChecked.toLocaleString()}</div>
                ${totalInFile > totalChecked ? `<div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.25rem;">из ${totalInFile.toLocaleString()} в файле</div>` : ''}
            </div>
            <div class="stat-item stat-fraud">
                <div class="stat-label">Мошеннических</div>
                <div class="stat-value">${fraudDetected.toLocaleString()}</div>
            </div>
            ${statistics.business_metrics ? `
            <div class="stat-item" style="border-left: 4px solid var(--security-green);">
                <div class="stat-label">Правильно заблокировано</div>
                <div class="stat-value" style="color: var(--security-green);">${statistics.business_metrics.correctly_blocked.toLocaleString()}</div>
                <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.25rem;">
                    Точность: ${statistics.business_metrics.blocking_accuracy}%
                </div>
            </div>
            ` : ''}
            <div class="stat-item stat-safe">
                <div class="stat-label">Безопасных</div>
                <div class="stat-value">${safeTransactions.toLocaleString()}</div>
            </div>
            <div class="stat-item stat-percentage">
                <div class="stat-label">Процент мошенничества</div>
                <div class="stat-value">${fraudPercentage.toFixed(2)}%</div>
        </div>
    `;
    
    // Добавляем статистику вероятностей если есть
    if (probStats.max !== undefined) {
        html += `
            <div class="stat-item">
                <div class="stat-label">Макс. вероятность</div>
                <div class="stat-value" style="font-size: 1.5rem;">${(probStats.max * 100).toFixed(1)}%</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Средняя вероятность</div>
                <div class="stat-value" style="font-size: 1.5rem;">${(probStats.avg * 100).toFixed(1)}%</div>
            </div>
        `;
    }
    
    html += `</div>`;
    
    if (probStats.high_risk_count !== undefined) {
        html += `
            <div style="margin-top: 1rem; padding: 1rem; background: var(--background-alt); border-radius: 6px; font-size: 0.875rem;">
                <strong>Детали:</strong> Высокий риск (≥${(currentThreshold * 100).toFixed(0)}%): ${probStats.high_risk_count}, 
                Средний риск (≥10%): ${probStats.medium_risk_count || 0}
            </div>
        `;
    }
    
    container.innerHTML = html;
}

function showTransactionDetail(index) {
    if (!fraudTransactions || index >= fraudTransactions.length) {
        return;
    }
    
    const txn = fraudTransactions[index];
    const container = document.getElementById('transaction-detail');
    
    const probability = (txn.fraud_probability * 100).toFixed(2);
    const riskLevel = txn.fraud_probability > 0.7 ? 'Высокий' : 
                     txn.fraud_probability > 0.4 ? 'Средний' : 'Низкий';
    const riskClass = txn.fraud_probability > 0.7 ? 'high' : 
                     txn.fraud_probability > 0.4 ? 'medium' : 'low';
    
    // Генерируем объяснения
    const explanations = generateExplanations(txn, probability, riskLevel);
    
    // Подсветка выбранной строки
    document.querySelectorAll('.fraud-row').forEach(row => {
        row.style.background = '';
    });
    const selectedRow = document.querySelector(`.fraud-row[data-index="${index}"]`);
    if (selectedRow) {
        selectedRow.style.background = 'var(--background-alt)';
    }
    
    container.innerHTML = `
        <div class="detail-card">
            <h4>Детали транзакции #${txn.id || index + 1}</h4>
            <div class="detail-grid">
                <div class="detail-item">
                    <span class="detail-label">Клиент ID</span>
                    <span class="detail-value">${txn.customer_id || txn.cst_dim_id || 'N/A'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Сумма транзакции</span>
                    <span class="detail-value">${formatAmount(txn.amount)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Дата транзакции</span>
                    <span class="detail-value">${formatDate(txn.date || txn.transdate || txn.transdatetime)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Вероятность мошенничества</span>
                    <span class="detail-value risk-${riskClass}" style="font-size: 1.5rem; font-weight: 700;">
                        ${probability}%
                    </span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Уровень риска</span>
                    <span class="detail-value risk-${riskClass}">${riskLevel}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Статус</span>
                    <span class="detail-value">
                        ${txn.is_confirmed_fraud ? '🔴 Подтверждено мошенничество' : 
                          txn.is_fraud_predicted ? '🟡 Подозрительная транзакция' : 
                          '🟢 Требует проверки'}
                    </span>
                </div>
            </div>
            
            ${txn.is_confirmed_fraud ? `
                <div style="margin-top: 1rem; padding: 1rem; background: #FEE2E2; border-radius: 6px; border-left: 4px solid var(--security-red);">
                    <strong>⚠️ Внимание:</strong> Эта транзакция помечена как подтвержденное мошенничество в обучающих данных.
                </div>
            ` : ''}
            
            <!-- Объяснения -->
            <div style="margin-top: 1.5rem; padding: 1.5rem; background: white; border-radius: 8px; border: 1px solid var(--border-light);">
                <h5 style="margin: 0 0 1rem 0; color: var(--text-color); font-size: 1.125rem; display: flex; align-items: center; gap: 0.5rem;">
                    <span>💡</span> Объяснение оценки риска
                </h5>
                <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                    ${explanations.map(exp => `
                        <div class="explanation-item" style="padding: 0.75rem; background: ${exp.bgColor}; border-radius: 6px; border-left: 3px solid ${exp.borderColor};">
                            <div style="display: flex; align-items: start; gap: 0.5rem;">
                                <span style="font-size: 1.25rem;">${exp.icon}</span>
                                <div style="flex: 1;">
                                    <div style="font-weight: 600; color: var(--text-color); margin-bottom: 0.25rem;">
                                        ${exp.title}
                                    </div>
                                    <div style="font-size: 0.875rem; color: var(--text-secondary); line-height: 1.5;">
                                        ${exp.description}
                                    </div>
                                    ${exp.impact ? `
                                        <div style="margin-top: 0.5rem; font-size: 0.75rem; color: ${exp.impactColor}; font-weight: 500;">
                                            ${exp.impact}
                                        </div>
                                    ` : ''}
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
            
            <!-- Рекомендации с действиями -->
            <div style="margin-top: 1rem; padding: 1rem; background: #EFF6FF; border-radius: 6px; border-left: 4px solid #3B82F6;">
                <strong style="color: #1E40AF; display: block; margin-bottom: 0.75rem;">📋 Рекомендуемые действия:</strong>
                <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                    ${generateRecommendations(txn, probability, riskLevel).map(rec => `
                        <div class="action-item" style="display: flex; align-items: center; justify-content: space-between; padding: 0.75rem; background: white; border-radius: 6px; border: 1px solid var(--border-light); transition: all 0.2s;">
                            <div style="display: flex; align-items: center; gap: 0.5rem; flex: 1;">
                                <span style="font-size: 1.25rem;">${rec.icon}</span>
                                <span style="font-size: 0.875rem; color: var(--text-color);">${rec.text}</span>
                            </div>
                            <button 
                                class="btn btn-small" 
                                onclick="executeAction(${index}, '${rec.action}')"
                                style="background: ${rec.color}; color: white; border: none; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem; font-weight: 600; transition: all 0.2s;"
                                onmouseover="this.style.transform='scale(1.05)'"
                                onmouseout="this.style.transform='scale(1)'"
                            >
                                Выполнить
                            </button>
                        </div>
                    `).join('')}
                </div>
                <div id="action-status-${index}" style="margin-top: 0.75rem; display: none;"></div>
            </div>
            
            <!-- Поведенческие паттерны клиента -->
            ${txn.behavioral_patterns ? `
            <div style="margin-top: 1.5rem; padding: 1.5rem; background: white; border-radius: 8px; border: 1px solid var(--border-light);">
                <h5 style="margin: 0 0 1rem 0; color: var(--text-color); font-size: 1.125rem; display: flex; align-items: center; gap: 0.5rem;">
                    <span>📊</span> Поведенческие паттерны клиента
                </h5>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                    ${formatBehavioralPatterns(txn.behavioral_patterns).map(pattern => `
                        <div style="padding: 0.75rem; background: ${pattern.bgColor}; border-radius: 6px; border-left: 3px solid ${pattern.borderColor};">
                            <div style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.25rem; font-weight: 500;">
                                ${pattern.label}
                            </div>
                            <div style="font-size: 1rem; font-weight: 600; color: var(--text-color);">
                                ${pattern.value}
                            </div>
                            ${pattern.description ? `
                                <div style="font-size: 0.7rem; color: var(--text-secondary); margin-top: 0.25rem; line-height: 1.3;">
                                    ${pattern.description}
                                </div>
                            ` : ''}
                        </div>
                    `).join('')}
                </div>
            </div>
            ` : ''}
            
            <!-- История транзакций клиента (будет загружена при запросе) -->
            <div id="client-history-${index}" style="margin-top: 1rem; display: none;">
                <!-- История будет загружена через API -->
            </div>
        </div>
    `;
    
    // Плавная прокрутка к деталям
    container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Форматирование поведенческих паттернов для отображения
function formatBehavioralPatterns(patterns) {
    if (!patterns) return [];
    
    const formatted = [];
    
    // Активность логинов
    if (patterns.logins_last_7_days !== undefined) {
        const value = Math.round(patterns.logins_last_7_days || 0);
        const riskLevel = value === 0 ? 'high' : value < 5 ? 'medium' : 'low';
        formatted.push({
            label: 'Логинов за 7 дней',
            value: value,
            description: value === 0 ? 'Нет активности' : value < 5 ? 'Низкая активность' : 'Нормальная активность',
            bgColor: riskLevel === 'high' ? '#FEE2E2' : riskLevel === 'medium' ? '#FEF3C7' : '#D1FAE5',
            borderColor: riskLevel === 'high' ? '#EF4444' : riskLevel === 'medium' ? '#F59E0B' : '#10B981'
        });
    }
    
    if (patterns.logins_last_30_days !== undefined) {
        formatted.push({
            label: 'Логинов за 30 дней',
            value: Math.round(patterns.logins_last_30_days || 0),
            description: 'Общая активность',
            bgColor: '#F3F4F6',
            borderColor: '#6B7280'
        });
    }
    
    if (patterns.login_frequency_7d !== undefined) {
        const value = (patterns.login_frequency_7d || 0).toFixed(2);
        formatted.push({
            label: 'Среднее логинов/день (7д)',
            value: value,
            description: 'Частота входа',
            bgColor: '#F3F4F6',
            borderColor: '#6B7280'
        });
    }
    
    // Изменения устройств
    if (patterns.monthly_phone_model_changes !== undefined) {
        const value = Math.round(patterns.monthly_phone_model_changes || 0);
        const riskLevel = value > 3 ? 'high' : value > 1 ? 'medium' : 'low';
        formatted.push({
            label: 'Смен устройств (30д)',
            value: value,
            description: value > 3 ? '⚠️ Подозрительно много смен' : value > 1 ? 'Несколько смен' : 'Стабильное устройство',
            bgColor: riskLevel === 'high' ? '#FEE2E2' : riskLevel === 'medium' ? '#FEF3C7' : '#D1FAE5',
            borderColor: riskLevel === 'high' ? '#EF4444' : riskLevel === 'medium' ? '#F59E0B' : '#10B981'
        });
    }
    
    if (patterns.monthly_os_changes !== undefined) {
        const value = Math.round(patterns.monthly_os_changes || 0);
        formatted.push({
            label: 'Смен ОС (30д)',
            value: value,
            description: value > 2 ? 'Частые смены' : 'Стабильная ОС',
            bgColor: value > 2 ? '#FEF3C7' : '#F3F4F6',
            borderColor: value > 2 ? '#F59E0B' : '#6B7280'
        });
    }
    
    // Устройство и ОС
    if (patterns.last_phone_model !== undefined && patterns.last_phone_model) {
        formatted.push({
            label: 'Последнее устройство',
            value: String(patterns.last_phone_model).substring(0, 20) + (String(patterns.last_phone_model).length > 20 ? '...' : ''),
            description: 'Модель телефона',
            bgColor: '#F3F4F6',
            borderColor: '#6B7280'
        });
    }
    
    if (patterns.last_os_version !== undefined && patterns.last_os_version) {
        formatted.push({
            label: 'Версия ОС',
            value: String(patterns.last_os_version).substring(0, 15) + (String(patterns.last_os_version).length > 15 ? '...' : ''),
            description: 'Последняя версия',
            bgColor: '#F3F4F6',
            borderColor: '#6B7280'
        });
    }
    
    // Интервалы между логинами
    if (patterns.avg_login_interval_30d !== undefined) {
        const hours = Math.round((patterns.avg_login_interval_30d || 0) / 3600);
        formatted.push({
            label: 'Средний интервал логинов',
            value: hours > 24 ? `${Math.round(hours / 24)} дней` : `${hours} часов`,
            description: 'За последние 30 дней',
            bgColor: '#F3F4F6',
            borderColor: '#6B7280'
        });
    }
    
    // Аномальная активность
    if (patterns.burstiness_login_interval !== undefined) {
        const value = (patterns.burstiness_login_interval || 0).toFixed(3);
        const riskLevel = Math.abs(parseFloat(value)) > 0.5 ? 'high' : 'low';
        formatted.push({
            label: 'Взрывность активности',
            value: value,
            description: Math.abs(parseFloat(value)) > 0.5 ? '⚠️ Неравномерная активность' : 'Регулярная активность',
            bgColor: riskLevel === 'high' ? '#FEE2E2' : '#D1FAE5',
            borderColor: riskLevel === 'high' ? '#EF4444' : '#10B981'
        });
    }
    
    if (patterns.freq_change_7d_vs_mean !== undefined) {
        const percent = ((patterns.freq_change_7d_vs_mean || 0) * 100).toFixed(1);
        const riskLevel = Math.abs(parseFloat(percent)) > 50 ? 'high' : Math.abs(parseFloat(percent)) > 20 ? 'medium' : 'low';
        formatted.push({
            label: 'Изменение активности',
            value: percent > 0 ? `+${percent}%` : `${percent}%`,
            description: percent > 50 ? 'Резкое увеличение' : percent < -50 ? 'Резкое снижение' : 'Стабильная активность',
            bgColor: riskLevel === 'high' ? '#FEE2E2' : riskLevel === 'medium' ? '#FEF3C7' : '#D1FAE5',
            borderColor: riskLevel === 'high' ? '#EF4444' : riskLevel === 'medium' ? '#F59E0B' : '#10B981'
        });
    }
    
    // Z-score (аномалия интервалов)
    if (patterns.zscore_avg_login_interval_7d !== undefined) {
        const zscore = (patterns.zscore_avg_login_interval_7d || 0).toFixed(2);
        const absZ = Math.abs(parseFloat(zscore));
        const riskLevel = absZ > 2 ? 'high' : absZ > 1 ? 'medium' : 'low';
        formatted.push({
            label: 'Z-score интервалов',
            value: zscore,
            description: absZ > 2 ? '⚠️ Аномальное поведение' : absZ > 1 ? 'Необычное поведение' : 'Типичное поведение',
            bgColor: riskLevel === 'high' ? '#FEE2E2' : riskLevel === 'medium' ? '#FEF3C7' : '#D1FAE5',
            borderColor: riskLevel === 'high' ? '#EF4444' : riskLevel === 'medium' ? '#F59E0B' : '#10B981'
        });
    }
    
    return formatted;
}

// Генерация объяснений на основе данных транзакции
function generateExplanations(txn, probability, riskLevel) {
    const explanations = [];
    const prob = parseFloat(probability);
    const amount = parseFloat(txn.amount) || 0;
    
    // Объяснение на основе вероятности
    if (prob >= 70) {
        explanations.push({
            icon: '🔴',
            title: 'Высокая вероятность мошенничества',
            description: `Модель определила вероятность мошенничества на уровне ${probability}%, что значительно превышает порог детекции.`,
            bgColor: '#FEE2E2',
            borderColor: '#EF4444',
            impact: `Влияние: Критическое - требует немедленной проверки`,
            impactColor: '#DC2626'
        });
    } else if (prob >= 40) {
        explanations.push({
            icon: '🟡',
            title: 'Средняя вероятность мошенничества',
            description: `Вероятность мошенничества составляет ${probability}%, что указывает на подозрительную активность.`,
            bgColor: '#FEF3C7',
            borderColor: '#F59E0B',
            impact: `Влияние: Умеренное - рекомендуется дополнительная проверка`,
            impactColor: '#D97706'
        });
    } else {
        explanations.push({
            icon: '🟢',
            title: 'Низкая вероятность мошенничества',
            description: `Вероятность мошенничества ${probability}% находится в пределах нормы, но транзакция превысила установленный порог.`,
            bgColor: '#D1FAE5',
            borderColor: '#10B981',
            impact: `Влияние: Низкое - стандартная проверка`,
            impactColor: '#059669'
        });
    }
    
    // Объяснение на основе суммы
    if (amount >= 100000) {
        explanations.push({
            icon: '💰',
            title: 'Крупная сумма транзакции',
            description: `Сумма транзакции составляет ${formatAmount(amount)}, что значительно превышает средние значения. Крупные транзакции часто связаны с повышенным риском.`,
            bgColor: '#F3F4F6',
            borderColor: '#6B7280',
            impact: `Влияние: Повышает риск на 15-25%`
        });
    } else if (amount >= 50000) {
        explanations.push({
            icon: '💵',
            title: 'Выше среднего сумма',
            description: `Сумма транзакции ${formatAmount(amount)} выше средних значений для данного типа операций.`,
            bgColor: '#F3F4F6',
            borderColor: '#6B7280',
            impact: `Влияние: Умеренное повышение риска`
        });
    }
    
    // Объяснение на основе времени (если есть дата)
    const dateStr = txn.date || txn.transdate || txn.transdatetime;
    if (dateStr) {
        try {
            const date = new Date(dateStr);
            const hour = date.getHours();
            const dayOfWeek = date.getDay();
            
            if (hour >= 22 || hour <= 6) {
                explanations.push({
                    icon: '🌙',
                    title: 'Ночная транзакция',
                    description: `Транзакция совершена в ночное время (${hour}:00), что может указывать на необычную активность. Мошенники часто действуют в нерабочее время.`,
                    bgColor: '#F3F4F6',
                    borderColor: '#6B7280',
                    impact: `Влияние: Повышает риск на 10-15%`
                });
            }
            
            if (dayOfWeek === 0 || dayOfWeek === 6) {
                explanations.push({
                    icon: '📅',
                    title: 'Транзакция в выходной день',
                    description: `Транзакция совершена в выходной день, что может быть необычным для некоторых типов операций.`,
                    bgColor: '#F3F4F6',
                    borderColor: '#6B7280',
                    impact: `Влияние: Незначительное повышение риска`
                });
            }
        } catch (e) {
            // Игнорируем ошибки парсинга даты
        }
    }
    
    // Объяснение на основе подтвержденного мошенничества
    if (txn.is_confirmed_fraud) {
        explanations.push({
            icon: '⚠️',
            title: 'Подтвержденное мошенничество',
            description: `Эта транзакция была помечена как мошенническая в обучающих данных. Модель успешно идентифицировала её как подозрительную.`,
            bgColor: '#FEE2E2',
            borderColor: '#EF4444',
            impact: `Влияние: Критическое - это известный случай мошенничества`,
            impactColor: '#DC2626'
        });
    }
    
    // Общее объяснение модели
    explanations.push({
        icon: '🤖',
        title: 'Анализ ML модели',
        description: `Модель машинного обучения проанализировала ${statistics?.total_checked || 'множество'} транзакций и выявила паттерны, указывающие на подозрительную активность в данной транзакции.`,
        bgColor: '#EFF6FF',
        borderColor: '#3B82F6',
        impact: `Порог детекции: ${(currentThreshold * 100).toFixed(0)}%`
    });
    
    return explanations;
}

// Генерация рекомендаций с действиями
function generateRecommendations(txn, probability, riskLevel) {
    const recommendations = [];
    const prob = parseFloat(probability);
    
    if (prob >= 70) {
        recommendations.push({
            text: 'Немедленно заблокировать транзакцию и связаться с клиентом',
            action: 'block',
            icon: '🚫',
            priority: 'high',
            color: 'var(--security-red)'
        });
        recommendations.push({
            text: 'Проверить историю транзакций клиента за последние 30 дней',
            action: 'view_history',
            icon: '📊',
            priority: 'high',
            color: 'var(--primary-color)'
        });
        recommendations.push({
            text: 'Запросить дополнительную верификацию у клиента',
            action: 'request_verification',
            icon: '🔐',
            priority: 'medium',
            color: 'var(--warning-color)'
        });
        recommendations.push({
            text: 'Передать дело в отдел безопасности для расследования',
            action: 'escalate',
            icon: '🔒',
            priority: 'high',
            color: 'var(--security-red)'
        });
    } else if (prob >= 40) {
        recommendations.push({
            text: 'Запросить дополнительную верификацию у клиента',
            action: 'request_verification',
            icon: '🔐',
            priority: 'medium',
            color: 'var(--warning-color)'
        });
        recommendations.push({
            text: 'Проверить соответствие транзакции обычному поведению клиента',
            action: 'view_history',
            icon: '📊',
            priority: 'medium',
            color: 'var(--primary-color)'
        });
        recommendations.push({
            text: 'Мониторить последующие транзакции этого клиента',
            action: 'monitor',
            icon: '👁️',
            priority: 'low',
            color: 'var(--text-secondary)'
        });
    } else {
        recommendations.push({
            text: 'Провести стандартную проверку транзакции',
            action: 'standard_check',
            icon: '✓',
            priority: 'low',
            color: 'var(--text-secondary)'
        });
        recommendations.push({
            text: 'Сравнить с историей транзакций клиента',
            action: 'view_history',
            icon: '📊',
            priority: 'low',
            color: 'var(--primary-color)'
        });
    }
    
    if (txn.is_confirmed_fraud) {
        recommendations.push({
            text: 'Использовать этот случай для улучшения модели детекции',
            action: 'improve_model',
            icon: '🤖',
            priority: 'low',
            color: 'var(--text-secondary)'
        });
    }
    
    return recommendations;
}

// ==================== Table Filtering and Sorting ====================
let sortDirection = {};

function sortTable(columnIndex) {
    const table = document.getElementById('fraud-table');
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    const direction = sortDirection[columnIndex] || 'asc';
    sortDirection[columnIndex] = direction === 'asc' ? 'desc' : 'asc';
    
    rows.sort((a, b) => {
        const aText = a.cells[columnIndex].textContent.trim();
        const bText = b.cells[columnIndex].textContent.trim();
        
        // Попытка числового сравнения
        const aNum = parseFloat(aText.replace(/[^\d.-]/g, ''));
        const bNum = parseFloat(bText.replace(/[^\d.-]/g, ''));
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return direction === 'asc' ? aNum - bNum : bNum - aNum;
        }
        
        return direction === 'asc' 
            ? aText.localeCompare(bText)
            : bText.localeCompare(aText);
    });
    
    rows.forEach(row => tbody.appendChild(row));
    
    // Обновление индикаторов сортировки
    table.querySelectorAll('th').forEach((th, idx) => {
        th.textContent = th.textContent.replace(/ ↕| ↑| ↓/g, '');
        if (idx === columnIndex) {
            th.textContent += direction === 'asc' ? ' ↑' : ' ↓';
        } else {
            th.textContent += ' ↕';
        }
    });
}

function filterTable() {
    const searchInput = document.getElementById('search-input');
    const riskFilter = document.getElementById('risk-filter');
    const searchTerm = (searchInput?.value || '').toLowerCase();
    const riskValue = riskFilter?.value || '';
    
    if (!fraudTransactions || fraudTransactions.length === 0) return;
    
    let filtered = allTransactions.filter(txn => {
        // Поиск
        const matchesSearch = !searchTerm || 
            String(txn.id || '').includes(searchTerm) ||
            String(txn.customer_id || txn.cst_dim_id || '').toLowerCase().includes(searchTerm) ||
            String(txn.amount || '').includes(searchTerm);
        
        // Фильтр по риску
        let matchesRisk = true;
        if (riskValue) {
            const prob = txn.fraud_probability || 0;
            if (riskValue === 'high') matchesRisk = prob > 0.7;
            else if (riskValue === 'medium') matchesRisk = prob > 0.4 && prob <= 0.7;
            else if (riskValue === 'low') matchesRisk = prob <= 0.4;
        }
        
        return matchesSearch && matchesRisk;
    });
    
    fraudTransactions = filtered;
    displayFraudList();
    
    // Показываем количество отфильтрованных
    const container = document.getElementById('fraud-list');
    const countDiv = container.querySelector('div[style*="margin-top"]');
    if (countDiv && filtered.length !== allTransactions.length) {
        countDiv.innerHTML = `Показано: ${filtered.length} из ${allTransactions.length} транзакций`;
    }
}

// ==================== Model Info ====================
function loadModelInfo() {
    fetch('/api/fraud-detection/model-info')
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('model-info');
            const metricsContainer = document.getElementById('model-metrics');
            
            if (data.success && data.model_info) {
                const info = data.model_info;
                const isTrained = info.is_trained || info.status === 'loaded';
                
                container.innerHTML = `
                    <div class="model-info-item">
                        <span class="info-label">Статус модели</span>
                        <span class="info-value ${isTrained ? 'status-loaded' : 'status-not-loaded'}">
                            ${isTrained ? '✓ Обучена' : '✗ Не обучена'}
                        </span>
                    </div>
                    <div class="model-info-item">
                        <span class="info-label">Тип модели</span>
                        <span class="info-value">${info.model_type || 'N/A'}</span>
                    </div>
                    <div class="model-info-item">
                        <span class="info-label">Количество признаков</span>
                        <span class="info-value">${info.feature_count || 0}</span>
                    </div>
                    ${!isTrained && info.message ? `
                        <div style="margin-top: 1rem; padding: 1rem; background: #FEF3C7; border-radius: 6px; border-left: 4px solid var(--warning-color); font-size: 0.875rem;">
                            ${info.message}
                        </div>
                    ` : ''}
                `;
                
                // Отображение метрик если есть
                if (info.metrics) {
                    const metrics = info.metrics;
                    metricsContainer.style.display = 'block';
                    
                    // Оценка качества метрик
                    const precisionScore = metrics.precision * 100;
                    const recallScore = metrics.recall * 100;
                    const fBetaScore = metrics.f_beta;
                    const rocAucScore = metrics.roc_auc;
                    
                    const getScoreColor = (score, isPercentage = false) => {
                        const value = isPercentage ? score : score * 100;
                        if (value >= 80) return 'var(--security-green)';
                        if (value >= 60) return 'var(--warning-color)';
                        return 'var(--security-red)';
                    };
                    
                    const getScoreLabel = (score, isPercentage = false) => {
                        const value = isPercentage ? score : score * 100;
                        if (value >= 80) return '✓ Отлично';
                        if (value >= 60) return '⚠ Хорошо';
                        return '✗ Требует улучшения';
                    };
                    
                    let recommendations = [];
                    const optimalThreshold = metrics.optimal_threshold;
                    const thresholdDiff = optimalThreshold ? Math.abs(optimalThreshold - currentThreshold) : 0;
                    
                    // Рекомендации с учетом оптимального порога
                    if (optimalThreshold && thresholdDiff > 0.05) {
                        const optimalPercent = (optimalThreshold * 100).toFixed(0);
                        const currentPercent = (currentThreshold * 100).toFixed(0);
                        if (optimalThreshold < currentThreshold) {
                            recommendations.push(`💡 Рекомендуется снизить порог до ${optimalPercent}% (текущий: ${currentPercent}%) для улучшения баланса Precision/Recall и максимизации F-Beta.`);
                        } else {
                            recommendations.push(`💡 Рекомендуется повысить порог до ${optimalPercent}% (текущий: ${currentPercent}%) для улучшения баланса Precision/Recall и максимизации F-Beta.`);
                        }
                    }
                    
                    if (recallScore < 50) {
                        recommendations.push('⚠️ Низкий Recall - модель пропускает много мошеннических транзакций. Рекомендуется переобучить модель с учетом дисбаланса классов или снизить порог детекции.');
                    }
                    if (precisionScore < 60) {
                        if (optimalThreshold && optimalThreshold > currentThreshold) {
                            recommendations.push(`⚠️ Низкий Precision - много ложных срабатываний. Рекомендуется повысить порог до оптимального значения ${(optimalThreshold * 100).toFixed(0)}% для улучшения Precision.`);
                        } else {
                            recommendations.push('⚠️ Низкий Precision - много ложных срабатываний. Рассмотрите повышение порога детекции или переобучение модели.');
                        }
                    }
                    if (fBetaScore < 0.5) {
                        if (optimalThreshold && thresholdDiff > 0.05) {
                            recommendations.push(`⚠️ Низкий F-Beta - баланс между Precision и Recall не оптимален. Примените оптимальный порог ${(optimalThreshold * 100).toFixed(0)}% для улучшения метрики.`);
                        } else {
                            recommendations.push('⚠️ Низкий F-Beta - баланс между Precision и Recall не оптимален. Рекомендуется переобучить модель.');
                        }
                    }
                    
                    metricsContainer.innerHTML = `
                        <h5 style="margin: 0 0 0.75rem 0; color: var(--text-color); font-size: 1rem;">📊 Метрики производительности:</h5>
                        <div class="stats-grid" style="grid-template-columns: repeat(2, 1fr); gap: 0.5rem; margin-bottom: 1rem;">
                            <div class="stat-item" style="padding: 0.75rem; border-left: 4px solid ${getScoreColor(precisionScore, true)};">
                                <div class="stat-label" style="font-size: 0.75rem;">Precision</div>
                                <div class="stat-value" style="font-size: 1.25rem; color: ${getScoreColor(precisionScore, true)};">
                                    ${precisionScore.toFixed(2)}%
                                </div>
                                <div style="font-size: 0.7rem; color: var(--text-secondary); margin-top: 0.25rem;">
                                    ${getScoreLabel(precisionScore, true)}
                                </div>
                            </div>
                            <div class="stat-item" style="padding: 0.75rem; border-left: 4px solid ${getScoreColor(recallScore, true)};">
                                <div class="stat-label" style="font-size: 0.75rem;">Recall</div>
                                <div class="stat-value" style="font-size: 1.25rem; color: ${getScoreColor(recallScore, true)};">
                                    ${recallScore.toFixed(2)}%
                                </div>
                                <div style="font-size: 0.7rem; color: var(--text-secondary); margin-top: 0.25rem;">
                                    ${getScoreLabel(recallScore, true)}
                                </div>
                            </div>
                            <div class="stat-item" style="padding: 0.75rem; border-left: 4px solid ${getScoreColor(fBetaScore)};">
                                <div class="stat-label" style="font-size: 0.75rem;">F-Beta (β=2)</div>
                                <div class="stat-value" style="font-size: 1.25rem; color: ${getScoreColor(fBetaScore)};">
                                    ${fBetaScore.toFixed(4)}
                                </div>
                                <div style="font-size: 0.7rem; color: var(--text-secondary); margin-top: 0.25rem;">
                                    ${getScoreLabel(fBetaScore)}
                                </div>
                            </div>
                            <div class="stat-item" style="padding: 0.75rem; border-left: 4px solid ${getScoreColor(rocAucScore)};">
                                <div class="stat-label" style="font-size: 0.75rem;">ROC-AUC</div>
                                <div class="stat-value" style="font-size: 1.25rem; color: ${getScoreColor(rocAucScore)};">
                                    ${rocAucScore.toFixed(4)}
                                </div>
                                <div style="font-size: 0.7rem; color: var(--text-secondary); margin-top: 0.25rem;">
                                    ${getScoreLabel(rocAucScore)}
                                </div>
                            </div>
                        </div>
                        ${optimalThreshold ? `
                            <div style="padding: 0.75rem; background: #EFF6FF; border-radius: 6px; border-left: 4px solid #3B82F6; margin-bottom: 1rem; font-size: 0.875rem;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                                    <div>
                                        <strong>💡 Оптимальный порог:</strong> ${(optimalThreshold * 100).toFixed(0)}% 
                                        <span style="color: var(--text-secondary); font-size: 0.8em;">(текущий: ${(currentThreshold * 100).toFixed(0)}%)</span>
                                    </div>
                                    ${thresholdDiff > 0.05 ? `
                                        <button 
                                            class="btn btn-small" 
                                            onclick="applyOptimalThreshold(${optimalThreshold})"
                                            style="background: #3B82F6; color: white; border: none; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem; font-weight: 600; transition: all 0.2s;"
                                            onmouseover="this.style.background='#2563EB'"
                                            onmouseout="this.style.background='#3B82F6'"
                                        >
                                            Применить
                                        </button>
                                    ` : ''}
                                </div>
                                <div style="font-size: 0.8rem; color: var(--text-secondary);">
                                    Найден для максимизации F-Beta (β=2) - баланса между Precision и Recall
                                </div>
                            </div>
                        ` : ''}
                        ${recommendations.length > 0 ? `
                            <div style="padding: 0.75rem; background: #FEF3C7; border-radius: 6px; border-left: 4px solid var(--warning-color); font-size: 0.875rem;">
                                <strong>📋 Рекомендации по улучшению:</strong>
                                <ul style="margin: 0.5rem 0 0 1.5rem; padding: 0;">
                                    ${recommendations.map(rec => `<li style="margin-bottom: 0.25rem;">${rec}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                        ${metrics.class_imbalance ? `
                            <div style="margin-top: 0.75rem; padding: 0.75rem; background: var(--background-alt); border-radius: 6px; font-size: 0.75rem; color: var(--text-secondary);">
                                Дисбаланс классов: ${metrics.class_imbalance.fraud_count} мошеннических из ${metrics.class_imbalance.total_count} 
                                (${(metrics.class_imbalance.fraud_ratio * 100).toFixed(2)}%)
                            </div>
                        ` : ''}
                    `;
                } else {
                    metricsContainer.style.display = 'none';
                }
                
                // Устанавливаем выбранный тип модели
                const modelTypeSelect = document.getElementById('model-type-select');
                if (modelTypeSelect && info.model_type) {
                    modelTypeSelect.value = info.model_type;
                }
                
                if (!isTrained) {
                    showToast('Модель не обучена. Рекомендуется обучить модель перед использованием.', 'warning', 8000);
                }
            } else {
                container.innerHTML = '<div class="empty-state"><div class="empty-state-text">Информация о модели недоступна</div></div>';
                metricsContainer.style.display = 'none';
            }
        })
        .catch(error => {
            console.error('Ошибка загрузки информации о модели:', error);
            document.getElementById('model-info').innerHTML = 
                '<div class="empty-state"><div class="empty-state-text">Ошибка загрузки информации</div></div>';
        });
}

// ==================== Model Retraining ====================
function retrainModel() {
    const btn = document.getElementById('retrain-btn');
    const progress = document.getElementById('retrain-progress');
    const modelType = document.getElementById('model-type-select').value;
    
    if (!confirm(`Вы уверены, что хотите переобучить модель? Это может занять несколько минут.\nТип модели: ${modelType.toUpperCase()}`)) {
        return;
    }
    
    btn.disabled = true;
    progress.classList.add('active');
    
    fetch('/api/fraud-detection/retrain', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ model_type: modelType })
    })
    .then(response => response.json())
    .then(data => {
        progress.classList.remove('active');
        btn.disabled = false;
        
        if (data.success) {
            showToast('Модель успешно переобучена!', 'success', 6000);
            
            // Показываем метрики
            if (data.metrics) {
                const metrics = data.metrics;
                let metricsMsg = `Метрики модели:\n`;
                metricsMsg += `Precision: ${(metrics.precision * 100).toFixed(2)}%\n`;
                metricsMsg += `Recall: ${(metrics.recall * 100).toFixed(2)}%\n`;
                metricsMsg += `F-Beta: ${metrics.f_beta.toFixed(4)}\n`;
                metricsMsg += `ROC-AUC: ${metrics.roc_auc.toFixed(4)}`;
                showToast(metricsMsg, 'info', 10000);
            }
            
            // Перезагружаем информацию о модели
            setTimeout(() => {
                loadModelInfo();
            }, 1000);
        } else {
            showToast(data.error || 'Ошибка при переобучении модели', 'error', 8000);
        }
    })
    .catch(error => {
        progress.classList.remove('active');
        btn.disabled = false;
        showToast('Ошибка при переобучении модели: ' + error.message, 'error');
    });
}

// ==================== Utility Functions ====================
function formatAmount(amount) {
    if (!amount && amount !== 0) return 'N/A';
    return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'KZT',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    try {
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return dateStr;
        return date.toLocaleDateString('ru-RU', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return dateStr;
    }
}

// ==================== Action Execution ====================
function executeAction(transactionIndex, actionType) {
    console.log('executeAction вызвана:', { transactionIndex, actionType });
    
    if (!fraudTransactions || transactionIndex >= fraudTransactions.length) {
        console.error('Транзакция не найдена:', { transactionIndex, total: fraudTransactions?.length });
        showToast('Транзакция не найдена', 'error');
        return;
    }
    
    const txn = fraudTransactions[transactionIndex];
    console.log('Данные транзакции:', txn);
    
    const statusDiv = document.getElementById(`action-status-${transactionIndex}`);
    if (!statusDiv) {
        console.error('Элемент action-status не найден:', `action-status-${transactionIndex}`);
        showToast('Ошибка: элемент интерфейса не найден', 'error');
        return;
    }
    
    // Специальная обработка для просмотра истории
    if (actionType === 'view_history') {
        loadClientHistory(transactionIndex, txn.customer_id || txn.cst_dim_id);
        return;
    }
    
    // Показываем статус
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = '<div class="loading-spinner"></div> <span style="margin-left: 0.5rem;">Выполнение действия...</span>';
    
    const actionData = {
        transaction_id: txn.id,
        customer_id: txn.customer_id || txn.cst_dim_id,
        action: actionType,
        transaction_data: txn
    };
    
    console.log('Отправка запроса:', actionData);
    
    fetch('/api/fraud-detection/execute-action', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(actionData)
    })
    .then(async response => {
        console.log('Ответ получен:', response.status, response.statusText);
        const contentType = response.headers.get('content-type');
        let data;
        
        if (contentType && contentType.includes('application/json')) {
            data = await response.json();
        } else {
            const text = await response.text();
            throw new Error(`Неожиданный формат ответа: ${text}`);
        }
        
        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        return data;
    })
    .then(data => {
        console.log('Данные ответа:', data);
        if (data.success) {
            statusDiv.innerHTML = `
                <div style="padding: 0.75rem; background: #D1FAE5; border-radius: 6px; border-left: 4px solid var(--security-green); color: #059669; font-size: 0.875rem;">
                    ✓ ${data.message || 'Действие выполнено успешно'}
                </div>
            `;
            showToast(data.message || 'Действие выполнено успешно', 'success', 5000);
            
            // Обновляем статус транзакции
            if (data.transaction_status) {
                txn.status = data.transaction_status;
                txn.action_taken = actionType;
                txn.action_taken_at = new Date().toISOString();
            }
        } else {
            statusDiv.innerHTML = `
                <div style="padding: 0.75rem; background: #FEE2E2; border-radius: 6px; border-left: 4px solid var(--security-red); color: #DC2626; font-size: 0.875rem;">
                    ✗ ${data.error || 'Ошибка при выполнении действия'}
                </div>
            `;
            showToast(data.error || 'Ошибка при выполнении действия', 'error', 8000);
        }
    })
    .catch(error => {
        console.error('Ошибка при выполнении действия:', error);
        statusDiv.innerHTML = `
            <div style="padding: 0.75rem; background: #FEE2E2; border-radius: 6px; border-left: 4px solid var(--security-red); color: #DC2626; font-size: 0.875rem;">
                ✗ Ошибка: ${error.message}
            </div>
        `;
        showToast('Ошибка при выполнении действия: ' + error.message, 'error', 8000);
    });
}

// Загрузка истории транзакций клиента
function loadClientHistory(transactionIndex, customerId) {
    const historyDiv = document.getElementById(`client-history-${transactionIndex}`);
    historyDiv.style.display = 'block';
    historyDiv.innerHTML = '<div class="loading-spinner"></div> <span style="margin-left: 0.5rem;">Загрузка истории транзакций...</span>';
    
    fetch(`/api/fraud-detection/client-history/${customerId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const transactions = data.transactions || [];
                const stats = data.statistics || {};
                
                if (transactions.length === 0) {
                    historyDiv.innerHTML = `
                        <div style="padding: 1rem; background: var(--background-alt); border-radius: 6px; text-align: center; color: var(--text-secondary);">
                            История транзакций для клиента ${customerId} не найдена за последние 30 дней
                        </div>
                    `;
                    return;
                }
                
                let html = `
                    <div style="padding: 1rem; background: white; border-radius: 6px; border: 1px solid var(--border-light);">
                        <h5 style="margin: 0 0 1rem 0; color: var(--text-color); display: flex; align-items: center; gap: 0.5rem;">
                            <span>📊</span> История транзакций клиента ${customerId}
                            ${data.total_all && data.total_all > transactions.length ? ` (показано ${transactions.length} из ${data.total_all})` : ''}
                        </h5>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0.75rem; margin-bottom: 1rem;">
                            <div style="padding: 0.75rem; background: var(--background-alt); border-radius: 6px;">
                                <div style="font-size: 0.75rem; color: var(--text-secondary);">Всего транзакций</div>
                                <div style="font-size: 1.25rem; font-weight: 700; color: var(--text-color);">${transactions.length}</div>
                            </div>
                            <div style="padding: 0.75rem; background: var(--background-alt); border-radius: 6px;">
                                <div style="font-size: 0.75rem; color: var(--text-secondary);">Общая сумма</div>
                                <div style="font-size: 1.25rem; font-weight: 700; color: var(--text-color);">${formatAmount(stats.total_amount || 0)}</div>
                            </div>
                            <div style="padding: 0.75rem; background: var(--background-alt); border-radius: 6px;">
                                <div style="font-size: 0.75rem; color: var(--text-secondary);">Средняя сумма</div>
                                <div style="font-size: 1.25rem; font-weight: 700; color: var(--text-color);">${formatAmount(stats.avg_amount || 0)}</div>
                            </div>
                            <div style="padding: 0.75rem; background: var(--background-alt); border-radius: 6px;">
                                <div style="font-size: 0.75rem; color: var(--text-secondary);">Мошеннических</div>
                                <div style="font-size: 1.25rem; font-weight: 700; color: ${stats.fraud_count > 0 ? 'var(--security-red)' : 'var(--security-green)'};">
                                    ${stats.fraud_count || 0}
                                </div>
                            </div>
                        </div>
                        <div style="max-height: 300px; overflow-y: auto; border: 1px solid var(--border-light); border-radius: 6px;">
                            <table style="width: 100%; border-collapse: collapse; font-size: 0.875rem;">
                                <thead style="background: var(--background-alt); position: sticky; top: 0;">
                                    <tr>
                                        <th style="padding: 0.75rem; text-align: left; border-bottom: 1px solid var(--border-light);">Дата</th>
                                        <th style="padding: 0.75rem; text-align: left; border-bottom: 1px solid var(--border-light);">Сумма</th>
                                        <th style="padding: 0.75rem; text-align: left; border-bottom: 1px solid var(--border-light);">Статус</th>
                                    </tr>
                                </thead>
                                <tbody>
                `;
                
                transactions.forEach(t => {
                    html += `
                        <tr style="border-bottom: 1px solid var(--border-light);">
                            <td style="padding: 0.75rem;">${formatDate(t.date)}</td>
                            <td style="padding: 0.75rem; font-weight: 600;">${formatAmount(t.amount)}</td>
                            <td style="padding: 0.75rem;">
                                <span style="padding: 0.25rem 0.5rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600; 
                                    background: ${t.is_fraud ? '#FEE2E2' : '#D1FAE5'}; 
                                    color: ${t.is_fraud ? '#DC2626' : '#059669'};">
                                    ${t.is_fraud ? '🔴 Мошенничество' : '🟢 Безопасно'}
                                </span>
                            </td>
                        </tr>
                    `;
                });
                
                html += `
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;
                
                historyDiv.innerHTML = html;
                showToast(`Загружено ${transactions.length} транзакций клиента ${customerId}`, 'success');
            } else {
                historyDiv.innerHTML = `
                    <div style="padding: 1rem; background: #FEE2E2; border-radius: 6px; border-left: 4px solid var(--security-red); color: #DC2626;">
                        ✗ Ошибка: ${data.error || 'Не удалось загрузить историю транзакций'}
                    </div>
                `;
                showToast(data.error || 'Ошибка загрузки истории', 'error');
            }
        })
        .catch(error => {
            historyDiv.innerHTML = `
                <div style="padding: 1rem; background: #FEE2E2; border-radius: 6px; border-left: 4px solid var(--security-red); color: #DC2626;">
                    ✗ Ошибка: ${error.message}
                </div>
            `;
            showToast('Ошибка загрузки истории: ' + error.message, 'error');
        });
}

// Применение оптимального порога
function applyOptimalThreshold(optimalThreshold) {
    if (!confirm(`Применить оптимальный порог ${(optimalThreshold * 100).toFixed(0)}%? Это изменит текущий порог детекции.`)) {
        return;
    }
    
    // Обновляем слайдер и значение
    const slider = document.getElementById('threshold-slider');
    const valueDisplay = document.getElementById('threshold-value');
    
    if (slider && valueDisplay) {
        slider.value = optimalThreshold;
        valueDisplay.textContent = (optimalThreshold * 100).toFixed(0) + '%';
        currentThreshold = optimalThreshold;
        
        // Применяем новый порог
        updateThreshold();
        
        showToast(`Порог обновлен до оптимального значения: ${(optimalThreshold * 100).toFixed(0)}%`, 'success', 5000);
    }
}

// Экспорт для использования в HTML
window.updateThresholdValue = updateThresholdValue;
window.updateThreshold = updateThreshold;
window.checkAllTransactions = checkAllTransactions;
window.showTransactionDetail = showTransactionDetail;
window.sortTable = sortTable;
window.filterTable = filterTable;
window.retrainModel = retrainModel;
window.executeAction = executeAction;
window.loadClientHistory = loadClientHistory;
window.applyOptimalThreshold = applyOptimalThreshold;


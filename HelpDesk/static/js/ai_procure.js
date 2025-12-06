// AI-Procure JavaScript
let currentTenderParams = null;
let currentAnalysisData = null;

// Плавная прокрутка к секции
function scrollToSection(sectionId, navItem) {
    const section = document.getElementById(sectionId);
    if (section) {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
        // Обновляем активный пункт навигации
        if (navItem) {
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });
            navItem.classList.add('active');
        }
    }
}

// Отслеживание прокрутки для обновления активного пункта меню
window.addEventListener('scroll', () => {
    const sections = document.querySelectorAll('.content-section');
    const navItems = document.querySelectorAll('.nav-item');
    
    let current = '';
    sections.forEach(section => {
        const sectionTop = section.offsetTop;
        const sectionHeight = section.clientHeight;
        if (window.pageYOffset >= sectionTop - 200) {
            current = section.getAttribute('id');
        }
    });
    
    navItems.forEach(item => {
        item.classList.remove('active');
        if (item.getAttribute('href') === `#${current}`) {
            item.classList.add('active');
        }
    });
});

// Переключение полей ввода в зависимости от типа источника
function toggleSourceFields(sourceType) {
    const pdfField = document.getElementById('pdf-source-field');
    const webField = document.getElementById('web-source-field');
    
    // Скрываем все дополнительные поля
    if (pdfField) pdfField.style.display = 'none';
    if (webField) webField.style.display = 'none';
    
    // Показываем соответствующее поле в зависимости от типа
    if (sourceType === 'pdf') {
        if (pdfField) pdfField.style.display = 'block';
    } else if (sourceType === 'web') {
        if (webField) webField.style.display = 'block';
    }
    // Для типа "text" дополнительные поля просто скрыты, текстовое поле всегда видимо
}

// Обработка выбора PDF файла
function handlePDFFileSelect(event) {
    const file = event.target.files[0];
    const fileNameSpan = document.getElementById('pdf-file-name');
    
    if (file) {
        if (file.type !== 'application/pdf') {
            alert('Пожалуйста, выберите PDF файл');
            event.target.value = '';
            if (fileNameSpan) fileNameSpan.textContent = '';
            return;
        }
        
        if (fileNameSpan) {
            fileNameSpan.textContent = `✅ ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
        }
    } else {
        if (fileNameSpan) fileNameSpan.textContent = '';
    }
}

// Генерация текста тендера через AI
function generateTenderTextWithAI() {
    const tenderText = document.getElementById('tender-text').value;
    
    if (!tenderText.trim()) {
        alert('Пожалуйста, введите краткое описание тендера для генерации полного текста');
        return;
    }
    
    const generateBtn = document.getElementById('generate-tender-btn');
    const originalText = generateBtn ? generateBtn.innerHTML : '';
    
    if (generateBtn) {
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<span class="spinner" style="width: 16px; height: 16px; border-width: 2px; margin: 0;"></span><span>Генерация...</span>';
    }
    
    fetch('/api/ai-procure/generate-tender-text', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({description: tenderText})
    })
    .then(r => r.json())
    .then(data => {
        if (generateBtn) {
            generateBtn.disabled = false;
            generateBtn.innerHTML = originalText;
        }
        
        if (data.error) {
            alert('Ошибка: ' + data.error);
            return;
        }
        
        document.getElementById('tender-text').value = data.tender_text || '';
        document.getElementById('tender-text').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    })
    .catch(e => {
        if (generateBtn) {
            generateBtn.disabled = false;
            generateBtn.innerHTML = originalText;
        }
        alert('Ошибка: ' + e.message);
    });
}

// Анализ тендера
function analyzeTender() {
    const sourceType = document.querySelector('input[name="source-type"]:checked').value;
    let tenderText = '';
    let pdfFile = null;
    let webUrl = '';
    
    // Получаем данные в зависимости от типа источника
    if (sourceType === 'text') {
        tenderText = document.getElementById('tender-text').value;
        if (!tenderText.trim()) {
            alert('Пожалуйста, введите текст тендера');
            return;
        }
    } else if (sourceType === 'pdf') {
        const pdfInput = document.getElementById('pdf-file-input');
        pdfFile = pdfInput ? pdfInput.files[0] : null;
        if (!pdfFile) {
            alert('Пожалуйста, выберите PDF файл');
            return;
        }
    } else if (sourceType === 'web') {
        webUrl = document.getElementById('web-url-input').value;
        if (!webUrl.trim()) {
            alert('Пожалуйста, введите ссылку на веб-сайт');
            return;
        }
        // Проверка формата URL
        try {
            new URL(webUrl);
        } catch (e) {
            alert('Пожалуйста, введите корректную ссылку (например, https://example.com)');
            return;
        }
    }
    
    const includeSuppliers = document.getElementById('func-suppliers').checked;
    const includeRisks = document.getElementById('func-risks').checked;
    const includePrice = document.getElementById('func-price').checked;
    const includeReport = document.getElementById('func-report').checked;
    
    const resultDiv = document.getElementById('analysis-results');
    const analyzeBtn = document.getElementById('analyze-btn');
    
    if (analyzeBtn) {
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<span class="spinner" style="width: 20px; height: 20px; border-width: 2px; margin: 0;"></span><span>Анализ...</span>';
    }
    
    resultDiv.style.display = 'block';
    
    // Показываем прогресс с процентами
    let progressHtml = `
        <div style="background: #F0F9FF; padding: 1.5rem; border-radius: 8px; margin-bottom: 1.5rem; border-left: 4px solid #0284C7;">
            <h4 style="margin: 0 0 1rem 0; color: #0C4A6E;">📊 Прогресс анализа</h4>
            
            <!-- Прогресс-бар с процентами -->
            <div style="margin-bottom: 1rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <span id="progress-text" style="font-weight: 600; color: #0C4A6E;">${sourceType === 'pdf' ? 'Обработка PDF файла...' : sourceType === 'web' ? 'Загрузка данных с сайта...' : 'Извлечение параметров тендера...'}</span>
                    <span id="progress-percent" style="font-weight: 700; color: #0284C7; font-size: 1.1rem;">0%</span>
                </div>
                <div style="width: 100%; height: 12px; background: #E0F2FE; border-radius: 6px; overflow: hidden; position: relative;">
                    <div id="progress-bar" style="height: 100%; width: 0%; background: linear-gradient(90deg, #0284C7 0%, #0EA5E9 100%); border-radius: 6px; transition: width 0.3s ease; position: relative; overflow: hidden;">
                        <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent); animation: shimmer 2s infinite;"></div>
                    </div>
                </div>
            </div>
            
            <div id="progress-steps" style="display: flex; flex-direction: column; gap: 0.75rem;">
                <div id="step-1" style="display: flex; align-items: center; gap: 0.75rem;">
                    <span class="spinner" style="width: 20px; height: 20px; border-width: 2px;"></span>
                    <span>${sourceType === 'pdf' ? 'Обработка PDF файла...' : sourceType === 'web' ? 'Загрузка данных с сайта...' : 'Извлечение параметров тендера...'}</span>
                </div>
            </div>
        </div>
        <div id="analysis-content"></div>
    `;
    resultDiv.innerHTML = progressHtml;
    
    // Добавляем CSS анимацию для shimmer эффекта
    if (!document.getElementById('progress-shimmer-style')) {
        const style = document.createElement('style');
        style.id = 'progress-shimmer-style';
        style.textContent = `
            @keyframes shimmer {
                0% { transform: translateX(-100%); }
                100% { transform: translateX(100%); }
            }
        `;
        document.head.appendChild(style);
    }
    
    let currentProgress = 0;
    
    function updateProgress(step, status, text, percent = null) {
        const stepEl = document.getElementById(`step-${step}`);
        const progressBar = document.getElementById('progress-bar');
        const progressPercent = document.getElementById('progress-percent');
        const progressText = document.getElementById('progress-text');
        
        // Обновляем проценты
        if (percent !== null) {
            currentProgress = Math.min(100, Math.max(0, percent));
            if (progressBar) {
                progressBar.style.width = currentProgress + '%';
            }
            if (progressPercent) {
                progressPercent.textContent = Math.round(currentProgress) + '%';
            }
        }
        
        // Обновляем текст прогресса
        if (progressText && text) {
            progressText.textContent = text;
        }
        
        // Обновляем шаги
        if (stepEl) {
            if (status === 'completed') {
                stepEl.innerHTML = `<span style="color: #10B981; font-size: 1.2rem;">✅</span><span style="color: #059669;">${text}</span>`;
                stepEl.style.opacity = '1';
            } else if (status === 'processing') {
                stepEl.innerHTML = `<span class="spinner" style="width: 20px; height: 20px; border-width: 2px;"></span><span>${text}</span>`;
                stepEl.style.opacity = '1';
            }
        }
    }
    
    // Симуляция прогресса во время загрузки
    const progressInterval = setInterval(() => {
        if (currentProgress < 90) {
            // Плавное увеличение до 90% во время ожидания ответа
            currentProgress += Math.random() * 3;
            updateProgress(null, null, null, currentProgress);
        }
    }, 200);
    
    // Подготовка данных для отправки
    let requestBody;
    let headers = {};
    
    if (sourceType === 'pdf' && pdfFile) {
        // Для PDF используем FormData
        const formData = new FormData();
        formData.append('pdf_file', pdfFile);
        formData.append('source_type', sourceType);
        formData.append('include_suppliers', includeSuppliers);
        formData.append('include_risks', includeRisks);
        formData.append('include_price_analysis', includePrice);
        formData.append('include_report', includeReport);
        requestBody = formData;
    } else {
        // Для текста и веб-сайта используем JSON
        headers = {'Content-Type': 'application/json'};
        requestBody = JSON.stringify({
            tender_text: tenderText,
            web_url: webUrl,
            source_type: sourceType,
            include_suppliers: includeSuppliers,
            include_risks: includeRisks,
            include_price_analysis: includePrice,
            include_report: includeReport
        });
    }
    
    // Используем комплексный анализ
    fetch('/api/ai-procure/analyze', {
        method: 'POST',
        headers: headers,
        body: requestBody
    })
    .then(r => r.json())
    .then(data => {
        clearInterval(progressInterval);
        
        if (data.error) throw new Error(data.error);
        
        currentTenderParams = data.tender_params;
        currentAnalysisData = data;
        
        // Начальный прогресс - извлечение параметров
        updateProgress(1, 'completed', 'Параметры тендера извлечены ✓', 30);
        
        let contentHtml = '';
        
        // Параметры тендера
        contentHtml += `
            <div class="result-section">
                <h3>📋 Извлечённые параметры тендера</h3>
                <div class="result-box">${formatTenderParams(data.tender_params, data.completeness)}</div>
            </div>
        `;
        
        // Поставщики
        if (includeSuppliers && data.suppliers) {
            updateProgress(2, 'completed', 'Поставщики подобраны ✓', 50);
            contentHtml += `
                <div class="result-section">
                    <h3>🔍 Подобранные поставщики</h3>
                    <div class="result-box">${formatSuppliers(data.suppliers, data.suppliers_summary)}</div>
                </div>
            `;
            // Обновляем секцию поставщиков
            document.getElementById('suppliers-results').innerHTML = formatSuppliers(data.suppliers, data.suppliers_summary);
        }
        
        // Риски
        if (includeRisks && data.risk_analysis) {
            updateProgress(3, 'completed', 'Риски проанализированы ✓', 75);
            contentHtml += `
                <div class="result-section">
                    <h3>⚠️ Анализ рисков</h3>
                    <div class="result-box">${formatRiskAnalysis(data.risk_analysis)}</div>
                </div>
            `;
            // Обновляем секцию рисков
            document.getElementById('risks-results').innerHTML = formatRiskAnalysis(data.risk_analysis);
        }
        
        // Анализ цен
        if (includePrice && data.price_analysis) {
            contentHtml += `
                <div class="result-section">
                    <h3>💰 Анализ цен</h3>
                    <div class="result-box">${formatPriceAnalysis(data.price_analysis)}</div>
                </div>
            `;
        }
        
        // Отчёт
        if (includeReport && data.report) {
            updateProgress(4, 'completed', 'Отчёт сгенерирован ✓', 90);
            contentHtml += `
                <div class="result-section">
                    <h3>📄 Комплексный отчёт</h3>
                    <div class="result-box">${formatReport(data.report)}</div>
                    <button class="btn btn-secondary" onclick="downloadReport()" style="margin-top: 1rem;">
                        💾 Скачать отчёт
                    </button>
                </div>
            `;
            // Обновляем секцию отчётов
            document.getElementById('reports-results').innerHTML = formatReport(data.report);
        }
        
        document.getElementById('analysis-content').innerHTML = contentHtml;
        
        // Прокручиваем к результатам
        resultDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
        // Обновляем пустые состояния в других секциях
        updateEmptyStates();
        
        // Обновляем статистику
        updateStats();
        
        // Финальный прогресс - 100%
        setTimeout(() => {
            updateProgress(null, null, 'Анализ завершен!', 100);
        }, 500);
    })
    .then(() => {
        if (analyzeBtn) {
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = '<span>🔍</span><span>Начать анализ</span>';
        }
        
        // Убираем прогресс-бар через 3 секунды
        setTimeout(() => {
            const progressDiv = resultDiv.querySelector('div[style*="background: #F0F9FF"]');
            if (progressDiv) {
                progressDiv.style.transition = 'opacity 0.5s';
                progressDiv.style.opacity = '0';
                setTimeout(() => progressDiv.remove(), 500);
            }
        }, 3000);
    })
    .catch(error => {
        clearInterval(progressInterval);
        updateProgress(null, null, 'Ошибка при анализе', 0);
        
        if (analyzeBtn) {
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = '<span>🔍</span><span>Начать анализ</span>';
        }
        document.getElementById('analysis-content').innerHTML = `<div class="error" style="background: #FEE2E2; color: #DC2626; padding: 1rem; border-radius: 8px; border-left: 4px solid #DC2626;">Ошибка: ${error.message}</div>`;
    });
}

// Форматирование параметров тендера
function formatTenderParams(params, completeness) {
    let html = '<div style="display: grid; gap: 1rem;">';
    
    html += `<div style="padding: 1rem; background: #F9FAFB; border-radius: 8px; border-left: 3px solid #8B1E2D;">
        <strong style="color: #8B1E2D; display: block; margin-bottom: 0.5rem;">Заказчик</strong>
        <span style="color: #2D2D2D;">${params.customer?.name || 'Не указан'}</span>
    </div>`;
    
    html += `<div style="padding: 1rem; background: #F9FAFB; border-radius: 8px; border-left: 3px solid #8B1E2D;">
        <strong style="color: #8B1E2D; display: block; margin-bottom: 0.5rem;">Предмет закупки</strong>
        <span style="color: #2D2D2D;">${params.subject?.description || 'Не указан'}</span>
    </div>`;
    
    html += `<div style="padding: 1rem; background: #F9FAFB; border-radius: 8px; border-left: 3px solid #8B1E2D;">
        <strong style="color: #8B1E2D; display: block; margin-bottom: 0.5rem;">Бюджет</strong>
        <span style="color: #2D2D2D; font-size: 1.1rem; font-weight: 600;">${params.budget?.amount || 'Не указан'} ${params.budget?.currency || ''}</span>
    </div>`;
    
    html += `<div style="padding: 1rem; background: #F9FAFB; border-radius: 8px; border-left: 3px solid #8B1E2D;">
        <strong style="color: #8B1E2D; display: block; margin-bottom: 0.5rem;">Срок подачи заявок</strong>
        <span style="color: #2D2D2D;">${params.timeline?.application_end || 'Не указан'}</span>
    </div>`;
    
    const completenessColor = completeness.completeness_percentage >= 80 ? '#059669' : 
                               completeness.completeness_percentage >= 50 ? '#D97706' : '#DC2626';
    html += `<div style="padding: 1rem; background: ${completenessColor === '#059669' ? '#D1FAE5' : completenessColor === '#D97706' ? '#FEF3C7' : '#FEE2E2'}; border-radius: 8px; border-left: 3px solid ${completenessColor};">
        <strong style="color: ${completenessColor}; display: block; margin-bottom: 0.5rem;">Полнота информации</strong>
        <span style="color: #2D2D2D; font-size: 1.1rem; font-weight: 600;">${completeness.completeness_percentage}%</span>
        <span style="color: #6B7280; display: block; margin-top: 0.25rem; font-size: 0.9rem;">${completeness.status}</span>
    </div>`;
    
    html += '</div>';
    return html;
}

// Форматирование поставщиков
function formatSuppliers(suppliers, summary) {
    let html = '<div class="suppliers-list">';
    if (summary) {
        html += `<p style="margin-bottom: 1rem;"><strong>Найдено поставщиков:</strong> ${summary.total_found || suppliers.length} (Высокая релевантность: ${summary.high_relevance || 0}, Средняя: ${summary.medium_relevance || 0})</p>`;
    }
    suppliers.forEach((supplier, index) => {
        html += `<div style="background: #F4F5F7; padding: 1rem; margin: 1rem 0; border-radius: 8px; border-left: 3px solid #8B1E2D;">
            <h4 style="margin: 0 0 0.5rem 0; color: #8B1E2D;">${index + 1}. ${supplier.name} (Релевантность: ${(supplier.relevance_score * 100).toFixed(1)}%)</h4>
            <p style="margin: 0.25rem 0;"><strong>Рейтинг:</strong> ${supplier.rating || 'N/A'}</p>
            <p style="margin: 0.25rem 0;"><strong>Опыт:</strong> ${supplier.experience || 'N/A'}</p>
            <p style="margin: 0.25rem 0;"><strong>Специализация:</strong> ${supplier.specialization || 'N/A'}</p>
            ${supplier.strengths && supplier.strengths.length > 0 ? `<p style="margin: 0.25rem 0;"><strong>Сильные стороны:</strong> ${supplier.strengths.join(', ')}</p>` : ''}
            ${supplier.recommendation ? `<p style="margin: 0.25rem 0;"><strong>Рекомендация:</strong> ${supplier.recommendation}</p>` : ''}
        </div>`;
    });
    html += '</div>';
    return html;
}

// Форматирование анализа рисков
function formatRiskAnalysis(risks) {
    let html = '<div class="risk-analysis">';
    html += `<p style="margin-bottom: 1rem;"><strong>Общий уровень риска:</strong> <span style="color: ${risks.overall_risk_level === 'критический' ? '#DC2626' : risks.overall_risk_level === 'высокий' ? '#F59E0B' : '#10B981'}; font-weight: 600;">${risks.overall_risk_level}</span> (Оценка: ${risks.risk_score || 'N/A'}/100)</p>`;
    html += `<p style="margin-bottom: 1rem;"><strong>Прозрачность:</strong> ${risks.transparency_score || 'N/A'}%</p>`;
    
    if (risks.risks && risks.risks.length > 0) {
        html += '<h4 style="margin-top: 1.5rem; margin-bottom: 1rem;">Выявленные риски:</h4>';
        risks.risks.forEach(risk => {
            html += `<div style="background: #fff; padding: 1rem; margin: 0.5rem 0; border-left: 4px solid #8B1E2D; border-radius: 4px;">
                <p style="margin: 0 0 0.5rem 0;"><strong>${risk.type}</strong> (${risk.severity})</p>
                <p style="margin: 0.5rem 0;">${risk.description}</p>
                ${risk.recommendations && risk.recommendations.length > 0 ? `<p style="margin: 0.5rem 0;"><strong>Рекомендации:</strong> ${risk.recommendations.join(', ')}</p>` : ''}
            </div>`;
        });
    }
    
    if (risks.red_flags && risks.red_flags.length > 0) {
        html += '<h4 style="margin-top: 1.5rem; margin-bottom: 1rem;">Красные флаги:</h4><ul style="list-style: none; padding: 0;">';
        risks.red_flags.forEach(flag => {
            html += `<li style="color: #DC2626; padding: 0.5rem 0; border-bottom: 1px solid #E5E7EB;">⚠️ ${flag}</li>`;
        });
        html += '</ul>';
    }
    
    html += '</div>';
    return html;
}

// Форматирование анализа цен
function formatPriceAnalysis(priceAnalysis) {
    let html = '<div class="price-analysis">';
    html += `<p style="margin-bottom: 1rem;"><strong>Тип аномалии:</strong> ${priceAnalysis.anomaly_type || 'Нет аномалий'}</p>`;
    html += `<p style="margin-bottom: 1rem;"><strong>Отклонение от рынка:</strong> ${priceAnalysis.market_deviation || 0}%</p>`;
    if (priceAnalysis.recommendations && priceAnalysis.recommendations.length > 0) {
        html += '<h4 style="margin-top: 1rem;">Рекомендации:</h4><ul>';
        priceAnalysis.recommendations.forEach(rec => {
            html += `<li>${rec}</li>`;
        });
        html += '</ul>';
    }
    html += '</div>';
    return html;
}

// Форматирование отчёта
function formatReport(report) {
    let html = '<div class="comprehensive-report">';
    
    if (report.executive_summary) {
        html += '<h4 style="margin-top: 0;">Краткое резюме</h4>';
        html += `<p>${report.executive_summary.tender_overview || ''}</p>`;
        html += `<p style="margin-top: 0.5rem;"><strong>Рекомендация:</strong> ${report.executive_summary.recommendation || ''}</p>`;
    }
    
    if (report.supplier_analysis && report.supplier_analysis.top_suppliers) {
        html += '<h4 style="margin-top: 1.5rem;">Топ поставщики</h4>';
        report.supplier_analysis.top_suppliers.forEach((supplier, index) => {
            html += `<p style="margin: 0.5rem 0;"><strong>${index + 1}. ${supplier.name}</strong> - ${supplier.recommendation || ''}</p>`;
        });
    }
    
    if (report.risk_assessment) {
        html += '<h4 style="margin-top: 1.5rem;">Оценка рисков</h4>';
        html += `<p>${report.risk_assessment.summary || ''}</p>`;
    }
    
    if (report.recommendations) {
        html += '<h4 style="margin-top: 1.5rem;">Рекомендации</h4>';
        if (report.recommendations.for_suppliers) {
            html += '<p><strong>Для поставщиков:</strong></p><ul>';
            report.recommendations.for_suppliers.forEach(rec => {
                html += `<li>${rec}</li>`;
            });
            html += '</ul>';
        }
    }
    
    html += '</div>';
    return html;
}

// Скачать отчёт
function downloadReport() {
    if (!currentAnalysisData || !currentAnalysisData.report) {
        alert('Отчёт не сгенерирован');
        return;
    }
    
    const reportText = JSON.stringify(currentAnalysisData.report, null, 2);
    const blob = new Blob([reportText], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `tender_report_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

// Сбор тендеров
function collectTenders() {
    const source = document.getElementById('collection-source').value;
    const resultsDiv = document.getElementById('collection-results');
    
    resultsDiv.innerHTML = '<div class="spinner"></div>';
    
    fetch('/api/ai-procure/collect', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({source: source, filters: {count: 10}})
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) throw new Error(data.error);
        
        let html = `<h3 style="margin-bottom: 1rem;">Найдено тендеров: ${data.count || 0}</h3>`;
        if (data.tenders && data.tenders.length > 0) {
            data.tenders.forEach(tender => {
                html += `<div style="background: #FFFFFF; padding: 1rem; margin: 1rem 0; border-radius: 8px; border: 1px solid #E5E7EB;">
                    <h4 style="margin: 0 0 0.5rem 0; color: #8B1E2D;">${tender.title || tender.tender_id}</h4>
                    <p style="margin: 0.25rem 0;"><strong>Заказчик:</strong> ${tender.customer?.name || 'Не указан'}</p>
                    <p style="margin: 0.25rem 0;"><strong>Бюджет:</strong> ${tender.budget?.amount || 'Не указан'} ${tender.budget?.currency || ''}</p>
                    <button class="btn btn-secondary" onclick="loadTenderForAnalysis('${tender.tender_id || ''}', \`${(tender.description || '').substring(0, 500)}\`)">Анализировать</button>
                </div>`;
            });
        }
        resultsDiv.innerHTML = html;
    })
    .catch(error => {
        resultsDiv.innerHTML = `<div class="error" style="background: #FEE2E2; color: #DC2626; padding: 1rem; border-radius: 8px;">Ошибка: ${error.message}</div>`;
    });
}

// Загрузить тендер для анализа
function loadTenderForAnalysis(tenderId, description) {
    document.getElementById('tender-text').value = description;
    scrollToSection('analysis');
}

// Загрузка метрик
function loadMetrics() {
    const accuracyEl = document.getElementById('metric-accuracy');
    const risksEl = document.getElementById('metric-risks');
    const timeEl = document.getElementById('metric-time');
    const completionEl = document.getElementById('metric-completion');
    
    // Проверяем, что элементы существуют
    if (!accuracyEl || !risksEl || !timeEl || !completionEl) {
        console.warn('Элементы метрик не найдены в DOM');
        return;
    }
    
    // Показываем загрузку
    accuracyEl.textContent = '...';
    risksEl.textContent = '...';
    timeEl.textContent = '...';
    completionEl.textContent = '...';
    
    // Сбрасываем цвета
    accuracyEl.style.color = '#8B1E2D';
    risksEl.style.color = '#8B1E2D';
    timeEl.style.color = '#8B1E2D';
    completionEl.style.color = '#8B1E2D';
    
    Promise.all([
        fetch('/api/ai-procure/metrics/performance').then(r => {
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            return r.json();
        }),
        fetch('/api/ai-procure/metrics/risks').then(r => {
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            return r.json();
        }),
        fetch('/api/ai-procure/metrics/usability').then(r => {
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            return r.json();
        })
    ])
    .then(([perfResponse, risksResponse, usabilityResponse]) => {
        const perf = perfResponse.metrics || perfResponse;
        const totalOperations = perf?.total_operations || {};
        const tendersProcessed = totalOperations.tenders_processed || 0;
        
        // Проверяем, были ли проведены анализы
        if (tendersProcessed === 0) {
            // Если анализов не было, показываем сообщение
            const metricsGrid = document.querySelector('.metrics-grid');
            if (metricsGrid) {
                metricsGrid.innerHTML = `
                    <div style="grid-column: 1 / -1; text-align: center; padding: 3rem 2rem; background: #F9FAFB; border-radius: 12px; border: 2px dashed #E5E7EB;">
                        <div style="font-size: 4rem; margin-bottom: 1rem; opacity: 0.5;">📊</div>
                        <h3 style="color: #374151; margin: 0 0 0.5rem 0; font-size: 1.25rem;">Метрики появятся после анализа</h3>
                        <p style="color: #6B7280; margin: 0 0 1.5rem 0; font-size: 0.9375rem;">Проведите анализ тендера, чтобы увидеть статистику производительности системы</p>
                        <button class="btn btn-primary" onclick="scrollToSection('analysis')">
                            <span>📊</span>
                            <span>Перейти к анализу</span>
                        </button>
                    </div>
                `;
            }
            return;
        }
        
        // Обработка метрик производительности
        if (perfResponse.error) {
            console.error('Ошибка метрик производительности:', perfResponse.error);
            accuracyEl.textContent = '0%';
            accuracyEl.style.color = '#6B7280';
            timeEl.textContent = '0с';
            timeEl.style.color = '#6B7280';
        } else {
            console.log('Метрики производительности:', perf);
            
            // Точность извлечения
            if (perf.extraction_accuracy) {
                if (perf.extraction_accuracy.average !== undefined && perf.extraction_accuracy.average > 0) {
                    // Структура с average (правильная структура)
                    const avg = perf.extraction_accuracy.average;
                    accuracyEl.textContent = `${avg.toFixed(1)}%`;
                    // Добавляем визуальную индикацию достижения цели
                    if (avg >= 90) {
                        accuracyEl.style.color = '#10B981';
                    } else if (avg >= 70) {
                        accuracyEl.style.color = '#F59E0B';
                    } else {
                        accuracyEl.style.color = '#EF4444';
                    }
                } else if (Array.isArray(perf.extraction_accuracy) && perf.extraction_accuracy.length > 0) {
                    // Массив значений (fallback)
                    const avg = perf.extraction_accuracy.reduce((a, b) => a + b, 0) / perf.extraction_accuracy.length;
                    if (avg > 0) {
                        accuracyEl.textContent = `${avg.toFixed(1)}%`;
                        if (avg >= 90) accuracyEl.style.color = '#10B981';
                        else if (avg >= 70) accuracyEl.style.color = '#F59E0B';
                        else accuracyEl.style.color = '#EF4444';
                    } else {
                        accuracyEl.textContent = '-';
                        accuracyEl.style.color = '#6B7280';
                    }
                } else {
                    accuracyEl.textContent = '-';
                    accuracyEl.style.color = '#6B7280';
                }
            } else {
                accuracyEl.textContent = '-';
                accuracyEl.style.color = '#6B7280';
            }
            
            // Время обработки
            if (perf.processing_time && perf.processing_time.average_seconds !== undefined && perf.processing_time.average_seconds > 0) {
                const avgTime = perf.processing_time.average_seconds;
                timeEl.textContent = `${avgTime.toFixed(2)}с`;
                timeEl.style.color = '#8B1E2D';
            } else {
                timeEl.textContent = '-';
                timeEl.style.color = '#6B7280';
            }
        }
        
        // Обработка метрик рисков (подтверждение рисков)
        // Используем endpoint для подтверждения рисков
        fetch('/api/ai-procure/risks/confirmation-statistics')
            .then(r => {
                if (!r.ok) throw new Error(`HTTP ${r.status}`);
                return r.json();
            })
            .then(data => {
                console.log('Статистика подтверждения рисков:', data);
                if (data.error || !data.statistics) {
                    // Fallback на метрики обнаружения рисков
                    const risks = risksResponse.metrics || risksResponse;
                    if (risks.high_risk_percentage !== undefined) {
                        risksEl.textContent = `${risks.high_risk_percentage.toFixed(1)}%`;
                        risksEl.style.color = '#8B1E2D';
                    } else {
                        risksEl.textContent = '0%';
                        risksEl.style.color = '#6B7280';
                    }
                } else {
                    const stats = data.statistics;
                    if (stats.confirmation_rate !== undefined) {
                        const rate = stats.confirmation_rate;
                        risksEl.textContent = `${rate.toFixed(1)}%`;
                        // Визуальная индикация достижения цели (≥80%)
                        if (rate >= 80) {
                            risksEl.style.color = '#10B981';
                        } else if (rate >= 60) {
                            risksEl.style.color = '#F59E0B';
                        } else {
                            risksEl.style.color = '#EF4444';
                        }
                    } else {
                        risksEl.textContent = '0%';
                        risksEl.style.color = '#6B7280';
                    }
                }
            })
            .catch(error => {
                console.warn('Ошибка загрузки статистики подтверждения рисков:', error);
                // Fallback на метрики обнаружения рисков
                const risks = risksResponse.metrics || risksResponse;
                if (risks.high_risk_percentage !== undefined && risks.high_risk_percentage > 0) {
                    risksEl.textContent = `${risks.high_risk_percentage.toFixed(1)}%`;
                    risksEl.style.color = '#8B1E2D';
                } else {
                    risksEl.textContent = '-';
                    risksEl.style.color = '#6B7280';
                }
            });
        
        // Обработка метрик usability
        if (usabilityResponse.error) {
            console.error('Ошибка метрик usability:', usabilityResponse.error);
            completionEl.textContent = '-';
            completionEl.style.color = '#6B7280';
        } else {
            const usability = usabilityResponse.metrics || usabilityResponse;
            console.log('Метрики usability:', usability);
            
            // Completion Rate
            if (usability.completion_rate_percent !== undefined && usability.completion_rate_percent > 0) {
                const rate = usability.completion_rate_percent;
                completionEl.textContent = `${rate.toFixed(1)}%`;
                // Визуальная индикация достижения цели (≥80%)
                if (rate >= 80) {
                    completionEl.style.color = '#10B981';
                } else if (rate >= 60) {
                    completionEl.style.color = '#F59E0B';
                } else {
                    completionEl.style.color = '#EF4444';
                }
            } else if (usability.completion_rate !== undefined && usability.completion_rate > 0) {
                const rate = usability.completion_rate * 100;
                completionEl.textContent = `${rate.toFixed(1)}%`;
                if (rate >= 80) completionEl.style.color = '#10B981';
                else if (rate >= 60) completionEl.style.color = '#F59E0B';
                else completionEl.style.color = '#EF4444';
            } else {
                // Вычисляем из данных
                const total = usability.total_requests || usability.total_dialogs || 0;
                const successful = usability.successful_completions || usability.reports_generated || usability.completed_dialogs || 0;
                if (total > 0 && successful > 0) {
                    const rate = (successful / total) * 100;
                    completionEl.textContent = `${rate.toFixed(1)}%`;
                    if (rate >= 80) completionEl.style.color = '#10B981';
                    else if (rate >= 60) completionEl.style.color = '#F59E0B';
                    else completionEl.style.color = '#EF4444';
                } else {
                    completionEl.textContent = '-';
                    completionEl.style.color = '#6B7280';
                }
            }
        }
    })
    .catch(error => {
        console.error('Ошибка загрузки метрик:', error);
        // Показываем сообщение об ошибке или пустое состояние
        const metricsGrid = document.querySelector('.metrics-grid');
        if (metricsGrid) {
            metricsGrid.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; padding: 3rem 2rem; background: #F9FAFB; border-radius: 12px; border: 2px dashed #E5E7EB;">
                    <div style="font-size: 4rem; margin-bottom: 1rem; opacity: 0.5;">📊</div>
                    <h3 style="color: #374151; margin: 0 0 0.5rem 0; font-size: 1.25rem;">Метрики появятся после анализа</h3>
                    <p style="color: #6B7280; margin: 0 0 1.5rem 0; font-size: 0.9375rem;">Проведите анализ тендера, чтобы увидеть статистику производительности системы</p>
                    <button class="btn btn-primary" onclick="scrollToSection('analysis')">
                        <span>📊</span>
                        <span>Перейти к анализу</span>
                    </button>
                </div>
            `;
        }
    });
}

// Обновление статистики
function updateStats() {
    // Обновляем статистику в сайдбаре
    const processed = parseInt(document.getElementById('stats-processed').textContent) || 0;
    document.getElementById('stats-processed').textContent = processed + 1;
    
    if (currentAnalysisData && currentAnalysisData.suppliers) {
        document.getElementById('stats-suppliers').textContent = currentAnalysisData.suppliers.length;
    }
}

// Обновление пустых состояний
function updateEmptyStates() {
    // Убираем пустые состояния, если есть данные
    if (currentAnalysisData) {
        const suppliersResults = document.getElementById('suppliers-results');
        const risksResults = document.getElementById('risks-results');
        const reportsResults = document.getElementById('reports-results');
        
        // Проверяем, есть ли уже контент (не пустое состояние)
        if (suppliersResults && currentAnalysisData.suppliers && suppliersResults.querySelector('.empty-state')) {
            suppliersResults.querySelector('.empty-state').remove();
        }
        
        if (risksResults && currentAnalysisData.risk_analysis && risksResults.querySelector('.empty-state')) {
            risksResults.querySelector('.empty-state').remove();
        }
        
        if (reportsResults && currentAnalysisData.report && reportsResults.querySelector('.empty-state')) {
            reportsResults.querySelector('.empty-state').remove();
        }
    }
}

// Функции для новичков
function loadBeginnerRating() {
    const ratingEl = document.getElementById('beginner-rating');
    if (!ratingEl) return;
    
    fetch('/api/ai-procure/beginner/rating')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                ratingEl.innerHTML = `<p>Ошибка: ${data.error}</p>`;
                return;
            }
            
            const rating = data.rating;
            let html = '<div class="rating-info">';
            html += `<p><strong>Уровень:</strong> ${rating.level}</p>`;
            html += `<p><strong>Рейтинг:</strong> ${rating.rating}%</p>`;
            html += `<p><strong>Очки опыта:</strong> ${rating.experience_points}</p>`;
            html += `<p><strong>Участий в тендерах:</strong> ${rating.tenders_participated}</p>`;
            html += '</div>';
            ratingEl.innerHTML = html;
        })
        .catch(error => {
            ratingEl.innerHTML = `<p>Ошибка: ${error.message}</p>`;
        });
}

function loadGuide() {
    const guideContentEl = document.getElementById('guide-content');
    if (!guideContentEl) return;
    
    const step = document.getElementById('guide-step')?.value || 1;
    if (!currentTenderParams) {
        alert('Сначала проанализируйте тендер');
        return;
    }
    
    guideContentEl.innerHTML = '<div class="spinner"></div>';
    
    fetch('/api/ai-procure/beginner/guide', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            tender_params: currentTenderParams,
            step: parseInt(step)
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            guideContentEl.innerHTML = `<p>Ошибка: ${data.error}</p>`;
            return;
        }
        
        const guide = data.guide;
        let html = `<h4>${guide.step_name}</h4>`;
        html += `<p>${guide.description}</p>`;
        
        if (guide.actions && guide.actions.length > 0) {
            html += '<h5>Действия:</h5><ul>';
            guide.actions.forEach(action => {
                html += `<li><strong>${action.action}</strong>: ${action.description}</li>`;
            });
            html += '</ul>';
        }
        
        if (guide.checklist && guide.checklist.length > 0) {
            html += '<h5>Чеклист:</h5><ul>';
            guide.checklist.forEach(item => {
                html += `<li>${item}</li>`;
            });
            html += '</ul>';
        }
        
        guideContentEl.innerHTML = html;
    })
    .catch(error => {
        guideContentEl.innerHTML = `<p>Ошибка: ${error.message}</p>`;
    });
}

function improveCompanyDescriptionWithAI() {
    const companyDesc = document.getElementById('beginner-company').value;
    
    if (!companyDesc.trim()) {
        alert('Пожалуйста, введите описание компании для улучшения');
        return;
    }
    
    fetch('/api/ai-procure/improve-company-description', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({description: companyDesc})
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) {
            alert('Ошибка: ' + data.error);
            return;
        }
        
        document.getElementById('beginner-company').value = data.improved_description || '';
    })
    .catch(e => {
        alert('Ошибка: ' + e.message);
    });
}

function findPartnerships() {
    const companyInfoEl = document.getElementById('beginner-company');
    const partnershipsResultEl = document.getElementById('partnerships-result');
    
    if (!companyInfoEl) return;
    
    const companyInfo = companyInfoEl.value;
    if (!companyInfo.trim()) {
        alert('Опишите вашу компанию');
        return;
    }
    
    if (!currentTenderParams) {
        alert('Сначала проанализируйте тендер');
        return;
    }
    
    if (partnershipsResultEl) {
        partnershipsResultEl.style.display = 'block';
        partnershipsResultEl.innerHTML = '<div class="spinner"></div>';
    }
    
    fetch('/api/ai-procure/beginner/partnerships', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            beginner_supplier: { description: companyInfo },
            tender_params: currentTenderParams
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            partnershipsResultEl.innerHTML = `<p>Ошибка: ${data.error}</p>`;
            return;
        }
        
        let html = '<h4>Потенциальные партнёры:</h4>';
        if (data.partners && data.partners.length > 0) {
            data.partners.forEach((partner, index) => {
                html += `<div style="background: #F4F5F7; padding: 1rem; margin: 1rem 0; border-radius: 8px;">
                    <h5>${index + 1}. ${partner.name}</h5>
                    <p><strong>Опыт:</strong> ${partner.experience || 'N/A'}</p>
                    <p><strong>Рекомендация:</strong> ${partner.recommendation || 'N/A'}</p>
                </div>`;
            });
        }
        partnershipsResultEl.innerHTML = html;
    })
    .catch(error => {
        partnershipsResultEl.innerHTML = `<p>Ошибка: ${error.message}</p>`;
    });
}

function generateDocuments() {
    if (!currentTenderParams) {
        alert('Сначала проанализируйте тендер');
        return;
    }
    
    const docTypeEl = document.getElementById('document-type');
    const generatedDocEl = document.getElementById('generated-document');
    
    if (!docTypeEl || !generatedDocEl) return;
    
    const docType = docTypeEl.value;
    generatedDocEl.style.display = 'block';
    generatedDocEl.innerHTML = '<div class="spinner"></div>';
    
    fetch('/api/ai-procure/beginner/generate-documents', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            tender_params: currentTenderParams,
            document_type: docType
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            generatedDocEl.innerHTML = `<p>Ошибка: ${data.error}</p>`;
            return;
        }
        
        const doc = data.document;
        let html = `<h4>${doc.title}</h4>`;
        html += `<p>Тип: ${doc.document_type}</p>`;
        if (doc.sections && doc.sections.length > 0) {
            html += '<h5>Разделы:</h5><ul>';
            doc.sections.forEach(section => {
                html += `<li>${section}</li>`;
            });
            html += '</ul>';
        }
        html += `<p>${doc.content}</p>`;
        generatedDocEl.innerHTML = html;
    })
    .catch(error => {
        generatedDocEl.innerHTML = `<p>Ошибка: ${error.message}</p>`;
    });
}

// Онбординг
let currentOnboardingStep = 1;
const totalOnboardingSteps = 3;

function showOnboarding() {
    const overlay = document.getElementById('onboarding-overlay');
    if (overlay) {
        overlay.style.display = 'flex';
        currentOnboardingStep = 1;
        updateOnboardingStep();
    }
}

function closeOnboarding() {
    const overlay = document.getElementById('onboarding-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
    // Сохраняем, что пользователь видел онбординг
    localStorage.setItem('ai-procure-onboarding-seen', 'true');
}

function nextOnboardingStep() {
    if (currentOnboardingStep < totalOnboardingSteps) {
        currentOnboardingStep++;
        updateOnboardingStep();
    }
}

function prevOnboardingStep() {
    if (currentOnboardingStep > 1) {
        currentOnboardingStep--;
        updateOnboardingStep();
    }
}

function updateOnboardingStep() {
    // Скрываем все шаги
    for (let i = 1; i <= totalOnboardingSteps; i++) {
        const step = document.getElementById(`onboarding-step-${i}`);
        if (step) {
            step.classList.remove('active');
        }
    }
    
    // Показываем текущий шаг
    const currentStep = document.getElementById(`onboarding-step-${currentOnboardingStep}`);
    if (currentStep) {
        currentStep.classList.add('active');
    }
    
    // Обновляем прогресс
    const currentEl = document.getElementById('onboarding-current');
    if (currentEl) {
        currentEl.textContent = currentOnboardingStep;
    }
    
    // Обновляем кнопки
    const prevBtn = document.getElementById('onboarding-prev');
    const nextBtn = document.getElementById('onboarding-next');
    const startBtn = document.getElementById('onboarding-start');
    
    if (prevBtn) {
        prevBtn.style.display = currentOnboardingStep > 1 ? 'inline-flex' : 'none';
    }
    
    if (nextBtn && startBtn) {
        if (currentOnboardingStep === totalOnboardingSteps) {
            nextBtn.style.display = 'none';
            startBtn.style.display = 'inline-flex';
        } else {
            nextBtn.style.display = 'inline-flex';
            startBtn.style.display = 'none';
        }
    }
}

function startUsing() {
    closeOnboarding();
    // Прокручиваем к секции анализа
    scrollToSection('analysis');
}

// Подсказки при наведении
let tooltipTimeout = null;

document.addEventListener('mouseover', (e) => {
    const element = e.target.closest('[data-tooltip]');
    if (element) {
        const tooltip = document.getElementById('tooltip');
        if (tooltip) {
            const text = element.getAttribute('data-tooltip');
            tooltip.textContent = text;
            tooltip.style.display = 'block';
            
            tooltipTimeout = setTimeout(() => {
                const rect = element.getBoundingClientRect();
                tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
                tooltip.style.top = rect.top - tooltip.offsetHeight - 10 + 'px';
            }, 100);
        }
    }
});

document.addEventListener('mouseout', (e) => {
    if (e.target.closest('[data-tooltip]')) {
        const tooltip = document.getElementById('tooltip');
        if (tooltip) {
            tooltip.style.display = 'none';
        }
        if (tooltipTimeout) {
            clearTimeout(tooltipTimeout);
        }
    }
});

// Загрузка примера тендера
function loadExampleTender() {
    const exampleText = `ТЕНДЕР НА ЗАКУПКУ ОФИСНОЙ ТЕХНИКИ

Заказчик: ТОО "ОфисСнаб"
ИНН: 123456789012
Адрес: г. Алматы, ул. Абая, 150

ПРЕДМЕТ ЗАКУПКИ:
Закупка офисной техники для оснащения рабочих мест:
- Персональные компьютеры: 20 шт.
- Мониторы: 20 шт.
- Принтеры: 5 шт.
- Клавиатуры и мыши: 20 комплектов

ТРЕБОВАНИЯ К КАЧЕСТВУ:
- Компьютеры: процессор не ниже Intel Core i5, RAM не менее 8GB, SSD не менее 256GB
- Мониторы: диагональ не менее 24 дюймов, разрешение Full HD
- Принтеры: лазерные, цветные, с функцией сканирования

БЮДЖЕТ:
Сумма: 8 500 000 тенге (с НДС)
Валюта: KZT
Тип цены: фиксированная

СРОКИ:
Дата публикации: 10.01.2025
Начало приёма заявок: 10.01.2025
Конец приёма заявок: 25.01.2025, 18:00
Период оценки: 26.01.2025 - 30.01.2025
Подписание договора: до 05.02.2025

ТРЕБОВАНИЯ К УЧАСТНИКАМ:
- Опыт работы в сфере IT не менее 3 лет
- Наличие лицензий на продажу компьютерной техники
- Минимальный годовой оборот: 10 000 000 тенге
- Наличие сертификатов качества на продукцию

КРИТЕРИИ ОЦЕНКИ:
- Цена: 40%
- Качество продукции: 30%
- Опыт и репутация: 20%
- Сроки поставки: 10%

МЕТОД ВЫБОРА:
Открытый конкурс с оценкой по критериям

КОНТАКТЫ:
Телефон: +7 (727) 123-45-67
Email: zakupki@ofissnab.kz`;

    document.getElementById('tender-text').value = exampleText;
    
    // Показываем уведомление
    showNotification('✅ Пример тендера загружен! Теперь можете нажать "Начать анализ"', 'success');
}

// Уведомления
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 100px;
        right: 20px;
        background: ${type === 'success' ? '#10B981' : type === 'error' ? '#EF4444' : '#3B82F6'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        z-index: 10001;
        animation: slideInRight 0.3s ease;
        max-width: 400px;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    // Проверяем, видел ли пользователь онбординг
    const onboardingSeen = localStorage.getItem('ai-procure-onboarding-seen');
    if (!onboardingSeen) {
        // Показываем онбординг через 1 секунду после загрузки
        setTimeout(() => {
            showOnboarding();
        }, 1000);
    }
    
    // Небольшая задержка, чтобы убедиться, что все элементы созданы
    setTimeout(() => {
        loadMetrics();
        loadBeginnerRating();
    }, 100);
    
    // Также загружаем метрики при прокрутке к секции метрик
    const metricsSection = document.getElementById('metrics');
    if (metricsSection) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    loadMetrics();
                }
            });
        }, { threshold: 0.1 });
        observer.observe(metricsSection);
    }
    
    // Добавляем анимации для карточек действий
    const actionCards = document.querySelectorAll('.action-card');
    actionCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-4px) scale(1.02)';
        });
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
    
    // Инициализация и обработка радио-кнопок типа источника
    const radioButtons = document.querySelectorAll('input[name="source-type"]');
    radioButtons.forEach(radio => {
        const label = radio.closest('label');
        
        // Инициализация выбранного состояния
        if (radio.checked && label) {
            label.classList.add('radio-selected');
        }
        
        // Обработчик изменения
        radio.addEventListener('change', function() {
            // Убираем класс со всех лейблов
            document.querySelectorAll('.radio-group label').forEach(lbl => {
                lbl.classList.remove('radio-selected');
            });
            
            // Добавляем класс к выбранному лейблу
            if (this.checked && label) {
                label.classList.add('radio-selected');
            }
            
            // Переключаем поля ввода в зависимости от выбранного типа
            toggleSourceFields(this.value);
        });
    });
    
    // Инициализация полей при загрузке
    toggleSourceFields(document.querySelector('input[name="source-type"]:checked').value);
});

// CSS анимации для уведомлений
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(100%);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    @keyframes slideOutRight {
        from {
            opacity: 1;
            transform: translateX(0);
        }
        to {
            opacity: 0;
            transform: translateX(100%);
        }
    }
`;
document.head.appendChild(style);


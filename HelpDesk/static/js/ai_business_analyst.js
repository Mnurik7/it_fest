// Global state
let chatHistory = [];
let currentBRD = null;
let useCases = [];
let userStories = [];

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    loadInitialData();
});

function loadInitialData() {
    // Load existing BRD, Use Cases, User Stories if any
    // This would typically come from the backend
}

// Requirements Chat Functions
function handleRequirementsKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendRequirementsMessage();
    }
}

// Переменная для хранения загруженного файла
let uploadedFile = null;

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // Проверяем формат
    const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
    const allowedExtensions = ['.pdf', '.doc', '.docx', '.txt'];
    const fileExt = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!allowedExtensions.includes(fileExt)) {
        alert('Поддерживаются только файлы: PDF, DOC, DOCX, TXT');
        return;
    }
    
    uploadedFile = file;
    
    // Показываем информацию о файле
    const fileInfo = document.getElementById('file-info');
    const fileName = document.getElementById('file-name');
    if (fileInfo && fileName) {
        fileName.textContent = `📄 ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
        fileInfo.style.display = 'flex';
    }
    
    // Автоматически загружаем и анализируем файл
    uploadAndAnalyzeDocument(file);
}

function removeFile() {
    uploadedFile = null;
    const fileInfo = document.getElementById('file-info');
    const fileInput = document.getElementById('file-input');
    if (fileInfo) fileInfo.style.display = 'none';
    if (fileInput) fileInput.value = '';
}

function uploadAndAnalyzeDocument(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    // Показываем сообщение о загрузке
    const loadingMsg = addRequirementsMessage('bot', '📄 Загружаю и анализирую документ...', true);
    
    fetch('/api/ai-business-analyst/upload-file', {
        method: 'POST',
        credentials: 'include',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        loadingMsg.remove();
        
        if (data.error) {
            addRequirementsMessage('bot', '❌ Ошибка: ' + data.error);
            removeFile();
            return;
        }
        
        if (data.text) {
            // Если анализ уже есть, используем его, иначе анализируем отдельно
            if (data.analysis) {
                displayDocumentAnalysis(data.analysis, data.filename || file.name);
                // Автоматически заполняем поля BRD
                setTimeout(() => {
                    fillBRDFromDocumentAnalysis(data.analysis);
                }, 1000);
            } else {
                // Анализируем документ отдельно
                analyzeDocumentInChat(data.text, file.name);
            }
        } else {
            addRequirementsMessage('bot', '❌ Не удалось извлечь текст из файла');
            removeFile();
        }
    })
    .catch(error => {
        loadingMsg.remove();
        addRequirementsMessage('bot', '❌ Ошибка при загрузке файла: ' + error.message);
        removeFile();
    });
}

function analyzeDocumentInChat(documentText, fileName) {
    // Показываем сообщение об анализе
    const analyzingMsg = addRequirementsMessage('bot', '🔍 Анализирую документ...', true);
    
    // Отправляем на анализ
    fetch('/api/ai-business-analyst/analyze-document', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
            document_text: documentText.substring(0, 50000), // Ограничиваем размер
            document_type: detectDocumentType(fileName)
        })
    })
    .then(response => response.json())
    .then(data => {
        analyzingMsg.remove();
        
        if (data.error) {
            addRequirementsMessage('bot', '❌ Ошибка анализа: ' + data.error);
            return;
        }
        
        // Показываем результаты анализа
        displayDocumentAnalysis(data.analysis, fileName);
        
        // Добавляем в историю
        chatHistory.push({
            role: 'user',
            content: `Загружен документ: ${fileName}`
        });
        chatHistory.push({
            role: 'assistant',
            content: 'Документ проанализирован. Результаты ниже.'
        });
        
        // Автоматически заполняем поля BRD из анализа
        if (data.analysis) {
            setTimeout(() => {
                fillBRDFromDocumentAnalysis(data.analysis);
            }, 1000);
        }
    })
    .catch(error => {
        analyzingMsg.remove();
        addRequirementsMessage('bot', '❌ Ошибка при анализе: ' + error.message);
    });
}

function displayDocumentAnalysis(analysis, fileName) {
    const container = document.getElementById('requirements-chat');
    const analysisDiv = document.createElement('div');
    analysisDiv.className = 'ba-message bot-message';
    
    let analysisContent = '';
    if (analysis && analysis.raw_analysis) {
        analysisContent = analysis.raw_analysis;
    } else if (typeof analysis === 'string') {
        analysisContent = analysis;
    } else {
        analysisContent = JSON.stringify(analysis, null, 2);
    }
    
    analysisDiv.innerHTML = `
        <div class="ba-message-avatar">📄</div>
        <div class="ba-message-content">
            <div class="ba-message-text">
                <div class="ba-document-analysis">
                    <h5>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                            <polyline points="14 2 14 8 20 8"></polyline>
                        </svg>
                        Анализ документа: ${escapeHtml(fileName)}
                    </h5>
                    <div class="ba-document-analysis-content">
                        ${formatMessage(analysisContent)}
                    </div>
                </div>
            </div>
        </div>
    `;
    
    container.appendChild(analysisDiv);
    container.scrollTop = container.scrollHeight;
}

function detectDocumentType(fileName) {
    const lowerName = fileName.toLowerCase();
    if (lowerName.includes('тз') || lowerName.includes('техническое задание')) return 'ТЗ';
    if (lowerName.includes('регламент')) return 'Регламент';
    if (lowerName.includes('требование') || lowerName.includes('requirement')) return 'Требования';
    if (lowerName.includes('письмо')) return 'Письмо';
    if (lowerName.includes('протокол')) return 'Протокол';
    return 'Документ';
}

function fillBRDFromDocumentAnalysis(analysis) {
    // Извлекаем информацию из анализа и заполняем поля BRD
    const analysisText = typeof analysis === 'string' ? analysis : (analysis.raw_analysis || '');
    
    // Пытаемся извлечь название проекта
    const projectNameMatch = analysisText.match(/(?:проект|название)[\s:]+([^\n]+)/i);
    if (projectNameMatch && !document.getElementById('project-name')?.value) {
        document.getElementById('project-name').value = projectNameMatch[1].trim();
    }
    
    // Пытаемся извлечь scope
    const scopeMatch = analysisText.match(/(?:scope|область|входит)[\s:]+([^\n]+)/i);
    if (scopeMatch) {
        const scopeItems = scopeMatch[1].split(/[,;]/).map(s => s.trim()).filter(s => s);
        scopeItems.forEach(item => {
            if (item && item.length > 3) {
                addScopeItem();
                const items = document.querySelectorAll('#scope-checklist .ba-editable-text');
                if (items.length > 0) {
                    items[items.length - 1].value = item;
                }
            }
        });
    }
    
    saveBRDData();
    
    // Показываем уведомление
    const notification = document.createElement('div');
    notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #10b981; color: white; padding: 1rem 1.5rem; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); z-index: 10000;';
    notification.textContent = '✅ Поля BRD заполнены из документа';
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}

function sendRequirementsMessage() {
    const input = document.getElementById('requirements-input');
    const message = input.value.trim();
    
    // Если есть загруженный файл, отправляем его вместе с сообщением
    if (uploadedFile && !message) {
        // Файл уже обработан, просто очищаем
        removeFile();
        return;
    }
    
    if (!message && !uploadedFile) return;
    
    // Add user message to chat
    addRequirementsMessage('user', message);
    input.value = '';
    
    // Show loading
    const loadingMsg = addRequirementsMessage('bot', '...', true);
    
    // Send to API
    fetch('/api/ai-business-analyst/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include', // Передаем cookies для сессии
        body: JSON.stringify({
            message: message,
            chat_history: chatHistory,
            session_id: getSessionId(),
            use_structured_dialog: true, // Используем структурированный диалог
            context: {
                customer: '',
                purpose: '',
                for_confluence: false
            }
        })
    })
    .then(response => response.json())
    .then(data => {
        loadingMsg.remove();
        if (data.error) {
            addRequirementsMessage('bot', 'Ошибка: ' + data.error);
        } else {
            addRequirementsMessage('bot', data.response);
            chatHistory.push({ role: 'user', content: message });
            chatHistory.push({ role: 'assistant', content: data.response });
            
            // Показываем предложения вариантов ответа из структурированного диалога
            if (data.answer_suggestions && data.answer_suggestions.length > 0) {
                setTimeout(() => {
                    displayAnswerSuggestions(data.answer_suggestions);
                }, 500);
            }
            // Или запрашиваем предложения через API, если их нет и это вопрос
            else if (data.response && data.response.length > 20 && (data.response.includes('?') || data.response.includes('Как'))) {
                setTimeout(() => {
                    showAnswerSuggestions(data.response);
                }, 500);
            }
            
            // Сохраняем session_id для дальнейшего использования
            if (data.session_id) {
                window.baSessionId = data.session_id;
            }
            
            // Автозаполнение полей BRD из чата
            if (chatHistory.length >= 4) {
                setTimeout(() => {
                    suggestAutofillFromChat();
                }, 1000);
            }
            
            // Auto-generate BRD if user provides project description
            if (message.length > 50 && (message.toLowerCase().includes('система') || message.toLowerCase().includes('проект'))) {
                generateBRDFromChat(message);
            }
            
            // Автоматическое заполнение полей BRD из собранных данных
            if (data.dialog_stats && data.dialog_stats.data_fields_collected > 0) {
                setTimeout(() => {
                    autoFillFieldsFromDialog(data);
                }, 1500);
            }
        }
    })
    .catch(error => {
        loadingMsg.remove();
        addRequirementsMessage('bot', 'Ошибка при отправке сообщения: ' + error.message);
    });
}

function autoFillFieldsFromDialog(data) {
    // Автоматически заполняем поля BRD из структурированного диалога
    if (data.session_id && data.current_stage) {
        fetch('/api/ai-business-analyst/autocomplete/fill-from-chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
                session_id: data.session_id,
                chat_history: chatHistory
            })
        })
        .then(response => response.json())
        .then(autofillData => {
            if (autofillData.success && autofillData.filled_data) {
                // Тихим образом заполняем поля, если они пустые
                const filled = autofillData.filled_data;
                
                // Заполняем название проекта, если пусто
                const projectNameInput = document.getElementById('project-name');
                if (projectNameInput && !projectNameInput.value && filled.project_name) {
                    projectNameInput.value = filled.project_name;
                }
                
                // Заполняем scope, если пусто
                const scopeChecklist = document.getElementById('scope-checklist');
                if (scopeChecklist && scopeChecklist.children.length === 0 && filled.scope) {
                    filled.scope.forEach(item => {
                        addScopeItem();
                        const items = document.querySelectorAll('#scope-checklist .ba-editable-text');
                        if (items.length > 0) {
                            items[items.length - 1].value = item;
                        }
                    });
                }
                
                saveBRDData();
            }
        })
        .catch(err => console.error('Auto-fill error:', err));
    }
}

function addRequirementsMessage(role, text, isLoading = false) {
    const container = document.getElementById('requirements-chat');
    const messageDiv = document.createElement('div');
    messageDiv.className = `ba-message ${role}-message`;
    
    if (role === 'user') {
        messageDiv.innerHTML = `
            <div class="ba-message-content">
                <div class="ba-message-text">${formatMessage(text)}</div>
            </div>
        `;
    } else {
        messageDiv.innerHTML = `
            <div class="ba-message-avatar">🧠</div>
            <div class="ba-message-content">
                <div class="ba-message-text">${isLoading ? '<div class="typing-indicator"><span></span><span></span><span></span></div>' : formatMessage(text)}</div>
            </div>
        `;
    }
    
    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
    
    return messageDiv;
}

function formatMessage(text) {
    if (typeof text !== 'string') text = String(text);
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
}

// BRD Functions
function generateBRDFromChat(projectDescription) {
    // Show loading indicator
    const loadingIndicator = document.createElement('div');
    loadingIndicator.textContent = 'Генерация BRD...';
    loadingIndicator.style.cssText = 'position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 1rem 2rem; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 1000;';
    document.body.appendChild(loadingIndicator);
    
    // First analyze the document
    fetch('/api/ai-business-analyst/analyze', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include', // Передаем cookies для сессии
        body: JSON.stringify({
            document_text: projectDescription,
            generate_documents: true
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => Promise.reject(new Error(err.error || 'Ошибка сервера')));
        }
        return response.json();
    })
    .then(data => {
        loadingIndicator.remove();
        
        if (data.success && data.brd) {
            // Extract content from BRD object
            let brdContent = '';
            if (typeof data.brd === 'string') {
                brdContent = data.brd;
            } else if (data.brd.content) {
                brdContent = data.brd.content;
            } else if (data.brd.error) {
                throw new Error(data.brd.error);
            } else {
                brdContent = JSON.stringify(data.brd);
            }
            
            updateBRDDisplay(brdContent);
            currentBRD = brdContent;
            
            // Also generate Use Cases and User Stories if available
            if (data.user_stories) {
                const stories = Array.isArray(data.user_stories) ? data.user_stories : [data.user_stories];
                stories.forEach(story => {
                    addUserStoryCard(story);
                });
            }
        } else if (data.success && data.analysis) {
            // Generate BRD from analysis
            fetch('/api/ai-business-analyst/generate-brd', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include', // Передаем cookies для сессии
                body: JSON.stringify({
                    analysis: data.analysis,
                    context: {}
                })
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => Promise.reject(new Error(err.error || 'Ошибка сервера')));
                }
                return response.json();
            })
            .then(brdData => {
                if (brdData.success && brdData.brd) {
                    // Extract content from BRD object
                    let brdContent = '';
                    if (typeof brdData.brd === 'string') {
                        brdContent = brdData.brd;
                    } else if (brdData.brd.content) {
                        brdContent = brdData.brd.content;
                    } else if (brdData.brd.error) {
                        throw new Error(brdData.brd.error);
                    } else {
                        brdContent = JSON.stringify(brdData.brd);
                    }
                    
                    updateBRDDisplay(brdContent);
                    currentBRD = brdContent;
                } else {
                    throw new Error(brdData.error || 'Не удалось сгенерировать BRD');
                }
            })
            .catch(error => {
                console.error('Error generating BRD:', error);
                alert('Ошибка генерации BRD: ' + error.message);
            });
        } else {
            throw new Error(data.error || 'Не удалось проанализировать документ');
        }
    })
    .catch(error => {
        loadingIndicator.remove();
        console.error('Error analyzing document:', error);
        alert('Ошибка анализа документа: ' + error.message);
    });
}

function updateBRDDisplay(brdContent) {
    const brdContainer = document.getElementById('brd-content');
    
    if (!brdContainer) {
        console.error('BRD container not found');
        return;
    }
    
    // If BRD content is from AI generation, try to parse it
    // Otherwise use editable fields directly
    if (typeof brdContent === 'string' && brdContent.trim()) {
        // Try to parse as JSON first
        try {
            const parsed = JSON.parse(brdContent);
            updateBRDDisplayEditable(parsed);
            return;
        } catch (e) {
            // Not JSON, try to extract structured data from markdown
        }
        // Simple parsing - in production, use proper markdown parser
        const lines = brdContent.split('\n');
        let html = '';
        let currentSection = '';
        let inChecklist = false;
        
        lines.forEach(line => {
            const trimmed = line.trim();
            if (trimmed.startsWith('# ')) {
                if (currentSection === 'open') {
                    if (inChecklist) html += '</div>';
                    html += '</div>';
                }
                html += `<div class="ba-brd-section"><h4>${trimmed.substring(2)}</h4>`;
                currentSection = 'open';
                inChecklist = false;
            } else if (trimmed.startsWith('## ')) {
                if (currentSection === 'open') {
                    if (inChecklist) html += '</div>';
                    html += '</div>';
                }
                html += `<div class="ba-brd-section"><h4>${trimmed.substring(3)}</h4>`;
                currentSection = 'open';
                inChecklist = false;
            } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
                if (!inChecklist) {
                    html += '<div class="ba-checklist">';
                    inChecklist = true;
                }
                html += `<div class="ba-checklist-item checked"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg><span>${trimmed.substring(2)}</span></div>`;
            } else if (trimmed) {
                if (inChecklist) {
                    html += '</div>';
                    inChecklist = false;
                }
                html += `<p>${trimmed}</p>`;
            }
        });
        
        if (inChecklist) html += '</div>';
        if (currentSection === 'open') html += '</div>';
        
        // If content was parsed, try to extract structured data
        // Otherwise, use default editable structure
        const projectNameMatch = brdContent.match(/Название проекта[:\s]*([^\n]+)/i) || 
                                 brdContent.match(/PROJECT[:\s]*([^\n]+)/i);
        const scopeMatches = brdContent.match(/- (.+)/g) || [];
        
        if (projectNameMatch || scopeMatches.length > 0) {
            const extractedData = {
                project_name: projectNameMatch ? projectNameMatch[1].trim() : 'Система автоматизации кредитования',
                scope: scopeMatches.map(m => m.replace(/^-\s*/, '')).slice(0, 10),
                kpi: [
                    { label: 'Время обработки заявки', goal: '< 5 минут', current: '2-3 дня' },
                    { label: 'Автоматическое одобрение', goal: '80%', current: '45%' }
                ]
            };
            updateBRDDisplayEditable(extractedData);
        } else {
            // Use default editable structure
            updateBRDDisplayEditable({});
        }
    } else {
        // Use empty editable structure
        updateBRDDisplayEditable({});
    }
}

// Initialize empty BRD on page load
document.addEventListener('DOMContentLoaded', function() {
    // Make sure BRD starts empty
    const projectNameInput = document.getElementById('project-name');
    if (projectNameInput && !projectNameInput.value) {
        projectNameInput.value = '';
    }
});

function exportBRD() {
    // Save current data first
    saveBRDData();
    
    // Get current BRD data from editable fields
    const projectName = document.getElementById('project-name')?.value || 'Система автоматизации кредитования';
    const scopeItems = Array.from(document.querySelectorAll('#scope-checklist .ba-editable-text')).map(input => input.value).filter(v => v.trim());
    const kpiItems = Array.from(document.querySelectorAll('#kpi-list .ba-kpi-item')).map(item => {
        const label = item.querySelector('.ba-kpi-label-input')?.value || '';
        const goal = item.querySelector('.ba-kpi-details span:first-child input')?.value || '';
        const current = item.querySelector('.ba-kpi-details span:last-child input')?.value || '';
        return { label, goal, current };
    }).filter(kpi => kpi.label.trim());
    
    // Format as markdown for export
    let brdContent = `# BUSINESS REQUIREMENTS DOCUMENT (BRD)\n\n`;
    brdContent += `## Название проекта\n${projectName}\n\n`;
    brdContent += `## Scope (Область охвата)\n`;
    scopeItems.forEach(item => {
        brdContent += `- ${item}\n`;
    });
    brdContent += `\n## KPI метрики\n`;
    kpiItems.forEach(kpi => {
        brdContent += `### ${kpi.label}\n`;
        brdContent += `- Цель: ${kpi.goal}\n`;
        brdContent += `- Сейчас: ${kpi.current}\n\n`;
    });
    
    // Show export options
    const format = confirm('Экспортировать в Word? (OK = Word, Cancel = PDF)') ? 'word' : 'pdf';
    
    fetch('/api/ai-business-analyst/export-brd', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include', // Передаем cookies для сессии
        body: JSON.stringify({
            brd_content: brdContent,
            format: format
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (data.filename) {
                // Download file
                window.location.href = `/uploads/${data.filename}`;
            } else {
                alert('Экспорт выполнен успешно!');
            }
        } else {
            alert('Ошибка экспорта: ' + (data.error || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        alert('Ошибка экспорта: ' + error.message);
    });
}

// Use Cases Functions
function generateMoreUseCases() {
    const requirements = extractRequirementsFromChat();
    
    // If no requirements from chat, use a default or prompt user
    let requirementText = requirements.length > 0 ? requirements.join('\n') : '';
    
    if (!requirementText || requirementText.trim().length < 10) {
        requirementText = prompt('Введите описание требования для генерации Use Case:');
        if (!requirementText || requirementText.trim().length < 10) {
            alert('Требование должно содержать минимум 10 символов');
            return;
        }
    }
    
    // Show loading indicator
    const loadingMsg = document.createElement('div');
    loadingMsg.textContent = 'Генерация Use Case...';
    loadingMsg.style.cssText = 'position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 1rem 2rem; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 1000;';
    document.body.appendChild(loadingMsg);
    
    fetch('/api/ai-business-analyst/generate-use-case', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include', // Передаем cookies для сессии
        body: JSON.stringify({
            requirement: requirementText,
            actor: 'Пользователь',
            context: {}
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => Promise.reject(new Error(err.error || 'Ошибка сервера')));
        }
        return response.json();
    })
    .then(data => {
        loadingMsg.remove();
        if (data.success && data.use_case) {
            addUseCaseCard(data.use_case);
        } else {
            alert('Ошибка генерации Use Case: ' + (data.error || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        loadingMsg.remove();
        console.error('Error generating Use Case:', error);
        alert('Ошибка генерации Use Case: ' + error.message);
    });
}

function addUseCaseCard(useCase) {
    const grid = document.getElementById('usecases-grid');
    const card = document.createElement('div');
    card.className = 'ba-usecase-card';
    
    // Parse use case data - handle both dict and string formats
    const id = `UC-${String(useCases.length + 1).padStart(3, '0')}`;
    let title = 'Новый Use Case';
    let role = 'Пользователь';
    let description = '';
    
    if (typeof useCase === 'string') {
        // If it's a string, try to extract title from markdown
        const lines = useCase.split('\n');
        for (const line of lines) {
            if (line.startsWith('# USE CASE:')) {
                title = line.replace('# USE CASE:', '').trim();
                break;
            } else if (line.startsWith('## АКТОР')) {
                const nextLine = lines[lines.indexOf(line) + 1];
                if (nextLine && !nextLine.startsWith('#')) {
                    role = nextLine.trim();
                }
            }
        }
        description = useCase.substring(0, 200) + (useCase.length > 200 ? '...' : '');
    } else if (typeof useCase === 'object') {
        // If it's an object
        title = useCase.title || useCase.name || (useCase.content ? extractTitleFromMarkdown(useCase.content) : 'Новый Use Case');
        role = useCase.actor || 'Пользователь';
        description = useCase.description || useCase.content || JSON.stringify(useCase);
        
        // If description is too long, truncate it
        if (description.length > 200) {
            description = description.substring(0, 200) + '...';
        }
    }
    
    card.innerHTML = `
        <div class="ba-usecase-header">
            <div class="ba-usecase-id">${id}</div>
            <span class="ba-status-badge draft">Черновик</span>
        </div>
        <h4 class="ba-usecase-title">${escapeHtml(title)}</h4>
        <div class="ba-usecase-role">Роль: <strong>${escapeHtml(role)}</strong></div>
        <p class="ba-usecase-desc">${escapeHtml(description)}</p>
    `;
    
    grid.appendChild(card);
    useCases.push({ id, title, role, description });
}

function extractTitleFromMarkdown(markdown) {
    if (typeof markdown !== 'string') return 'Новый Use Case';
    const lines = markdown.split('\n');
    for (const line of lines) {
        if (line.startsWith('# USE CASE:') || line.startsWith('# USE CASE ')) {
            return line.replace(/^# USE CASE:?\s*/, '').trim() || 'Новый Use Case';
        }
    }
    return 'Новый Use Case';
}

function escapeHtml(text) {
    if (typeof text !== 'string') text = String(text);
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// User Stories Functions
function addUserStory() {
    const storyText = prompt('Введите User Story в формате "Как [роль], я хочу [действие], чтобы [цель]"');
    if (!storyText) return;
    
    fetch('/api/ai-business-analyst/generate-user-stories', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include', // Передаем cookies для сессии
        body: JSON.stringify({
            requirements: [storyText],
            roles: []
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.user_stories) {
            const stories = Array.isArray(data.user_stories) ? data.user_stories : [data.user_stories];
                stories.forEach(story => {
                    addUserStoryCard(story);
                });
        }
    })
    .catch(error => {
        alert('Ошибка создания User Story: ' + error.message);
    });
}

function addUserStoryCard(story) {
    const grid = document.getElementById('userstories-grid');
    const card = document.createElement('div');
    card.className = 'ba-userstory-card';
    
    const id = `US-${String(userStories.length + 101)}`;
    const text = typeof story === 'string' ? story : (story.text || story);
    
    card.innerHTML = `
        <div class="ba-userstory-header">
            <div class="ba-userstory-id">${id}</div>
            <span class="ba-status-badge draft">Черновик</span>
        </div>
        <p class="ba-userstory-text">${text}</p>
    `;
    
    grid.appendChild(card);
    userStories.push({ id, text });
}

// Bottom Actions Functions
function generateBPMN() {
    const processDescription = prompt('Опишите бизнес-процесс для генерации BPMN диаграммы:');
    if (!processDescription) return;
    
    fetch('/api/ai-business-analyst/generate-bpmn', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include', // Передаем cookies для сессии
        body: JSON.stringify({
            process_description: processDescription,
            use_cases: useCases
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show BPMN diagram in modal
            if (data.bpmn_data) {
                showBPMNDiagram(data.bpmn_data, data.bpmn);
            } else if (data.bpmn) {
                showBPMNModal(data.bpmn);
            }
        } else {
            alert('Ошибка генерации BPMN: ' + (data.error || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        alert('Ошибка генерации BPMN: ' + error.message);
    });
}

function showBPMNDiagram(bpmnData, bpmnXml) {
    const modal = document.createElement('div');
    modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 10000; display: flex; align-items: center; justify-content: center;';
    
    const diagramContainer = document.createElement('div');
    diagramContainer.id = 'bpmn-diagram-container';
    
    modal.innerHTML = `
        <div style="background: white; padding: 2rem; border-radius: 12px; max-width: 90vw; max-height: 90vh; overflow: auto; position: relative;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <h3 style="margin: 0; font-size: 24px; font-weight: 600;">BPMN Диаграмма: ${escapeHtml(bpmnData.process_name || 'Процесс')}</h3>
                <button onclick="this.closest('div[style*=\"position: fixed\"]').remove()" style="background: #f3f4f6; border: none; border-radius: 50%; width: 36px; height: 36px; cursor: pointer; font-size: 20px; color: #6b7280; display: flex; align-items: center; justify-content: center;">×</button>
            </div>
            <div id="bpmn-diagram-svg" style="background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 2rem; min-height: 400px; overflow: auto;"></div>
            <div style="margin-top: 1rem; display: flex; gap: 0.5rem; justify-content: flex-end;">
                <button onclick="downloadBPMNSVG()" style="padding: 0.5rem 1rem; background: #8B1E2D; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px;">Скачать SVG</button>
                <button onclick="this.closest('div[style*=\"position: fixed\"]').remove()" style="padding: 0.5rem 1rem; background: #f3f4f6; color: #4b5563; border: none; border-radius: 8px; cursor: pointer; font-size: 14px;">Закрыть</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Генерируем визуальную диаграмму
    generateBPMNDiagramSVG(bpmnData, document.getElementById('bpmn-diagram-svg'));
}

function generateBPMNDiagramSVG(bpmnData, container) {
    const tasks = bpmnData.tasks || [];
    const gateways = bpmnData.gateways || [];
    const startEvent = bpmnData.start_event || {id: 'start', label: 'Start'};
    const endEvents = bpmnData.end_events || [{id: 'end', label: 'End'}];
    const flows = bpmnData.flows || [];
    
    // Параметры для позиционирования
    const nodeWidth = 140;
    const nodeHeight = 70;
    const gatewaySize = 60;
    const eventSize = 50;
    const spacing = 100;
    const startX = 50;
    const startY = 150;
    
    // Создаем карту всех элементов
    const allElementsMap = new Map();
    allElementsMap.set(startEvent.id, {type: 'start', ...startEvent});
    tasks.forEach(task => allElementsMap.set(task.id, {type: 'task', ...task}));
    gateways.forEach(gw => allElementsMap.set(gw.id, {type: 'gateway', ...gw}));
    endEvents.forEach(evt => allElementsMap.set(evt.id, {type: 'end', ...evt}));
    
    // Определяем порядок элементов через flows (топологическая сортировка)
    const orderedElements = [];
    const visited = new Set();
    const processing = new Set();
    
    function visitNode(nodeId) {
        if (processing.has(nodeId)) return; // Цикл
        if (visited.has(nodeId)) return;
        
        processing.add(nodeId);
        const node = allElementsMap.get(nodeId);
        if (node) {
            // Сначала посещаем предков
            flows.forEach(flow => {
                if (flow.to === nodeId) {
                    visitNode(flow.from);
                }
            });
            
            if (!visited.has(nodeId)) {
                orderedElements.push({...node, id: nodeId});
                visited.add(nodeId);
            }
        }
        processing.delete(nodeId);
    }
    
    // Начинаем с start event
    visitNode(startEvent.id);
    
    // Посещаем остальные элементы
    allElementsMap.forEach((_, nodeId) => visitNode(nodeId));
    
    // Позиционируем элементы
    orderedElements.forEach((el, index) => {
        el.x = startX + index * (nodeWidth + spacing);
        el.y = startY;
    });
    
    const svgWidth = Math.max(900, startX + orderedElements.length * (nodeWidth + spacing) + 150);
    const svgHeight = 400;
    
    const svg = `
        <svg width="${svgWidth}" height="${svgHeight}" xmlns="http://www.w3.org/2000/svg" style="font-family: Arial, sans-serif;">
            <defs>
                <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                    <polygon points="0 0, 10 3, 0 6" fill="#374151" />
                </marker>
            </defs>
            
            ${flows.map(flow => {
                const fromEl = orderedElements.find(e => e.id === flow.from);
                const toEl = orderedElements.find(e => e.id === flow.to);
                if (!fromEl || !toEl) return '';
                
                const fromX = fromEl.x + (fromEl.type === 'start' || fromEl.type === 'end' ? eventSize/2 : fromEl.type === 'gateway' ? gatewaySize/2 : nodeWidth/2);
                const fromY = fromEl.y + (fromEl.type === 'start' || fromEl.type === 'end' ? eventSize/2 : fromEl.type === 'gateway' ? gatewaySize/2 : nodeHeight/2);
                const toX = toEl.x + (toEl.type === 'start' || toEl.type === 'end' ? eventSize/2 : toEl.type === 'gateway' ? gatewaySize/2 : nodeWidth/2);
                const toY = toEl.y + (toEl.type === 'start' || toEl.type === 'end' ? eventSize/2 : toEl.type === 'gateway' ? gatewaySize/2 : nodeHeight/2);
                
                const midX = (fromX + toX) / 2;
                const midY = (fromY + toY) / 2 - 15;
                
                return `
                    <line x1="${fromX}" y1="${fromY}" x2="${toX}" y2="${toY}" 
                          stroke="#374151" stroke-width="2.5" marker-end="url(#arrowhead)" />
                    ${flow.label ? `<text x="${midX}" y="${midY}" text-anchor="middle" font-size="11" fill="#6b7280" font-weight="500">${escapeHtml(flow.label)}</text>` : ''}
                `;
            }).join('')}
            
            ${orderedElements.map(el => {
                if (el.type === 'start') {
                    return `
                        <circle cx="${el.x + eventSize/2}" cy="${el.y + eventSize/2}" r="${eventSize/2}" 
                                fill="#10b981" stroke="#059669" stroke-width="2" />
                        <text x="${el.x + eventSize/2}" y="${el.y + eventSize/2 + 5}" text-anchor="middle" font-size="11" fill="white" font-weight="bold">${escapeHtml(el.label || 'Start')}</text>
                    `;
                } else if (el.type === 'end') {
                    return `
                        <circle cx="${el.x + eventSize/2}" cy="${el.y + eventSize/2}" r="${eventSize/2}" 
                                fill="#ef4444" stroke="#dc2626" stroke-width="3" />
                        <text x="${el.x + eventSize/2}" y="${el.y + eventSize/2 + 5}" text-anchor="middle" font-size="11" fill="white" font-weight="bold">${escapeHtml(el.label || 'End')}</text>
                    `;
                } else if (el.type === 'gateway') {
                    return `
                        <polygon points="${el.x},${el.y + gatewaySize/2} ${el.x + gatewaySize/2},${el.y} ${el.x + gatewaySize},${el.y + gatewaySize/2} ${el.x + gatewaySize/2},${el.y + gatewaySize}" 
                                fill="#fbbf24" stroke="#f59e0b" stroke-width="2" />
                        <text x="${el.x + gatewaySize/2}" y="${el.y + gatewaySize/2 + 5}" text-anchor="middle" font-size="10" fill="#92400e">${escapeHtml(el.label || '?')}</text>
                    `;
                } else {
                    return `
                        <rect x="${el.x}" y="${el.y}" width="${nodeWidth}" height="${nodeHeight}" rx="8" 
                              fill="#3b82f6" stroke="#2563eb" stroke-width="2" />
                        <text x="${el.x + nodeWidth/2}" y="${el.y + nodeHeight/2}" text-anchor="middle" font-size="12" fill="white" font-weight="500">${escapeHtml(el.label || 'Task')}</text>
                    `;
                }
            }).join('')}
        </svg>
    `;
    
    container.innerHTML = svg;
}

function downloadBPMNSVG() {
    const svg = document.querySelector('#bpmn-diagram-svg svg');
    if (!svg) return;
    
    const svgData = new XMLSerializer().serializeToString(svg);
    const blob = new Blob([svgData], {type: 'image/svg+xml'});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'bpmn-diagram.svg';
    link.click();
    URL.revokeObjectURL(url);
}

function showBPMNModal(bpmnContent) {
    const modal = document.createElement('div');
    modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center;';
    modal.innerHTML = `
        <div style="background: white; padding: 2rem; border-radius: 12px; max-width: 800px; max-height: 80vh; overflow-y: auto;">
            <h3 style="margin-top: 0;">BPMN Диаграмма</h3>
            <pre style="white-space: pre-wrap; font-family: monospace; background: #f3f4f6; padding: 1rem; border-radius: 8px;">${bpmnContent}</pre>
            <button onclick="this.closest('div[style*=\"position: fixed\"]').remove()" style="margin-top: 1rem; padding: 0.5rem 1rem; background: #8B1E2D; color: white; border: none; border-radius: 8px; cursor: pointer;">Закрыть</button>
        </div>
    `;
    document.body.appendChild(modal);
}

function downloadBRD() {
    exportBRD();
}

function publishToConfluence() {
    // Save current data first
    saveBRDData();
    
    // Get current BRD data from editable fields
    const projectName = document.getElementById('project-name')?.value?.trim() || 'Business Requirements Document';
    const scopeItems = Array.from(document.querySelectorAll('#scope-checklist .ba-editable-text')).map(input => input.value.trim()).filter(v => v);
    const kpiItems = Array.from(document.querySelectorAll('#kpi-list .ba-kpi-item')).map(item => {
        const label = item.querySelector('.ba-kpi-label-input')?.value?.trim() || '';
        const goal = item.querySelector('.ba-kpi-details span:first-child input')?.value?.trim() || '';
        const current = item.querySelector('.ba-kpi-details span:last-child input')?.value?.trim() || '';
        return { label, goal, current };
    }).filter(kpi => kpi.label);
    
    // Format BRD content
    let brdContent = currentBRD || '';
    if (!brdContent || brdContent.trim().length < 50) {
        // Generate content from fields
        brdContent = `# BUSINESS REQUIREMENTS DOCUMENT (BRD)\n\n`;
        if (projectName) {
            brdContent += `## Название проекта\n${projectName}\n\n`;
        }
        if (scopeItems.length > 0) {
            brdContent += `## Scope (Область охвата)\n`;
            scopeItems.forEach(item => {
                brdContent += `- ${item}\n`;
            });
            brdContent += `\n`;
        }
        if (kpiItems.length > 0) {
            brdContent += `## KPI метрики\n`;
            kpiItems.forEach(kpi => {
                brdContent += `### ${kpi.label}\n`;
                brdContent += `- Цель: ${kpi.goal}\n`;
                brdContent += `- Сейчас: ${kpi.current}\n\n`;
            });
        }
    }
    
    const spaceKey = prompt('Введите ключ пространства Confluence (например, BA):', 'BA');
    if (!spaceKey || !spaceKey.trim()) {
        alert('Ключ пространства обязателен');
        return;
    }
    
    const pageTitle = prompt('Введите название страницы:', projectName || 'Business Requirements Document');
    if (!pageTitle || !pageTitle.trim()) {
        alert('Название страницы обязательно');
        return;
    }
    
    // Show loading
    const loadingMsg = document.createElement('div');
    loadingMsg.textContent = 'Публикация в Confluence...';
    loadingMsg.style.cssText = 'position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 1rem 2rem; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 1000;';
    document.body.appendChild(loadingMsg);
    
    // Publish to local Confluence storage
    fetch('/api/ai-business-analyst/publish-confluence', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include', // Передаем cookies для сессии
        body: JSON.stringify({
            page_content: brdContent,
            page_title: pageTitle.trim(),
            space_key: spaceKey.trim(),
            brd_content: brdContent
        })
    })
    .then(response => response.json())
    .then(publishData => {
        loadingMsg.remove();
        if (publishData.success) {
            const viewDocs = confirm(publishData.message + '\n\nХотите открыть страницу с документами?');
            if (viewDocs) {
                window.location.href = publishData.page_url || '/confluence-docs';
            }
        } else {
            alert('Ошибка публикации: ' + (publishData.error || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        loadingMsg.remove();
        console.error('Error publishing to Confluence:', error);
        alert('Ошибка публикации: ' + error.message);
    });
}

// Manual BRD Generation
function generateBRDManually() {
    const requirements = extractRequirementsFromChat();
    let requirementText = requirements.length > 0 ? requirements.join('\n') : '';
    
    if (!requirementText || requirementText.trim().length < 20) {
        requirementText = prompt('Введите описание проекта или требования для генерации BRD (минимум 20 символов):');
        if (!requirementText || requirementText.trim().length < 20) {
            alert('Описание должно содержать минимум 20 символов');
            return;
        }
    }
    
    generateBRDFromChat(requirementText);
}

// Header Functions
function openConfluence() {
    window.location.href = '/confluence-docs';
}

function newProject() {
    if (confirm('Создать новый проект? Все текущие данные будут сброшены.')) {
        location.reload();
    }
}

// Utility Functions
function extractRequirementsFromChat() {
    return chatHistory
        .filter(msg => msg.role === 'user')
        .map(msg => msg.content);
}

// Progress cards removed - function no longer needed

function toggleExpand(element) {
    element.classList.toggle('expanded');
    const icon = element.querySelector('.expand-icon');
    if (icon) {
        icon.style.transform = element.classList.contains('expanded') ? 'rotate(180deg)' : 'rotate(0deg)';
    }
}

// BRD Editing Functions
function saveBRDData() {
    // Collect all BRD data
    const projectName = document.getElementById('project-name')?.value || '';
    const scopeItems = Array.from(document.querySelectorAll('#scope-checklist .ba-editable-text')).map(input => input.value).filter(v => v.trim());
    const kpiItems = Array.from(document.querySelectorAll('#kpi-list .ba-kpi-item')).map(item => {
        const label = item.querySelector('.ba-kpi-label-input')?.value || '';
        const goal = item.querySelector('.ba-kpi-details span:first-child input')?.value || '';
        const current = item.querySelector('.ba-kpi-details span:last-child input')?.value || '';
        return { label, goal, current };
    }).filter(kpi => kpi.label.trim());
    
    // Update currentBRD
    const brdData = {
        project_name: projectName,
        scope: scopeItems,
        kpi: kpiItems
    };
    
    currentBRD = JSON.stringify(brdData);
    // Progress cards removed - no need to update
}

function addScopeItem() {
    const checklist = document.getElementById('scope-checklist');
    if (!checklist) return;
    
    const newItem = document.createElement('div');
    newItem.className = 'ba-checklist-item checked';
    newItem.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
        <input type="text" class="ba-editable-text" value="" onblur="saveBRDData()" placeholder="Введите элемент" autofocus>
        <button class="ba-remove-btn" onclick="removeScopeItem(this)" title="Удалить">×</button>
    `;
    checklist.appendChild(newItem);
    
    // Focus on the new input
    const input = newItem.querySelector('.ba-editable-text');
    if (input) {
        setTimeout(() => input.focus(), 10);
    }
}

function removeScopeItem(button) {
    const item = button.closest('.ba-checklist-item');
    if (item && confirm('Удалить этот элемент?')) {
        item.remove();
        saveBRDData();
    }
}

function addKPIItem() {
    const kpiList = document.getElementById('kpi-list');
    if (!kpiList) return;
    
    const newItem = document.createElement('div');
    newItem.className = 'ba-kpi-item';
    newItem.innerHTML = `
        <input type="text" class="ba-kpi-label-input" value="" onblur="saveBRDData()" placeholder="Название метрики" autofocus>
        <div class="ba-kpi-details">
            <span>Цель: <input type="text" class="ba-kpi-value-input" value="" onblur="saveBRDData()" placeholder="Цель"></span>
            <span>Сейчас: <input type="text" class="ba-kpi-value-input" value="" onblur="saveBRDData()" placeholder="Текущее значение"></span>
        </div>
        <button class="ba-remove-btn" onclick="removeKPIItem(this)" title="Удалить">×</button>
    `;
    kpiList.appendChild(newItem);
    
    // Focus on the new input
    const input = newItem.querySelector('.ba-kpi-label-input');
    if (input) {
        setTimeout(() => input.focus(), 10);
    }
}

function removeKPIItem(button) {
    const item = button.closest('.ba-kpi-item');
    if (item && confirm('Удалить эту метрику?')) {
        item.remove();
        saveBRDData();
    }
}

// Show format selection dialog
function showFormatSelectionDialog(callback) {
    const modal = document.createElement('div');
    modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 2000; display: flex; align-items: center; justify-content: center;';
    modal.innerHTML = `
        <div style="background: white; padding: 2rem; border-radius: 12px; max-width: 500px; width: 90%; box-shadow: 0 20px 60px rgba(0,0,0,0.3);">
            <h2 style="margin: 0 0 1.5rem 0; color: #1a1a1a; font-size: 24px;">Выберите формат документа</h2>
            <div style="display: flex; flex-direction: column; gap: 1rem;">
                <button onclick="selectFormat('docx', this)" style="padding: 1rem; background: linear-gradient(135deg, #A52A2A 0%, #8B1E2D 100%); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 500; font-size: 16px; transition: transform 0.2s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'">
                    📄 Microsoft Word (.docx)
                </button>
                <button onclick="selectFormat('doc', this)" style="padding: 1rem; background: linear-gradient(135deg, #A52A2A 0%, #8B1E2D 100%); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 500; font-size: 16px; transition: transform 0.2s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'">
                    📄 Microsoft Word (.doc)
                </button>
                <button onclick="selectFormat('pdf', this)" style="padding: 1rem; background: linear-gradient(135deg, #A52A2A 0%, #8B1E2D 100%); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 500; font-size: 16px; transition: transform 0.2s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'">
                    📄 PDF (.pdf)
                </button>
                <button onclick="selectFormat(null, this)" style="padding: 1rem; background: #f3f4f6; color: #1a1a1a; border: none; border-radius: 8px; cursor: pointer; font-weight: 500; font-size: 16px; transition: background 0.2s;" onmouseover="this.style.background='#e5e7eb'" onmouseout="this.style.background='#f3f4f6'">
                    Отмена
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    
    window.selectFormat = function(format, button) {
        document.body.removeChild(modal);
        delete window.selectFormat;
        if (format !== null) {
            callback(format);
        }
    };
}

// Generate BRD from user input fields
function generateBRDFromFields() {
    // Save current data first
    saveBRDData();
    
    // Get current BRD data from editable fields
    const projectName = document.getElementById('project-name')?.value?.trim() || '';
    const scopeItems = Array.from(document.querySelectorAll('#scope-checklist .ba-editable-text')).map(input => input.value.trim()).filter(v => v);
    const kpiItems = Array.from(document.querySelectorAll('#kpi-list .ba-kpi-item')).map(item => {
        const label = item.querySelector('.ba-kpi-label-input')?.value?.trim() || '';
        const goal = item.querySelector('.ba-kpi-details span:first-child input')?.value?.trim() || '';
        const current = item.querySelector('.ba-kpi-details span:last-child input')?.value?.trim() || '';
        return { label, goal, current };
    }).filter(kpi => kpi.label);
    
    // Validate that user has entered some data
    if (!projectName && scopeItems.length === 0 && kpiItems.length === 0) {
        alert('Пожалуйста, заполните хотя бы одно поле перед генерацией документа.');
        return;
    }
    
    // Show format selection dialog
    showFormatSelectionDialog((selectedFormat) => {
        // Show loading indicator
        const generateBtn = document.querySelector('.ba-generate-btn');
        const originalText = generateBtn.innerHTML;
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spinning"><circle cx="12" cy="12" r="10"></circle></svg> Генерация...';
        
        // Format data for AI generation using user's input
        let description = '';
        if (projectName) {
            description += `Название проекта: ${projectName}\n\n`;
        }
        if (scopeItems.length > 0) {
            description += `Scope (Область охвата):\n${scopeItems.map(item => `- ${item}`).join('\n')}\n\n`;
        }
        if (kpiItems.length > 0) {
            description += `KPI метрики:\n${kpiItems.map(kpi => `- ${kpi.label}: Цель - ${kpi.goal}, Сейчас - ${kpi.current}`).join('\n')}\n`;
        }
        
        // Generate BRD using AI with selected format
        fetch('/api/ai-business-analyst/generate-brd', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include', // Важно: передаем cookies для сессии
            body: JSON.stringify({
                analysis: {
                    project_description: description,
                    project_name: projectName,
                    scope: scopeItems,
                    kpi: kpiItems
                },
                context: {},
                export_format: selectedFormat // Передаем выбранный формат
            })
        })
        .then(response => {
            if (!response.ok) {
                // Если 401, значит проблема с авторизацией
                if (response.status === 401) {
                    return Promise.reject(new Error('Ошибка авторизации. Пожалуйста, перезагрузите страницу и войдите снова.'));
                }
                return response.json().then(err => Promise.reject(new Error(err.error || 'Ошибка сервера')));
            }
            return response.json();
        })
        .then(data => {
            generateBtn.disabled = false;
            generateBtn.innerHTML = originalText;
            
            if (data.success && data.brd) {
                // Extract content from BRD object
                let brdContent = '';
                if (typeof data.brd === 'string') {
                    brdContent = data.brd;
                } else if (data.brd.content) {
                    brdContent = data.brd.content;
                } else if (data.brd.error) {
                    throw new Error(data.brd.error);
                } else {
                    brdContent = JSON.stringify(data.brd);
                }
                
                // If file was generated, download it
                if (data.filename) {
                    window.location.href = `/uploads/${data.filename}`;
                }
                
                // Save BRD content globally
                currentBRD = brdContent;
                
                // Show generated BRD in a modal
                showGeneratedBRD(brdContent, data.filename);
            } else {
                throw new Error(data.error || 'Не удалось сгенерировать BRD');
            }
        })
        .catch(error => {
            generateBtn.disabled = false;
            generateBtn.innerHTML = originalText;
            console.error('Error generating BRD:', error);
            alert('Ошибка генерации BRD: ' + error.message);
        });
    });
}

function showGeneratedBRD(brdContent, filename = null) {
    // Parse and format BRD content
    const formattedBRD = formatBRDContent(brdContent);
    
    // Create modal to show generated BRD
    const modal = document.createElement('div');
    modal.id = 'brd-modal';
    modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 2rem;';
    
    const successMessage = filename ? `<div style="background: #d1fae5; color: #065f46; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; border: 1px solid #6ee7b7;">
        <strong>✓ Документ успешно создан!</strong> Файл ${filename} был загружен.
    </div>` : '';
    
    modal.innerHTML = `
        <div style="background: white; padding: 2rem; border-radius: 12px; max-width: 900px; width: 100%; max-height: 90vh; overflow: hidden; display: flex; flex-direction: column; box-shadow: 0 20px 60px rgba(0,0,0,0.3);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; flex-shrink: 0;">
                <h2 style="margin: 0; color: #1a1a1a; font-size: 24px;">Сгенерированный BRD документ</h2>
                <button onclick="closeBRDModal()" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #6b7280; padding: 0; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 50%; transition: background 0.2s;" onmouseover="this.style.background='#f3f4f6'" onmouseout="this.style.background='none'">×</button>
            </div>
            ${successMessage}
            <div id="brd-formatted-content" style="flex: 1; overflow-y: auto; padding-right: 0.5rem; margin-bottom: 1.5rem;">
                ${formattedBRD}
            </div>
            <div style="flex-shrink: 0; padding-top: 1rem; border-top: 1px solid #e5e7eb; margin-bottom: 1rem;">
                <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
                    <label for="confluence-space-key" style="font-size: 14px; font-weight: 500; color: #374151; white-space: nowrap;">Ключ пространства:</label>
                    <input type="text" id="confluence-space-key" value="BA" placeholder="BA" style="flex: 1; padding: 0.5rem 0.75rem; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; transition: border-color 0.2s;" onfocus="this.style.borderColor='#A52A2A'; this.style.outline='none'" onblur="this.style.borderColor='#d1d5db'">
                    <span style="font-size: 12px; color: #6b7280;">(например: BA, DEV, PROD)</span>
                </div>
            </div>
            <div style="display: flex; gap: 0.75rem; justify-content: flex-end; flex-shrink: 0;">
                <button onclick="closeBRDModal()" style="padding: 0.625rem 1.5rem; background: #f3f4f6; border: none; border-radius: 8px; cursor: pointer; font-weight: 500; transition: background 0.2s;" onmouseover="this.style.background='#e5e7eb'" onmouseout="this.style.background='#f3f4f6'">Закрыть</button>
                <button onclick="copyBRDToClipboard()" style="padding: 0.625rem 1.5rem; background: #f3f4f6; border: none; border-radius: 8px; cursor: pointer; font-weight: 500; transition: background 0.2s;" onmouseover="this.style.background='#e5e7eb'" onmouseout="this.style.background='#f3f4f6'">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display: inline-block; vertical-align: middle; margin-right: 0.5rem;"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                    Копировать
                </button>
                <button onclick="addBRDToConfluence()" style="padding: 0.625rem 1.5rem; background: linear-gradient(135deg, #A52A2A 0%, #8B1E2D 100%); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 500; transition: transform 0.2s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display: inline-block; vertical-align: middle; margin-right: 0.5rem;"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                    Добавить в Confluence
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    
    // Store original content for copying and Confluence
    modal.dataset.originalContent = brdContent;
}

// Add BRD to Confluence
function addBRDToConfluence() {
    const modal = document.getElementById('brd-modal');
    if (!modal) {
        console.error('BRD modal not found');
        alert('Ошибка: модальное окно не найдено');
        return;
    }
    
    // Try multiple ways to get BRD content
    let brdContent = modal.dataset.originalContent || '';
    
    // If not in dataset, try to get from formatted content
    if (!brdContent) {
        const formattedContent = document.getElementById('brd-formatted-content');
        if (formattedContent) {
            // Try to extract text from formatted HTML
            brdContent = formattedContent.innerText || formattedContent.textContent || '';
        }
    }
    
    // If still empty, try to get from currentBRD global variable
    if (!brdContent && typeof currentBRD !== 'undefined' && currentBRD) {
        brdContent = currentBRD;
    }
    
    if (!brdContent || brdContent.trim().length < 10) {
        console.error('BRD content is empty or too short:', brdContent);
        alert('Ошибка: содержимое BRD не найдено или слишком короткое. Пожалуйста, сгенерируйте BRD заново.');
        return;
    }
    
    // Get project name for title
    const projectName = document.getElementById('project-name')?.value?.trim() || 'Business Requirements Document';
    
    // Get space key from input field in modal
    const spaceKeyInput = document.getElementById('confluence-space-key');
    let spaceKey = 'BA'; // Default value
    if (spaceKeyInput) {
        spaceKey = spaceKeyInput.value.trim() || 'BA';
    }
    
    if (!spaceKey || !spaceKey.trim()) {
        alert('Ключ пространства обязателен. Пожалуйста, введите ключ в поле выше.');
        if (spaceKeyInput) {
            spaceKeyInput.focus();
        }
        return;
    }
    
    // Show loading
    const loadingMsg = document.createElement('div');
    loadingMsg.textContent = 'Публикация в Confluence...';
    loadingMsg.style.cssText = 'position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 1rem 2rem; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 2000;';
    document.body.appendChild(loadingMsg);
    
    console.log('Publishing to Confluence:', {
        title: projectName,
        space_key: spaceKey.trim(),
        content_length: brdContent.length
    });
    
    // Publish to local Confluence storage
    fetch('/api/ai-business-analyst/publish-confluence', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
            page_content: brdContent,
            page_title: projectName,
            space_key: spaceKey.trim(),
            brd_content: brdContent
        })
    })
    .then(response => {
        console.log('Response status:', response.status);
        if (!response.ok) {
            // Если 401, значит проблема с авторизацией
            if (response.status === 401) {
                return response.json().then(err => {
                    const errorMsg = err.error || 'Unauthorized';
                    return Promise.reject(new Error(`Ошибка авторизации (${errorMsg}). Пожалуйста, перезагрузите страницу и войдите снова.`));
                });
            }
            return response.json().then(err => Promise.reject(new Error(err.error || `HTTP ${response.status}`)));
        }
        return response.json();
    })
    .then(publishData => {
        loadingMsg.remove();
        console.log('Publish response:', publishData);
        if (publishData.success) {
            alert('BRD успешно добавлен в Confluence!');
            // Optionally close modal and redirect
            closeBRDModal();
            setTimeout(() => {
                window.location.href = '/confluence-docs';
            }, 500);
        } else {
            alert('Ошибка публикации: ' + (publishData.error || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        loadingMsg.remove();
        console.error('Error publishing to Confluence:', error);
        const errorMessage = error.message || 'Неизвестная ошибка';
        
        // Если ошибка авторизации, предлагаем перезагрузить страницу
        if (errorMessage.includes('авторизации') || errorMessage.includes('Unauthorized')) {
            if (confirm('Ошибка авторизации. Ваша сессия могла истечь.\n\nПерезагрузить страницу и войти снова?')) {
                window.location.reload();
            }
        } else {
            alert('Ошибка публикации: ' + errorMessage);
        }
    });
}

function formatBRDContent(content) {
    if (!content || typeof content !== 'string') {
        return '<p style="color: #6b7280; font-style: italic;">Содержимое документа пусто</p>';
    }
    
    let html = '';
    const lines = content.split('\n');
    let inList = false;
    let listItems = [];
    let currentSection = '';
    
    lines.forEach((line, index) => {
        const trimmed = line.trim();
        
        if (!trimmed) {
            if (inList && listItems.length > 0) {
                html += '<ul style="margin: 0.75rem 0; padding-left: 1.5rem; color: #4b5563;">';
                listItems.forEach(item => {
                    html += `<li style="margin: 0.5rem 0; line-height: 1.6;">${escapeHtml(item)}</li>`;
                });
                html += '</ul>';
                listItems = [];
                inList = false;
            }
            return;
        }
        
        // Main title (# Title)
        if (trimmed.startsWith('# ')) {
            if (inList && listItems.length > 0) {
                html += '<ul style="margin: 0.75rem 0; padding-left: 1.5rem; color: #4b5563;">';
                listItems.forEach(item => {
                    html += `<li style="margin: 0.5rem 0; line-height: 1.6;">${escapeHtml(item)}</li>`;
                });
                html += '</ul>';
                listItems = [];
                inList = false;
            }
            const title = trimmed.substring(2).trim();
            html += `<h1 style="font-size: 28px; font-weight: 700; color: #1a1a1a; margin: 1.5rem 0 1rem 0; padding-bottom: 0.75rem; border-bottom: 2px solid #e5e7eb;">${escapeHtml(title)}</h1>`;
        }
        // Section title (## Section)
        else if (trimmed.startsWith('## ')) {
            if (inList && listItems.length > 0) {
                html += '<ul style="margin: 0.75rem 0; padding-left: 1.5rem; color: #4b5563;">';
                listItems.forEach(item => {
                    html += `<li style="margin: 0.5rem 0; line-height: 1.6;">${escapeHtml(item)}</li>`;
                });
                html += '</ul>';
                listItems = [];
                inList = false;
            }
            const section = trimmed.substring(3).trim();
            html += `<h2 style="font-size: 20px; font-weight: 600; color: #1a1a1a; margin: 1.5rem 0 0.75rem 0; padding-top: 1rem;">${escapeHtml(section)}</h2>`;
        }
        // Subsection (### Subsection)
        else if (trimmed.startsWith('### ')) {
            if (inList && listItems.length > 0) {
                html += '<ul style="margin: 0.75rem 0; padding-left: 1.5rem; color: #4b5563;">';
                listItems.forEach(item => {
                    html += `<li style="margin: 0.5rem 0; line-height: 1.6;">${escapeHtml(item)}</li>`;
                });
                html += '</ul>';
                listItems = [];
                inList = false;
            }
            const subsection = trimmed.substring(4).trim();
            html += `<h3 style="font-size: 16px; font-weight: 600; color: #374151; margin: 1rem 0 0.5rem 0;">${escapeHtml(subsection)}</h3>`;
        }
        // List item (- or *)
        else if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || /^\d+\.\s/.test(trimmed)) {
            const item = trimmed.replace(/^[-*]\s*/, '').replace(/^\d+\.\s*/, '').trim();
            if (item) {
                listItems.push(item);
                inList = true;
            }
        }
        // Regular paragraph
        else {
            if (inList && listItems.length > 0) {
                html += '<ul style="margin: 0.75rem 0; padding-left: 1.5rem; color: #4b5563;">';
                listItems.forEach(item => {
                    html += `<li style="margin: 0.5rem 0; line-height: 1.6;">${escapeHtml(item)}</li>`;
                });
                html += '</ul>';
                listItems = [];
                inList = false;
            }
            // Check for bold text
            let formattedLine = trimmed
                .replace(/\*\*(.*?)\*\*/g, '<strong style="font-weight: 600; color: #1a1a1a;">$1</strong>')
                .replace(/\*(.*?)\*/g, '<em style="font-style: italic;">$1</em>')
                .replace(/`(.*?)`/g, '<code style="background: #f3f4f6; padding: 0.2rem 0.4rem; border-radius: 4px; font-family: monospace; font-size: 0.9em;">$1</code>');
            
            html += `<p style="margin: 0.75rem 0; line-height: 1.7; color: #4b5563; font-size: 14px;">${formattedLine}</p>`;
        }
    });
    
    // Close any remaining list
    if (inList && listItems.length > 0) {
        html += '<ul style="margin: 0.75rem 0; padding-left: 1.5rem; color: #4b5563;">';
        listItems.forEach(item => {
            html += `<li style="margin: 0.5rem 0; line-height: 1.6;">${escapeHtml(item)}</li>`;
        });
        html += '</ul>';
    }
    
    return html || '<p style="color: #6b7280; font-style: italic;">Не удалось отформатировать документ</p>';
}

function closeBRDModal() {
    const modal = document.getElementById('brd-modal');
    if (modal) {
        modal.remove();
    }
}

function copyBRDToClipboard() {
    const modal = document.getElementById('brd-modal');
    if (!modal) return;
    
    const originalContent = modal.dataset.originalContent || '';
    
    if (!originalContent) {
        alert('Ошибка: содержимое документа не найдено');
        return;
    }
    
    // Copy to clipboard
    navigator.clipboard.writeText(originalContent).then(() => {
        // Show success message
        const button = event.target.closest('button');
        const originalText = button.innerHTML;
        button.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display: inline-block; vertical-align: middle; margin-right: 0.5rem;"><polyline points="20 6 9 17 4 12"></polyline></svg>Скопировано!';
        button.style.background = '#10b981';
        
        setTimeout(() => {
            button.innerHTML = originalText;
            button.style.background = 'linear-gradient(135deg, #A52A2A 0%, #8B1E2D 100%)';
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = originalContent;
        textArea.style.position = 'fixed';
        textArea.style.opacity = '0';
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            alert('BRD документ скопирован в буфер обмена!');
        } catch (e) {
            alert('Не удалось скопировать. Пожалуйста, скопируйте вручную.');
        }
        document.body.removeChild(textArea);
    });
}

// Update BRD display to use editable fields
function updateBRDDisplayEditable(brdData) {
    const brdContainer = document.getElementById('brd-content');
    if (!brdContainer) return;
    
    // Parse BRD data - use empty defaults if no data provided
    let projectName = '';
    let scopeItems = [];
    let kpiItems = [];
    
    if (typeof brdData === 'string') {
        try {
            const parsed = JSON.parse(brdData);
            if (parsed.project_name) projectName = parsed.project_name;
            if (parsed.scope) scopeItems = parsed.scope;
            if (parsed.kpi) kpiItems = parsed.kpi;
        } catch (e) {
            // If not JSON, try to extract from markdown
            const lines = brdData.split('\n');
            for (const line of lines) {
                if (line.includes('Название проекта') || line.includes('PROJECT')) {
                    const nextLine = lines[lines.indexOf(line) + 1];
                    if (nextLine && !nextLine.startsWith('#')) {
                        projectName = nextLine.trim();
                    }
                }
            }
        }
    } else if (typeof brdData === 'object') {
        if (brdData.project_name) projectName = brdData.project_name;
        if (brdData.scope) scopeItems = brdData.scope;
        if (brdData.kpi) kpiItems = brdData.kpi;
    }
    
    // Update project name
    const projectNameInput = document.getElementById('project-name');
    if (projectNameInput) {
        projectNameInput.value = projectName;
    }
    
    // Update scope items
    const scopeChecklist = document.getElementById('scope-checklist');
    if (scopeChecklist) {
        scopeChecklist.innerHTML = scopeItems.map(item => `
            <div class="ba-checklist-item checked">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
                <input type="text" class="ba-editable-text" value="${escapeHtml(item)}" onblur="saveBRDData()" placeholder="Введите элемент">
                <button class="ba-remove-btn" onclick="removeScopeItem(this)" title="Удалить">×</button>
            </div>
        `).join('');
    }
    
    // Update KPI items
    const kpiList = document.getElementById('kpi-list');
    if (kpiList) {
        kpiList.innerHTML = kpiItems.map(kpi => `
            <div class="ba-kpi-item">
                <input type="text" class="ba-kpi-label-input" value="${escapeHtml(kpi.label)}" onblur="saveBRDData()" placeholder="Название метрики">
                <div class="ba-kpi-details">
                    <span>Цель: <input type="text" class="ba-kpi-value-input" value="${escapeHtml(kpi.goal)}" onblur="saveBRDData()" placeholder="Цель"></span>
                    <span class="${kpi.current && kpi.current.includes('дня') ? 'ba-kpi-bad' : ''}">Сейчас: <input type="text" class="ba-kpi-value-input" value="${escapeHtml(kpi.current)}" onblur="saveBRDData()" placeholder="Текущее значение"></span>
                </div>
                <button class="ba-remove-btn" onclick="removeKPIItem(this)" title="Удалить">×</button>
            </div>
        `).join('');
    }
}

// Autocomplete functions
function showAnswerSuggestions(question) {
    // Запрашиваем предложения вариантов ответа
    fetch('/api/ai-business-analyst/autocomplete/suggest-answers', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
            question: question,
            context: {
                collected_data: getCurrentBRDData(),
                conversation_history: chatHistory.slice(-5)
            }
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.suggestions && data.suggestions.length > 0) {
            displayAnswerSuggestions(data.suggestions);
        }
    })
    .catch(error => {
        console.error('Error fetching suggestions:', error);
    });
}

function displayAnswerSuggestions(suggestions) {
    const container = document.getElementById('requirements-chat');
    
    // Удаляем старые предложения
    const oldSuggestions = container.querySelector('.ba-suggestions');
    if (oldSuggestions) {
        oldSuggestions.remove();
    }
    
    const suggestionsDiv = document.createElement('div');
    suggestionsDiv.className = 'ba-suggestions';
    suggestionsDiv.innerHTML = `
        <div class="ba-suggestions-header">
            <span>💡 Предложенные варианты ответа:</span>
        </div>
        <div class="ba-suggestions-list">
            ${suggestions.map((suggestion, idx) => `
                <div class="ba-suggestion-item" onclick="useSuggestion('${escapeHtml(suggestion).replace(/'/g, "\\'")}')">
                    ${escapeHtml(suggestion)}
                </div>
            `).join('')}
        </div>
    `;
    
    container.appendChild(suggestionsDiv);
    container.scrollTop = container.scrollHeight;
}

function useSuggestion(suggestion) {
    const input = document.getElementById('requirements-input');
    input.value = suggestion;
    input.focus();
    
    // Убираем предложения
    const suggestionsDiv = document.querySelector('.ba-suggestions');
    if (suggestionsDiv) {
        suggestionsDiv.remove();
    }
}

function suggestAutofillFromChat() {
    // Показываем кнопку автозаполнения, если в чате есть информация
    const chatContainer = document.getElementById('requirements-chat');
    const existingButton = document.querySelector('.ba-autofill-button');
    
    if (existingButton) return; // Кнопка уже есть
    
    if (chatHistory.length >= 4) {
        const button = document.createElement('div');
        button.className = 'ba-autofill-button';
        button.innerHTML = `
            <button onclick="autofillBRDFromChat()" class="ba-btn-autofill">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2v20M2 12h20"></path>
                </svg>
                🤖 Автозаполнить поля BRD из чата
            </button>
        `;
        
        chatContainer.appendChild(button);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
}

function autofillBRDFromChat() {
    const button = document.querySelector('.ba-btn-autofill');
    if (button) {
        button.disabled = true;
        button.innerHTML = '<span class="spinner" style="width: 14px; height: 14px; border-width: 2px; margin: 0;"></span> Заполнение...';
    }
    
    fetch('/api/ai-business-analyst/autocomplete/fill-from-chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
            chat_history: chatHistory,
            collected_data: getCurrentBRDData(),
            session_id: getSessionId()
        })
    })
    .then(response => response.json())
    .then(data => {
        if (button) {
            button.disabled = false;
            button.innerHTML = '🤖 Автозаполнить поля BRD из чата';
        }
        
        if (data.success && data.filled_data) {
            applyAutofillData(data.filled_data);
            alert('Поля успешно заполнены!');
        } else {
            alert('Не удалось заполнить поля: ' + (data.error || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        if (button) {
            button.disabled = false;
            button.innerHTML = '🤖 Автозаполнить поля BRD из чата';
        }
        alert('Ошибка автозаполнения: ' + error.message);
    });
}

function getCurrentBRDData() {
    const projectName = document.getElementById('project-name')?.value || '';
    const scopeItems = Array.from(document.querySelectorAll('#scope-checklist .ba-editable-text'))
        .map(input => input.value.trim()).filter(v => v);
    const kpiItems = Array.from(document.querySelectorAll('#kpi-list .ba-kpi-item')).map(item => {
        const label = item.querySelector('.ba-kpi-label-input')?.value || '';
        const goal = item.querySelector('.ba-kpi-details span:first-child input')?.value || '';
        const current = item.querySelector('.ba-kpi-details span:last-child input')?.value || '';
        return { label, goal, current };
    }).filter(kpi => kpi.label);
    
    return {
        project_name: projectName,
        scope: scopeItems,
        kpi: kpiItems
    };
}

function getSessionId() {
    // Генерируем или получаем session_id
    if (!window.baSessionId) {
        window.baSessionId = `session_${Date.now()}`;
    }
    return window.baSessionId;
}

function applyAutofillData(filledData) {
    // Заполняем поля BRD
    if (filledData.project_name && !document.getElementById('project-name')?.value) {
        document.getElementById('project-name').value = filledData.project_name;
    }
    
    if (filledData.scope && Array.isArray(filledData.scope)) {
        filledData.scope.forEach(item => {
            if (item && !document.querySelector(`#scope-checklist .ba-editable-text[value="${escapeHtml(item)}"]`)) {
                addScopeItem();
                const items = document.querySelectorAll('#scope-checklist .ba-editable-text');
                if (items.length > 0) {
                    const lastItem = items[items.length - 1];
                    lastItem.value = item;
                }
            }
        });
    }
    
    if (filledData.kpi && Array.isArray(filledData.kpi)) {
        filledData.kpi.forEach(kpi => {
            if (kpi && kpi.label) {
                addKPIItem();
                const items = document.querySelectorAll('#kpi-list .ba-kpi-item');
                if (items.length > 0) {
                    const lastItem = items[items.length - 1];
                    const labelInput = lastItem.querySelector('.ba-kpi-label-input');
                    const goalInput = lastItem.querySelector('.ba-kpi-details span:first-child input');
                    const currentInput = lastItem.querySelector('.ba-kpi-details span:last-child input');
                    if (labelInput) labelInput.value = kpi.label || '';
                    if (goalInput) goalInput.value = kpi.goal || '';
                    if (currentInput) currentInput.value = kpi.current || '';
                }
            }
        });
    }
    
    saveBRDData();
}

function autofillFromText() {
    const text = prompt('Вставьте текст для автозаполнения полей (описание проекта, требования и т.д.):');
    if (!text || text.trim().length < 10) {
        alert('Текст должен содержать минимум 10 символов');
        return;
    }
    
    const loadingMsg = document.createElement('div');
    loadingMsg.textContent = 'Автозаполнение полей...';
    loadingMsg.style.cssText = 'position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 1rem 2rem; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 1000;';
    document.body.appendChild(loadingMsg);
    
    fetch('/api/ai-business-analyst/autocomplete/fill-from-text', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
            text: text
        })
    })
    .then(response => response.json())
    .then(data => {
        loadingMsg.remove();
        if (data.success && data.filled_data) {
            applyAutofillData(data.filled_data);
            alert('Поля успешно заполнены из текста!');
        } else {
            alert('Ошибка автозаполнения: ' + (data.error || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        loadingMsg.remove();
        alert('Ошибка автозаполнения: ' + error.message);
    });
}

function suggestScopeItems() {
    const projectDescription = document.getElementById('project-name')?.value || 
                              Array.from(document.querySelectorAll('#requirements-chat .ba-message-text'))
                                  .map(m => m.textContent).join(' ').slice(0, 500);
    
    if (!projectDescription || projectDescription.trim().length < 5) {
        alert('Сначала укажите название проекта или опишите проект в чате');
        return;
    }
    
    const existingScope = Array.from(document.querySelectorAll('#scope-checklist .ba-editable-text'))
        .map(input => input.value.trim()).filter(v => v);
    
    const loadingIndicator = document.createElement('div');
    loadingIndicator.textContent = 'Генерация предложений...';
    loadingIndicator.style.cssText = 'position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 1rem 2rem; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 1000;';
    document.body.appendChild(loadingIndicator);
    
    fetch('/api/ai-business-analyst/autocomplete/suggest-scope', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
            project_description: projectDescription,
            existing_scope: existingScope,
            session_id: getSessionId()
        })
    })
    .then(response => response.json())
    .then(data => {
        loadingIndicator.remove();
        if (data.success && data.suggestions && data.suggestions.length > 0) {
            showScopeSuggestions(data.suggestions);
        } else {
            alert('Не удалось получить предложения');
        }
    })
    .catch(error => {
        loadingIndicator.remove();
        alert('Ошибка: ' + error.message);
    });
}

function showScopeSuggestions(suggestions) {
    const modal = document.createElement('div');
    modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center;';
    modal.innerHTML = `
        <div style="background: white; padding: 2rem; border-radius: 12px; max-width: 600px; max-height: 80vh; overflow-y: auto;">
            <h3 style="margin-top: 0;">Предложенные элементы Scope</h3>
            <p style="color: #666; margin-bottom: 1rem;">Выберите элементы для добавления:</p>
            <div style="display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1.5rem;">
                ${suggestions.map(s => `
                    <label style="display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem; border: 1px solid #e5e7eb; border-radius: 8px; cursor: pointer; transition: background 0.2s;" onmouseover="this.style.background='#f9fafb'" onmouseout="this.style.background='white'">
                        <input type="checkbox" value="${escapeHtml(s)}" style="width: 18px; height: 18px; cursor: pointer;">
                        <span>${escapeHtml(s)}</span>
                    </label>
                `).join('')}
            </div>
            <div style="display: flex; gap: 0.75rem; justify-content: flex-end;">
                <button onclick="this.closest('div[style*=\"position: fixed\"]').remove()" style="padding: 0.625rem 1.5rem; background: #f3f4f6; border: none; border-radius: 8px; cursor: pointer;">Отмена</button>
                <button onclick="addSelectedScopeItems(this)" style="padding: 0.625rem 1.5rem; background: linear-gradient(135deg, #A52A2A 0%, #8B1E2D 100%); color: white; border: none; border-radius: 8px; cursor: pointer;">Добавить выбранные</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    
    window.addSelectedScopeItems = function(button) {
        const modal = button.closest('div[style*="position: fixed"]');
        const checkboxes = modal.querySelectorAll('input[type="checkbox"]:checked');
        checkboxes.forEach(cb => {
            addScopeItem();
            const items = document.querySelectorAll('#scope-checklist .ba-editable-text');
            if (items.length > 0) {
                items[items.length - 1].value = cb.value;
            }
        });
        modal.remove();
        delete window.addSelectedScopeItems;
        saveBRDData();
    };
}

// Новые функции для встроенного автозаполнения
function handleProjectNameInput(input) {
    const value = input.value.trim();
    if (value.length > 2) {
        showAutocompleteSuggestions(input, 'project_name');
    } else {
        hideAutocompleteSuggestions(input);
    }
}

function showAutocompleteSuggestions(input, fieldType) {
    const dropdown = document.getElementById(input.id + '-autocomplete');
    if (!dropdown) return;
    
    const value = input.value.trim();
    if (value.length < 2) {
        dropdown.classList.remove('show');
        return;
    }
    
    fetch('/api/ai-business-analyst/autocomplete/field', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        credentials: 'include',
        body: JSON.stringify({
            field_name: fieldType,
            partial_value: value,
            context: {collected_data: getCurrentBRDData()}
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success && data.suggestions && data.suggestions.length > 0) {
            dropdown.innerHTML = data.suggestions.map(s => 
                `<div class="ba-autocomplete-item" onclick="useAutocompleteSuggestion('${input.id}', '${escapeHtml(s).replace(/'/g, "\\'")}')">${escapeHtml(s)}</div>`
            ).join('');
            dropdown.classList.add('show');
        } else {
            dropdown.classList.remove('show');
        }
    })
    .catch(() => dropdown.classList.remove('show'));
}

function hideAutocompleteSuggestions(input) {
    setTimeout(() => {
        const dropdown = document.getElementById(input.id + '-autocomplete');
        if (dropdown) dropdown.classList.remove('show');
    }, 200);
}

function useAutocompleteSuggestion(inputId, value) {
    const input = document.getElementById(inputId);
    if (input) {
        input.value = value;
        input.focus();
        hideAutocompleteSuggestions(input);
        saveBRDData();
    }
}

function handleScopeInputKeyDown(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        const input = event.target;
        const value = input.value.trim();
        if (value) {
            addScopeItem();
            const items = document.querySelectorAll('#scope-checklist .ba-editable-text');
            if (items.length > 0) items[items.length - 1].value = value;
            input.value = '';
            saveBRDData();
        }
    }
}

function handleKPIInputKeyDown(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        const input = event.target;
        const value = input.value.trim();
        if (value) {
            addKPIItem();
            const items = document.querySelectorAll('#kpi-list .ba-kpi-item');
            if (items.length > 0) {
                const labelInput = items[items.length - 1].querySelector('.ba-kpi-label-input');
                if (labelInput) labelInput.value = value;
            }
            input.value = '';
            saveBRDData();
        }
    }
}

function quickFillFromChat(buttonElement) {
    // Проверяем, есть ли история диалога
    if (!chatHistory || chatHistory.length === 0) {
        alert('История диалога пуста. Сначала отправьте сообщение в чат, чтобы создать историю.');
        return;
    }
    
    // Находим кнопку: либо переданный элемент, либо ищем по селектору
    let activeButton = buttonElement;
    if (!activeButton) {
        // Ищем кнопку через селектор с onclick, содержащим quickFillFromChat
        const buttons = document.querySelectorAll('button[onclick*="quickFillFromChat"]');
        activeButton = buttons.length > 0 ? buttons[0] : null;
    }
    
    // Сохраняем оригинальный HTML кнопки
    const originalHTML = activeButton ? activeButton.innerHTML : '';
    
    // Показываем статус загрузки
    if (activeButton) {
        activeButton.disabled = true;
        activeButton.innerHTML = '<span class="spinner" style="width: 14px; height: 14px; margin: 0 8px 0 0; display: inline-block; vertical-align: middle; border: 2px solid currentColor; border-top-color: transparent; border-radius: 50%; animation: spin 0.6s linear infinite;"></span> Заполнение...';
    }
    
    fetch('/api/ai-business-analyst/autocomplete/fill-from-chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
            chat_history: chatHistory,
            collected_data: getCurrentBRDData(),
            session_id: getSessionId()
        })
    })
    .then(response => response.json())
    .then(data => {
        // Восстанавливаем кнопку
        if (activeButton) {
            activeButton.disabled = false;
            activeButton.innerHTML = originalHTML;
        }
        
        if (data.success && data.filled_data) {
            applyAutofillData(data.filled_data);
            alert('Поля успешно заполнены из диалога!');
        } else {
            alert('Не удалось заполнить поля: ' + (data.error || 'Недостаточно информации в диалоге'));
        }
    })
    .catch(error => {
        // Восстанавливаем кнопку при ошибке
        if (activeButton) {
            activeButton.disabled = false;
            activeButton.innerHTML = originalHTML;
        }
        console.error('Ошибка автозаполнения:', error);
        alert('Ошибка при заполнении полей: ' + error.message);
    });
}

function quickFillFromText() {
    autofillFromText();
}

function suggestKPIMetrics() {
    const projectDescription = document.getElementById('project-name')?.value || '';
    if (!projectDescription || projectDescription.trim().length < 5) {
        alert('Сначала укажите название проекта');
        return;
    }
    
    const existingKPI = Array.from(document.querySelectorAll('#kpi-list .ba-kpi-item')).map(item => {
        const label = item.querySelector('.ba-kpi-label-input')?.value?.trim() || '';
        return { label };
    }).filter(kpi => kpi.label);
    
    const loading = document.createElement('div');
    loading.textContent = 'Генерация метрик...';
    loading.style.cssText = 'position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 1rem 2rem; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 1000;';
    document.body.appendChild(loading);
    
    fetch('/api/ai-business-analyst/autocomplete/suggest-kpi', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        credentials: 'include',
        body: JSON.stringify({
            project_description: projectDescription,
            existing_kpi: existingKPI,
            session_id: getSessionId()
        })
    })
    .then(r => r.json())
    .then(data => {
        loading.remove();
        if (data.success && data.suggestions && data.suggestions.length > 0) {
            showKPISuggestions(data.suggestions);
        }
    })
    .catch(err => {
        loading.remove();
        alert('Ошибка: ' + err.message);
    });
}

function showKPISuggestions(suggestions) {
    const modal = document.createElement('div');
    modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center;';
    modal.innerHTML = `
        <div style="background: white; padding: 2rem; border-radius: 12px; max-width: 600px; max-height: 80vh; overflow-y: auto;">
            <h3 style="margin-top: 0;">Предложенные KPI метрики</h3>
            <div style="display: flex; flex-direction: column; gap: 0.5rem; margin: 1rem 0;">
                ${suggestions.map(kpi => `
                    <label style="display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem; border: 1px solid #e5e7eb; border-radius: 8px; cursor: pointer;">
                        <input type="checkbox" value='${JSON.stringify(kpi)}' style="width: 18px; height: 18px;">
                        <div><strong>${escapeHtml(kpi.label || '')}</strong><br><small>Цель: ${escapeHtml(kpi.goal || '')}</small></div>
                    </label>
                `).join('')}
            </div>
            <div style="display: flex; gap: 0.75rem; justify-content: flex-end;">
                <button onclick="this.closest('div[style*=\"position: fixed\"]').remove()" style="padding: 0.625rem 1.5rem; background: #f3f4f6; border: none; border-radius: 8px; cursor: pointer;">Отмена</button>
                <button onclick="addSelectedKPIMetrics(this)" style="padding: 0.625rem 1.5rem; background: linear-gradient(135deg, #A52A2A 0%, #8B1E2D 100%); color: white; border: none; border-radius: 8px; cursor: pointer;">Добавить</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    
    window.addSelectedKPIMetrics = function(button) {
        const modal = button.closest('div[style*="position: fixed"]');
        const checkboxes = modal.querySelectorAll('input[type="checkbox"]:checked');
        checkboxes.forEach(cb => {
            const kpi = JSON.parse(cb.value);
            addKPIItem();
            const items = document.querySelectorAll('#kpi-list .ba-kpi-item');
            if (items.length > 0) {
                const item = items[items.length - 1];
                const labelInput = item.querySelector('.ba-kpi-label-input');
                const goalInput = item.querySelector('.ba-kpi-details span:first-child input');
                if (labelInput) labelInput.value = kpi.label || '';
                if (goalInput) goalInput.value = kpi.goal || '';
            }
        });
        modal.remove();
        delete window.addSelectedKPIMetrics;
        saveBRDData();
    };
}

function showScopeSuggestions() {
    suggestScopeItems();
}

// Export functions to window for onclick handlers
window.sendRequirementsMessage = sendRequirementsMessage;
window.handleRequirementsKeyDown = handleRequirementsKeyDown;
window.exportBRD = exportBRD;
window.generateBRDManually = generateBRDManually;
window.generateMoreUseCases = generateMoreUseCases;
window.addUserStory = addUserStory;
window.generateBPMN = generateBPMN;
window.downloadBRD = downloadBRD;
window.publishToConfluence = publishToConfluence;
window.openConfluence = openConfluence;
window.newProject = newProject;
window.toggleExpand = toggleExpand;
window.saveBRDData = saveBRDData;
window.addScopeItem = addScopeItem;
window.removeScopeItem = removeScopeItem;
window.addKPIItem = addKPIItem;
window.removeKPIItem = removeKPIItem;
window.generateBRDFromFields = generateBRDFromFields;
window.showFormatSelectionDialog = showFormatSelectionDialog;
window.addBRDToConfluence = addBRDToConfluence;
window.copyBRDToClipboard = copyBRDToClipboard;
window.closeBRDModal = closeBRDModal;
window.handleProjectNameInput = handleProjectNameInput;
window.showAutocompleteSuggestions = showAutocompleteSuggestions;
window.hideAutocompleteSuggestions = hideAutocompleteSuggestions;
window.useAutocompleteSuggestion = useAutocompleteSuggestion;
window.handleScopeInputKeyDown = handleScopeInputKeyDown;
window.handleKPIInputKeyDown = handleKPIInputKeyDown;
window.quickFillFromChat = quickFillFromChat;
window.quickFillFromText = quickFillFromText;
window.suggestKPIMetrics = suggestKPIMetrics;
window.showScopeSuggestions = showScopeSuggestions;
window.handleFileSelect = handleFileSelect;
window.removeFile = removeFile;
window.downloadBPMNSVG = downloadBPMNSVG;


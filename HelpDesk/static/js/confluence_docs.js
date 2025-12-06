// Global state
let allDocuments = [];
let currentDocId = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadDocuments();
});

// Load all documents
function loadDocuments() {
    fetch('/api/confluence-docs/list')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                allDocuments = data.documents || [];
                displayDocuments(allDocuments);
                updateSpaceFilter(allDocuments);
            } else {
                showEmptyState();
            }
        })
        .catch(error => {
            console.error('Error loading documents:', error);
            showEmptyState();
        });
}

// Display documents
function displayDocuments(documents) {
    const grid = document.getElementById('documents-grid');
    const emptyState = document.getElementById('empty-state');
    
    if (documents.length === 0) {
        grid.innerHTML = '';
        showEmptyState();
        return;
    }
    
    emptyState.style.display = 'none';
    
    grid.innerHTML = documents.map(doc => `
        <div class="confluence-doc-card" onclick="viewDocument('${doc.id}')">
            <div class="confluence-doc-header">
                <div style="flex: 1;">
                    <h3 class="confluence-doc-title">${escapeHtml(doc.title)}</h3>
                    <span class="confluence-doc-space">${escapeHtml(doc.space_key)}</span>
                </div>
            </div>
            <div class="confluence-doc-meta">
                <div><strong>Тип:</strong> ${escapeHtml(doc.type || 'BRD')}</div>
                <div><strong>Создан:</strong> ${formatDate(doc.created_at)}</div>
                <div><strong>Автор:</strong> ${escapeHtml(doc.created_by || 'Неизвестно')}</div>
            </div>
        </div>
    `).join('');
}

// Show empty state
function showEmptyState() {
    const grid = document.getElementById('documents-grid');
    const emptyState = document.getElementById('empty-state');
    grid.innerHTML = '';
    emptyState.style.display = 'block';
}

// Update space filter dropdown
function updateSpaceFilter(documents) {
    const filter = document.getElementById('space-filter');
    const spaces = [...new Set(documents.map(doc => doc.space_key).filter(Boolean))].sort();
    
    // Clear existing options except "All"
    filter.innerHTML = '<option value="">Все пространства</option>';
    
    spaces.forEach(space => {
        const option = document.createElement('option');
        option.value = space;
        option.textContent = space;
        filter.appendChild(option);
    });
}

// Filter documents
function filterDocuments() {
    const searchTerm = document.getElementById('search-input').value.toLowerCase();
    const spaceFilter = document.getElementById('space-filter').value;
    
    let filtered = allDocuments;
    
    if (searchTerm) {
        filtered = filtered.filter(doc => 
            doc.title.toLowerCase().includes(searchTerm) ||
            doc.space_key.toLowerCase().includes(searchTerm) ||
            (doc.created_by && doc.created_by.toLowerCase().includes(searchTerm))
        );
    }
    
    if (spaceFilter) {
        filtered = filtered.filter(doc => doc.space_key === spaceFilter);
    }
    
    displayDocuments(filtered);
}

// View document
function viewDocument(docId) {
    currentDocId = docId;
    
    fetch(`/api/confluence-docs/${docId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.document) {
                const doc = data.document;
                const modal = document.getElementById('doc-modal');
                const modalTitle = document.getElementById('modal-title');
                const modalBody = document.getElementById('modal-body');
                
                modalTitle.textContent = doc.title;
                modalBody.innerHTML = formatBRDContent(doc.content);
                modal.style.display = 'flex';
            } else {
                alert('Ошибка загрузки документа: ' + (data.error || 'Неизвестная ошибка'));
            }
        })
        .catch(error => {
            console.error('Error loading document:', error);
            alert('Ошибка загрузки документа: ' + error.message);
        });
}

// Close document modal
function closeDocumentModal() {
    const modal = document.getElementById('doc-modal');
    modal.style.display = 'none';
    currentDocId = null;
}

// Delete current document
function deleteCurrentDocument() {
    if (!currentDocId) return;
    
    if (!confirm('Вы уверены, что хотите удалить этот документ?')) {
        return;
    }
    
    fetch(`/api/confluence-docs/${currentDocId}`, {
        method: 'DELETE'
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Документ успешно удален');
                closeDocumentModal();
                loadDocuments(); // Reload list
            } else {
                alert('Ошибка удаления: ' + (data.error || 'Неизвестная ошибка'));
            }
        })
        .catch(error => {
            console.error('Error deleting document:', error);
            alert('Ошибка удаления: ' + error.message);
        });
}

// Format BRD content (reuse from ai_business_analyst.js)
function formatBRDContent(content) {
    if (!content || typeof content !== 'string') {
        return '<p style="color: #6b7280; font-style: italic;">Содержимое документа пусто</p>';
    }
    
    let html = '';
    const lines = content.split('\n');
    let inList = false;
    let listItems = [];
    
    lines.forEach((line) => {
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
        else if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || /^\d+\.\s/.test(trimmed)) {
            const item = trimmed.replace(/^[-*]\s*/, '').replace(/^\d+\.\s*/, '').trim();
            if (item) {
                listItems.push(item);
                inList = true;
            }
        }
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
            let formattedLine = trimmed
                .replace(/\*\*(.*?)\*\*/g, '<strong style="font-weight: 600; color: #1a1a1a;">$1</strong>')
                .replace(/\*(.*?)\*/g, '<em style="font-style: italic;">$1</em>')
                .replace(/`(.*?)`/g, '<code style="background: #f3f4f6; padding: 0.2rem 0.4rem; border-radius: 4px; font-family: monospace; font-size: 0.9em;">$1</code>');
            
            html += `<p style="margin: 0.75rem 0; line-height: 1.7; color: #4b5563; font-size: 14px;">${formattedLine}</p>`;
        }
    });
    
    if (inList && listItems.length > 0) {
        html += '<ul style="margin: 0.75rem 0; padding-left: 1.5rem; color: #4b5563;">';
        listItems.forEach(item => {
            html += `<li style="margin: 0.5rem 0; line-height: 1.6;">${escapeHtml(item)}</li>`;
        });
        html += '</ul>';
    }
    
    return html || '<p style="color: #6b7280; font-style: italic;">Не удалось отформатировать документ</p>';
}

// Utility functions
function escapeHtml(text) {
    if (typeof text !== 'string') text = String(text);
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    if (!dateString) return 'Неизвестно';
    try {
        const date = new Date(dateString);
        return date.toLocaleString('ru-RU', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return dateString;
    }
}

// Export functions
window.viewDocument = viewDocument;
window.closeDocumentModal = closeDocumentModal;
window.deleteCurrentDocument = deleteCurrentDocument;
window.filterDocuments = filterDocuments;


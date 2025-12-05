// Основной JavaScript файл

// Форматирование телефона
document.addEventListener('DOMContentLoaded', function() {
    const phoneInputs = document.querySelectorAll('input[type="tel"]');
    
    phoneInputs.forEach(input => {
        input.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            if (value.startsWith('7')) {
                value = value.substring(1);
            }
            if (value.length > 0) {
                if (value.length <= 3) {
                    value = `+7 (${value}`;
                } else if (value.length <= 6) {
                    value = `+7 (${value.substring(0, 3)}) ${value.substring(3)}`;
                } else if (value.length <= 8) {
                    value = `+7 (${value.substring(0, 3)}) ${value.substring(3, 6)}-${value.substring(6)}`;
                } else {
                    value = `+7 (${value.substring(0, 3)}) ${value.substring(3, 6)}-${value.substring(6, 8)}-${value.substring(8, 10)}`;
                }
            }
            e.target.value = value;
        });
    });
});

// Утилиты
function showAlert(element, message, type = 'info') {
    element.innerHTML = message;
    element.className = `ticket-response ${type} show`;
    element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideAlert(element) {
    element.classList.remove('show');
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}


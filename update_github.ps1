# Скрипт для обновления GitHub репозитория
# Выполните этот скрипт после установки Git

Write-Host "🚀 Обновление GitHub репозитория HelpDesk AI Platform" -ForegroundColor Green
Write-Host ""

# Проверка наличия Git
try {
    $gitVersion = git --version
    Write-Host "✅ Git найден: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Git не установлен!" -ForegroundColor Red
    Write-Host "Установите Git с https://git-scm.com/download/win" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "📝 Добавление изменений..." -ForegroundColor Cyan
git add README.md
git add HelpDesk/PRESENTATION_TEXT.md
git add HelpDesk/PRESENTATION_SHORT.md

Write-Host ""
Write-Host "💾 Создание коммита..." -ForegroundColor Cyan
git commit -m "Обновлен README: добавлена информация о полной платформе HelpDesk AI Platform

- Обновлено описание проекта на комплексную платформу
- Добавлена информация о 6 Help Desk модулях
- Добавлена информация о 5 AI-ассистентах
- Добавлены ключевые метрики и результаты
- Улучшена структура и документация
- Добавлены тексты для презентации проекта"

Write-Host ""
Write-Host "📤 Отправка изменений на GitHub..." -ForegroundColor Cyan
git push origin main

Write-Host ""
Write-Host "✅ Готово! Репозиторий обновлен на GitHub" -ForegroundColor Green
Write-Host "Проверьте: https://github.com/Mnurik7/it_fest" -ForegroundColor Cyan


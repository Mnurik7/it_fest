#!/bin/bash

# Скрипт для обновления GitHub репозитория (Linux/Mac)
# Выполните: chmod +x update_github.sh && ./update_github.sh

echo "🚀 Обновление GitHub репозитория HelpDesk AI Platform"
echo ""

# Проверка наличия Git
if ! command -v git &> /dev/null; then
    echo "❌ Git не установлен!"
    echo "Установите Git: sudo apt-get install git (Linux) или brew install git (Mac)"
    exit 1
fi

echo "✅ Git найден: $(git --version)"
echo ""
echo "📝 Добавление изменений..."
git add README.md
git add HelpDesk/PRESENTATION_TEXT.md
git add HelpDesk/PRESENTATION_SHORT.md

echo ""
echo "💾 Создание коммита..."
git commit -m "Обновлен README: добавлена информация о полной платформе HelpDesk AI Platform

- Обновлено описание проекта на комплексную платформу
- Добавлена информация о 6 Help Desk модулях
- Добавлена информация о 5 AI-ассистентах
- Добавлены ключевые метрики и результаты
- Улучшена структура и документация
- Добавлены тексты для презентации проекта"

echo ""
echo "📤 Отправка изменений на GitHub..."
git push origin main

echo ""
echo "✅ Готово! Репозиторий обновлен на GitHub"
echo "Проверьте: https://github.com/Mnurik7/it_fest"


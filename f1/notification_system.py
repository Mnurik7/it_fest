"""
Система уведомлений о статусе заявок
"""
from database import Database
from telegram import Bot
import os
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional

load_dotenv()

class NotificationSystem:
    def __init__(self):
        self.db = Database()
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.bot = Bot(token=self.bot_token) if self.bot_token else None
    
    async def notify_request_status(self, request_id: int, status: str, comment: Optional[str] = None):
        """Уведомление об изменении статуса заявки"""
        if not self.bot:
            return
        
        # Получаем информацию о заявке
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.id, r.client_id, r.status, r.problem_type, c.telegram_id, c.full_name
            FROM requests r
            JOIN clients c ON r.client_id = c.id
            WHERE r.id = ?
        ''', (request_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row or not row[4]:  # Нет telegram_id
            return
        
        request_id_db, client_id, current_status, problem_type, telegram_id, full_name = row
        
        # Определяем язык (упрощенно, можно улучшить)
        language = 'ru'  # По умолчанию русский
        
        if status == 'in_work':
            if language == 'kk':
                message = f"⏳ **Заявка №{request_id} жұмысқа алынды**\n\n"
                message += f"Мәселе: {problem_type}\n"
                message += "Инженер мәселені шешуде."
            else:
                message = f"⏳ **Заявка №{request_id} взята в работу**\n\n"
                message += f"Проблема: {problem_type}\n"
                message += "Инженер решает проблему."
        
        elif status == 'engineer_dispatched':
            if language == 'kk':
                message = f"🚗 **Инженер сізге жолдады**\n\n"
                message += f"Заявка №{request_id}\n"
                message += "Инженер келе жатыр."
            else:
                message = f"🚗 **Инженер выехал к вам**\n\n"
                message += f"Заявка №{request_id}\n"
                message += "Инженер в пути."
        
        elif status == 'closed':
            if language == 'kk':
                message = f"✅ **Жұмыстар аяқталды**\n\n"
                message += f"Заявка №{request_id}\n"
                if comment:
                    message += f"Комментарий: {comment}\n\n"
                message += "Барлығы жұмыс істей ме?"
            else:
                message = f"✅ **Работы завершены**\n\n"
                message += f"Заявка №{request_id}\n"
                if comment:
                    message += f"Комментарий: {comment}\n\n"
                message += "Всё работает?"
        
        else:
            return  # Неизвестный статус
        
        try:
            await self.bot.send_message(chat_id=telegram_id, text=message, parse_mode='Markdown')
        except Exception as e:
            print(f"Ошибка отправки уведомления: {e}")
    
    def update_request_status(self, request_id: int, status: str, comment: Optional[str] = None):
        """Обновление статуса заявки с уведомлением"""
        import asyncio
        
        # Обновляем в базе
        self.db.update_request(request_id, status=status, comment=comment)
        
        # Отправляем уведомление
        if self.bot:
            asyncio.run(self.notify_request_status(request_id, status, comment))


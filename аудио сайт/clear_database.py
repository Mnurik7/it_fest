"""
Скрипт для очистки всех данных из базы данных SQLite
"""
import os
from flask import Flask
from models import db, Ticket, User, Chat, ChatMessage

# Загрузка переменных окружения
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///helpdesk.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    try:
        print("Очистка данных из базы данных...")
        
        # Удаляем все записи (в правильном порядке для соблюдения внешних ключей)
        deleted_messages = ChatMessage.query.delete()
        print(f"  - Удалено сообщений чата: {deleted_messages}")
        
        deleted_chats = Chat.query.delete()
        print(f"  - Удалено чатов: {deleted_chats}")
        
        deleted_tickets = Ticket.query.delete()
        print(f"  - Удалено тикетов: {deleted_tickets}")
        
        deleted_users = User.query.delete()
        print(f"  - Удалено пользователей: {deleted_users}")
        
        # Коммитим изменения
        db.session.commit()
        
        print("\n✓ Все данные успешно очищены из базы данных!")
        print("\nПримечание: Таблицы остались, но все записи удалены.")
        print("Для полного удаления базы данных удалите файл instance/helpdesk.db")
        
    except Exception as e:
        db.session.rollback()
        print(f"\n✗ Ошибка при очистке данных: {e}")
        raise


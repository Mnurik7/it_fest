"""
Скрипт для миграции базы данных с сохранением данных
Добавляет новые колонки в chat_messages таблицу
"""
import os
import sqlite3
from flask import Flask
from models import db
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///helpdesk.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def migrate_database():
    """Миграция базы данных с сохранением данных"""
    db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
    
    if not os.path.exists(db_path):
        print("База данных не найдена. Создаю новую...")
        with app.app_context():
            db.create_all()
        print("✓ База данных создана")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Проверяем наличие таблицы chat_messages
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chat_messages'")
        if not cursor.fetchone():
            print("Таблица chat_messages не найдена. Создаю все таблицы...")
            conn.close()
            with app.app_context():
                db.create_all()
            print("✓ Все таблицы созданы")
            return
        
        # Получаем список колонок
        cursor.execute("PRAGMA table_info(chat_messages)")
        columns = [col[1] for col in cursor.fetchall()]
        
        print(f"Текущие колонки в chat_messages: {columns}")
        
        # Добавляем новые колонки, если их нет
        new_columns = {
            'message_type': "VARCHAR(20) DEFAULT 'text'",
            'attachment_url': 'VARCHAR(500)',
            'attachment_filename': 'VARCHAR(255)',
            'attachment_size': 'INTEGER',
            'is_formatted': 'BOOLEAN DEFAULT 0'
        }
        
        added_columns = []
        for col_name, col_type in new_columns.items():
            if col_name not in columns:
                try:
                    cursor.execute(f"ALTER TABLE chat_messages ADD COLUMN {col_name} {col_type}")
                    added_columns.append(col_name)
                    print(f"  ✓ Добавлена колонка: {col_name}")
                except sqlite3.OperationalError as e:
                    print(f"  ✗ Ошибка при добавлении колонки {col_name}: {e}")
        
        conn.commit()
        
        if added_columns:
            print(f"\n✓ Миграция успешно завершена! Добавлено колонок: {len(added_columns)}")
        else:
            print("\n✓ База данных уже актуальна. Все необходимые колонки уже существуют.")
            
    except Exception as e:
        conn.rollback()
        print(f"\n✗ Ошибка при миграции: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    print("=" * 60)
    print("Миграция базы данных SQLite")
    print("=" * 60)
    print()
    
    migrate_database()
    
    print()
    print("=" * 60)
    print("Миграция завершена!")
    print("=" * 60)


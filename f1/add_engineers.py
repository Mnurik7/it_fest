"""
Скрипт для добавления инженеров в базу данных
"""
from database import Database

def add_sample_engineers():
    """Добавление примеров инженеров"""
    db = Database()
    
    engineers = [
        ("Алексей Иванов", "интернет", None),
        ("Мария Петрова", "телефония", None),
        ("Дмитрий Сидоров", "телевидение", None),
        ("Анна Козлова", "оборудование", None),
        ("Сергей Волков", "оплата", None),
        ("Елена Новикова", "общая поддержка", None),
    ]
    
    for name, specialization, telegram_id in engineers:
        db.add_engineer(name, specialization, telegram_id)
        print(f"Добавлен инженер: {name} - {specialization}")

if __name__ == '__main__':
    add_sample_engineers()
    print("\nИнженеры успешно добавлены в базу данных!")


"""
Скрипт для генерации 100 транзакций в JSON формате
Создает смесь обычных, подозрительных и мошеннических переводов
"""

import json
import random
from datetime import datetime, timedelta

# Триггеры для разных типов переводов
RED_COMMENTS = [
    "Мы из банка, с вашей карты пытаются списать деньги, подтвердите перевод",
    "Служба безопасности банка требует подтверждения перевода",
    "Переведите на безопасный счет, ваша карта заблокирована",
    "Срочно подтвердите перевод, банк требует подтверждения",
    "Мы из банка, разблокируйте карту, переведите на безопасный счет",
    "Подтвердите перевод, с вашей карты пытаются списать деньги",
    "Банк требует подтверждения, переведите на безопасный счёт",
    "Ваша карта заблокирована, подтвердите перевод для разблокировки"
]

YELLOW_COMMENTS = [
    "я случайно скинул вам 5000тг, можете отправить обратно",
    "ошибочно перевел деньги, верните пожалуйста",
    "я случайно скинул, можете отправить обратно",
    "ошибочно перевёл, верните деньги",
    "случайный перевод, верните пожалуйста",
    "ошибся с номером, верните деньги",
    "неправильно перевел, отдайте обратно",
    "я случайно скинул вам, верните пожалуйста"
]

GREEN_COMMENTS = [
    "Оплата за услуги",
    "Перевод за покупку",
    "Оплата товара",
    "Перевод другу",
    "Оплата за работу",
    "Перевод за аренду",
    "Оплата за обучение",
    "Перевод за подарок",
    "Оплата за ремонт",
    "Перевод за продукты"
]

def generate_transactions(count=100):
    """Генерирует список транзакций"""
    transactions = []
    
    # Генерируем ID отправителей и получателей
    sender_ids = [f"user{random.randint(1000, 9999)}" for _ in range(30)]
    receiver_ids = [f"user{random.randint(1000, 9999)}" for _ in range(30)]
    
    # Распределение: 60% GREEN, 25% YELLOW, 15% RED
    green_count = int(count * 0.60)
    yellow_count = int(count * 0.25)
    red_count = count - green_count - yellow_count
    
    transaction_id = 1
    
    # Генерируем GREEN транзакции
    for i in range(green_count):
        transactions.append({
            "id": transaction_id,
            "sender_id": random.choice(sender_ids),
            "receiver_id": random.choice(receiver_ids),
            "amount": round(random.uniform(1000, 50000), 2),
            "currency": "KZT",
            "comment": random.choice(GREEN_COMMENTS),
            "timestamp": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat()
        })
        transaction_id += 1
    
    # Генерируем YELLOW транзакции (подозрительные)
    # Создаем несколько отправителей, которые будут делать множественные подозрительные переводы
    suspicious_senders = [f"suspicious{random.randint(1, 5)}" for _ in range(5)]
    
    for i in range(yellow_count):
        # Некоторые отправители делают несколько подозрительных переводов
        if i < 10:
            sender = random.choice(suspicious_senders)
        else:
            sender = random.choice(sender_ids)
        
        transactions.append({
            "id": transaction_id,
            "sender_id": sender,
            "receiver_id": random.choice(receiver_ids),
            "amount": round(random.uniform(2000, 20000), 2),
            "currency": "KZT",
            "comment": random.choice(YELLOW_COMMENTS),
            "timestamp": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat()
        })
        transaction_id += 1
    
    # Генерируем RED транзакции (мошенничество)
    fraud_senders = [f"fraudster{random.randint(1, 3)}" for _ in range(3)]
    
    for i in range(red_count):
        transactions.append({
            "id": transaction_id,
            "sender_id": random.choice(fraud_senders),
            "receiver_id": random.choice(receiver_ids),
            "amount": round(random.uniform(10000, 100000), 2),
            "currency": "KZT",
            "comment": random.choice(RED_COMMENTS),
            "timestamp": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat()
        })
        transaction_id += 1
    
    # Перемешиваем транзакции для реалистичности
    random.shuffle(transactions)
    
    # Переназначаем ID в правильном порядке
    for i, trans in enumerate(transactions, 1):
        trans["id"] = i
    
    return transactions

def main():
    """Главная функция"""
    print("Генерация 100 транзакций...")
    
    transactions = generate_transactions(100)
    
    # Сохраняем в JSON файл
    filename = "transactions_100.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            "transactions": transactions,
            "total": len(transactions),
            "generated_at": datetime.now().isoformat(),
            "description": "100 транзакций для анализа антифрод системой"
        }, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Создано {len(transactions)} транзакций")
    print(f"📁 Файл сохранен: {filename}")
    
    # Статистика
    green_count = sum(1 for t in transactions if any(green in t["comment"].lower() for green in ["оплата", "перевод", "покупка", "работа", "аренда", "обучение", "ремонт", "продукты", "подарок", "товар"]))
    yellow_count = sum(1 for t in transactions if any(yellow in t["comment"].lower() for yellow in ["случайно", "ошибочно", "верните", "отправить обратно"]))
    red_count = sum(1 for t in transactions if any(red in t["comment"].lower() for red in ["мы из банка", "подтвердите", "безопасный счет", "заблокирована"]))
    
    print(f"\n📊 Статистика:")
    print(f"  - Обычные (GREEN): ~{green_count}")
    print(f"  - Подозрительные (YELLOW): ~{yellow_count}")
    print(f"  - Мошеннические (RED): ~{red_count}")

if __name__ == "__main__":
    main()


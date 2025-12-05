"""
Скрипт для проверки данных в базе
"""
from database import Database

def main():
    db = Database()
    
    print("=" * 60)
    print("Проверка базы данных Казахтелеком")
    print("=" * 60)
    
    # Проверяем клиентов
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM clients")
    clients_count = cursor.fetchone()[0]
    print(f"\n📊 Клиенты: {clients_count}")
    
    cursor.execute("SELECT COUNT(*) FROM network_segments")
    segments_count = cursor.fetchone()[0]
    print(f"📊 Сегменты сети: {segments_count}")
    
    cursor.execute("SELECT COUNT(*) FROM outages WHERE status = 'active'")
    active_outages = cursor.fetchone()[0]
    print(f"📊 Активных аварий: {active_outages}")
    
    cursor.execute("SELECT COUNT(*) FROM outages WHERE status = 'completed'")
    completed_outages = cursor.fetchone()[0]
    print(f"📊 Завершенных аварий: {completed_outages}")
    
    cursor.execute("SELECT COUNT(*) FROM services")
    services_count = cursor.fetchone()[0]
    print(f"📊 Услуг: {services_count}")
    
    cursor.execute("SELECT COUNT(*) FROM requests")
    requests_count = cursor.fetchone()[0]
    print(f"📊 Заявок: {requests_count}")
    
    # Показываем примеры клиентов
    print("\n" + "=" * 60)
    print("Примеры клиентов:")
    print("=" * 60)
    
    cursor.execute("""
        SELECT telegram_id, full_name, city, street, house_number, contract_number
        FROM clients
        LIMIT 5
    """)
    
    for row in cursor.fetchall():
        print(f"\n  Telegram ID: {row[0]}")
        print(f"  Имя: {row[1]}")
        print(f"  Адрес: {row[2]}, {row[3]}, д.{row[4]}")
        print(f"  Договор: {row[5]}")
    
    # Показываем активные аварии
    print("\n" + "=" * 60)
    print("Активные аварии:")
    print("=" * 60)
    
    cursor.execute("""
        SELECT o.id, o.reason, o.started_at, o.estimated_end, ns.node_name, ns.city, ns.street
        FROM outages o
        JOIN network_segments ns ON o.segment_id = ns.id
        WHERE o.status = 'active'
        LIMIT 5
    """)
    
    outages = cursor.fetchall()
    if outages:
        for row in outages:
            print(f"\n  Узел: {row[4]}")
            print(f"  Адрес: {row[5]}, {row[6]}")
            print(f"  Причина: {row[1]}")
            print(f"  Начало: {row[2]}")
            print(f"  Восстановление: {row[3]}")
    else:
        print("  Нет активных аварий")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ Проверка завершена!")
    print("=" * 60)

if __name__ == '__main__':
    main()


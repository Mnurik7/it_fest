"""
Скрипт для установки пароля "123456" всем клиентам в базе данных
"""
from database import Database

def main():
    db = Database()
    
    # Получаем всех клиентов
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, phone_number, full_name FROM clients")
    clients = cursor.fetchall()
    
    print(f"Найдено клиентов: {len(clients)}")
    
    # Устанавливаем пароль "123456" для всех клиентов
    password_hash = db.hash_password("123456")
    
    updated_count = 0
    for client in clients:
        client_id, phone, name = client
        cursor.execute("""
            UPDATE clients 
            SET password = ? 
            WHERE id = ?
        """, (password_hash, client_id))
        updated_count += 1
        print(f"Обновлен пароль для: {name} ({phone})")
    
    conn.commit()
    conn.close()
    
    print(f"\n[OK] Успешно обновлено паролей: {updated_count}")
    print("Теперь все клиенты могут войти с паролем: 123456")
    print("\nПримеры номеров телефонов для входа:")
    
    # Показываем первые 5 номеров
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT phone_number, full_name FROM clients LIMIT 5")
    examples = cursor.fetchall()
    conn.close()
    
    for phone, name in examples:
        print(f"  - {phone} ({name})")

if __name__ == '__main__':
    main()


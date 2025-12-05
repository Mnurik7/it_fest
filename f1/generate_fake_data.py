"""
Скрипт для генерации фейковых данных по Казахстану
"""
import random
from datetime import datetime, timedelta
from database import Database

# Казахские имена и фамилии
FIRST_NAMES = [
    "Айдар", "Асылбек", "Данияр", "Ерлан", "Жанат", "Касым", "Марат", "Нурлан",
    "Рахат", "Серик", "Талгат", "Айгуль", "Алма", "Гульнара", "Жанар", "Камила",
    "Ляззат", "Мадина", "Нургуль", "Сауле", "Айжан", "Алтынай", "Ботагоз", "Динара"
]

LAST_NAMES = [
    "Абдуллаев", "Алиев", "Беков", "Даулетов", "Ермеков", "Жумабеков", "Касымов",
    "Муканов", "Нургалиев", "Омаров", "Рахимов", "Садыков", "Таукелов", "Усенов",
    "Абдуллаева", "Алиева", "Бекова", "Даулетова", "Ермекова", "Жумабекова", "Касымова",
    "Муканова", "Нургалиева", "Омарова", "Рахимова", "Садыкова", "Таукелова", "Усенова"
]

# Города Казахстана
CITIES = [
    ("Алматы", ["Алмалинский", "Медеуский", "Турксибский", "Жетысуский", "Ауэзовский"]),
    ("Астана", ["Алматинский", "Сарыаркинский", "Есильский", "Байконурский"]),
    ("Шымкент", ["Абайский", "Енбекшинский", "Каратауский"]),
    ("Караганда", ["Октябрьский", "Казыбекбийский", "Бухаржырауский"]),
    ("Актобе", ["Алгинский", "Мартукский", "Хромтауский"]),
    ("Тараз", ["Байзакский", "Жамбылский", "Таласский"]),
    ("Павлодар", ["Аксуский", "Баянаульский", "Иртышский"]),
    ("Усть-Каменогорск", ["Алтайский", "Глубоковский", "Зыряновский"]),
    ("Семей", ["Абайский", "Бородулихинский", "Жарминский"]),
    ("Кызылорда", ["Аральский", "Жалагашский", "Сырдарьинский"])
]

# Улицы (общие для всех городов)
STREETS = [
    "Абая", "Достык", "Саина", "Толе би", "Назарбаева", "Курмангазы", "Шевченко",
    "Гоголя", "Пушкина", "Ленина", "Мира", "Мира", "Жибек жолы", "Байтурсынова",
    "Алмалы", "Сарыарка", "Кабанбай батыра", "Райымбека", "Жандосова", "Тимирязева"
]

# Тарифы
TARIFFS = [
    "Интернет 50 Мбит/с",
    "Интернет 100 Мбит/с",
    "Интернет 200 Мбит/с",
    "Интернет + ТВ",
    "Интернет + ТВ + Телефония",
    "Только ТВ",
    "Только Телефония"
]

# Причины аварий
OUTAGE_REASONS = [
    "Плановые работы",
    "Обрыв кабеля",
    "Авария на узле",
    "Ремонт оборудования",
    "Перегрузка сети",
    "Техническое обслуживание"
]

def generate_phone_number():
    """Генерация казахстанского номера телефона"""
    return f"+7{random.randint(700, 799)}{random.randint(1000000, 9999999)}"

def generate_contract_number():
    """Генерация номера договора"""
    return f"KT{random.randint(100000, 999999)}"

def generate_fake_clients(db: Database, count: int = 200):
    """Генерация фейковых клиентов"""
    print(f"Генерация {count} клиентов...")
    clients = []
    
    for i in range(count):
        city_data = random.choice(CITIES)
        city = city_data[0]
        district = random.choice(city_data[1])
        street = random.choice(STREETS)
        house_number = str(random.randint(1, 150))
        
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        full_name = f"{last_name} {first_name}"
        
        phone = generate_phone_number()
        contract = generate_contract_number()
        telegram_id = 1000000000 + i  # Фейковые telegram_id
        
        client_id = db.add_client(
            full_name=full_name,
            phone_number=phone,
            telegram_id=telegram_id,
            city=city,
            street=street,
            house_number=house_number,
            contract_number=contract
        )
        
        clients.append({
            'id': client_id,
            'telegram_id': telegram_id,
            'city': city,
            'street': street,
            'house_number': house_number
        })
        
        # Добавляем услуги для клиента
        tariff = random.choice(TARIFFS)
        is_blocked = random.random() < 0.1  # 10% с блокировкой
        debt = random.randint(0, 50000) if is_blocked else 0
        
        db.add_service(
            client_id=client_id,
            tariff_name=tariff,
            is_active=True,
            is_blocked=is_blocked,
            debt_amount=debt
        )
        
        if (i + 1) % 50 == 0:
            print(f"  Создано {i + 1} клиентов...")
    
    print(f"✅ Создано {count} клиентов")
    return clients

def generate_network_segments(db: Database):
    """Генерация сегментов сети"""
    print("Генерация сегментов сети...")
    segments = []
    segment_id = 1
    
    for city_data in CITIES:
        city = city_data[0]
        for street in STREETS[:10]:  # По 10 улиц на город
            # Создаем несколько сегментов на улицу
            for seg in range(3):
                house_from = seg * 50 + 1
                house_to = (seg + 1) * 50
                district = random.choice(city_data[1])
                node_name = f"{city}-{district}-Узел{segment_id}"
                
                seg_id = db.add_network_segment(
                    city=city,
                    district=district,
                    street=street,
                    house_from=house_from,
                    house_to=house_to,
                    node_name=node_name
                )
                
                segments.append({
                    'id': seg_id,
                    'city': city,
                    'street': street,
                    'node_name': node_name
                })
                segment_id += 1
    
    print(f"✅ Создано {len(segments)} сегментов сети")
    return segments

def generate_outages(db: Database, segments: list):
    """Генерация аварий"""
    print("Генерация аварий...")
    outages = []
    
    # Создаем несколько активных аварий
    active_count = random.randint(5, 15)
    for i in range(active_count):
        segment = random.choice(segments)
        started_at = datetime.now() - timedelta(hours=random.randint(1, 12))
        estimated_end = datetime.now() + timedelta(hours=random.randint(1, 6))
        reason = random.choice(OUTAGE_REASONS)
        
        outage_id = db.add_outage(
            segment_id=segment['id'],
            started_at=started_at,
            estimated_end=estimated_end,
            reason=reason,
            status='active'
        )
        
        outages.append({
            'id': outage_id,
            'segment_id': segment['id'],
            'city': segment['city'],
            'street': segment['street']
        })
    
    # Создаем несколько завершенных аварий
    completed_count = random.randint(10, 30)
    for i in range(completed_count):
        segment = random.choice(segments)
        started_at = datetime.now() - timedelta(days=random.randint(1, 30))
        actual_end = started_at + timedelta(hours=random.randint(1, 8))
        reason = random.choice(OUTAGE_REASONS)
        
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO outages (segment_id, started_at, actual_end, reason, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (segment['id'], started_at, actual_end, reason, 'completed'))
        conn.commit()
        conn.close()
    
    print(f"✅ Создано {active_count} активных и {completed_count} завершенных аварий")
    return outages

def generate_requests(db: Database, clients: list):
    """Генерация заявок"""
    print("Генерация заявок...")
    
    problem_types = [
        "нет интернета", "низкая скорость", "не работает ТВ", "проблемы с телефонией",
        "не работает оборудование", "вопрос по тарифу", "задолженность", "другое"
    ]
    
    channels = ["telegram", "звонок", "личный визит"]
    statuses = ["open", "in_work", "closed"]
    
    request_count = random.randint(50, 150)
    for i in range(request_count):
        client = random.choice(clients)
        problem_type = random.choice(problem_types)
        channel = random.choice(channels)
        status = random.choice(statuses)
        
        comment = None
        resolved_at = None
        if status == "closed":
            comment = "Проблема решена"
            resolved_at = datetime.now() - timedelta(days=random.randint(1, 10))
        
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO requests (client_id, channel, problem_type, status, comment, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (client['id'], channel, problem_type, status, comment, resolved_at))
        conn.commit()
        conn.close()
    
    print(f"✅ Создано {request_count} заявок")

def main():
    """Основная функция генерации данных"""
    print("=" * 50)
    print("Генерация фейковой базы данных Казахтелеком")
    print("=" * 50)
    
    db = Database()
    
    # Генерируем клиентов
    clients = generate_fake_clients(db, count=200)
    
    # Генерируем сегменты сети
    segments = generate_network_segments(db)
    
    # Генерируем аварии
    outages = generate_outages(db, segments)
    
    # Генерируем заявки
    generate_requests(db, clients)
    
    print("=" * 50)
    print("✅ Генерация данных завершена!")
    print("=" * 50)
    print(f"\nСтатистика:")
    print(f"  Клиентов: {len(clients)}")
    print(f"  Сегментов сети: {len(segments)}")
    print(f"  Активных аварий: {len(outages)}")
    print(f"\nБаза данных готова к использованию!")

if __name__ == '__main__':
    main()


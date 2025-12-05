import sqlite3
import os
import hashlib
from datetime import datetime
from typing import Optional, List, Dict

class Database:
    def __init__(self, db_path: str = "kazakhtelecom.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Инициализация базы данных и создание таблиц"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица обращений (tickets)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message_text TEXT NOT NULL,
                problem_category TEXT,
                ai_solution TEXT,
                status TEXT DEFAULT 'open',
                assigned_engineer TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица инженеров
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS engineers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                specialization TEXT,
                telegram_id INTEGER,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Таблица истории диалогов для контекста
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticket_id INTEGER,
                message_text TEXT NOT NULL,
                is_user_message INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (ticket_id) REFERENCES tickets (id)
            )
        ''')
        
        # Таблица клиентов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                phone_number TEXT NOT NULL,
                password TEXT,
                telegram_id INTEGER UNIQUE,
                city TEXT NOT NULL,
                street TEXT NOT NULL,
                house_number TEXT NOT NULL,
                contract_number TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Добавляем поле password если его нет (для существующих БД)
        try:
            cursor.execute('ALTER TABLE clients ADD COLUMN password TEXT')
        except sqlite3.OperationalError:
            pass  # Поле уже существует
        
        # Таблица районов/сегментов сети
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS network_segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL,
                district TEXT NOT NULL,
                street TEXT NOT NULL,
                house_from INTEGER NOT NULL,
                house_to INTEGER NOT NULL,
                node_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица аварий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS outages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                segment_id INTEGER NOT NULL,
                started_at TIMESTAMP NOT NULL,
                estimated_end TIMESTAMP,
                actual_end TIMESTAMP,
                status TEXT DEFAULT 'active',
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (segment_id) REFERENCES network_segments (id)
            )
        ''')
        
        # Таблица услуг/тарифов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                tariff_name TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                is_blocked INTEGER DEFAULT 0,
                debt_amount REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients (id)
            )
        ''')
        
        # Таблица заявок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                channel TEXT NOT NULL,
                problem_type TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                comment TEXT,
                resolved_at TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_user(self, user_id: int, username: Optional[str] = None, 
                 first_name: Optional[str] = None, last_name: Optional[str] = None):
        """Добавление или обновление пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name))
        conn.commit()
        conn.close()
    
    def create_ticket(self, user_id: int, message_text: str, 
                     problem_category: Optional[str] = None,
                     ai_solution: Optional[str] = None) -> int:
        """Создание нового обращения"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO tickets (user_id, message_text, problem_category, ai_solution)
            VALUES (?, ?, ?, ?)
        ''', (user_id, message_text, problem_category, ai_solution))
        ticket_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return ticket_id
    
    def update_ticket(self, ticket_id: int, status: Optional[str] = None,
                     assigned_engineer: Optional[str] = None,
                     resolved_at: Optional[datetime] = None):
        """Обновление обращения"""
        conn = self.get_connection()
        cursor = conn.cursor()
        updates = []
        params = []
        
        if status:
            updates.append("status = ?")
            params.append(status)
        if assigned_engineer:
            updates.append("assigned_engineer = ?")
            params.append(assigned_engineer)
        if resolved_at:
            updates.append("resolved_at = ?")
            params.append(resolved_at)
        
        if updates:
            params.append(ticket_id)
            cursor.execute(f'''
                UPDATE tickets SET {', '.join(updates)}
                WHERE id = ?
            ''', params)
            conn.commit()
        conn.close()
    
    def add_conversation(self, user_id: int, message_text: str, 
                        ticket_id: Optional[int] = None, is_user_message: bool = True):
        """Добавление сообщения в историю диалога"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO conversations (user_id, ticket_id, message_text, is_user_message)
            VALUES (?, ?, ?, ?)
        ''', (user_id, ticket_id, message_text, 1 if is_user_message else 0))
        conn.commit()
        conn.close()
    
    def get_user_conversation_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Получение истории диалога пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT message_text, is_user_message, created_at
            FROM conversations
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (user_id, limit))
        results = cursor.fetchall()
        conn.close()
        return [
            {
                'message': row[0],
                'is_user': bool(row[1]),
                'created_at': row[2]
            }
            for row in results
        ]
    
    def get_user_tickets(self, user_id: int) -> List[Dict]:
        """Получение всех обращений пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, message_text, problem_category, status, created_at
            FROM tickets
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        results = cursor.fetchall()
        conn.close()
        return [
            {
                'id': row[0],
                'message': row[1],
                'category': row[2],
                'status': row[3],
                'created_at': row[4]
            }
            for row in results
        ]
    
    def add_engineer(self, name: str, specialization: str, telegram_id: Optional[int] = None):
        """Добавление инженера"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO engineers (name, specialization, telegram_id)
            VALUES (?, ?, ?)
        ''', (name, specialization, telegram_id))
        conn.commit()
        conn.close()
    
    def get_engineers_by_specialization(self, specialization: str) -> List[Dict]:
        """Получение инженеров по специализации"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, telegram_id
            FROM engineers
            WHERE specialization = ? AND is_active = 1
        ''', (specialization,))
        results = cursor.fetchall()
        conn.close()
        return [
            {
                'id': row[0],
                'name': row[1],
                'telegram_id': row[2]
            }
            for row in results
        ]
    
    # Методы для работы с клиентами
    def get_client_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """Получение клиента по telegram_id"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, full_name, phone_number, password, telegram_id, city, street, house_number, contract_number
            FROM clients
            WHERE telegram_id = ?
        ''', (telegram_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                'id': row[0],
                'full_name': row[1],
                'phone_number': row[2],
                'password': row[3],
                'telegram_id': row[4],
                'city': row[5],
                'street': row[6],
                'house_number': row[7],
                'contract_number': row[8]
            }
        return None
    
    def get_client_by_contract_number(self, contract_number: str) -> Optional[Dict]:
        """Получение клиента по номеру договора (лицевому счету)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        # Убираем пробелы и приводим к верхнему регистру для поиска
        contract_clean = contract_number.strip().upper()
        cursor.execute('''
            SELECT id, full_name, phone_number, password, telegram_id, city, street, house_number, contract_number
            FROM clients
            WHERE UPPER(REPLACE(contract_number, ' ', '')) = UPPER(REPLACE(?, ' ', ''))
        ''', (contract_clean,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                'id': row[0],
                'full_name': row[1],
                'phone_number': row[2],
                'password': row[3],
                'telegram_id': row[4],
                'city': row[5],
                'street': row[6],
                'house_number': row[7],
                'contract_number': row[8]
            }
        return None
    
    def get_client_by_phone(self, phone_number: str) -> Optional[Dict]:
        """Получение клиента по номеру телефона"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, full_name, phone_number, password, telegram_id, city, street, house_number, contract_number
            FROM clients
            WHERE phone_number = ?
        ''', (phone_number,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                'id': row[0],
                'full_name': row[1],
                'phone_number': row[2],
                'password': row[3],
                'telegram_id': row[4],
                'city': row[5],
                'street': row[6],
                'house_number': row[7],
                'contract_number': row[8]
            }
        return None
    
    def hash_password(self, password: str) -> str:
        """Хэширование пароля"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Проверка пароля"""
        return self.hash_password(password) == password_hash
    
    def update_client_password(self, client_id: int, password: str):
        """Обновление пароля клиента"""
        password_hash = self.hash_password(password)
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE clients
            SET password = ?
            WHERE id = ?
        ''', (password_hash, client_id))
        conn.commit()
        conn.close()
    
    def link_telegram_to_client(self, telegram_id: int, contract_number: str) -> bool:
        """Привязка telegram_id к клиенту по номеру договора"""
        client = self.get_client_by_contract_number(contract_number)
        if client:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE clients
                SET telegram_id = ?
                WHERE id = ?
            ''', (telegram_id, client['id']))
            conn.commit()
            conn.close()
            return True
        return False
    
    def add_client(self, full_name: str, phone_number: str, telegram_id: Optional[int],
                   city: str, street: str, house_number: str, contract_number: str, password: Optional[str] = None) -> int:
        """Добавление клиента"""
        password_hash = self.hash_password(password) if password else None
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO clients (full_name, phone_number, telegram_id, city, street, house_number, contract_number, password)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (full_name, phone_number, telegram_id, city, street, house_number, contract_number, password_hash))
        client_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return client_id
    
    # Методы для работы с сегментами сети
    def get_segment_by_address(self, city: str, street: str, house_number: str) -> Optional[Dict]:
        """Получение сегмента сети по адресу"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            house_num = int(house_number)
        except ValueError:
            house_num = 0
        
        cursor.execute('''
            SELECT id, city, district, street, house_from, house_to, node_name
            FROM network_segments
            WHERE city = ? AND street = ? AND house_from <= ? AND house_to >= ?
        ''', (city, street, house_num, house_num))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                'id': row[0],
                'city': row[1],
                'district': row[2],
                'street': row[3],
                'house_from': row[4],
                'house_to': row[5],
                'node_name': row[6]
            }
        return None
    
    def add_network_segment(self, city: str, district: str, street: str,
                           house_from: int, house_to: int, node_name: str) -> int:
        """Добавление сегмента сети"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO network_segments (city, district, street, house_from, house_to, node_name)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (city, district, street, house_from, house_to, node_name))
        segment_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return segment_id
    
    # Методы для работы с авариями
    def get_active_outage_by_segment(self, segment_id: int) -> Optional[Dict]:
        """Получение активной аварии по сегменту"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, segment_id, started_at, estimated_end, actual_end, status, reason
            FROM outages
            WHERE segment_id = ? AND status = 'active'
            ORDER BY started_at DESC
            LIMIT 1
        ''', (segment_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                'id': row[0],
                'segment_id': row[1],
                'started_at': row[2],
                'estimated_end': row[3],
                'actual_end': row[4],
                'status': row[5],
                'reason': row[6]
            }
        return None
    
    def add_outage(self, segment_id: int, started_at: datetime, estimated_end: Optional[datetime],
                   reason: str, status: str = 'active') -> int:
        """Добавление аварии"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO outages (segment_id, started_at, estimated_end, reason, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (segment_id, started_at, estimated_end, reason, status))
        outage_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return outage_id
    
    # Методы для работы с услугами
    def get_client_services(self, client_id: int) -> List[Dict]:
        """Получение услуг клиента"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, client_id, tariff_name, is_active, is_blocked, debt_amount
            FROM services
            WHERE client_id = ?
        ''', (client_id,))
        results = cursor.fetchall()
        conn.close()
        return [
            {
                'id': row[0],
                'client_id': row[1],
                'tariff_name': row[2],
                'is_active': bool(row[3]),
                'is_blocked': bool(row[4]),
                'debt_amount': row[5]
            }
            for row in results
        ]
    
    def add_service(self, client_id: int, tariff_name: str, is_active: bool = True,
                   is_blocked: bool = False, debt_amount: float = 0) -> int:
        """Добавление услуги"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO services (client_id, tariff_name, is_active, is_blocked, debt_amount)
            VALUES (?, ?, ?, ?, ?)
        ''', (client_id, tariff_name, 1 if is_active else 0, 1 if is_blocked else 0, debt_amount))
        service_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return service_id
    
    # Методы для работы с заявками
    def create_request(self, client_id: int, channel: str, problem_type: str,
                      status: str = 'open', comment: Optional[str] = None) -> int:
        """Создание заявки"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO requests (client_id, channel, problem_type, status, comment)
            VALUES (?, ?, ?, ?, ?)
        ''', (client_id, channel, problem_type, status, comment))
        request_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return request_id
    
    def get_client_requests(self, client_id: int) -> List[Dict]:
        """Получение заявок клиента"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, client_id, created_at, channel, problem_type, status, comment, resolved_at
            FROM requests
            WHERE client_id = ?
            ORDER BY created_at DESC
        ''', (client_id,))
        results = cursor.fetchall()
        conn.close()
        return [
            {
                'id': row[0],
                'client_id': row[1],
                'created_at': row[2],
                'channel': row[3],
                'problem_type': row[4],
                'status': row[5],
                'comment': row[6],
                'resolved_at': row[7]
            }
            for row in results
        ]
    
    def update_request(self, request_id: int, status: Optional[str] = None,
                      comment: Optional[str] = None, resolved_at: Optional[datetime] = None):
        """Обновление заявки"""
        conn = self.get_connection()
        cursor = conn.cursor()
        updates = []
        params = []
        
        if status:
            updates.append("status = ?")
            params.append(status)
        if comment:
            updates.append("comment = ?")
            params.append(comment)
        if resolved_at:
            updates.append("resolved_at = ?")
            params.append(resolved_at)
        
        if updates:
            params.append(request_id)
            cursor.execute(f'''
                UPDATE requests SET {', '.join(updates)}
                WHERE id = ?
            ''', params)
            conn.commit()
        conn.close()


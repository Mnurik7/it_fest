from datetime import datetime, UTC
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Enum, ForeignKey
from werkzeug.security import generate_password_hash, check_password_hash
import enum

# Функция для получения текущего времени в UTC
def utc_now():
    return datetime.now(UTC)

db = SQLAlchemy()


class TicketStatus(enum.Enum):
    OPEN = "OPEN"
    AUTO_CLOSED = "AUTO_CLOSED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


class TicketPriority(enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TicketType(enum.Enum):
    INCIDENT = "INCIDENT"
    REQUEST = "REQUEST"
    QUESTION = "QUESTION"
    COMPLAINT = "COMPLAINT"


class Ticket(db.Model):
    __tablename__ = 'tickets'

    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    source = Column(String(50), nullable=False)  # portal, chat, email, phone
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # пользователь, создавший тикет
    
    # Связь с пользователем
    user = db.relationship('User', backref='tickets', lazy=True)
    
    # AI-анализ
    language = Column(String(10))  # ru, kk
    summary = Column(Text)
    category = Column(String(100))
    priority = Column(String(20))  # LOW, MEDIUM, HIGH, CRITICAL
    type = Column(String(20))  # INCIDENT, REQUEST, QUESTION, COMPLAINT
    department = Column(String(100))
    is_auto_closed = Column(Boolean, default=False)
    auto_response = Column(Text)  # предложенный AI ответ
    
    # Статус и управление
    status = Column(String(20), default='OPEN')
    is_urgent = Column(Boolean, default=False)
    
    # Ответ оператора
    last_response = Column(Text)
    
    # Метаданные
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    ai_raw_response = Column(Text)  # сырой JSON ответ от Gemini
    
    def to_dict(self):
        """Преобразование модели в словарь для JSON API"""
        return {
            'id': self.id,
            'text': self.text,
            'source': self.source,
            'language': self.language,
            'summary': self.summary,
            'category': self.category,
            'priority': self.priority,
            'type': self.type,
            'department': self.department,
            'is_auto_closed': self.is_auto_closed,
            'auto_response': self.auto_response,
            'status': self.status,
            'is_urgent': self.is_urgent,
            'last_response': self.last_response,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class User(db.Model):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default='user')  # admin, operator, specialist, user
    department = Column(String(100))  # отдел оператора или специалиста
    avatar_url = Column(String(255), nullable=True)  # URL аватара/фото профиля
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, nullable=True)  # последняя активность для отслеживания онлайн статуса
    is_online_manual = Column(Boolean, default=True)  # ручное управление онлайн статусом (для операторов)
    is_active = Column(Boolean, default=True)

    def set_password(self, password):
        """Установка пароля (хеширование)"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Проверка пароля"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Преобразование модели в словарь (без пароля)"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'department': self.department,
            'avatar_url': self.avatar_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def is_admin(self):
        """Проверка, является ли пользователь администратором"""
        return self.role == 'admin'

    def is_operator(self):
        """Проверка, является ли пользователь оператором"""
        return self.role in ['admin', 'operator']
    
    def is_specialist(self):
        """Проверка, является ли пользователь специалистом"""
        return self.role == 'specialist'
    
    def is_staff(self):
        """Проверка, является ли пользователь сотрудником (оператор, специалист или админ)"""
        return self.role in ['admin', 'operator', 'specialist']


class Chat(db.Model):
    """Модель чата между клиентом и оператором"""
    __tablename__ = 'chats'
    
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # клиент
    operator_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # оператор (null пока не принят)
    status = Column(String(20), default='WAITING')  # WAITING, ACTIVE, CLOSED
    rating = Column(Integer, nullable=True)  # Оценка от 1 до 5 (null если не оценено)
    closed_at = Column(DateTime, nullable=True)  # Дата закрытия чата
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    # Связи
    ticket = db.relationship('Ticket', backref='chat', lazy=True)
    user = db.relationship('User', foreign_keys=[user_id], backref='user_chats', lazy=True)
    operator = db.relationship('User', foreign_keys=[operator_id], backref='operator_chats', lazy=True)
    messages = db.relationship('ChatMessage', backref='chat', lazy=True, order_by='ChatMessage.created_at')
    
    def to_dict(self):
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'user_id': self.user_id,
            'operator_id': self.operator_id,
            'status': self.status,
            'rating': self.rating,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'user': self.user.to_dict() if self.user else None,
            'operator': self.operator.to_dict() if self.operator else None,
            'ticket': self.ticket.to_dict() if self.ticket else None,
        }


class ChatMessage(db.Model):
    """Модель сообщения в чате"""
    __tablename__ = 'chat_messages'
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, ForeignKey('chats.id'), nullable=False)
    sender_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    message = Column(Text, nullable=False)
    is_from_user = Column(Boolean, default=True)  # True если от клиента, False если от оператора
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Кеңейтілген функциялар үшін
    message_type = Column(String(20), default='text')  # text, file, voice, image
    attachment_url = Column(String(500), nullable=True)  # Файл URL
    attachment_filename = Column(String(255), nullable=True)  # Оригиналды атауы
    attachment_size = Column(Integer, nullable=True)  # Файл өлшемі (байт)
    is_formatted = Column(Boolean, default=False)  # Markdown форматирование бар ма?
    
    # Связи
    sender = db.relationship('User', backref='messages', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'chat_id': self.chat_id,
            'sender_id': self.sender_id,
            'message': self.message,
            'is_from_user': self.is_from_user,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'sender': self.sender.to_dict() if self.sender else None,
            'message_type': self.message_type or 'text',
            'attachment_url': self.attachment_url,
            'attachment_filename': self.attachment_filename,
            'attachment_size': self.attachment_size,
            'is_formatted': self.is_formatted or False,
        }


class Dispatch(db.Model):
    """Модель отправки специалиста к клиенту"""
    __tablename__ = 'dispatches'
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, ForeignKey('chats.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # клиент
    specialist_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # специалист
    operator_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # оператор, отправивший специалиста
    
    # Адрес клиента
    client_address = Column(Text, nullable=True)
    client_latitude = Column(String(50), nullable=True)
    client_longitude = Column(String(50), nullable=True)
    
    # Адрес специалиста (текущее местоположение)
    specialist_latitude = Column(String(50), nullable=True)
    specialist_longitude = Column(String(50), nullable=True)
    
    # Статус маршрута
    status = Column(String(20), default='PENDING')  # PENDING, ACCEPTED, IN_ROUTE, ARRIVED, COMPLETED, CANCELLED
    
    # 2GIS маршрут данные
    route_data = Column(Text, nullable=True)  # JSON с данными маршрута от 2GIS
    
    # Метаданные
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    arrived_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Связи
    chat = db.relationship('Chat', backref='dispatches', lazy=True)
    user = db.relationship('User', foreign_keys=[user_id], backref='client_dispatches', lazy=True)
    specialist = db.relationship('User', foreign_keys=[specialist_id], backref='specialist_dispatches', lazy=True)
    operator = db.relationship('User', foreign_keys=[operator_id], backref='operator_dispatches', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'chat_id': self.chat_id,
            'user_id': self.user_id,
            'specialist_id': self.specialist_id,
            'operator_id': self.operator_id,
            'client_address': self.client_address,
            'client_latitude': self.client_latitude,
            'client_longitude': self.client_longitude,
            'specialist_latitude': self.specialist_latitude,
            'specialist_longitude': self.specialist_longitude,
            'status': self.status,
            'route_data': self.route_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'arrived_at': self.arrived_at.isoformat() if self.arrived_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'user': self.user.to_dict() if self.user else None,
            'specialist': self.specialist.to_dict() if self.specialist else None,
            'operator': self.operator.to_dict() if self.operator else None,
        }

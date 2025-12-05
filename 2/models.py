from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Enum, ForeignKey
from werkzeug.security import generate_password_hash, check_password_hash
import enum

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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
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
    created_at = Column(DateTime, default=datetime.utcnow)
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


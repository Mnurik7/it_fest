import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime, UTC
from models import db, Ticket, User, Chat, ChatMessage, Dispatch
from ai_client import analyze_ticket
import logging
from dotenv import load_dotenv
from functools import wraps
import uuid
from werkzeug.utils import secure_filename
import requests

# Загрузка переменных окружения из .env
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Конфигурация из переменных окружения
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///helpdesk.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads/avatars'
app.config['TICKET_FILES_FOLDER'] = 'static/uploads/tickets'
app.config['CHAT_FILES_FOLDER'] = 'static/uploads/chat'
app.config['VOICE_MESSAGES_FOLDER'] = 'static/uploads/voice_messages'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['ALLOWED_TICKET_FILE_EXTENSIONS'] = {
    'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'doc', 'docx', 
    'xls', 'xlsx', 'txt', 'csv', 'zip', 'rar', '7z'
}
app.config['ALLOWED_CHAT_FILE_EXTENSIONS'] = {
    'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'doc', 'docx', 
    'xls', 'xlsx', 'txt', 'csv', 'zip', 'rar', '7z', 'mp3', 'wav', 'ogg', 'm4a'
}
app.config['ALLOWED_VOICE_EXTENSIONS'] = {'mp3', 'wav', 'ogg', 'm4a', 'webm'}
app.config['TGIS_API_KEY'] = os.getenv('TGIS_API_KEY', '9a1cdbf5-0328-4158-80ad-0e742c1f2b67')
# Координаты офиса (по умолчанию Алматы)
app.config['OFFICE_LATITUDE'] = os.getenv('OFFICE_LATITUDE', '51.1694')
app.config['OFFICE_LONGITUDE'] = os.getenv('OFFICE_LONGITUDE', '71.4491')

# Создаем папки для загрузки файлов
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TICKET_FILES_FOLDER'], exist_ok=True)
os.makedirs(app.config['CHAT_FILES_FOLDER'], exist_ok=True)
os.makedirs(app.config['VOICE_MESSAGES_FOLDER'], exist_ok=True)

# Инициализация БД
db.init_app(app)

# Инициализация SocketIO для WebRTC signaling
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Хранилище активных звонков {call_id: {caller_id, callee_id, status}}
active_calls = {}

# Создание таблиц при первом запуске
with app.app_context():
    try:
        # Проверяем структуру таблицы tickets - есть ли колонка user_id
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()
        tickets_columns = [col['name'] for col in inspector.get_columns('tickets')] if 'tickets' in table_names else []
        
        # Проверяем наличие таблиц чатов
        has_chats_table = 'chats' in table_names
        has_chat_messages_table = 'chat_messages' in table_names
        has_dispatches_table = 'dispatches' in table_names
        
        # Проверяем наличие новых полей в таблице chats
        chats_columns = [col['name'] for col in inspector.get_columns('chats')] if has_chats_table else []
        
        # Проверяем наличие поля last_activity в таблице users
        users_columns = [col['name'] for col in inspector.get_columns('users')] if 'users' in table_names else []
        
        # Проверяем наличие новых полей в chat_messages
        chat_messages_columns = [col['name'] for col in inspector.get_columns('chat_messages')] if has_chat_messages_table else []
        
        needs_recreate = False
        reason = ""
        
        if 'tickets' in table_names and 'user_id' not in tickets_columns:
            needs_recreate = True
            reason = "missing user_id column in tickets"
        elif not has_chats_table or not has_chat_messages_table:
            needs_recreate = True
            reason = "missing chat tables"
        elif has_chats_table and ('rating' not in chats_columns or 'closed_at' not in chats_columns):
            needs_recreate = True
            reason = "missing rating or closed_at columns in chats"
        elif 'users' in table_names and ('last_activity' not in users_columns or 'is_online_manual' not in users_columns or 'avatar_url' not in users_columns):
            needs_recreate = True
            reason = "missing last_activity, is_online_manual or avatar_url column in users"
        elif not has_dispatches_table:
            needs_recreate = True
            reason = "missing dispatches table"
        elif has_chat_messages_table and ('message_type' not in chat_messages_columns or 'attachment_url' not in chat_messages_columns):
            needs_recreate = True
            reason = "missing message_type or attachment_url columns in chat_messages"
        
        if needs_recreate:
            logger.info(f"Database schema outdated ({reason}). Recreating database...")
            db.drop_all()
            db.create_all()
            logger.info("Database tables recreated with new schema")
        elif 'tickets' not in table_names:
            # Если таблиц нет вообще, создаём их
            logger.info("Creating database tables...")
            db.create_all()
            logger.info("Database tables created")
        else:
            logger.info("Database schema is up to date")
    except Exception as e:
        # Если что-то пошло не так, пересоздаём БД
        logger.warning(f"Error checking database schema: {e}. Recreating database...")
        try:
            db.drop_all()
            db.create_all()
            logger.info("Database tables recreated")
        except Exception as e2:
            logger.error(f"Error recreating database: {e2}")
    
    # Создаём первого администратора, если его нет
    try:
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@helpdesk.local', role='admin')
            admin.set_password('admin123')  # Измените пароль в продакшене!
            db.session.add(admin)
            db.session.commit()
            logger.info("Default admin user created (username: admin, password: admin123)")
    except Exception as e:
        logger.warning(f"Could not create admin user: {e}. Database may need to be recreated.")


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ АВТОРИЗАЦИИ ==========

def get_current_user():
    """Получение текущего пользователя из сессии"""
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None


def login_required(f):
    """Декоратор для защиты роутов (требует авторизации)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Проверяем, является ли запрос JSON (по заголовку Accept или Content-Type)
            is_json_request = (
                request.is_json or 
                request.headers.get('Content-Type', '').startswith('application/json') or
                request.headers.get('Accept', '').startswith('application/json')
            )
            if is_json_request:
                return jsonify({'error': 'Authentication required', 'success': False}), 401
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Декоратор для защиты роутов (требует роль администратора)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('login'))
        
        user = get_current_user()
        if not user or not user.is_admin():
            if request.is_json:
                return jsonify({'error': 'Admin access required'}), 403
            flash('Доступ запрещён. Требуются права администратора', 'error')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function


def operator_required(f):
    """Декоратор для защиты роутов (требует роль оператора или администратора)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('login'))
        
        user = get_current_user()
        if not user or not user.is_operator():
            if request.is_json:
                return jsonify({'error': 'Operator access required'}), 403
            flash('Доступ запрещён. Требуются права оператора', 'error')
            return redirect(url_for('index'))
        
        # Обновляем активность оператора
        if user.role == 'operator':
            user.last_activity = datetime.now(UTC)
            db.session.commit()
        
        return f(*args, **kwargs)
    return decorated_function


def specialist_required(f):
    """Декоратор для защиты роутов (требует роль специалиста)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('login'))
        
        user = get_current_user()
        if not user or not user.is_specialist():
            if request.is_json:
                return jsonify({'error': 'Specialist access required'}), 403
            flash('Доступ запрещён. Требуются права специалиста', 'error')
            return redirect(url_for('index'))
        
        # Обновляем активность специалиста
        if user.role == 'specialist':
            user.last_activity = datetime.now(UTC)
            db.session.commit()
        
        return f(*args, **kwargs)
    return decorated_function


def is_operator_online(operator):
    """Проверка, онлайн ли оператор (приоритет ручному статусу)"""
    # Если оператор вручную установил статус, используем его
    if hasattr(operator, 'is_online_manual'):
        if operator.is_online_manual is False:
            return False
        # Если статус онлайн вручную, оператор онлайн (независимо от last_activity)
        if operator.is_online_manual is True:
            return True
    
    # Если ручной статус не установлен, проверяем автоматический статус по активности
    if not operator.last_activity:
        return False
    from datetime import timedelta
    try:
        time_diff = datetime.now(UTC) - operator.last_activity
        return time_diff < timedelta(minutes=5)
    except Exception as e:
        logger.warning(f"Error checking operator online status: {e}")
        return False


@app.route('/')
def index():
    """Главная страница - перенаправление на вход или форму создания обращения"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Если пользователь авторизован, показываем форму создания обращения
    return render_template('index.html')


@app.route('/create')
@login_required
def create_ticket_page():
    """Страница создания обращения (для авторизованных пользователей)"""
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Заполните все поля', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash(f'Добро пожаловать, {user.username}!', 'success')
            
            # Перенаправляем в зависимости от роли
            if user.role == 'admin':
                return redirect(url_for('admin'))
            elif user.role == 'operator':
                return redirect(url_for('operator_dashboard'))
            elif user.role == 'specialist':
                return redirect(url_for('specialist_dashboard'))
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Страница регистрации для обычных пользователей"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        # Валидация
        if not username or not email or not password:
            flash('Заполните все поля', 'error')
            return render_template('register.html')
        
        if password != password_confirm:
            flash('Пароли не совпадают', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Пароль должен содержать минимум 6 символов', 'error')
            return render_template('register.html')
        
        # Проверка на существование пользователя
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует', 'error')
            return render_template('register.html')
        
        # Создание нового пользователя
        user = User(username=username, email=email, role='user')
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('Регистрация успешна! Теперь вы можете войти', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating user: {e}")
            flash('Ошибка при регистрации', 'error')
    
    return render_template('register.html')


@app.route('/register-operator', methods=['GET', 'POST'])
def register_operator():
    """Страница регистрации для операторов"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        department = request.form.get('department', '').strip()
        
        # Валидация
        if not username or not email or not password or not department:
            flash('Заполните все поля', 'error')
            return render_template('register_operator.html')
        
        if password != password_confirm:
            flash('Пароли не совпадают', 'error')
            return render_template('register_operator.html')
        
        if len(password) < 6:
            flash('Пароль должен содержать минимум 6 символов', 'error')
            return render_template('register_operator.html')
        
        # Проверка на существование пользователя
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует', 'error')
            return render_template('register_operator.html')
        
        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует', 'error')
            return render_template('register_operator.html')
        
        # Создание нового оператора
        user = User(username=username, email=email, role='operator', department=department)
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('Регистрация оператора успешна! Теперь вы можете войти', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating operator: {e}")
            flash('Ошибка при регистрации', 'error')
    
    return render_template('register_operator.html')


@app.route('/register-specialist', methods=['GET', 'POST'])
def register_specialist():
    """Страница регистрации для специалистов"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        department = request.form.get('department', '').strip()
        
        # Валидация
        if not username or not email or not password or not department:
            flash('Заполните все поля', 'error')
            return render_template('register_specialist.html')
        
        if password != password_confirm:
            flash('Пароли не совпадают', 'error')
            return render_template('register_specialist.html')
        
        if len(password) < 6:
            flash('Пароль должен содержать минимум 6 символов', 'error')
            return render_template('register_specialist.html')
        
        # Проверка на существование пользователя
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует', 'error')
            return render_template('register_specialist.html')
        
        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует', 'error')
            return render_template('register_specialist.html')
        
        # Создание нового специалиста
        user = User(username=username, email=email, role='specialist', department=department)
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('Регистрация специалиста успешна! Теперь вы можете войти', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating specialist: {e}")
            flash('Ошибка при регистрации', 'error')
    
    return render_template('register_specialist.html')


@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))


@app.route('/profile')
@login_required
def profile():
    """Страница профиля пользователя"""
    user = get_current_user()
    return render_template('user_profile.html', user=user)


@app.route('/admin')
@admin_required
def admin():
    """Страница администратора - дашборд с тикетами"""
    return render_template('admin.html')


@app.route('/admin/operator/<int:operator_id>')
@admin_required
def operator_detail(operator_id):
    """Детальная страница оператора"""
    try:
        operator = User.query.get_or_404(operator_id)
        
        if operator.role != 'operator':
            flash('Пользователь не является оператором', 'error')
            return redirect(url_for('admin'))
        
        # Статистика по чатам оператора
        total_chats = Chat.query.filter(Chat.operator_id == operator.id).count()
        active_chats = Chat.query.filter(Chat.operator_id == operator.id, Chat.status == 'ACTIVE').count()
        closed_chats = Chat.query.filter(Chat.operator_id == operator.id, Chat.status == 'CLOSED').count()
        waiting_chats = Chat.query.filter(Chat.operator_id == operator.id, Chat.status == 'WAITING').count()
        
        # Средняя оценка
        rated_chats = Chat.query.filter(
            Chat.operator_id == operator.id,
            Chat.rating.isnot(None)
        ).all()
        
        avg_rating = 0
        if rated_chats:
            total_rating = sum(chat.rating for chat in rated_chats if chat.rating)
            avg_rating = round(total_rating / len(rated_chats), 2)
        
        # Статистика по тикетам отдела оператора
        tickets_in_dept = Ticket.query.filter(Ticket.department == operator.department).count() if operator.department else 0
        resolved_tickets = Ticket.query.filter(
            Ticket.department == operator.department,
            Ticket.status.in_(['RESOLVED', 'AUTO_CLOSED'])
        ).count() if operator.department else 0
        
        # Последняя активность
        last_closed_chat = Chat.query.filter(
            Chat.operator_id == operator.id,
            Chat.status == 'CLOSED'
        ).order_by(Chat.closed_at.desc()).first()
        
        # Список всех чатов оператора
        all_chats = Chat.query.filter(Chat.operator_id == operator.id).order_by(Chat.created_at.desc()).limit(20).all()
        
        return render_template('operator_detail.html',
            operator=operator,
            total_chats=total_chats,
            active_chats=active_chats,
            closed_chats=closed_chats,
            waiting_chats=waiting_chats,
            avg_rating=avg_rating,
            total_ratings=len(rated_chats),
            tickets_in_department=tickets_in_dept,
            resolved_tickets=resolved_tickets,
            last_closed_chat=last_closed_chat,
            all_chats=all_chats
        )
    except Exception as e:
        logger.error(f"Error loading operator detail: {e}", exc_info=True)
        flash('Ошибка загрузки информации об операторе', 'error')
        return redirect(url_for('admin'))


@app.route('/admin/specialist/<int:specialist_id>')
@admin_required
def specialist_detail(specialist_id):
    """Детальная страница специалиста"""
    try:
        specialist = User.query.get_or_404(specialist_id)
        
        if specialist.role != 'specialist':
            flash('Пользователь не является специалистом', 'error')
            return redirect(url_for('admin'))
        
        # Проверяем онлайн статус
        is_online = is_operator_online(specialist)
        
        # Статистика по тикетам отдела специалиста
        tickets_in_dept = Ticket.query.filter(Ticket.department == specialist.department).count() if specialist.department else 0
        resolved_tickets = Ticket.query.filter(
            Ticket.department == specialist.department,
            Ticket.status.in_(['RESOLVED', 'AUTO_CLOSED'])
        ).count() if specialist.department else 0
        in_progress_tickets = Ticket.query.filter(
            Ticket.department == specialist.department,
            Ticket.status == 'IN_PROGRESS'
        ).count() if specialist.department else 0
        open_tickets = Ticket.query.filter(
            Ticket.department == specialist.department,
            Ticket.status == 'OPEN'
        ).count() if specialist.department else 0
        
        # Средняя оценка (пока 0, можно добавить позже)
        avg_rating = 0.0
        total_ratings = 0
        
        # Последние обработанные тикеты
        recent_tickets = Ticket.query.filter(
            Ticket.department == specialist.department
        ).order_by(Ticket.updated_at.desc()).limit(20).all() if specialist.department else []
        
        return render_template('specialist_detail.html',
            specialist=specialist,
            is_online=is_online,
            tickets_in_department=tickets_in_dept,
            resolved_tickets=resolved_tickets,
            in_progress_tickets=in_progress_tickets,
            open_tickets=open_tickets,
            avg_rating=avg_rating,
            total_ratings=total_ratings,
            recent_tickets=recent_tickets
        )
    except Exception as e:
        logger.error(f"Error loading specialist detail: {e}", exc_info=True)
        flash('Ошибка загрузки информации о специалисте', 'error')
        return redirect(url_for('admin'))


@app.route('/chat/<int:chat_id>')
@login_required
def chat_page(chat_id):
    """Страница чата"""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    chat = Chat.query.get_or_404(chat_id)
    
    # Проверяем права доступа
    if user.role == 'user' and chat.user_id != user.id:
        flash('Доступ запрещён', 'error')
        return redirect(url_for('index'))
    elif user.role in ['operator', 'admin']:
        if chat.operator_id and chat.operator_id != user.id:
            flash('Этот чат уже принят другим оператором', 'error')
            return redirect(url_for('operator_dashboard'))
    
    return render_template('chat.html', chat=chat, user=user)


@app.route('/operator')
@operator_required
def operator_dashboard():
    """Страница оператора - дашборд с тикетами его отдела"""
    user = get_current_user()
    return render_template('operator.html', user=user, user_department=user.department if user else None, config=app.config)


@app.route('/specialist')
@specialist_required
def specialist_dashboard():
    """Страница специалиста - дашборд с тикетами его отдела"""
    user = get_current_user()
    return render_template('specialist.html', user=user, user_department=user.department if user else None)


def allowed_file(filename):
    """Проверка расширения файла"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/api/upload-avatar', methods=['POST'])
@login_required
def upload_avatar():
    """Загрузка аватара пользователя"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        if 'avatar' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['avatar']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            # Генерируем уникальное имя файла
            # Извлекаем расширение из оригинального имени файла
            original_filename = file.filename
            if '.' not in original_filename:
                return jsonify({'error': 'File must have an extension'}), 400
            
            ext = original_filename.rsplit('.', 1)[1].lower()
            if ext not in app.config['ALLOWED_EXTENSIONS']:
                return jsonify({'error': 'Invalid file type. Allowed: png, jpg, jpeg, gif, webp'}), 400
            
            new_filename = f"{user.id}_{uuid.uuid4().hex[:8]}.{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
            
            # Сохраняем файл
            file.save(filepath)
            
            # Обновляем URL аватара в БД
            avatar_url = f"/static/uploads/avatars/{new_filename}"
            user.avatar_url = avatar_url
            db.session.commit()
            
            return jsonify({
                'success': True,
                'avatar_url': avatar_url
            }), 200
        else:
            return jsonify({'error': 'Invalid file type. Allowed: png, jpg, jpeg, gif, webp'}), 400
            
    except Exception as e:
        logger.error(f"Error uploading avatar: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/static/uploads/avatars/<filename>')
def uploaded_avatar(filename):
    """Отдача загруженных аватаров"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/static/uploads/tickets/<filename>')
@login_required
def uploaded_ticket_file(filename):
    """Отдача загруженных файлов тикетов"""
    return send_from_directory(app.config['TICKET_FILES_FOLDER'], filename)


@app.route('/api/chats/<int:chat_id>/upload-file', methods=['POST'])
@login_required
def upload_chat_file(chat_id):
    """Загрузка файла в чат"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        chat = Chat.query.get_or_404(chat_id)
        
        # Проверяем права доступа
        if user.role == 'user' and chat.user_id != user.id:
            return jsonify({'error': 'Access denied'}), 403
        elif user.role in ['operator', 'admin']:
            if chat.status == 'ACTIVE' and chat.operator_id and chat.operator_id != user.id:
                if user.role == 'operator':
                    return jsonify({'error': 'Access denied'}), 403
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Проверяем расширение
        if '.' not in file.filename:
            return jsonify({'error': 'File must have an extension'}), 400
        
        ext = file.filename.rsplit('.', 1)[1].lower()
        
        # Определяем тип файла
        message_type = 'file'
        if ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
            message_type = 'image'
        elif ext in app.config['ALLOWED_VOICE_EXTENSIONS']:
            message_type = 'voice'
        elif ext not in app.config['ALLOWED_CHAT_FILE_EXTENSIONS']:
            return jsonify({'error': f'File type not allowed. Allowed: {", ".join(app.config["ALLOWED_CHAT_FILE_EXTENSIONS"])}'}), 400
        
        # Генерируем уникальное имя файла
        filename = secure_filename(file.filename)
        new_filename = f"chat_{chat_id}_{uuid.uuid4().hex[:8]}.{ext}"
        
        # Выбираем папку в зависимости от типа
        if message_type == 'voice':
            folder = app.config['VOICE_MESSAGES_FOLDER']
        else:
            folder = app.config['CHAT_FILES_FOLDER']
        
        filepath = os.path.join(folder, new_filename)
        file.save(filepath)
        
        file_size = os.path.getsize(filepath)
        
        # Формируем URL
        if message_type == 'voice':
            file_url = f"/static/uploads/voice_messages/{new_filename}"
        else:
            file_url = f"/static/uploads/chat/{new_filename}"
        
        return jsonify({
            'success': True,
            'file_url': file_url,
            'filename': filename,
            'file_size': file_size,
            'message_type': message_type
        }), 200
        
    except Exception as e:
        logger.error(f"Error uploading chat file: {e}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/static/uploads/chat/<filename>')
@login_required
def uploaded_chat_file(filename):
    """Отдача загруженных файлов чата"""
    return send_from_directory(app.config['CHAT_FILES_FOLDER'], filename)


@app.route('/static/uploads/voice_messages/<filename>')
@login_required
def uploaded_voice_message(filename):
    """Отдача загруженных voice messages"""
    return send_from_directory(app.config['VOICE_MESSAGES_FOLDER'], filename)


@app.route('/api/user-info', methods=['GET'])
@login_required
def get_current_user_info():
    """Получение информации о текущем пользователе"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        }), 200
    except Exception as e:
        logger.error(f"Error in get_current_user_info: {e}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Обновление профиля пользователя"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        data = request.get_json()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        
        if not username or not email:
            return jsonify({'error': 'Username and email are required'}), 400
        
        # Проверка уникальности username (если изменился)
        if username != user.username:
            existing_user = User.query.filter_by(username=username).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({'error': 'Username already exists'}), 400
        
        # Проверка уникальности email (если изменился)
        if email != user.email:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({'error': 'Email already exists'}), 400
        
        # Обновляем данные
        user.username = username
        user.email = email
        db.session.commit()
        
        # Обновляем сессию
        session['username'] = username
        
        return jsonify({
            'success': True,
            'username': username,
            'email': email,
            'message': 'Profile updated successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating profile: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


# ========== API ENDPOINTS ==========

@app.route('/api/analyze', methods=['POST'])
@login_required
def analyze_request():
    """
    Анализ обращения и получение совета от ИИ (без создания тикета).
    Принимает JSON: {"text": "..."}
    Возвращает совет от ИИ и анализ проблемы
    """
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Missing required field: text'}), 400
        
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': 'Text cannot be empty'}), 400
        
        # Вызываем AI для анализа
        logger.info(f"Analyzing request (advice only)")
        ai_result = analyze_ticket(text)
        
        # Убеждаемся, что advice всегда есть
        advice = ai_result.get('advice', '').strip()
        auto_response = ai_result.get('auto_response', '').strip()
        
        # Если advice пустое, но есть auto_response - используем его
        if not advice and auto_response:
            advice = auto_response
        
        # Если все еще пусто - создаем базовый совет в зависимости от типа проблемы
        if not advice:
            text_lower = text.lower()
            # Проверяем тип проблемы для более точного совета
            if any(word in text_lower for word in ["болит", "боль", "голова", "головная", "ауру", "сыздау", "здоровье", "саулық"]):
                if ai_result.get('language') == 'kk':
                    advice = "1. Дене температурасын өлшеңіз. 2. Егер қарсы көрсеткіштер болмаса, ауруды басатын дәрі қабылдаңыз. 3. Демалуды қамтамасыз етіңіз. 4. Егер ауру күшті болса немесе 24 сағаттан астам өтпейді - дәрігерге хабарласыңыз."
                else:
                    advice = "1. Измерьте температуру тела. 2. Примите обезболивающее (если нет противопоказаний). 3. Обеспечьте покой. 4. Если боль сильная или не проходит более 24 часов - обратитесь к врачу."
            elif any(word in text_lower for word in ["не работает", "ошибка", "проблема", "не могу", "сломал"]):
                if ai_result.get('language') == 'kk':
                    advice = f"Мәселені шешу үшін: 1. Мәселені толығырақ сипаттаңыз. 2. Қате хабарламаларын тексеріңіз. 3. Жүйені қайта жүктеңіз. 4. Қолдау қызметіне хабарласыңыз. Категория: {ai_result.get('category', 'другое')}."
                else:
                    advice = f"Для решения проблемы: 1. Опишите проблему подробнее. 2. Проверьте сообщения об ошибках. 3. Перезагрузите систему. 4. Обратитесь в службу поддержки. Категория: {ai_result.get('category', 'другое')}."
            else:
                if ai_result.get('language') == 'kk':
                    advice = "Сіздің сұрауыңызды алдық. Маман сіздің мәселеңізді талдап, шешім ұсынады. Егер бұл шұғыл болса - мәселені толығырақ сипаттаңыз."
                else:
                    advice = "Спасибо за обращение! Специалист проанализирует вашу проблему и предоставит решение. Если это срочно - опишите проблему подробнее."
        
        return jsonify({
            'success': True,
            'analysis': {
                'language': ai_result.get('language'),
                'summary': ai_result.get('summary'),
                'category': ai_result.get('category'),
                'priority': ai_result.get('priority', 'MEDIUM'),
                'type': ai_result.get('type', 'QUESTION'),
                'department': ai_result.get('department', 'IT'),
                'advice': advice,  # Всегда возвращаем решение
                'auto_resolve': ai_result.get('auto_resolve', False),
                'auto_response': auto_response,
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error analyzing request: {e}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/tickets', methods=['POST'])
@login_required
def create_ticket():
    """
    Создание нового тикета.
    Принимает FormData с полями: text, source, file_0, file_1, ...
    Или JSON: {"text": "...", "source": "portal"}
    Требует авторизации (любой авторизованный пользователь может создать тикет)
    """
    try:
        logger.info(f"Creating ticket request from user_id: {session.get('user_id')}")
        
        # Проверяем, это FormData или JSON
        if request.content_type and 'multipart/form-data' in request.content_type:
            # FormData - для загрузки файлов
            text = request.form.get('text', '').strip()
            source = request.form.get('source', 'portal')
            
            # Получаем все файлы
            uploaded_files = []
            file_index = 0
            while f'file_{file_index}' in request.files:
                file = request.files[f'file_{file_index}']
                if file and file.filename:
                    uploaded_files.append(file)
                file_index += 1
        else:
            # JSON
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Missing required data'}), 400
            
            text = data.get('text', '').strip()
            source = data.get('source', 'portal')
            uploaded_files = []
        
        if not text and not uploaded_files:
            return jsonify({'error': 'Text or files are required'}), 400
        
        # Вызываем AI для анализа
        logger.info(f"Analyzing ticket from {source}")
        ai_result = analyze_ticket(text)
        
        # Получаем текущего пользователя
        user = get_current_user()
        
        # Создаём тикет
        ticket = Ticket(
            text=text,
            source=source,
            user_id=user.id if user else None,  # связываем тикет с пользователем
            language=ai_result.get('language'),
            summary=ai_result.get('summary'),
            category=ai_result.get('category'),
            priority=ai_result.get('priority', 'MEDIUM'),
            type=ai_result.get('type', 'QUESTION'),
            department=ai_result.get('department', 'IT'),
            ai_raw_response=ai_result.get('ai_raw_response', ''),
        )
        
        # Сохраняем совет от ИИ (ОБЯЗАТЕЛЬНО должно быть решение)
        advice = ai_result.get('advice', '').strip()
        auto_response = ai_result.get('auto_response', '').strip()
        
        # Если advice пустое, но есть auto_response - используем его как advice
        if not advice and auto_response:
            advice = auto_response
        
        # Если все еще пусто - создаем базовый совет
        if not advice:
            if ai_result.get('language') == 'kk':
                advice = "Мәселені шешу үшін: 1. Мәселені толығырақ сипаттаңыз. 2. Қате хабарламаларын тексеріңіз. 3. Жүйені қайта жүктеңіз. 4. Қолдау қызметіне хабарласыңыз."
            else:
                advice = "Для решения проблемы: 1. Опишите проблему подробнее. 2. Проверьте сообщения об ошибках. 3. Перезагрузите систему. 4. Обратитесь в службу поддержки."
        
        # Сохраняем решение в auto_response
        if auto_response and advice:
            ticket.auto_response = f"{auto_response}\n\nРешение проблемы:\n{advice}"
        else:
            ticket.auto_response = advice
        
        # Проверяем, можно ли авто-закрыть
        if ai_result.get('auto_resolve', False):
            ticket.is_auto_closed = True
            ticket.status = 'AUTO_CLOSED'
        else:
            ticket.status = 'OPEN'
            ticket.is_auto_closed = False
        
        # Определяем срочность
        if ai_result.get('priority') in ['HIGH', 'CRITICAL']:
            ticket.is_urgent = True
        
        # Сохраняем в БД
        db.session.add(ticket)
        db.session.flush()  # Получаем ID тикета
        
        # Обрабатываем загруженные файлы
        attachments = []
        if uploaded_files:
            for file in uploaded_files:
                if file.filename:
                    # Проверяем расширение
                    if '.' not in file.filename:
                        continue
                    ext = file.filename.rsplit('.', 1)[1].lower()
                    if ext not in app.config['ALLOWED_TICKET_FILE_EXTENSIONS']:
                        continue
                    
                    # Генерируем уникальное имя файла
                    filename = secure_filename(file.filename)
                    new_filename = f"ticket_{ticket.id}_{uuid.uuid4().hex[:8]}.{ext}"
                    filepath = os.path.join(app.config['TICKET_FILES_FOLDER'], new_filename)
                    
                    # Сохраняем файл
                    file.save(filepath)
                    
                    # Сохраняем информацию о файле
                    file_url = f"/static/uploads/tickets/{new_filename}"
                    attachments.append({
                        'filename': filename,
                        'url': file_url,
                        'size': os.path.getsize(filepath)
                    })
        
        # Если источник - чат, проверяем наличие онлайн операторов
        chat = None
        if source == 'chat':
            # Проверяем наличие онлайн операторов
            operators = User.query.filter(User.role == 'operator').all()
            has_online = any(is_operator_online(op) for op in operators)
            
            if not has_online:
                db.session.commit()  # Сохраняем тикет
                return jsonify({
                    'success': False,
                    'error': 'Онлайн операторов сейчас нет. Пожалуйста, попробуйте позже.',
                    'no_online_operators': True
                }), 200
            
            chat = Chat(
                ticket_id=ticket.id,
                user_id=user.id if user else None,
                status='WAITING'
            )
            db.session.add(chat)
        
        db.session.commit()
        
        logger.info(f"Ticket {ticket.id} created with status {ticket.status}")
        if chat:
            logger.info(f"Chat {chat.id} created for ticket {ticket.id}")
        
        ticket_dict = ticket.to_dict()
        if attachments:
            ticket_dict['attachments'] = attachments
        
        result = {
            'success': True,
            'ticket': ticket_dict
        }
        if chat:
            result['chat'] = chat.to_dict()
        
        return jsonify(result), 201
        
    except Exception as e:
        logger.error(f"Error creating ticket: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/tickets', methods=['GET'])
def get_tickets():
    """
    Получение списка тикетов с фильтрацией.
    Query params: status, department, source, priority, specialist_view, my_tickets
    - Для операторов: specialist_view=true - показывает тикеты их отдела
    - Для пользователей: my_tickets=true - показывает только их тикеты
    """
    try:
        # Безопасное получение пользователя
        user = None
        user_id = None
        user_role = None
        user_department = None
        
        try:
            user = get_current_user()
            if user:
                user_id = getattr(user, 'id', None)
                user_role = getattr(user, 'role', None)
                user_department = getattr(user, 'department', None)
        except Exception as e:
            logger.warning(f"Error getting current user: {e}")
            user = None
        
        status = request.args.get('status')
        department = request.args.get('department')
        source = request.args.get('source')
        priority = request.args.get('priority')
        operator_view = request.args.get('operator_view', 'false').lower() == 'true'
        specialist_view = request.args.get('specialist_view', 'false').lower() == 'true'
        my_tickets = request.args.get('my_tickets', 'false').lower() == 'true'
        
        logger.info(f"get_tickets: user_id={user_id}, role={user_role}, department={user_department}, operator_view={operator_view}, specialist_view={specialist_view}, my_tickets={my_tickets}")
        
        # Проверка авторизации для operator_view, specialist_view и my_tickets
        if operator_view or specialist_view or my_tickets:
            if not user:
                logger.warning("operator_view/specialist_view/my_tickets requested but user is not authenticated")
                return jsonify({'error': 'Authentication required'}), 401
            
            # Проверка для my_tickets - любой авторизованный пользователь может видеть свои тикеты
            if my_tickets:
                if not user_role or not user_id:
                    logger.warning(f"my_tickets requested but user_role or user_id is None: user_id={user_id}, role={user_role}")
                    return jsonify({'error': 'Authentication required'}), 401
            
            if operator_view:
                # Админы могут использовать operator_view для просмотра всех тикетов
                if user_role not in ['operator', 'admin']:
                    logger.warning(f"operator_view requested but user is not operator or admin: user_id={user_id}, role={user_role}")
                    return jsonify({'error': 'Access denied. Operator view requires operator or admin role'}), 403
                # Для операторов проверяем наличие отдела, для админов это не требуется
                if user_role == 'operator' and not user_department:
                    logger.warning(f"operator_view requested but user has no department: user_id={user_id}, role={user_role}")
                    return jsonify({
                        'success': True,
                        'tickets': [],
                        'user_department': None,
                        'message': 'No department assigned. Please contact administrator.'
                    }), 200
            if specialist_view:
                if user_role != 'specialist':
                    logger.warning(f"specialist_view requested but user is not specialist: user_id={user_id}, role={user_role}")
                    return jsonify({'error': 'Access denied. Specialist view requires specialist role'}), 403
                if not user_department:
                    logger.warning(f"specialist_view requested but user has no department: user_id={user_id}, role={user_role}")
                    return jsonify({
                        'success': True,
                        'tickets': [],
                        'user_department': None,
                        'message': 'No department assigned. Please contact administrator.'
                    }), 200
        
        # Безопасное создание запроса
        try:
            query = Ticket.query
        except Exception as e:
            logger.error(f"Error creating query: {e}", exc_info=True)
            return jsonify({'error': 'Database connection error'}), 500
        
        # Если пользователь запрашивает свои тикеты (любая роль)
        if my_tickets and user and user_id:
            try:
                query = query.filter(Ticket.user_id == user_id)
                logger.info(f"Filtering tickets for user {user_id} (role: {user_role})")
            except Exception as e:
                logger.error(f"Error filtering by user_id: {e}", exc_info=True)
        # Если это оператор, показываем только тикеты его отдела
        # Админы видят все тикеты при operator_view
        elif operator_view and user and user_role == 'operator' and user_department:
            try:
                query = query.filter(Ticket.department == user_department)
                logger.info(f"Filtering tickets for operator department: {user_department}")
            except Exception as e:
                logger.error(f"Error filtering by department: {e}", exc_info=True)
        # Админы при operator_view видят все тикеты без фильтрации по отделу
        # Если это специалист, показываем только тикеты его отдела
        elif specialist_view and user and user_role == 'specialist' and user_department:
            try:
                query = query.filter(Ticket.department == user_department)
                logger.info(f"Filtering tickets for specialist department: {user_department}")
            except Exception as e:
                logger.error(f"Error filtering by department: {e}", exc_info=True)
        elif department:
            try:
                query = query.filter(Ticket.department == department)
            except Exception as e:
                logger.error(f"Error filtering by department param: {e}", exc_info=True)
        
        if status:
            try:
                query = query.filter(Ticket.status == status)
            except Exception as e:
                logger.warning(f"Error filtering by status: {e}")
        if priority:
            try:
                query = query.filter(Ticket.priority == priority)
            except Exception as e:
                logger.warning(f"Error filtering by priority: {e}")
        if source:
            try:
                query = query.filter(Ticket.source == source)
            except Exception as e:
                logger.warning(f"Error filtering by source: {e}")
        
        # Сортировка по дате создания (новые сначала)
        try:
            tickets = query.order_by(Ticket.created_at.desc()).all()
            logger.info(f"Found {len(tickets)} tickets")
        except Exception as e:
            logger.error(f"Error executing query: {e}", exc_info=True)
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({'error': f'Database query error: {str(e)}'}), 500
        
        # Безопасная сериализация тикетов
        tickets_data = []
        for ticket in tickets:
            try:
                if ticket:
                    ticket_dict = ticket.to_dict()
                    tickets_data.append(ticket_dict)
            except AttributeError as e:
                logger.error(f"AttributeError serializing ticket {getattr(ticket, 'id', 'unknown')}: {e}", exc_info=True)
                continue
            except Exception as e:
                logger.error(f"Error serializing ticket {getattr(ticket, 'id', 'unknown')}: {e}", exc_info=True)
                import traceback
                logger.error(traceback.format_exc())
                continue
        
        return jsonify({
            'success': True,
            'tickets': tickets_data,
            'user_department': user_department if user and user_role == 'operator' else None
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting tickets: {e}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/tickets/<int:ticket_id>', methods=['GET'])
@login_required
def get_ticket(ticket_id):
    """Получение детальной информации о тикете"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        try:
            ticket = Ticket.query.get_or_404(ticket_id)
        except Exception as e:
            logger.error(f"Error getting ticket {ticket_id}: {e}", exc_info=True)
            return jsonify({'error': 'Ticket not found'}), 404
        
        # Безопасное получение атрибутов пользователя
        user_role = getattr(user, 'role', None)
        user_id = getattr(user, 'id', None)
        user_department = getattr(user, 'department', None)
        
        # Проверяем права доступа
        # Пользователь может видеть только свои тикеты
        # Оператор может видеть тикеты своего отдела
        # Специалист может видеть тикеты своего отдела
        # Админ может видеть все
        if user_role == 'user':
            ticket_user_id = getattr(ticket, 'user_id', None)
            if ticket_user_id != user_id:
                return jsonify({'error': 'Access denied'}), 403
        elif user_role == 'operator':
            ticket_department = getattr(ticket, 'department', None)
            if ticket_department != user_department:
                return jsonify({'error': 'Access denied'}), 403
        elif user_role == 'specialist':
            ticket_department = getattr(ticket, 'department', None)
            if ticket_department != user_department:
                return jsonify({'error': 'Access denied'}), 403
        
        try:
            ticket_dict = ticket.to_dict()
        except Exception as e:
            logger.error(f"Error serializing ticket {ticket_id}: {e}", exc_info=True)
            return jsonify({'error': 'Error serializing ticket data'}), 500
        
        return jsonify({
            'success': True,
            'ticket': ticket_dict
        }), 200
    except Exception as e:
        logger.error(f"Error getting ticket {ticket_id}: {e}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/tickets/<int:ticket_id>', methods=['PATCH'])
@login_required
def update_ticket(ticket_id):
    """
    Обновление тикета (статус, ответ оператора и т.д.)
    Принимает JSON: {"status": "...", "last_response": "..."}
    """
    try:
        ticket = Ticket.query.get_or_404(ticket_id)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Обновляем поля
        if 'status' in data:
            ticket.status = data['status']
        
        if 'last_response' in data:
            ticket.last_response = data['last_response']
        
        if 'department' in data:
            ticket.department = data['department']
        
        if 'priority' in data:
            ticket.priority = data['priority']
            ticket.is_urgent = data['priority'] in ['HIGH', 'CRITICAL']
        
        ticket.updated_at = datetime.now(UTC)
        
        db.session.commit()
        
        logger.info(f"Ticket {ticket_id} updated")
        
        return jsonify({
            'success': True,
            'ticket': ticket.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating ticket {ticket_id}: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/users/<int:user_id>', methods=['GET'])
@login_required
def get_user_info(user_id):
    """Получение информации о пользователе (для отображения в тикетах)"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        # Проверяем права доступа - операторы, специалисты и админы могут видеть информацию о пользователях
        if user.role not in ['admin', 'operator', 'specialist']:
            # Обычные пользователи могут видеть только свою информацию
            if user.id != user_id:
                return jsonify({'error': 'Access denied'}), 403
        
        try:
            target_user = User.query.get(user_id)
            if not target_user:
                return jsonify({'error': 'User not found'}), 404
            
            return jsonify({
                'success': True,
                'user': target_user.to_dict()
            }), 200
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}", exc_info=True)
            return jsonify({'error': 'Error retrieving user data'}), 500
        
    except Exception as e:
        logger.error(f"Error in get_user_info: {e}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/operators/online', methods=['GET'])
@login_required
def check_online_operators():
    """Проверка наличия онлайн операторов"""
    try:
        operators = User.query.filter(User.role == 'operator').all()
        online_count = sum(1 for op in operators if is_operator_online(op))
        
        return jsonify({
            'success': True,
            'has_online_operators': online_count > 0,
            'online_count': online_count,
            'total_count': len(operators)
        }), 200
    except Exception as e:
        logger.error(f"Error checking online operators: {e}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/operators/heartbeat', methods=['POST'])
@operator_required
def operator_heartbeat():
    """Обновление активности оператора (heartbeat)"""
    try:
        user = get_current_user()
        if user and user.role == 'operator':
            # Обновляем активность только если оператор вручную установил статус онлайн
            is_online_manual = getattr(user, 'is_online_manual', True)
            if is_online_manual:
                user.last_activity = datetime.now(UTC)
                db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Activity updated',
                'is_online': is_online_manual
            }), 200
        return jsonify({'error': 'Not an operator'}), 403
    except Exception as e:
        logger.error(f"Error updating operator heartbeat: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/specialists/heartbeat', methods=['POST'])
@specialist_required
def specialist_heartbeat():
    """Обновление активности специалиста (heartbeat)"""
    try:
        user = get_current_user()
        if user and user.role == 'specialist':
            # Обновляем активность специалиста
            user.last_activity = datetime.now(UTC)
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Activity updated'
            }), 200
        return jsonify({'error': 'Not a specialist'}), 403
    except Exception as e:
        logger.error(f"Error updating specialist heartbeat: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/operators/toggle-status', methods=['POST'])
@operator_required
def toggle_operator_status():
    """Переключение статуса онлайн/офлайн оператора"""
    try:
        user = get_current_user()
        if not user or user.role != 'operator':
            return jsonify({'error': 'Not an operator'}), 403
        
        # Переключаем статус
        if hasattr(user, 'is_online_manual'):
            user.is_online_manual = not user.is_online_manual
        else:
            # Если поле не существует, создаем его
            user.is_online_manual = True
        
        # Если переключаемся на онлайн, обновляем активность
        if user.is_online_manual:
            user.last_activity = datetime.now(UTC)
        
        db.session.commit()
        
        logger.info(f"Operator {user.id} toggled status to {'online' if user.is_online_manual else 'offline'}")
        
        return jsonify({
            'success': True,
            'is_online': user.is_online_manual
        }), 200
    except Exception as e:
        logger.error(f"Error toggling operator status: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/operators/my-status', methods=['GET'])
@operator_required
def get_my_operator_status():
    """Получение текущего статуса оператора"""
    try:
        user = get_current_user()
        if not user or user.role != 'operator':
            return jsonify({'error': 'Not an operator'}), 403
        
        is_online_manual = getattr(user, 'is_online_manual', True)
        is_online = is_operator_online(user)
        
        return jsonify({
            'success': True,
            'is_online_manual': is_online_manual,
            'is_online': is_online
        }), 200
    except Exception as e:
        logger.error(f"Error getting operator status: {e}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/operators', methods=['GET'])
@admin_required
def get_operators():
    """Получение списка операторов с их статистикой"""
    try:
        # Получаем всех операторов
        operators = User.query.filter(User.role == 'operator').all()
        
        operators_data = []
        for operator in operators:
            try:
                # Проверяем онлайн статус
                is_online = is_operator_online(operator)
            except Exception as e:
                logger.warning(f"Error checking online status for operator {operator.id}: {e}")
                is_online = False
            
            try:
                # Статистика по чатам оператора
                total_chats = Chat.query.filter(Chat.operator_id == operator.id).count()
                active_chats = Chat.query.filter(Chat.operator_id == operator.id, Chat.status == 'ACTIVE').count()
                closed_chats = Chat.query.filter(Chat.operator_id == operator.id, Chat.status == 'CLOSED').count()
            except Exception as e:
                logger.warning(f"Error getting chat stats for operator {operator.id}: {e}")
                total_chats = 0
                active_chats = 0
                closed_chats = 0
            
            try:
                # Средняя оценка
                rated_chats = Chat.query.filter(
                    Chat.operator_id == operator.id,
                    Chat.rating.isnot(None)
                ).all()
                
                avg_rating = 0
                if rated_chats:
                    total_rating = sum(chat.rating for chat in rated_chats if chat.rating)
                    avg_rating = round(total_rating / len(rated_chats), 2)
            except Exception as e:
                logger.warning(f"Error getting ratings for operator {operator.id}: {e}")
                rated_chats = []
                avg_rating = 0
            
            try:
                # Статистика по тикетам отдела оператора
                tickets_in_dept = Ticket.query.filter(Ticket.department == operator.department).count() if operator.department else 0
                resolved_tickets = Ticket.query.filter(
                    Ticket.department == operator.department,
                    Ticket.status.in_(['RESOLVED', 'AUTO_CLOSED'])
                ).count() if operator.department else 0
            except Exception as e:
                logger.warning(f"Error getting ticket stats for operator {operator.id}: {e}")
                tickets_in_dept = 0
                resolved_tickets = 0
            
            # Последняя активность (последний закрытый чат)
            last_activity = None
            try:
                last_closed_chat = Chat.query.filter(
                    Chat.operator_id == operator.id,
                    Chat.status == 'CLOSED'
                ).order_by(Chat.closed_at.desc()).first()
                
                if last_closed_chat and last_closed_chat.closed_at:
                    last_activity = last_closed_chat.closed_at.isoformat()
            except Exception as e:
                logger.warning(f"Error getting last activity for operator {operator.id}: {e}")
            
            try:
                operators_data.append({
                    'id': operator.id,
                    'username': operator.username,
                    'email': operator.email,
                    'department': operator.department,
                    'avatar_url': operator.avatar_url if hasattr(operator, 'avatar_url') else None,
                    'created_at': operator.created_at.isoformat() if operator.created_at else None,
                    'last_activity': operator.last_activity.isoformat() if hasattr(operator, 'last_activity') and operator.last_activity else None,
                    'is_online': is_online,
                    'stats': {
                        'total_chats': total_chats,
                        'active_chats': active_chats,
                        'closed_chats': closed_chats,
                        'avg_rating': avg_rating,
                        'total_ratings': len(rated_chats),
                        'tickets_in_department': tickets_in_dept,
                        'resolved_tickets': resolved_tickets,
                        'last_activity': last_activity
                    }
                })
            except Exception as e:
                logger.error(f"Error adding operator {operator.id} to list: {e}", exc_info=True)
                continue
        
        return jsonify({
            'success': True,
            'operators': operators_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting operators: {e}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/specialists', methods=['GET'])
@admin_required
def get_specialists():
    """Получение списка специалистов с их статистикой"""
    try:
        # Получаем всех специалистов
        specialists = User.query.filter(User.role == 'specialist').all()
        
        specialists_data = []
        for specialist in specialists:
            try:
                # Проверяем онлайн статус (используем ту же функцию, что и для операторов)
                is_online = is_operator_online(specialist)
            except Exception as e:
                logger.warning(f"Error checking online status for specialist {specialist.id}: {e}")
                is_online = False
            
            try:
                # Статистика по тикетам отдела специалиста
                tickets_in_dept = Ticket.query.filter(Ticket.department == specialist.department).count() if specialist.department else 0
                resolved_tickets = Ticket.query.filter(
                    Ticket.department == specialist.department,
                    Ticket.status.in_(['RESOLVED', 'AUTO_CLOSED'])
                ).count() if specialist.department else 0
                in_progress_tickets = Ticket.query.filter(
                    Ticket.department == specialist.department,
                    Ticket.status == 'IN_PROGRESS'
                ).count() if specialist.department else 0
            except Exception as e:
                logger.warning(f"Error getting ticket stats for specialist {specialist.id}: {e}")
                tickets_in_dept = 0
                resolved_tickets = 0
                in_progress_tickets = 0
            
            try:
                # Средняя оценка из тикетов (если есть поле rating в Ticket)
                # Пока используем упрощенную версию - можно добавить позже
                avg_rating = 0.0
                total_ratings = 0
                
                specialists_data.append({
                    'id': specialist.id,
                    'username': specialist.username,
                    'email': specialist.email,
                    'department': specialist.department,
                    'avatar_url': specialist.avatar_url if hasattr(specialist, 'avatar_url') else None,
                    'created_at': specialist.created_at.isoformat() if specialist.created_at else None,
                    'is_online': is_online,
                    'stats': {
                        'tickets_in_department': tickets_in_dept,
                        'resolved_tickets': resolved_tickets,
                        'in_progress_tickets': in_progress_tickets,
                        'avg_rating': avg_rating,
                        'total_ratings': total_ratings
                    }
                })
            except Exception as e:
                logger.error(f"Error adding specialist {specialist.id} to list: {e}", exc_info=True)
                continue
        
        return jsonify({
            'success': True,
            'specialists': specialists_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting specialists: {e}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/stats', methods=['GET'])
@operator_required
def get_stats():
    """Получение статистики по тикетам"""
    try:
        total = Ticket.query.count()
        auto_closed = Ticket.query.filter(Ticket.is_auto_closed == True).count()
        auto_closed_percent = (auto_closed / total * 100) if total > 0 else 0
        
        # Среднее время ответа (для AUTO_CLOSED - время между created_at и updated_at)
        resolved_tickets = Ticket.query.filter(
            Ticket.status.in_(['AUTO_CLOSED', 'RESOLVED'])
        ).all()
        
        avg_response_time = 0
        if resolved_tickets:
            total_seconds = 0
            count_with_times = 0
            for ticket in resolved_tickets:
                if ticket.created_at and ticket.updated_at:
                    try:
                        delta = (ticket.updated_at - ticket.created_at).total_seconds()
                        total_seconds += delta
                        count_with_times += 1
                    except Exception as e:
                        logger.warning(f"Error calculating time delta for ticket {ticket.id}: {e}")
                        continue
            avg_response_time = total_seconds / count_with_times if count_with_times > 0 else 0
        
        # Статистика по статусам
        status_counts = {}
        for status in ['OPEN', 'AUTO_CLOSED', 'IN_PROGRESS', 'RESOLVED']:
            try:
                status_counts[status] = Ticket.query.filter(Ticket.status == status).count()
            except Exception as e:
                logger.warning(f"Error counting status {status}: {e}")
                status_counts[status] = 0
        
        # Статистика по отделам
        department_counts = {}
        try:
            departments = db.session.query(Ticket.department).distinct().all()
            for dept in departments:
                if dept and dept[0]:
                    try:
                        department_counts[dept[0]] = Ticket.query.filter(
                            Ticket.department == dept[0]
                        ).count()
                    except Exception as e:
                        logger.warning(f"Error counting department {dept[0]}: {e}")
                        continue
        except Exception as e:
            logger.warning(f"Error getting departments: {e}")
        
        return jsonify({
            'success': True,
            'stats': {
                'total': total,
                'auto_closed': auto_closed,
                'auto_closed_percent': round(auto_closed_percent, 2),
                'avg_response_time_seconds': round(avg_response_time, 2),
                'status_counts': status_counts,
                'department_counts': department_counts,
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


# ========== CHAT API ENDPOINTS ==========

@app.route('/api/chats', methods=['GET'])
@operator_required
def get_chats():
    # Активность уже обновлена в декораторе operator_required
    """Получение списка чатов для оператора"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        status = request.args.get('status', 'WAITING')  # WAITING, ACTIVE
        
        # Используем eager loading для оптимизации
        from sqlalchemy.orm import joinedload
        query = Chat.query.options(
            joinedload(Chat.user),
            joinedload(Chat.operator),
            joinedload(Chat.ticket)
        )
        
        # Оператор видит только чаты своего отдела или все, если админ
        if user.role == 'operator' and user.department:
            query = query.join(Ticket).filter(Ticket.department == user.department)
        
        if status:
            query = query.filter(Chat.status == status)
        
        chats = query.order_by(Chat.created_at.desc()).limit(50).all()  # Ограничиваем до 50
        
        return jsonify({
            'success': True,
            'chats': [chat.to_dict() for chat in chats]
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting chats: {e}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/chats/<int:chat_id>/accept', methods=['POST'])
@operator_required
def accept_chat(chat_id):
    """Принятие чата оператором"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        chat = Chat.query.get_or_404(chat_id)
        
        # Проверяем права доступа
        if user.role == 'operator' and user.department:
            if chat.ticket.department != user.department:
                return jsonify({'error': 'Access denied'}), 403
        
        if chat.status != 'WAITING':
            return jsonify({'error': 'Chat is not waiting for operator'}), 400
        
        chat.operator_id = user.id
        chat.status = 'ACTIVE'
        chat.updated_at = datetime.now(UTC)
        
        # Обновляем статус тикета
        chat.ticket.status = 'IN_PROGRESS'
        chat.ticket.updated_at = datetime.now(UTC)
        
        db.session.commit()
        
        # Обновляем объект из БД для получения актуальных данных
        db.session.refresh(chat)
        
        logger.info(f"Chat {chat_id} accepted by operator {user.id}. Status: {chat.status}, Operator ID: {chat.operator_id}")
        
        return jsonify({
            'success': True,
            'chat': chat.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error accepting chat: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/chats/<int:chat_id>', methods=['GET'])
@login_required
def get_chat(chat_id):
    """Получение информации о чате"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        chat = Chat.query.get_or_404(chat_id)
        
        # Проверяем права доступа
        if user.role == 'user':
            if chat.user_id != user.id:
                return jsonify({'error': 'Access denied'}), 403
        elif user.role in ['operator', 'admin']:
            # Оператор может видеть чат если он принял его или чат ожидает в его отделе
            if chat.status == 'ACTIVE':
                if not chat.operator_id or chat.operator_id != user.id:
                    if user.role == 'operator' and user.department:
                        if chat.ticket.department != user.department:
                            return jsonify({'error': 'Access denied'}), 403
            elif chat.status == 'WAITING':
                if user.role == 'operator' and user.department:
                    if chat.ticket.department != user.department:
                        return jsonify({'error': 'Access denied'}), 403
        else:
            return jsonify({'error': 'Access denied'}), 403
        
        return jsonify({
            'success': True,
            'chat': chat.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting chat: {e}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/chats/<int:chat_id>/messages', methods=['GET'])
@login_required
def get_chat_messages(chat_id):
    """Получение сообщений чата"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        chat = Chat.query.get_or_404(chat_id)
        
        # Обновляем объект из БД для получения актуального статуса
        db.session.refresh(chat)
        
        logger.info(f"get_chat_messages: user_id={user.id}, role={user.role}, chat_id={chat_id}, chat.user_id={chat.user_id}, chat.status={chat.status}, chat.operator_id={chat.operator_id}")
        
        # Проверяем права доступа
        if user.role == 'user':
            # Клиент может видеть только свои чаты, независимо от статуса
            if chat.user_id != user.id:
                logger.warning(f"User {user.id} tried to access chat {chat_id} owned by user {chat.user_id}")
                return jsonify({'error': 'Access denied'}), 403
            # Клиент имеет доступ к своему чату
            logger.info(f"User {user.id} granted access to their chat {chat_id}")
        elif user.role in ['operator', 'admin']:
            # Админы могут видеть все чаты
            if user.role == 'admin':
                logger.info(f"Admin {user.id} granted access to chat {chat_id}")
            # Оператор может видеть чаты своего отдела
            elif user.role == 'operator':
                # Загружаем ticket с отделом для проверки
                if not chat.ticket:
                    logger.error(f"Chat {chat_id} has no ticket")
                    return jsonify({'error': 'Chat has no associated ticket'}), 500
                if user.department and chat.ticket.department != user.department:
                    logger.warning(f"Operator {user.id} from department {user.department} tried to access chat {chat_id} from department {chat.ticket.department}")
                    return jsonify({'error': 'Access denied'}), 403
                # Оператор может видеть чат если он его принял или чат еще ожидает в его отделе
                if chat.status == 'ACTIVE' and chat.operator_id and chat.operator_id != user.id:
                    logger.warning(f"Operator {user.id} tried to access active chat {chat_id} handled by operator {chat.operator_id}")
                    return jsonify({'error': 'Access denied'}), 403
                logger.info(f"Operator {user.id} granted access to chat {chat_id}")
        else:
            logger.warning(f"User {user.id} with role {user.role} tried to access chat {chat_id}")
            return jsonify({'error': 'Access denied'}), 403
        
        messages = ChatMessage.query.filter_by(chat_id=chat_id).order_by(ChatMessage.created_at.asc()).all()
        
        return jsonify({
            'success': True,
            'messages': [msg.to_dict() for msg in messages]
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting chat messages: {e}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/chats/<int:chat_id>/messages', methods=['POST'])
@login_required
def send_chat_message(chat_id):
    """Отправка сообщения в чат (поддерживает файлы и FormData)"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        # Проверяем, это FormData или JSON
        if request.content_type and 'multipart/form-data' in request.content_type:
            # FormData - для файлов и voice messages
            message_text = request.form.get('message', '').strip()
            message_type = request.form.get('message_type', 'text')  # text, file, voice, image
            attachment_url = request.form.get('attachment_url', '')  # Если файл уже загружен
            is_formatted = request.form.get('is_formatted', 'false').lower() == 'true'
        else:
            # JSON
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Missing required data'}), 400
            message_text = data.get('message', '').strip()
            message_type = data.get('message_type', 'text')
            attachment_url = data.get('attachment_url', '')
            is_formatted = data.get('is_formatted', False)
        
        # Если нет текста и нет attachment_url, это ошибка
        if not message_text and not attachment_url and message_type == 'text':
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        chat = Chat.query.get_or_404(chat_id)
        
        # Обновляем объект из БД для получения актуального статуса
        db.session.refresh(chat)
        
        # Проверяем права доступа
        is_from_user = False
        if user.role == 'user':
            if chat.user_id != user.id:
                return jsonify({'error': 'Access denied'}), 403
            is_from_user = True
            # Пользователь может отправлять сообщения только если чат активен
            if chat.status == 'WAITING':
                logger.info(f"User {user.id} tried to send message to waiting chat {chat_id}")
                return jsonify({'error': 'Waiting for operator to accept chat'}), 400
        elif user.role in ['operator', 'admin']:
            # Оператор может отправлять сообщения если он принял чат
            if chat.status == 'ACTIVE':
                # Если чат активен, только принявший оператор может отправлять
                if not chat.operator_id or chat.operator_id != user.id:
                    logger.warning(f"Operator {user.id} tried to send message to chat {chat_id} but operator_id is {chat.operator_id}")
                    return jsonify({'error': 'Access denied. This chat is handled by another operator'}), 403
            elif chat.status == 'WAITING':
                # Если чат ожидает, оператор может принять его автоматически при первой отправке
                # Проверяем отдел оператора
                if user.role == 'operator' and user.department:
                    if chat.ticket.department != user.department:
                        return jsonify({'error': 'Access denied. Wrong department'}), 403
                # Автоматически принимаем чат
                chat.operator_id = user.id
                chat.status = 'ACTIVE'
                chat.updated_at = datetime.now(UTC)
                chat.ticket.status = 'IN_PROGRESS'
                chat.ticket.updated_at = datetime.now(UTC)
                db.session.commit()
                logger.info(f"Chat {chat_id} auto-accepted by operator {user.id} on first message")
            else:
                return jsonify({'error': 'Chat is closed'}), 400
            is_from_user = False
        else:
            return jsonify({'error': 'Access denied'}), 403
        
        # Обновляем объект чата из БД перед созданием сообщения
        db.session.refresh(chat)
        
        # Проверяем еще раз статус после обновления
        if is_from_user and chat.status == 'WAITING':
            return jsonify({'error': 'Waiting for operator to accept chat'}), 400
        
        # Обновляем объект чата из БД перед созданием сообщения (на случай если статус изменился)
        db.session.refresh(chat)
        
        # Проверяем еще раз статус после обновления
        if is_from_user and chat.status == 'WAITING':
            return jsonify({'error': 'Waiting for operator to accept chat'}), 400
        
        # Создаем сообщение
        message = ChatMessage(
            chat_id=chat_id,
            sender_id=user.id,
            message=message_text or (attachment_url if attachment_url else ''),
            is_from_user=is_from_user,
            message_type=message_type,
            attachment_url=attachment_url if attachment_url else None,
            is_formatted=is_formatted
        )
        
        db.session.add(message)
        chat.updated_at = datetime.now(UTC)
        db.session.commit()
        
        logger.info(f"Message sent in chat {chat_id} by user {user.id} (type: {message_type}, role: {user.role}, is_from_user: {is_from_user}, chat_status: {chat.status}, operator_id: {chat.operator_id})")
        
        return jsonify({
            'success': True,
            'message': message.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Error sending chat message: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/chats/<int:chat_id>/ai-suggestions', methods=['GET'])
@operator_required
def get_chat_ai_suggestions(chat_id):
    """Получение AI-предложений для оператора (контекст чата, предложенные ответы)"""
    try:
        user = get_current_user()
        if not user or user.role not in ['operator', 'admin']:
            return jsonify({'error': 'Access denied'}), 403
        
        chat = Chat.query.get_or_404(chat_id)
        
        # Проверяем права доступа
        if user.role == 'operator' and chat.operator_id != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Получаем последние сообщения чата (до 10)
        messages = ChatMessage.query.filter_by(chat_id=chat_id).order_by(ChatMessage.created_at.desc()).limit(10).all()
        messages.reverse()  # Хронологический порядок
        
        # Формируем контекст для AI
        conversation_context = ""
        for msg in messages:
            sender = "Клиент" if msg.is_from_user else "Оператор"
            conversation_context += f"{sender}: {msg.message}\n"
        
        # Получаем информацию о тикете
        ticket = chat.ticket
        ticket_info = f"Тикет #{ticket.id}: {ticket.category} - {ticket.priority} приоритет. Проблема: {ticket.text[:200]}"
        
        # Формируем промпт для AI
        prompt = f"""Ты - AI-помощник для оператора службы поддержки. Оператор общается с клиентом в чате.

Информация о тикете:
{ticket_info}

История переписки:
{conversation_context}

Верни JSON со следующими полями:
{{
  "summary": "краткое резюме проблемы клиента (1-2 предложения)",
  "sentiment": "позитивный/нейтральный/негативный - эмоциональное состояние клиента",
  "suggested_response": "предложенный ответ оператору (краткий, профессиональный, на русском языке)",
  "key_points": ["ключевой момент 1", "ключевой момент 2"] - важные моменты для понимания проблемы
}}

Помоги оператору лучше понять проблему и дай полезный совет для ответа."""
        
        # Вызываем AI
        from ai_client import analyze_ticket
        ai_result = analyze_ticket(prompt)
        
        # Извлекаем данные из AI ответа
        summary = ai_result.get('summary', '')
        suggested_response = ai_result.get('auto_response', '') or ai_result.get('advice', '')
        
        # Определяем sentiment (если AI не вернул, пытаемся определить по тексту)
        sentiment = "нейтральный"
        if summary or conversation_context:
            text_lower = (summary + " " + conversation_context).lower()
            if any(word in text_lower for word in ["спасибо", "благодарю", "отлично", "хорошо"]):
                sentiment = "позитивный"
            elif any(word in text_lower for word in ["плохо", "не работает", "проблема", "ошибка", "недоволен"]):
                sentiment = "негативный"
        
        # Формируем ключевые моменты
        key_points = []
        if ticket.category:
            key_points.append(f"Категория: {ticket.category}")
        if ticket.priority:
            key_points.append(f"Приоритет: {ticket.priority}")
        
        return jsonify({
            'success': True,
            'suggestions': {
                'summary': summary or 'Контекст чата анализируется...',
                'sentiment': sentiment,
                'suggested_response': suggested_response or 'AI анализирует переписку...',
                'key_points': key_points
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting AI suggestions: {e}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/chats/user/<int:user_id>', methods=['GET'])
@login_required
def get_user_chat(user_id):
    """Получение активного чата пользователя"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        if user.id != user_id and user.role not in ['admin', 'operator']:
            return jsonify({'error': 'Access denied'}), 403
        
        # Ищем активный чат пользователя
        chat = Chat.query.filter_by(user_id=user_id, status='ACTIVE').first()
        
        if not chat:
            return jsonify({
                'success': True,
                'chat': None
            }), 200
        
        return jsonify({
            'success': True,
            'chat': chat.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user chat: {e}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/chats/<int:chat_id>/close', methods=['POST'])
@login_required
def close_chat(chat_id):
    """Закрытие чата клиентом или оператором"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        chat = Chat.query.get_or_404(chat_id)
        
        # Проверяем права доступа:
        # - Клиент может закрыть свой чат
        # - Оператор может закрыть чат, который он ведет
        # - Админ может закрыть любой чат
        can_close = False
        if user.role == 'admin':
            can_close = True
        elif user.role == 'operator' and chat.operator_id == user.id:
            can_close = True
        elif user.role == 'user' and chat.user_id == user.id:
            can_close = True
        
        if not can_close:
            return jsonify({'error': 'Access denied'}), 403
        
        if chat.status == 'CLOSED':
            return jsonify({'error': 'Chat is already closed'}), 400
        
        # Закрываем чат
        chat.status = 'CLOSED'
        chat.closed_at = datetime.now(UTC)
        chat.updated_at = datetime.now(UTC)
        
        # Обновляем статус тикета
        if chat.ticket:
            chat.ticket.status = 'RESOLVED'
            chat.ticket.updated_at = datetime.now(UTC)
        
        db.session.commit()
        
        logger.info(f"Chat {chat_id} closed by user {user.id}")
        
        return jsonify({
            'success': True,
            'chat': chat.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error closing chat: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/chats/<int:chat_id>/rate', methods=['POST'])
@login_required
def rate_chat(chat_id):
    """Оценка чата оператором"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        data = request.get_json()
        if not data or 'rating' not in data:
            return jsonify({'error': 'Missing required field: rating'}), 400
        
        rating = data.get('rating')
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({'error': 'Rating must be an integer between 1 and 5'}), 400
        
        chat = Chat.query.get_or_404(chat_id)
        
        # Только оператор, который принял чат, может поставить оценку
        if user.role not in ['operator', 'admin']:
            return jsonify({'error': 'Access denied. Only operators can rate chats'}), 403
        
        if chat.status != 'CLOSED':
            return jsonify({'error': 'Can only rate closed chats'}), 400
        
        if chat.operator_id != user.id and user.role != 'admin':
            return jsonify({'error': 'Access denied. You can only rate chats you handled'}), 403
        
        # Сохраняем оценку
        chat.rating = rating
        chat.updated_at = datetime.now(UTC)
        db.session.commit()
        
        logger.info(f"Chat {chat_id} rated {rating} by operator {user.id}")
        
        return jsonify({
            'success': True,
            'chat': chat.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error rating chat: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


# ========== DISPATCH / SPECIALIST ROUTES ==========

@app.route('/api/dispatches/pending', methods=['GET'])
@login_required
def get_pending_dispatches():
    """Получение ожидающих запросов для специалиста"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        # Только специалисты могут видеть свои ожидающие запросы
        if user.role != 'specialist':
            return jsonify({'error': 'Access denied'}), 403
        
        # Ищем все ожидающие запросы для этого специалиста
        dispatches = Dispatch.query.filter(
            Dispatch.specialist_id == user.id,
            Dispatch.status == 'PENDING'
        ).order_by(Dispatch.created_at.desc()).all()
        
        dispatches_data = [dispatch.to_dict() for dispatch in dispatches]
        
        return jsonify({
            'success': True,
            'dispatches': dispatches_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting pending dispatches: {e}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/dispatches/active', methods=['GET'])
@login_required
def get_active_dispatch():
    """Получение активной отправки для текущего пользователя"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        # Ищем активную отправку
        dispatch = None
        if user.role == 'user':
            dispatch = Dispatch.query.filter(
                Dispatch.user_id == user.id,
                Dispatch.status.in_(['PENDING', 'ACCEPTED', 'IN_ROUTE', 'ARRIVED'])
            ).order_by(Dispatch.created_at.desc()).first()
        elif user.role == 'specialist':
            dispatch = Dispatch.query.filter(
                Dispatch.specialist_id == user.id,
                Dispatch.status.in_(['PENDING', 'ACCEPTED', 'IN_ROUTE', 'ARRIVED'])
            ).order_by(Dispatch.created_at.desc()).first()
        elif user.role in ['operator', 'admin']:
            # Операторы и админы могут видеть любые активные отправки
            dispatch = Dispatch.query.filter(
                Dispatch.status.in_(['PENDING', 'ACCEPTED', 'IN_ROUTE', 'ARRIVED'])
            ).order_by(Dispatch.created_at.desc()).first()
        
        if dispatch:
            return jsonify({
                'success': True,
                'dispatch': dispatch.to_dict()
            }), 200
        else:
            return jsonify({
                'success': True,
                'dispatch': None
            }), 200
        
    except Exception as e:
        logger.error(f"Error getting active dispatch: {e}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/specialists/online', methods=['GET'])
@login_required
def get_online_specialists():
    """Получение списка онлайн специалистов"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        # Только операторы и админы могут видеть список специалистов
        if user.role not in ['admin', 'operator']:
            return jsonify({'error': 'Access denied'}), 403
        
        specialists = User.query.filter(User.role == 'specialist', User.is_active == True).all()
        
        specialists_data = []
        for specialist in specialists:
            # Проверяем онлайн статус
            is_online = False
            
            # Если статус онлайн вручную, специалист онлайн
            if hasattr(specialist, 'is_online_manual') and specialist.is_online_manual is True:
                is_online = True
            # Если ручной статус не установлен, проверяем автоматический статус по активности
            elif hasattr(specialist, 'last_activity') and specialist.last_activity:
                from datetime import timedelta
                try:
                    time_diff = datetime.now(UTC) - specialist.last_activity
                    is_online = time_diff < timedelta(minutes=5)
                except Exception as e:
                    logger.warning(f"Error checking specialist online status: {e}")
            
            if is_online:
                specialists_data.append({
                    'id': specialist.id,
                    'username': specialist.username,
                    'email': specialist.email,
                    'department': specialist.department,
                    'avatar_url': specialist.avatar_url if hasattr(specialist, 'avatar_url') else None,
                })
        
        return jsonify({
            'success': True,
            'specialists': specialists_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting online specialists: {e}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/dispatches', methods=['POST'])
@login_required
def create_dispatch():
    """Создание отправки специалиста к клиенту"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        # Только операторы могут отправлять специалистов
        if user.role not in ['admin', 'operator']:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        chat_id = data.get('chat_id')
        specialist_id = data.get('specialist_id')
        client_address = data.get('client_address', '').strip()
        
        # Получаем координаты напрямую, если они были переданы
        client_lat = data.get('client_latitude')
        client_lon = data.get('client_longitude')
        
        if not chat_id or not specialist_id:
            return jsonify({'error': 'chat_id and specialist_id are required'}), 400
        
        # Проверяем чат
        chat = Chat.query.get(chat_id)
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404
        
        # Проверяем, что оператор имеет доступ к этому чату
        if chat.operator_id != user.id and user.role != 'admin':
            return jsonify({'error': 'Access denied to this chat'}), 403
        
        # Проверяем специалиста
        specialist = User.query.get(specialist_id)
        if not specialist or specialist.role != 'specialist':
            return jsonify({'error': 'Specialist not found'}), 404
        
        # Проверяем, нет ли уже активной отправки для этого чата
        existing_dispatch = Dispatch.query.filter(
            Dispatch.chat_id == chat_id,
            Dispatch.status.in_(['PENDING', 'IN_ROUTE'])
        ).first()
        
        if existing_dispatch:
            return jsonify({'error': 'There is already an active dispatch for this chat'}), 400
        
        # Если координаты не были переданы напрямую, пытаемся получить их через геокодинг
        if not client_lat or not client_lon:
            if client_address:
                try:
                    api_key = app.config['TGIS_API_KEY']
                    geocode_url = "https://catalog.api.2gis.com/geo/search"
                    geocode_params = {
                        'key': api_key,
                        'q': client_address,
                        'type': 'building',
                        'fields': 'items.point'
                    }
                    
                    geocode_response = requests.get(geocode_url, params=geocode_params, timeout=10)
                    if geocode_response.status_code == 200:
                        geocode_data = geocode_response.json()
                        if geocode_data.get('result') and geocode_data['result'].get('items'):
                            first_item = geocode_data['result']['items'][0]
                            if 'point' in first_item:
                                client_lon = str(first_item['point']['lon'])
                                client_lat = str(first_item['point']['lat'])
                except Exception as e:
                    logger.warning(f"Error geocoding address: {e}")
        
        # Преобразуем координаты в строки, если они были переданы как числа
        if client_lat is not None:
            client_lat = str(client_lat)
        if client_lon is not None:
            client_lon = str(client_lon)
        
        # Используем координаты офиса для всех специалистов
        office_lat = app.config['OFFICE_LATITUDE']
        office_lon = app.config['OFFICE_LONGITUDE']
        
        # Создаем отправку (статус PENDING - специалист должен принять)
        dispatch = Dispatch(
            chat_id=chat_id,
            user_id=chat.user_id,
            specialist_id=specialist_id,
            operator_id=user.id,
            client_address=client_address,
            client_latitude=client_lat,
            client_longitude=client_lon,
            specialist_latitude=office_lat,  # Все специалисты из одного офиса
            specialist_longitude=office_lon,
            status='PENDING'  # Ожидает принятия специалистом
        )
        
        db.session.add(dispatch)
        db.session.commit()
        
        logger.info(f"Dispatch {dispatch.id} created: specialist {specialist_id} to chat {chat_id}")
        
        return jsonify({
            'success': True,
            'dispatch': dispatch.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating dispatch: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/dispatches/<int:dispatch_id>/accept', methods=['POST'])
@login_required
def accept_dispatch(dispatch_id):
    """Принятие отправки специалистом"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        # Только специалисты могут принимать отправки
        if user.role != 'specialist':
            return jsonify({'error': 'Access denied. Only specialists can accept dispatches'}), 403
        
        dispatch = Dispatch.query.get_or_404(dispatch_id)
        
        # Проверяем, что специалист является назначенным специалистом для этой отправки
        if dispatch.specialist_id != user.id:
            return jsonify({'error': 'Access denied. This dispatch is not assigned to you'}), 403
        
        # Проверяем, что отправка в статусе PENDING
        if dispatch.status != 'PENDING':
            return jsonify({'error': f'Dispatch is already {dispatch.status}. Cannot accept.'}), 400
        
        # Обновляем статус на ACCEPTED
        dispatch.status = 'ACCEPTED'
        dispatch.updated_at = datetime.now(UTC)
        db.session.commit()
        
        logger.info(f"Dispatch {dispatch_id} accepted by specialist {user.id}")
        
        return jsonify({
            'success': True,
            'dispatch': dispatch.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error accepting dispatch: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/dispatches/<int:dispatch_id>/status', methods=['POST'])
@login_required
def update_dispatch_status(dispatch_id):
    """Обновление статуса отправки специалистом"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        # Только специалисты могут обновлять статус своих отправок
        if user.role != 'specialist':
            return jsonify({'error': 'Access denied. Only specialists can update dispatch status'}), 403
        
        dispatch = Dispatch.query.get_or_404(dispatch_id)
        
        # Проверяем, что специалист является назначенным специалистом для этой отправки
        if dispatch.specialist_id != user.id:
            return jsonify({'error': 'Access denied. This dispatch is not assigned to you'}), 403
        
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'error': 'Status is required'}), 400
        
        # Валидация статусов
        valid_statuses = ['PENDING', 'ACCEPTED', 'IN_ROUTE', 'ARRIVED', 'COMPLETED', 'CANCELLED']
        if new_status not in valid_statuses:
            return jsonify({'error': f'Invalid status. Valid statuses: {", ".join(valid_statuses)}'}), 400
        
        # Валидация переходов статусов
        current_status = dispatch.status
        valid_transitions = {
            'PENDING': ['ACCEPTED', 'CANCELLED'],
            'ACCEPTED': ['IN_ROUTE', 'CANCELLED'],
            'IN_ROUTE': ['ARRIVED', 'CANCELLED'],
            'ARRIVED': ['COMPLETED'],
            'COMPLETED': [],  # Финальный статус
            'CANCELLED': []  # Финальный статус
        }
        
        if new_status not in valid_transitions.get(current_status, []):
            return jsonify({
                'error': f'Invalid status transition. Cannot change from {current_status} to {new_status}'
            }), 400
        
        # Обновляем статус
        dispatch.status = new_status
        dispatch.updated_at = datetime.now(UTC)
        
        # Устанавливаем временные метки для определенных статусов
        if new_status == 'ARRIVED' and not dispatch.arrived_at:
            dispatch.arrived_at = datetime.now(UTC)
        elif new_status == 'COMPLETED' and not dispatch.completed_at:
            dispatch.completed_at = datetime.now(UTC)
        
        db.session.commit()
        
        logger.info(f"Dispatch {dispatch_id} status updated to {new_status} by specialist {user.id}")
        
        return jsonify({
            'success': True,
            'dispatch': dispatch.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating dispatch status: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/dispatches/<int:dispatch_id>/location', methods=['POST'])
@login_required
def update_dispatch_location(dispatch_id):
    """Обновление местоположения специалиста"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        # Только специалисты могут обновлять свое местоположение
        if user.role != 'specialist':
            return jsonify({'error': 'Access denied. Only specialists can update location'}), 403
        
        dispatch = Dispatch.query.get_or_404(dispatch_id)
        
        # Проверяем, что специалист является назначенным специалистом для этой отправки
        if dispatch.specialist_id != user.id:
            return jsonify({'error': 'Access denied. This dispatch is not assigned to you'}), 403
        
        data = request.get_json()
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if latitude is None or longitude is None:
            return jsonify({'error': 'latitude and longitude are required'}), 400
        
        # Обновляем местоположение специалиста
        dispatch.specialist_latitude = str(latitude)
        dispatch.specialist_longitude = str(longitude)
        dispatch.updated_at = datetime.now(UTC)
        
        db.session.commit()
        
        logger.info(f"Dispatch {dispatch_id} location updated by specialist {user.id}: {latitude}, {longitude}")
        
        return jsonify({
            'success': True,
            'dispatch': dispatch.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating dispatch location: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/api/dispatches/<int:dispatch_id>/route', methods=['GET'])
@login_required
def get_dispatch_route(dispatch_id):
    """Получение маршрута для отправки (используя 2GIS API)"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        dispatch = Dispatch.query.get_or_404(dispatch_id)
        
        # Проверяем права доступа
        can_view = False
        if user.role == 'admin':
            can_view = True
        elif user.id == dispatch.user_id:  # клиент
            can_view = True
        elif user.id == dispatch.specialist_id:  # специалист
            can_view = True
        elif user.role == 'operator' and dispatch.operator_id == user.id:  # оператор
            can_view = True
        
        if not can_view:
            return jsonify({'error': 'Access denied'}), 403
        
        # Если есть координаты обоих точек, получаем маршрут от 2GIS (даже если статус PENDING)
        route_data = None
        if dispatch.client_latitude and dispatch.client_longitude and dispatch.specialist_latitude and dispatch.specialist_longitude:
            try:
                api_key = app.config['TGIS_API_KEY']
                
                # Формируем URL для 2GIS Routing API
                # Формат: https://catalog.api.2gis.com/routing/7.0.0/global?key=API_KEY&point1=lon1,lat1&point2=lon2,lat2
                url = "https://catalog.api.2gis.com/routing/7.0.0/global"
                params = {
                    'key': api_key,
                    'point1': f"{dispatch.specialist_longitude},{dispatch.specialist_latitude}",
                    'point2': f"{dispatch.client_longitude},{dispatch.client_latitude}"
                }
                
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    route_data = response.json()
                else:
                    logger.warning(f"2GIS API returned status {response.status_code}: {response.text}")
            except Exception as e:
                logger.warning(f"Error getting route from 2GIS: {e}")
        
        return jsonify({
            'success': True,
            'dispatch': dispatch.to_dict(),
            'route': route_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting dispatch route: {e}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/route/<int:dispatch_id>')
@login_required
def route_page(dispatch_id):
    """Страница маршрута для клиента и специалиста"""
    try:
        user = get_current_user()
        if not user:
            flash('Требуется авторизация', 'error')
            return redirect(url_for('login'))
        
        dispatch = Dispatch.query.get_or_404(dispatch_id)
        
        # Проверяем права доступа
        can_view = False
        if user.role == 'admin':
            can_view = True
        elif user.id == dispatch.user_id:  # клиент - может видеть маршрут даже если статус PENDING (чтобы видеть адрес)
            can_view = True
        elif user.id == dispatch.specialist_id:  # специалист
            can_view = True
        elif user.role == 'operator' and dispatch.operator_id == user.id:  # оператор, отправивший специалиста
            can_view = True
        
        if not can_view:
            flash('Доступ запрещён', 'error')
            return redirect(url_for('index'))
        
        return render_template('route.html', dispatch=dispatch, user=user, config=app.config)
        
    except Exception as e:
        logger.error(f"Error loading route page: {e}", exc_info=True)
        flash('Ошибка загрузки страницы маршрута', 'error')
        return redirect(url_for('index'))


# ========== VOICE CALL ROUTES ==========

@app.route('/voice/call/<int:chat_id>')
@login_required
def voice_call_page(chat_id):
    """Страница голосового звонка"""
    try:
        user = get_current_user()
        if not user:
            return redirect(url_for('login'))
        
        chat = Chat.query.get_or_404(chat_id)
        
        # Проверяем права доступа
        if user.role == 'user':
            if chat.user_id != user.id:
                flash('Доступ запрещён', 'error')
                return redirect(url_for('index'))
        elif user.role in ['operator', 'admin']:
            if chat.status == 'ACTIVE' and chat.operator_id and chat.operator_id != user.id:
                if user.role == 'operator':
                    flash('Этот чат уже принят другим оператором', 'error')
                    return redirect(url_for('operator_dashboard'))
        
        # Определяем собеседника
        if user.role == 'user':
            callee = chat.operator if chat.operator else None
        else:
            callee = chat.user
        
        return render_template('voice_call.html', 
            chat=chat, 
            user=user,
            callee=callee,
            call_id=str(uuid.uuid4())
        )
    except Exception as e:
        logger.error(f"Error loading voice call page: {e}", exc_info=True)
        flash('Ошибка загрузки страницы звонка', 'error')
        return redirect(url_for('index'))


@app.route('/api/voice/token', methods=['POST'])
@login_required
def get_voice_token():
    """Получение токена для голосового звонка (для внешних провайдеров)"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        data = request.get_json()
        chat_id = data.get('chat_id')
        
        if not chat_id:
            return jsonify({'error': 'Missing chat_id'}), 400
        
        chat = Chat.query.get_or_404(chat_id)
        
        # Проверяем права доступа
        if user.role == 'user' and chat.user_id != user.id:
            return jsonify({'error': 'Access denied'}), 403
        elif user.role in ['operator', 'admin']:
            if chat.status == 'ACTIVE' and chat.operator_id and chat.operator_id != user.id:
                if user.role == 'operator':
                    return jsonify({'error': 'Access denied'}), 403
        
        # Генерируем токен (для WebRTC можно использовать простой UUID)
        # Для внешних провайдеров (Twilio/Agora) здесь будет генерация реального токена
        token = str(uuid.uuid4())
        
        return jsonify({
            'success': True,
            'token': token,
            'chat_id': chat_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating voice token: {e}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


# ========== WEBSOCKET HANDLERS FOR WEBRTC SIGNALING ==========

@socketio.on('connect')
def handle_connect():
    """Обработка подключения клиента"""
    user_id = session.get('user_id')
    if user_id:
        join_room(f'user_{user_id}')
        logger.info(f"User {user_id} connected to WebSocket")
        emit('connected', {'user_id': user_id})


@socketio.on('disconnect')
def handle_disconnect():
    """Обработка отключения клиента"""
    user_id = session.get('user_id')
    if user_id:
        leave_room(f'user_{user_id}')
        logger.info(f"User {user_id} disconnected from WebSocket")


@socketio.on('call_initiate')
def handle_call_initiate(data):
    """Инициация звонка"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            emit('error', {'message': 'Not authenticated'})
            return
        
        chat_id = data.get('chat_id')
        call_id = data.get('call_id')
        
        if not chat_id or not call_id:
            emit('error', {'message': 'Missing chat_id or call_id'})
            return
        
        chat = Chat.query.get_or_404(chat_id)
        
        # Определяем собеседника
        if user_id == chat.user_id:
            callee_id = chat.operator_id
        elif user_id == chat.operator_id:
            callee_id = chat.user_id
        else:
            emit('error', {'message': 'Access denied'})
            return
        
        if not callee_id:
            emit('error', {'message': 'No callee found'})
            return
        
        # Сохраняем информацию о звонке
        active_calls[call_id] = {
            'caller_id': user_id,
            'callee_id': callee_id,
            'chat_id': chat_id,
            'status': 'ringing'
        }
        
        # Отправляем сигнал собеседнику
        emit('incoming_call', {
            'call_id': call_id,
            'chat_id': chat_id,
            'caller_id': user_id
        }, room=f'user_{callee_id}')
        
        logger.info(f"Call {call_id} initiated by user {user_id} to user {callee_id}")
        
    except Exception as e:
        logger.error(f"Error initiating call: {e}", exc_info=True)
        emit('error', {'message': str(e)})


@socketio.on('call_answer')
def handle_call_answer(data):
    """Ответ на звонок"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            emit('error', {'message': 'Not authenticated'})
            return
        
        call_id = data.get('call_id')
        answer = data.get('answer')  # 'accept' or 'reject'
        
        if not call_id or call_id not in active_calls:
            emit('error', {'message': 'Call not found'})
            return
        
        call = active_calls[call_id]
        
        if call['callee_id'] != user_id:
            emit('error', {'message': 'Not authorized to answer this call'})
            return
        
        if answer == 'accept':
            call['status'] = 'active'
            # Отправляем сигнал инициатору
            emit('call_accepted', {
                'call_id': call_id
            }, room=f'user_{call["caller_id"]}')
            
            # Создаем комнату для звонка
            join_room(f'call_{call_id}')
            socketio.server.enter_room(f'user_{call["caller_id"]}', f'call_{call_id}')
            
            logger.info(f"Call {call_id} accepted by user {user_id}")
        else:
            # Отклонение звонка
            emit('call_rejected', {
                'call_id': call_id
            }, room=f'user_{call["caller_id"]}')
            
            # Удаляем звонок
            del active_calls[call_id]
            
            logger.info(f"Call {call_id} rejected by user {user_id}")
        
    except Exception as e:
        logger.error(f"Error answering call: {e}", exc_info=True)
        emit('error', {'message': str(e)})


@socketio.on('call_end')
def handle_call_end(data):
    """Завершение звонка"""
    try:
        user_id = session.get('user_id')
        call_id = data.get('call_id')
        
        if call_id and call_id in active_calls:
            call = active_calls[call_id]
            
            # Уведомляем другого участника
            other_user_id = call['callee_id'] if user_id == call['caller_id'] else call['caller_id']
            emit('call_ended', {
                'call_id': call_id
            }, room=f'user_{other_user_id}')
            
            # Удаляем звонок
            del active_calls[call_id]
            
            logger.info(f"Call {call_id} ended by user {user_id}")
        
    except Exception as e:
        logger.error(f"Error ending call: {e}", exc_info=True)


@socketio.on('webrtc_offer')
def handle_webrtc_offer(data):
    """Обработка WebRTC offer"""
    try:
        user_id = session.get('user_id')
        call_id = data.get('call_id')
        offer = data.get('offer')
        
        if call_id not in active_calls:
            emit('error', {'message': 'Call not found'})
            return
        
        call = active_calls[call_id]
        other_user_id = call['callee_id'] if user_id == call['caller_id'] else call['caller_id']
        
        # Пересылаем offer другому участнику
        emit('webrtc_offer', {
            'call_id': call_id,
            'offer': offer
        }, room=f'user_{other_user_id}')
        
    except Exception as e:
        logger.error(f"Error handling WebRTC offer: {e}", exc_info=True)
        emit('error', {'message': str(e)})


@socketio.on('webrtc_answer')
def handle_webrtc_answer(data):
    """Обработка WebRTC answer"""
    try:
        user_id = session.get('user_id')
        call_id = data.get('call_id')
        answer = data.get('answer')
        
        if call_id not in active_calls:
            emit('error', {'message': 'Call not found'})
            return
        
        call = active_calls[call_id]
        other_user_id = call['callee_id'] if user_id == call['caller_id'] else call['caller_id']
        
        # Пересылаем answer другому участнику
        emit('webrtc_answer', {
            'call_id': call_id,
            'answer': answer
        }, room=f'user_{other_user_id}')
        
    except Exception as e:
        logger.error(f"Error handling WebRTC answer: {e}", exc_info=True)
        emit('error', {'message': str(e)})


@socketio.on('webrtc_ice_candidate')
def handle_webrtc_ice_candidate(data):
    """Обработка WebRTC ICE candidate"""
    try:
        user_id = session.get('user_id')
        call_id = data.get('call_id')
        candidate = data.get('candidate')
        
        if call_id not in active_calls:
            return
        
        call = active_calls[call_id]
        other_user_id = call['callee_id'] if user_id == call['caller_id'] else call['caller_id']
        
        # Пересылаем ICE candidate другому участнику
        emit('webrtc_ice_candidate', {
            'call_id': call_id,
            'candidate': candidate
        }, room=f'user_{other_user_id}')
        
    except Exception as e:
        logger.error(f"Error handling WebRTC ICE candidate: {e}", exc_info=True)


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)


import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from datetime import datetime
from models import db, Ticket, User
from ai_client import analyze_ticket
import logging
from dotenv import load_dotenv
from functools import wraps

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

# Инициализация БД
db.init_app(app)

# Создание таблиц при первом запуске
with app.app_context():
    try:
        # Проверяем структуру таблицы tickets - есть ли колонка user_id
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tickets_columns = [col['name'] for col in inspector.get_columns('tickets')] if 'tickets' in inspector.get_table_names() else []
        
        # Если таблица tickets существует, но в ней нет колонки user_id, пересоздаём БД
        if 'tickets' in inspector.get_table_names() and 'user_id' not in tickets_columns:
            logger.info("Database schema outdated (missing user_id column). Recreating database...")
            db.drop_all()
            db.create_all()
            logger.info("Database tables recreated with new schema")
        elif 'tickets' not in inspector.get_table_names():
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
        
        return f(*args, **kwargs)
    return decorated_function


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


@app.route('/admin')
@operator_required
def admin():
    """Страница администратора - дашборд с тикетами"""
    return render_template('admin.html')


@app.route('/operator')
@operator_required
def operator_dashboard():
    """Страница оператора - дашборд с тикетами его отдела"""
    user = get_current_user()
    return render_template('operator.html', user_department=user.department if user else None)


@app.route('/specialist')
@specialist_required
def specialist_dashboard():
    """Страница специалиста - дашборд с тикетами его отдела"""
    user = get_current_user()
    return render_template('specialist.html', user_department=user.department if user else None)


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
        
        return jsonify({
            'success': True,
            'analysis': {
                'language': ai_result.get('language'),
                'summary': ai_result.get('summary'),
                'category': ai_result.get('category'),
                'priority': ai_result.get('priority', 'MEDIUM'),
                'type': ai_result.get('type', 'QUESTION'),
                'department': ai_result.get('department', 'IT'),
                'advice': ai_result.get('advice', ''),
                'auto_resolve': ai_result.get('auto_resolve', False),
                'auto_response': ai_result.get('auto_response', ''),
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
    Принимает JSON: {"text": "...", "source": "portal"}
    Требует авторизации (любой авторизованный пользователь может создать тикет)
    """
    try:
        logger.info(f"Creating ticket request from user_id: {session.get('user_id')}")
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Missing required field: text'}), 400
        
        text = data.get('text', '').strip()
        source = data.get('source', 'portal')  # portal, chat, email, phone
        
        if not text:
            return jsonify({'error': 'Text cannot be empty'}), 400
        
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
        
        # Сохраняем совет от ИИ
        if ai_result.get('advice'):
            # Если есть и auto_response и advice, объединяем их
            if ai_result.get('auto_response'):
                ticket.auto_response = f"{ai_result.get('auto_response')}\n\nСовет от ИИ:\n{ai_result.get('advice')}"
            else:
                ticket.auto_response = ai_result.get('advice')
        elif ai_result.get('auto_response'):
            ticket.auto_response = ai_result.get('auto_response')
        
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
        db.session.commit()
        
        logger.info(f"Ticket {ticket.id} created with status {ticket.status}")
        
        return jsonify({
            'success': True,
            'ticket': ticket.to_dict()
        }), 201
        
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
            if operator_view:
                if user_role != 'operator':
                    logger.warning(f"operator_view requested but user is not operator: user_id={user_id}, role={user_role}")
                    return jsonify({'error': 'Access denied. Operator view requires operator role'}), 403
                if not user_department:
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
            if my_tickets and user_role != 'user':
                logger.warning(f"my_tickets requested but user is not regular user: user_id={user_id}, role={user_role}")
                return jsonify({'error': 'Access denied. my_tickets is only for regular users'}), 403
        
        # Безопасное создание запроса
        try:
            query = Ticket.query
        except Exception as e:
            logger.error(f"Error creating query: {e}", exc_info=True)
            return jsonify({'error': 'Database connection error'}), 500
        
        # Если пользователь запрашивает свои тикеты
        if my_tickets and user and user_role == 'user' and user_id:
            try:
                query = query.filter(Ticket.user_id == user_id)
                logger.info(f"Filtering tickets for user {user_id}")
            except Exception as e:
                logger.error(f"Error filtering by user_id: {e}", exc_info=True)
        # Если это оператор, показываем только тикеты его отдела
        elif operator_view and user and user_role == 'operator' and user_department:
            try:
                query = query.filter(Ticket.department == user_department)
                logger.info(f"Filtering tickets for operator department: {user_department}")
            except Exception as e:
                logger.error(f"Error filtering by department: {e}", exc_info=True)
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
        
        from datetime import datetime
        ticket.updated_at = datetime.utcnow()
        
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


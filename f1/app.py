from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from database import Database
from gemini_client import GeminiClient
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-this-in-production')

db = Database()
gemini = GeminiClient()

@app.route('/')
def index():
    """Главная страница - редирект на логин если не авторизован"""
    if 'client_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password')
        
        if not phone or not password:
            return render_template('login.html', error='Заполните все поля')
        
        # Нормализуем номер телефона (убираем форматирование)
        phone_clean = phone.replace('+', '').replace(' ', '').replace('(', '').replace(')', '').replace('-', '')
        if phone_clean.startswith('7'):
            phone_clean = phone_clean[1:]
        phone_clean = '+7' + phone_clean
        
        client = db.get_client_by_phone(phone_clean)
        
        if client and client.get('password'):
            if db.verify_password(password, client['password']):
                session['client_id'] = client['id']
                session['client_name'] = client['full_name']
                session['client_phone'] = client['phone_number']
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error='Неверный пароль')
        else:
            return render_template('login.html', error='Клиент не найден или пароль не установлен')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Страница регистрации"""
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        city = request.form.get('city')
        street = request.form.get('street')
        house_number = request.form.get('house_number')
        contract_number = request.form.get('contract_number')
        
        # Валидация
        if not all([full_name, phone, password, city, street, house_number, contract_number]):
            return render_template('register.html', error='Заполните все обязательные поля')
        
        if password != password_confirm:
            return render_template('register.html', error='Пароли не совпадают')
        
        if len(password) < 6:
            return render_template('register.html', error='Пароль должен быть не менее 6 символов')
        
        # Нормализуем номер телефона
        phone_clean = phone.replace('+', '').replace(' ', '').replace('(', '').replace(')', '').replace('-', '')
        if phone_clean.startswith('7'):
            phone_clean = phone_clean[1:]
        phone_clean = '+7' + phone_clean
        
        # Проверка существования клиента
        existing = db.get_client_by_phone(phone_clean)
        if existing:
            return render_template('register.html', error='Клиент с таким номером телефона уже существует')
        
        existing_contract = db.get_client_by_contract_number(contract_number)
        if existing_contract:
            return render_template('register.html', error='Клиент с таким номером договора уже существует')
        
        # Создание клиента
        try:
            client_id = db.add_client(
                full_name=full_name,
                phone_number=phone_clean,
                telegram_id=None,
                city=city,
                street=street,
                house_number=house_number,
                contract_number=contract_number,
                password=password
            )
            
            session['client_id'] = client_id
            session['client_name'] = full_name
            session['client_phone'] = phone
            return redirect(url_for('dashboard'))
        except Exception as e:
            return render_template('register.html', error=f'Ошибка при регистрации: {str(e)}')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    """Главная страница клиента"""
    if 'client_id' not in session:
        return redirect(url_for('login'))
    
    client_id = session['client_id']
    client_info = db.get_client_by_phone(session['client_phone'])
    
    if not client_info:
        session.clear()
        return redirect(url_for('login'))
    
    # Получаем услуги
    services = db.get_client_services(client_id)
    
    # Проверяем сегмент сети и аварии
    segment = db.get_segment_by_address(
        client_info['city'],
        client_info['street'],
        client_info['house_number']
    )
    
    outage_info = None
    if segment:
        outage = db.get_active_outage_by_segment(segment['id'])
        if outage:
            outage_info = {**outage, 'node_name': segment.get('node_name', 'не указан')}
    
    # Получаем последние заявки
    requests = db.get_client_requests(client_id)[:5]
    
    return render_template('dashboard.html', 
                         client=client_info,
                         services=services,
                         outage=outage_info,
                         requests=requests)

@app.route('/tickets')
def tickets():
    """Страница с обращениями"""
    if 'client_id' not in session:
        return redirect(url_for('login'))
    
    client_id = session['client_id']
    client_info = db.get_client_by_phone(session['client_phone'])
    
    # Получаем заявки из системы
    requests = db.get_client_requests(client_id)
    
    # Получаем обращения из бота (если есть telegram_id)
    tickets_list = []
    if client_info.get('telegram_id'):
        tickets_list = db.get_user_tickets(client_info['telegram_id'])
    
    return render_template('tickets.html', 
                         client=client_info,
                         requests=requests,
                         tickets=tickets_list)

@app.route('/create_ticket', methods=['POST'])
def create_ticket():
    """Создание обращения через веб-интерфейс"""
    if 'client_id' not in session:
        return jsonify({'error': 'Не авторизован'}), 401
    
    client_id = session['client_id']
    client_info = db.get_client_by_phone(session['client_phone'])
    
    if not client_info:
        return jsonify({'error': 'Клиент не найден'}), 404
    
    data = request.get_json()
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({'error': 'Сообщение не может быть пустым'}), 400
    
    # Получаем услуги клиента
    services_info = db.get_client_services(client_id)
    
    # Проверяем сегмент сети и аварии
    segment = db.get_segment_by_address(
        client_info['city'],
        client_info['street'],
        client_info['house_number']
    )
    
    outage_info = None
    if segment:
        outage = db.get_active_outage_by_segment(segment['id'])
        if outage:
            outage_info = {**outage, 'node_name': segment.get('node_name', 'не указан')}
    
    # Получаем историю диалога (если есть telegram_id)
    conversation_history = []
    if client_info.get('telegram_id'):
        conversation_history = db.get_user_conversation_history(client_info['telegram_id'])
    
    # Анализируем проблему с помощью Gemini
    analysis = gemini.analyze_problem(
        user_message,
        conversation_history,
        client_info=client_info,
        outage_info=outage_info,
        services_info=services_info
    )
    
    language = analysis.get('language', 'ru')
    
    # Сохраняем сообщение в историю (если есть telegram_id)
    if client_info.get('telegram_id'):
        db.add_conversation(client_info['telegram_id'], user_message, is_user_message=True)
    
    # Обработка результата анализа
    result = {
        'analysis': analysis,
        'language': language
    }
    
    # Если есть авария и проблема связана с отсутствием услуги
    if outage_info and analysis.get('problem_type') in ['авария', 'отсутствие услуги']:
        result['type'] = 'outage'
        result['outage'] = outage_info
        return jsonify(result)
    
    # Если проблема может быть решена самостоятельно
    if analysis.get('can_solve_self', False) and analysis.get('diagnostic_steps'):
        ticket_id = db.create_ticket(
            user_id=client_info.get('telegram_id') or 0,
            message_text=user_message,
            problem_category=analysis.get('category'),
            ai_solution=analysis.get('solution')
        )
        result['type'] = 'diagnostic'
        result['ticket_id'] = ticket_id
        result['diagnostic_steps'] = analysis.get('diagnostic_steps', [])
        return jsonify(result)
    
    # Если нужен инженер - создаем заявку
    if analysis.get('needs_engineer', False):
        ticket_id = db.create_ticket(
            user_id=client_info.get('telegram_id') or 0,
            message_text=user_message,
            problem_category=analysis.get('category'),
            ai_solution=analysis.get('solution')
        )
        
        request_id = db.create_request(
            client_id=client_id,
            channel='web',
            problem_type=analysis.get('problem_type', analysis.get('category', 'другое')),
            status='open',
            comment=f"Услуга: {analysis.get('service', 'не указана')}, Срочность: {analysis.get('urgency', 'средняя')}"
        )
        
        # Генерируем время визита
        now = datetime.now()
        visit_time_start = now.replace(hour=15, minute=0, second=0, microsecond=0)
        if now.hour >= 15:
            visit_time_start = (now + timedelta(days=1)).replace(hour=15, minute=0, second=0, microsecond=0)
        visit_time_end = visit_time_start + timedelta(hours=4)
        
        result['type'] = 'engineer'
        result['ticket_id'] = ticket_id
        result['request_id'] = request_id
        result['visit_time_start'] = visit_time_start.strftime('%d.%m.%Y %H:%M')
        result['visit_time_end'] = visit_time_end.strftime('%H:%M')
        return jsonify(result)
    
    # Обычный ответ
    ticket_id = db.create_ticket(
        user_id=client_info.get('telegram_id') or 0,
        message_text=user_message,
        problem_category=analysis.get('category'),
        ai_solution=analysis.get('solution')
    )
    result['type'] = 'normal'
    result['ticket_id'] = ticket_id
    return jsonify(result)

@app.route('/diagnostic_step', methods=['POST'])
def diagnostic_step():
    """Обработка шага диагностики"""
    if 'client_id' not in session:
        return jsonify({'error': 'Не авторизован'}), 401
    
    data = request.get_json()
    ticket_id = data.get('ticket_id')
    step = data.get('step', 0)
    solved = data.get('solved', False)
    
    if solved:
        db.update_ticket(ticket_id, status='resolved', resolved_at=datetime.now())
        return jsonify({'success': True, 'message': 'Проблема решена!'})
    
    # Если все шаги пройдены, создаем заявку
    # (логика будет в JS на клиенте)
    return jsonify({'success': True, 'next_step': step + 1})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

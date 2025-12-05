import os
import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv
from database import Database
from gemini_client import GeminiClient

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()

class KazakhtelecomBot:
    def __init__(self):
        self.db = Database()
        self.gemini = GeminiClient()
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
        
        self.application = Application.builder().token(self.bot_token).build()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("my_tickets", self.my_tickets_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    def _get_main_keyboard(self):
        """Клавиатура быстрых действий"""
        keyboard = [
            [
                KeyboardButton("📋 Мой лицевой счет"),
                KeyboardButton("📞 Мои обращения")
            ],
            [
                KeyboardButton("❓ Помощь"),
                KeyboardButton("ℹ️ О боте")
            ]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        self.db.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        # Проверяем, есть ли уже привязанный клиент
        client_info = self.db.get_client_by_telegram_id(user.id)
        
        if client_info:
            welcome_message = f"""👋 Здравствуйте, {client_info.get('full_name', user.first_name)}!

✅ Вы авторизованы как клиент Казахтелекома
📋 Лицевой счет: {client_info.get('contract_number')}

Я могу помочь вам:
• Решить проблемы с интернетом, телефонией и телевидением
• Ответить на вопросы об услугах
• Принять ваше обращение и передать его инженеру

Просто опишите вашу проблему, и я постараюсь помочь!"""
        else:
            welcome_message = f"""👋 Здравствуйте, {user.first_name}!

Я - умный помощник службы поддержки Казахтелекома.

🔐 **Для начала работы нужен ваш лицевой счет (номер договора)**

Пожалуйста, введите ваш лицевой счет в формате: **KT123456**

Или используйте кнопку ниже для входа."""
        
        await update.message.reply_text(
            welcome_message,
            reply_markup=self._get_main_keyboard(),
            parse_mode='Markdown'
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """📋 Справка по использованию бота

Я - AI Help Desk для Казахтелекома. Вот что я умею:

1. **Анализ проблем** - опишите вашу проблему, и я определю её категорию
2. **Автоматические решения** - для простых проблем я предложу решение
3. **Передача инженеру** - сложные проблемы автоматически передаются специалисту

**Категории проблем:**
• Интернет (скорость, подключение, настройки)
• Телефония (звонки, настройки)
• Телевидение (каналы, качество сигнала)
• Оборудование (модемы, роутеры, приставки)
• Оплата (счета, платежи, тарифы)
• Другое

**Команды:**
/start - начать работу с ботом
/my_tickets - посмотреть мои обращения
/help - эта справка

Просто напишите мне о вашей проблеме!"""
        
        await update.message.reply_text(
            help_text,
            reply_markup=self._get_main_keyboard()
        )
    
    async def my_tickets_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /my_tickets"""
        user_id = update.effective_user.id
        
        # Получаем клиента
        client_info = self.db.get_client_by_telegram_id(user_id)
        
        if not client_info:
            tickets = self.db.get_user_tickets(user_id)
            if not tickets:
                await update.message.reply_text(
                    "У вас пока нет обращений.",
                    reply_markup=self._get_main_keyboard()
                )
                return
            
            message = "📋 Ваши обращения:\n\n"
            for ticket in tickets:
                status_emoji = "✅" if ticket['status'] == 'resolved' else "⏳" if ticket['status'] == 'in_progress' else "🆕"
                message += f"{status_emoji} #{ticket['id']}\n"
                message += f"Проблема: {ticket['message'][:50]}...\n"
                message += f"Категория: {ticket['category'] or 'не определена'}\n"
                message += f"Статус: {ticket['status']}\n"
                message += f"Дата: {ticket['created_at']}\n\n"
            
            await update.message.reply_text(
                message,
                reply_markup=self._get_main_keyboard()
            )
        else:
            # Показываем заявки из системы
            requests = self.db.get_client_requests(client_info['id'])
            tickets = self.db.get_user_tickets(user_id)
            
            if not requests and not tickets:
                await update.message.reply_text("У вас пока нет обращений.")
                return
            
            message = f"📋 Ваши обращения:\n\n"
            message += f"👤 Клиент: {client_info.get('full_name', 'не указано')}\n"
            message += f"📋 Договор: {client_info.get('contract_number', 'не указан')}\n\n"
            
            if requests:
                message += "📝 Заявки в системе:\n"
                for req in requests[:10]:  # Показываем последние 10
                    status_emoji = "✅" if req['status'] == 'closed' else "⏳" if req['status'] == 'in_work' else "🆕"
                    message += f"{status_emoji} Заявка #{req['id']}\n"
                    message += f"Тип: {req['problem_type']}\n"
                    message += f"Статус: {req['status']}\n"
                    message += f"Дата: {req['created_at']}\n\n"
            
            if tickets:
                message += "💬 Обращения в боте:\n"
                for ticket in tickets[:5]:  # Показываем последние 5
                    status_emoji = "✅" if ticket['status'] == 'resolved' else "⏳" if ticket['status'] == 'in_progress' else "🆕"
                    message += f"{status_emoji} #{ticket['id']}\n"
                    message += f"Проблема: {ticket['message'][:40]}...\n"
                    message += f"Статус: {ticket['status']}\n\n"
            
            await update.message.reply_text(
                message,
                reply_markup=self._get_main_keyboard()
            )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback кнопок"""
        query = update.callback_query
        await query.answer()
        
        data = query.data.split('_')
        action = data[0]
        user_id = query.from_user.id
        
        if action == 'diagnostic':
            step = int(data[1])
            result = data[2]  # 'yes' or 'no'
            ticket_id = int(data[3]) if len(data) > 3 else None
            
            # Сохраняем результат диагностики
            context.user_data[f'diagnostic_step_{step}'] = result
            
            if result == 'yes':
                await query.edit_message_text(
                    "✅ Отлично! Проблема решена?\n\n"
                    "Если проблема осталась, напишите мне об этом."
                )
            else:
                # Переходим к следующему шагу или создаем заявку
                await self._continue_diagnostic(query, step, ticket_id, user_id, context)
    
    async def _continue_diagnostic(self, query, current_step: int, ticket_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Продолжение пошаговой диагностики"""
        # Здесь можно добавить больше шагов
        steps = [
            "1. Перезапустите роутер (выключите на 30 секунд и включите снова)",
            "2. Проверьте кабель подключения",
            "3. Проверьте оплату услуг",
            "4. Проверьте индикаторы на оборудовании"
        ]
        
        if current_step < len(steps):
            next_step = current_step + 1
            keyboard = [
                [
                    InlineKeyboardButton("✅ Помогло", callback_data=f"diagnostic_{next_step}_yes_{ticket_id}"),
                    InlineKeyboardButton("❌ Не помогло", callback_data=f"diagnostic_{next_step}_no_{ticket_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"🔧 Шаг {next_step}:\n\n{steps[next_step-1]}\n\nПомогло?",
                reply_markup=reply_markup
            )
        else:
            # Все шаги пройдены, создаем заявку
            await self._create_ticket_from_diagnostic(query, ticket_id, user_id, context)
    
    async def _create_ticket_from_diagnostic(self, query, ticket_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Создание заявки после диагностики"""
        client_info = self.db.get_client_by_telegram_id(user_id)
        
        if not client_info:
            await query.edit_message_text(
                "Для создания заявки мне нужна дополнительная информация.\n\n"
                "Пожалуйста, укажите:\n"
                "• Ваш адрес\n"
                "• Номер договора (лицевой счет)\n"
                "• Когда началась проблема"
            )
            return
        
        # Создаем заявку
        request_id = self.db.create_request(
            client_id=client_info['id'],
            channel='telegram',
            problem_type='техническая проблема',
            status='open',
            comment='Диагностика не помогла, требуется выезд инженера'
        )
        
        # Генерируем время визита
        now = datetime.now()
        visit_time_start = now.replace(hour=15, minute=0, second=0, microsecond=0)
        if now.hour >= 15:
            visit_time_start = (now + timedelta(days=1)).replace(hour=15, minute=0, second=0, microsecond=0)
        visit_time_end = visit_time_start + timedelta(hours=4)
        
        await query.edit_message_text(
            f"✅ Заявка №{request_id} принята!\n\n"
            f"👨‍💼 Инженер приедет {visit_time_start.strftime('%d.%m.%Y')} "
            f"с {visit_time_start.strftime('%H:%M')} до {visit_time_end.strftime('%H:%M')}\n\n"
            f"📍 Адрес: {client_info.get('city')}, {client_info.get('street')}, д.{client_info.get('house_number')}\n\n"
            f"Мы уведомим вас о статусе заявки."
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений с улучшенной логикой"""
        user = update.effective_user
        user_message = update.message.text
        
        # Сохраняем пользователя
        self.db.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        # Обработка быстрых действий
        if user_message == "📋 Мой лицевой счет":
            client_info = self.db.get_client_by_telegram_id(user.id)
            if client_info:
                await update.message.reply_text(
                    f"📋 Ваш лицевой счет: **{client_info.get('contract_number')}**\n\n"
                    f"👤 Клиент: {client_info.get('full_name')}\n"
                    f"📍 Адрес: {client_info.get('city')}, {client_info.get('street')}, д.{client_info.get('house_number')}",
                    reply_markup=self._get_main_keyboard(),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "🔐 Вы не авторизованы.\n\n"
                    "Пожалуйста, введите ваш лицевой счет в формате: **KT123456**",
                    reply_markup=self._get_main_keyboard(),
                    parse_mode='Markdown'
                )
            return
        
        if user_message == "📞 Мои обращения":
            await self.my_tickets_command(update, context)
            return
        
        if user_message == "❓ Помощь":
            await self.help_command(update, context)
            return
        
        if user_message == "ℹ️ О боте":
            await update.message.reply_text(
                "ℹ️ **О боте**\n\n"
                "Я - AI Help Desk для Казахтелекома.\n\n"
                "Я могу:\n"
                "• Анализировать проблемы\n"
                "• Проверять аварии в вашем районе\n"
                "• Предлагать пошаговые решения\n"
                "• Создавать заявки для инженеров\n\n"
                "Поддерживаю русский и казахский языки!",
                reply_markup=self._get_main_keyboard(),
                parse_mode='Markdown'
            )
            return
        
        # Проверяем, не является ли сообщение лицевым счетом
        contract_pattern = r'\bKT\d{6}\b'
        contract_match = re.search(contract_pattern, user_message.upper())
        
        if contract_match:
            contract_number = contract_match.group()
            await self._process_login(update, user.id, contract_number, context)
            return
        
        # ВАЖНО: Проверяем, есть ли лицевой счет перед анализом проблемы
        client_info = self.db.get_client_by_telegram_id(user.id)
        
        if not client_info:
            # Просим ввести лицевой счет
            await update.message.reply_text(
                "🔐 **Для анализа проблемы нужен ваш лицевой счет**\n\n"
                "Пожалуйста, введите ваш лицевой счет (номер договора) в формате: **KT123456**\n\n"
                "Или используйте команду: /login KT123456",
                reply_markup=self._get_main_keyboard(),
                parse_mode='Markdown'
            )
            return
        
        # Продолжаем обработку проблемы (клиент авторизован)
        await self._process_problem(update, context, user, user_message, client_info)
    
    async def _process_login(self, update: Update, telegram_id: int, contract_number: str, context: ContextTypes.DEFAULT_TYPE):
        """Обработка входа по лицевому счету"""
        client_info = self.db.get_client_by_contract_number(contract_number)
        
        if client_info:
            # Привязываем telegram_id к клиенту
            success = self.db.link_telegram_to_client(telegram_id, contract_number)
            if success:
                # Получаем обновленную информацию
                client_info = self.db.get_client_by_telegram_id(telegram_id)
                services = self.db.get_client_services(client_info['id'])
                
                response = f"✅ **Авторизация успешна!**\n\n"
                response += f"👤 Клиент: {client_info.get('full_name')}\n"
                response += f"📞 Телефон: {client_info.get('phone_number')}\n"
                response += f"📋 Лицевой счет: {client_info.get('contract_number')}\n"
                response += f"📍 Адрес: {client_info.get('city')}, {client_info.get('street')}, д.{client_info.get('house_number')}\n\n"
                
                if services:
                    response += "📦 Ваши услуги:\n"
                    for service in services:
                        status = "✅ Активна" if service.get('is_active') else "❌ Неактивна"
                        blocked = " 🔒 Заблокирована" if service.get('is_blocked') else ""
                        debt = f" (Долг: {service.get('debt_amount', 0):.0f} тг)" if service.get('is_blocked') else ""
                        response += f"• {service.get('tariff_name')}: {status}{blocked}{debt}\n"
                
                response += "\nТеперь я могу помочь вам с вашими услугами!"
                await update.message.reply_text(
                    response,
                    reply_markup=self._get_main_keyboard(),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ Ошибка при привязке аккаунта. Попробуйте еще раз.",
                    reply_markup=self._get_main_keyboard()
                )
        else:
            await update.message.reply_text(
                f"❌ Клиент с номером договора {contract_number} не найден.\n\n"
                "Проверьте правильность номера договора и попробуйте еще раз.\n"
                "Формат: KT123456 (без пробелов)",
                reply_markup=self._get_main_keyboard()
            )
    
    async def _process_problem(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user, user_message: str, client_info: Dict):
        """Обработка проблемы (клиент уже авторизован)"""
        services_info = None
        outage_info = None
        segment = None
        
        if client_info:
            # Получаем услуги клиента
            services_info = self.db.get_client_services(client_info['id'])
            
            # Проверяем сегмент сети и аварии
            segment = self.db.get_segment_by_address(
                client_info['city'],
                client_info['street'],
                client_info['house_number']
            )
            
            if segment:
                # Проверяем активные аварии на этом сегменте
                outage = self.db.get_active_outage_by_segment(segment['id'])
                if outage:
                    outage_info = {
                        **outage,
                        'node_name': segment.get('node_name', 'не указан')
                    }
        
        # Получаем историю диалога для контекста
        conversation_history = self.db.get_user_conversation_history(user.id)
        
        # Сохраняем сообщение пользователя
        self.db.add_conversation(user.id, user_message, is_user_message=True)
        
        # Показываем, что бот печатает
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        
        # Анализируем проблему с помощью Gemini
        analysis = self.gemini.analyze_problem(
            user_message, 
            conversation_history,
            client_info=client_info,
            outage_info=outage_info,
            services_info=services_info
        )
        
        language = analysis.get('language', 'ru')
        
        # ВАЖНО: Если есть авария и проблема связана с отсутствием услуги - НЕ создаем заявку
        if outage_info and analysis.get('problem_type') in ['авария', 'отсутствие услуги']:
            await self._handle_outage_response(update, outage_info, analysis, language)
            return
        
        # Если проблема может быть решена самостоятельно - предлагаем пошаговую диагностику
        if analysis.get('can_solve_self', False) and analysis.get('diagnostic_steps'):
            await self._handle_self_diagnostic(update, analysis, language, context)
            return
        
        # Если нужен инженер - создаем заявку
        if analysis.get('needs_engineer', False):
            await self._handle_engineer_request(update, analysis, client_info, user.id, language)
            return
        
        # Обычный ответ
        await self._handle_normal_response(update, analysis, client_info, language)
    
    async def _handle_outage_response(self, update: Update, outage_info: Dict, analysis: Dict, language: str):
        """Обработка ответа при наличии аварии"""
        from datetime import datetime
        
        estimated_end = outage_info.get('estimated_end', '')
        if estimated_end:
            try:
                if isinstance(estimated_end, str):
                    estimated_end = datetime.fromisoformat(estimated_end.replace('Z', '+00:00'))
                hours_left = (estimated_end - datetime.now()).total_seconds() / 3600
                if hours_left > 0:
                    time_str = f"примерно через {int(hours_left)} час(ов)"
                else:
                    time_str = "скоро"
            except:
                time_str = "в ближайшее время"
        else:
            time_str = "в ближайшее время"
        
        if language == 'kk':
            response = f"⚠️ **Сіздің ауданыңызда авариялық жұмыстар жүргізілуде.**\n\n"
            response += f"Себебі: {outage_info.get('reason', 'көрсетілмеген')}\n"
            response += f"Интернет {time_str} пайда болады.\n\n"
            response += "✅ Заявка қажет емес - бұл аймақтық мәселе."
        else:
            response = f"⚠️ **В вашем районе ведутся восстановительные работы.**\n\n"
            response += f"Причина: {outage_info.get('reason', 'не указана')}\n"
            response += f"Интернет появится {time_str}.\n\n"
            response += "✅ Заявка не требуется - это районная проблема."
        
        await update.message.reply_text(
            response,
            reply_markup=self._get_main_keyboard(),
            parse_mode='Markdown'
        )
    
    async def _handle_self_diagnostic(self, update: Update, analysis: Dict, language: str, context: ContextTypes.DEFAULT_TYPE):
        """Обработка пошаговой диагностики"""
        diagnostic_steps = analysis.get('diagnostic_steps', [])
        
        if not diagnostic_steps:
            # Если шагов нет, используем стандартные
            diagnostic_steps = [
                "Перезапустите роутер (выключите на 30 секунд и включите снова)",
                "Проверьте кабель подключения",
                "Проверьте оплату услуг",
                "Проверьте индикаторы на оборудовании"
            ]
        
        # Создаем обращение для отслеживания
        ticket_id = self.db.create_ticket(
            user_id=update.effective_user.id,
            message_text=update.message.text,
            problem_category=analysis.get('category'),
            ai_solution=analysis.get('solution')
        )
        
        # Первый шаг диагностики
        first_step = diagnostic_steps[0] if diagnostic_steps else "Перезапустите роутер"
        
        if language == 'kk':
            response = f"🔧 **Мәселені шешуге көмектесейік.**\n\n"
            response += f"1-қадам:\n{first_step}\n\n"
            response += "Көмектесті ме?"
        else:
            response = f"🔧 **Давайте попробуем решить проблему.**\n\n"
            response += f"Шаг 1:\n{first_step}\n\n"
            response += "Помогло?"
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Помогло", callback_data=f"diagnostic_1_yes_{ticket_id}"),
                InlineKeyboardButton("❌ Не помогло", callback_data=f"diagnostic_1_no_{ticket_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            response,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def _handle_engineer_request(self, update: Update, analysis: Dict, client_info: Optional[Dict], user_id: int, language: str):
        """Обработка запроса инженера с автоматическим созданием заявки"""
        # Создаем обращение
        ticket_id = self.db.create_ticket(
            user_id=user_id,
            message_text=update.message.text,
            problem_category=analysis.get('category'),
            ai_solution=analysis.get('solution')
        )
        
        # Создаем заявку
        request_id = None
        if client_info:
            request_id = self.db.create_request(
                client_id=client_info['id'],
                channel='telegram',
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
            
            if language == 'kk':
                response = f"✅ **Заявка №{request_id} қабылданды!**\n\n"
                response += f"👨‍💼 Инженер {visit_time_start.strftime('%d.%m.%Y')} күні "
                response += f"{visit_time_start.strftime('%H:%M')} - {visit_time_end.strftime('%H:%M')} аралығында келеді.\n\n"
                response += f"📍 Мекен-жай: {client_info.get('city')}, {client_info.get('street')}, д.{client_info.get('house_number')}\n\n"
                response += "Біз сізге заявканың статусы туралы хабарлаймыз."
            else:
                response = f"✅ **Заявка №{request_id} принята!**\n\n"
                response += f"👨‍💼 Инженер приедет {visit_time_start.strftime('%d.%m.%Y')} "
                response += f"с {visit_time_start.strftime('%H:%M')} до {visit_time_end.strftime('%H:%M')}\n\n"
                response += f"📍 Адрес: {client_info.get('city')}, {client_info.get('street')}, д.{client_info.get('house_number')}\n\n"
                response += "Мы уведомим вас о статусе заявки."
        else:
            # Клиент не найден, просим дополнительную информацию
            if language == 'kk':
                response = f"📝 **Заявка құру үшін қосымша ақпарат қажет.**\n\n"
                response += "Көрсетіңіз:\n"
                response += "• Мекен-жайыңыз\n"
                response += "• Келісім-шарт нөмірі (жеке шот)\n"
                response += "• Мәселе қашан басталды"
            else:
                response = f"📝 **Для создания заявки нужна дополнительная информация.**\n\n"
                response += "Пожалуйста, укажите:\n"
                response += "• Ваш адрес\n"
                response += "• Номер договора (лицевой счет)\n"
                response += "• Когда началась проблема"
        
        # Обновляем статус обращения
        self.db.update_ticket(
            ticket_id=ticket_id,
            status='assigned',
            assigned_engineer=analysis.get('engineer_specialization', 'общая поддержка')
        )
        
        await update.message.reply_text(
            response,
            reply_markup=self._get_main_keyboard(),
            parse_mode='Markdown'
        )
    
    async def _handle_normal_response(self, update: Update, analysis: Dict, client_info: Optional[Dict], language: str):
        """Обработка обычного ответа"""
        solution = analysis.get('solution', 'Решение в процессе')
        
        if language == 'kk':
            response = f"✅ **Шешім:**\n{solution}\n\n"
            response += "Егер мәселе шешілмесе, маған қайта жазыңыз."
        else:
            response = f"✅ **Решение:**\n{solution}\n\n"
            response += "Если проблема не решена, напишите мне еще раз."
        
        await update.message.reply_text(
            response,
            reply_markup=self._get_main_keyboard(),
            parse_mode='Markdown'
        )
    
    async def check_and_notify_requests(self):
        """Периодическая проверка и уведомления о статусе заявок"""
        # Эта функция может быть вызвана по расписанию
        # Для простоты оставляем заглушку
        pass
    
    def run(self):
        """Запуск бота"""
        logger.info("Запуск бота Казахтелеком...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    try:
        bot = KazakhtelecomBot()
        bot.run()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")


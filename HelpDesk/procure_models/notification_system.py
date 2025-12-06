"""
Модуль для системы уведомлений (email, SMS, мессенджеры)
"""
from typing import Dict, List, Optional, Any
import json
from datetime import datetime
import logging
import os

# Опциональные импорты
try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    SMTP_AVAILABLE = True
except ImportError:
    SMTP_AVAILABLE = False
    logging.warning("smtplib недоступен. Email уведомления недоступны.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NotificationSystem:
    """Система уведомлений для AI-Procure"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация системы уведомлений
        
        Args:
            config: Конфигурация (SMTP настройки, API ключи и т.д.)
        """
        self.config = config or {}
        self.notification_history = []
        self.notification_file = "data/notifications.json"
        self._ensure_data_dir()
        
        # Настройки SMTP
        self.smtp_config = {
            'enabled': self.config.get('smtp_enabled', False),
            'host': self.config.get('smtp_host', 'smtp.gmail.com'),
            'port': self.config.get('smtp_port', 587),
            'username': self.config.get('smtp_username', ''),
            'password': self.config.get('smtp_password', ''),
            'from_email': self.config.get('from_email', '')
        }
        
        # Настройки SMS (требует интеграции с провайдером)
        self.sms_config = {
            'enabled': self.config.get('sms_enabled', False),
            'provider': self.config.get('sms_provider', ''),
            'api_key': self.config.get('sms_api_key', '')
        }
    
    def _ensure_data_dir(self):
        """Создаёт директорию для данных если не существует"""
        os.makedirs(os.path.dirname(self.notification_file), exist_ok=True)
    
    def send_email(self, to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        """
        Отправляет email уведомление
        
        Args:
            to_email: Email получателя
            subject: Тема письма
            body: Текст письма
            html_body: HTML версия письма (опционально)
            
        Returns:
            True если отправлено успешно, False иначе
        """
        if not self.smtp_config['enabled'] or not SMTP_AVAILABLE:
            logger.warning("Email уведомления отключены или SMTP недоступен")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_config['from_email']
            msg['To'] = to_email
            
            # Добавляем текстовую версию
            text_part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # Добавляем HTML версию если есть
            if html_body:
                html_part = MIMEText(html_body, 'html', 'utf-8')
                msg.attach(html_part)
            
            # Отправляем
            with smtplib.SMTP(self.smtp_config['host'], self.smtp_config['port']) as server:
                server.starttls()
                server.login(self.smtp_config['username'], self.smtp_config['password'])
                server.send_message(msg)
            
            # Сохраняем в историю
            self._save_notification({
                'type': 'email',
                'to': to_email,
                'subject': subject,
                'timestamp': datetime.now().isoformat(),
                'status': 'sent'
            })
            
            logger.info(f"Email отправлен: {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при отправке email: {e}")
            self._save_notification({
                'type': 'email',
                'to': to_email,
                'subject': subject,
                'timestamp': datetime.now().isoformat(),
                'status': 'failed',
                'error': str(e)
            })
            return False
    
    def send_sms(self, phone_number: str, message: str) -> bool:
        """
        Отправляет SMS уведомление
        
        Args:
            phone_number: Номер телефона получателя
            message: Текст сообщения
            
        Returns:
            True если отправлено успешно, False иначе
        """
        if not self.sms_config['enabled']:
            logger.warning("SMS уведомления отключены")
            return False
        
        # TODO: Интеграция с SMS провайдером (Twilio, SMS.ru и т.д.)
        logger.info(f"SMS отправка (симуляция): {phone_number} - {message}")
        
        self._save_notification({
            'type': 'sms',
            'to': phone_number,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'status': 'sent'
        })
        
        return True
    
    def notify_new_tender(self, user_email: str, tender_info: Dict[str, Any]) -> bool:
        """
        Уведомляет о новом тендере
        
        Args:
            user_email: Email пользователя
            tender_info: Информация о тендере
            
        Returns:
            True если отправлено успешно
        """
        subject = f"Новый тендер: {tender_info.get('subject', {}).get('description', 'Без названия')[:50]}"
        
        body = f"""
Новый тендер обнаружен!

Заказчик: {tender_info.get('customer', {}).get('name', 'Не указан')}
Предмет закупки: {tender_info.get('subject', {}).get('description', 'Не указан')}
Бюджет: {tender_info.get('budget', {}).get('amount', 'Не указан')} {tender_info.get('budget', {}).get('currency', '')}
Срок подачи заявок: {tender_info.get('timeline', {}).get('application_end', 'Не указан')}

ID тендера: {tender_info.get('metadata', {}).get('tender_id', 'Не указан')}

Просмотреть детали: http://localhost:5000/ai-procure
"""
        
        html_body = f"""
<html>
<body>
<h2>Новый тендер обнаружен!</h2>
<p><strong>Заказчик:</strong> {tender_info.get('customer', {}).get('name', 'Не указан')}</p>
<p><strong>Предмет закупки:</strong> {tender_info.get('subject', {}).get('description', 'Не указан')}</p>
<p><strong>Бюджет:</strong> {tender_info.get('budget', {}).get('amount', 'Не указан')} {tender_info.get('budget', {}).get('currency', '')}</p>
<p><strong>Срок подачи заявок:</strong> {tender_info.get('timeline', {}).get('application_end', 'Не указан')}</p>
<p><strong>ID тендера:</strong> {tender_info.get('metadata', {}).get('tender_id', 'Не указан')}</p>
<a href="http://localhost:5000/ai-procure">Просмотреть детали</a>
</body>
</html>
"""
        
        return self.send_email(user_email, subject, body, html_body)
    
    def notify_risk_detected(self, user_email: str, tender_info: Dict[str, Any], risk_analysis: Dict[str, Any]) -> bool:
        """
        Уведомляет о выявленных рисках в тендере
        
        Args:
            user_email: Email пользователя
            tender_info: Информация о тендере
            risk_analysis: Результаты анализа рисков
            
        Returns:
            True если отправлено успешно
        """
        risk_level = risk_analysis.get('overall_risk_level', 'неизвестно')
        risk_score = risk_analysis.get('risk_score', 0)
        
        subject = f"⚠️ Риски обнаружены в тендере (Уровень: {risk_level})"
        
        risks_list = "\n".join([
            f"- {r.get('type', 'Неизвестно')}: {r.get('description', '')[:100]}"
            for r in risk_analysis.get('risks', [])[:5]
        ])
        
        body = f"""
Обнаружены риски в тендере!

Тендер: {tender_info.get('metadata', {}).get('tender_id', 'Не указан')}
Заказчик: {tender_info.get('customer', {}).get('name', 'Не указан')}

Уровень риска: {risk_level} (Оценка: {risk_score}/100)
Прозрачность: {risk_analysis.get('transparency_score', 0)}/100

Выявленные риски:
{risks_list}

Рекомендуется провести дополнительный анализ перед участием.

Просмотреть детальный отчёт: http://localhost:5000/ai-procure
"""
        
        return self.send_email(user_email, subject, body)
    
    def notify_price_anomaly(self, user_email: str, tender_info: Dict[str, Any], price_analysis: Dict[str, Any]) -> bool:
        """
        Уведомляет об аномалиях в цене
        
        Args:
            user_email: Email пользователя
            tender_info: Информация о тендере
            price_analysis: Результаты анализа цен
            
        Returns:
            True если отправлено успешно
        """
        anomaly_type = price_analysis.get('anomaly_type', 'неизвестно')
        deviation = price_analysis.get('market_deviation', 0)
        
        subject = f"💰 Аномалия цены обнаружена: {anomaly_type}"
        
        body = f"""
Обнаружена аномалия в цене тендера!

Тендер: {tender_info.get('metadata', {}).get('tender_id', 'Не указан')}
Заказчик: {tender_info.get('customer', {}).get('name', 'Не указан')}

Тип аномалии: {anomaly_type}
Отклонение от рынка: {deviation:.1f}%
Рыночная цена: {price_analysis.get('market_price', 'Не указано')}
Цена тендера: {tender_info.get('budget', {}).get('amount', 'Не указано')}

Рекомендация: {price_analysis.get('recommendation', 'Требуется дополнительный анализ')}

Просмотреть детальный анализ: http://localhost:5000/ai-procure
"""
        
        return self.send_email(user_email, subject, body)
    
    def notify_affiliation_detected(self, user_email: str, tender_info: Dict[str, Any], affiliation_data: Dict[str, Any]) -> bool:
        """
        Уведомляет об обнаруженной аффилированности
        
        Args:
            user_email: Email пользователя
            tender_info: Информация о тендере
            affiliation_data: Данные об аффилированности
            
        Returns:
            True если отправлено успешно
        """
        connections = affiliation_data.get('suspicious_connections', [])
        
        subject = "🔗 Обнаружена аффилированность в тендере"
        
        connections_list = "\n".join([
            f"- {c.get('entity1', '')} ↔ {c.get('entity2', '')} ({c.get('connection_type', '')}) - Риск: {c.get('risk_level', '')}"
            for c in connections[:5]
        ])
        
        body = f"""
Обнаружена аффилированность в тендере!

Тендер: {tender_info.get('metadata', {}).get('tender_id', 'Не указан')}
Заказчик: {tender_info.get('customer', {}).get('name', 'Не указан')}

Подозрительные связи:
{connections_list}

Это может указывать на потенциальные риски коррупции или сговора.

Рекомендуется провести дополнительное расследование.

Просмотреть детальный анализ: http://localhost:5000/ai-procure
"""
        
        return self.send_email(user_email, subject, body)
    
    def _save_notification(self, notification: Dict[str, Any]):
        """Сохраняет уведомление в историю"""
        self.notification_history.append(notification)
        
        # Загружаем существующие уведомления
        if os.path.exists(self.notification_file):
            try:
                with open(self.notification_file, 'r', encoding='utf-8') as f:
                    all_notifications = json.load(f)
            except:
                all_notifications = []
        else:
            all_notifications = []
        
        # Добавляем новое
        all_notifications.append(notification)
        
        # Сохраняем (оставляем последние 1000)
        all_notifications = all_notifications[-1000:]
        
        try:
            with open(self.notification_file, 'w', encoding='utf-8') as f:
                json.dump(all_notifications, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка при сохранении уведомления: {e}")
    
    def get_notification_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Получает историю уведомлений
        
        Args:
            limit: Максимальное количество записей
            
        Returns:
            Список уведомлений
        """
        if os.path.exists(self.notification_file):
            try:
                with open(self.notification_file, 'r', encoding='utf-8') as f:
                    all_notifications = json.load(f)
                    return all_notifications[-limit:]
            except:
                pass
        return self.notification_history[-limit:]


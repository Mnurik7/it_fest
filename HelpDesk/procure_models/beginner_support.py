"""
Модуль поддержки новичков: песочница, рейтинг, партнёрства
"""
from typing import Dict, List, Optional, Any
import json
from datetime import datetime
import os


class BeginnerSupport:
    """Поддержка новичков в тендерах"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.ratings_file = os.path.join(data_dir, "beginner_ratings.json")
        self.sandbox_file = os.path.join(data_dir, "sandbox_tenders.json")
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """Создаёт директорию для данных если не существует"""
        os.makedirs(self.data_dir, exist_ok=True)
    
    def get_beginner_rating(self, user_id: str) -> Dict[str, Any]:
        """
        Получает рейтинг новичка
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Информация о рейтинге
        """
        ratings = self._load_ratings()
        user_rating = ratings.get(user_id, {
            "user_id": user_id,
            "rating": 0.0,
            "level": "новичок",
            "tenders_participated": 0,
            "tenders_won": 0,
            "tenders_lost": 0,
            "partnerships": 0,
            "experience_points": 0,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        })
        
        # Определяем уровень
        experience = user_rating.get("experience_points", 0)
        if experience >= 1000:
            user_rating["level"] = "эксперт"
        elif experience >= 500:
            user_rating["level"] = "опытный"
        elif experience >= 100:
            user_rating["level"] = "продвинутый"
        else:
            user_rating["level"] = "новичок"
        
        return user_rating
    
    def update_rating(self, user_id: str, action: str, success: bool = False):
        """
        Обновляет рейтинг новичка
        
        Args:
            user_id: ID пользователя
            action: Действие (participate, win, lose, partnership)
            success: Успешность действия
        """
        ratings = self._load_ratings()
        user_rating = ratings.get(user_id, {
            "user_id": user_id,
            "rating": 0.0,
            "level": "новичок",
            "tenders_participated": 0,
            "tenders_won": 0,
            "tenders_lost": 0,
            "partnerships": 0,
            "experience_points": 0,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        })
        
        # Обновляем статистику
        if action == "participate":
            user_rating["tenders_participated"] += 1
            user_rating["experience_points"] += 10
        elif action == "win":
            user_rating["tenders_won"] += 1
            user_rating["experience_points"] += 50
        elif action == "lose":
            user_rating["tenders_lost"] += 1
            user_rating["experience_points"] += 5
        elif action == "partnership":
            user_rating["partnerships"] += 1
            user_rating["experience_points"] += 30
        
        # Пересчитываем рейтинг
        total = user_rating["tenders_participated"]
        if total > 0:
            win_rate = user_rating["tenders_won"] / total
            user_rating["rating"] = round(win_rate * 100, 2)
        
        user_rating["last_updated"] = datetime.now().isoformat()
        ratings[user_id] = user_rating
        self._save_ratings(ratings)
    
    def create_sandbox_tender(self, tender_params: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Создаёт тренировочный тендер в песочнице
        
        Args:
            tender_params: Параметры тендера
            user_id: ID пользователя
            
        Returns:
            Информация о созданном тендере в песочнице
        """
        sandbox_tenders = self._load_sandbox_tenders()
        
        sandbox_tender = {
            "tender_id": f"sandbox_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "user_id": user_id,
            "tender_params": tender_params,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "attempts": 0,
            "last_attempt": None,
            "feedback": []
        }
        
        sandbox_tenders.append(sandbox_tender)
        self._save_sandbox_tenders(sandbox_tenders)
        
        return sandbox_tender
    
    def get_sandbox_tenders(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Получает список тендеров в песочнице для пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список тендеров в песочнице
        """
        sandbox_tenders = self._load_sandbox_tenders()
        return [t for t in sandbox_tenders if t.get("user_id") == user_id]
    
    def submit_sandbox_attempt(self, tender_id: str, user_id: str, attempt_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Отправляет попытку в песочнице
        
        Args:
            tender_id: ID тендера в песочнице
            user_id: ID пользователя
            attempt_data: Данные попытки
            
        Returns:
            Обратная связь по попытке
        """
        sandbox_tenders = self._load_sandbox_tenders()
        
        for tender in sandbox_tenders:
            if tender["tender_id"] == tender_id and tender["user_id"] == user_id:
                tender["attempts"] += 1
                tender["last_attempt"] = datetime.now().isoformat()
                
                # Генерируем обратную связь
                feedback = {
                    "attempt_number": tender["attempts"],
                    "timestamp": datetime.now().isoformat(),
                    "score": self._evaluate_attempt(attempt_data, tender["tender_params"]),
                    "strengths": ["Сильные стороны попытки"],
                    "weaknesses": ["Слабые стороны попытки"],
                    "recommendations": ["Рекомендации по улучшению"]
                }
                
                tender["feedback"].append(feedback)
                self._save_sandbox_tenders(sandbox_tenders)
                
                return feedback
        
        return {"error": "Тендер не найден"}
    
    def _evaluate_attempt(self, attempt_data: Dict[str, Any], tender_params: Dict[str, Any]) -> float:
        """Оценивает попытку в песочнице"""
        score = 0.0
        max_score = 100.0
        
        # Проверяем наличие ключевых элементов
        if attempt_data.get("price"):
            score += 20
        if attempt_data.get("description"):
            score += 20
        if attempt_data.get("documents"):
            score += 20
        if attempt_data.get("guarantee"):
            score += 20
        if attempt_data.get("delivery_time"):
            score += 20
        
        return round(score, 2)
    
    def generate_documents(self, tender_params: Dict[str, Any], document_type: str = "application") -> Dict[str, Any]:
        """
        Генерирует документы для тендера
        
        Args:
            tender_params: Параметры тендера
            document_type: Тип документа (application, contract, etc.)
            
        Returns:
            Сгенерированный документ
        """
        templates = {
            "application": {
                "title": "Заявка на участие в тендере",
                "sections": [
                    "Информация о поставщике",
                    "Предложение по цене",
                    "Техническое описание",
                    "Гарантийные обязательства",
                    "Сроки поставки",
                    "Приложения"
                ]
            },
            "contract": {
                "title": "Проект договора",
                "sections": [
                    "Предмет договора",
                    "Цена и условия оплаты",
                    "Сроки и условия поставки",
                    "Гарантийные обязательства",
                    "Ответственность сторон",
                    "Прочие условия"
                ]
            }
        }
        
        template = templates.get(document_type, templates["application"])
        
        return {
            "document_type": document_type,
            "title": template["title"],
            "sections": template["sections"],
            "tender_info": tender_params,
            "generated_at": datetime.now().isoformat(),
            "content": f"Автоматически сгенерированный {template['title']} на основе параметров тендера"
        }
    
    def _load_ratings(self) -> Dict[str, Dict[str, Any]]:
        """Загружает рейтинги из файла"""
        if os.path.exists(self.ratings_file):
            try:
                with open(self.ratings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {item["user_id"]: item for item in data} if isinstance(data, list) else data
            except:
                return {}
        return {}
    
    def _save_ratings(self, ratings: Dict[str, Dict[str, Any]]):
        """Сохраняет рейтинги в файл"""
        with open(self.ratings_file, 'w', encoding='utf-8') as f:
            json.dump(list(ratings.values()), f, ensure_ascii=False, indent=2)
    
    def _load_sandbox_tenders(self) -> List[Dict[str, Any]]:
        """Загружает тендеры из песочницы"""
        if os.path.exists(self.sandbox_file):
            try:
                with open(self.sandbox_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_sandbox_tenders(self, tenders: List[Dict[str, Any]]):
        """Сохраняет тендеры в песочнице"""
        with open(self.sandbox_file, 'w', encoding='utf-8') as f:
            json.dump(tenders, f, ensure_ascii=False, indent=2)


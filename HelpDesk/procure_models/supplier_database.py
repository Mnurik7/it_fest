"""
Модуль для работы с базой данных поставщиков
"""
from typing import Dict, List, Optional, Any
import json
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SupplierDatabase:
    """База данных поставщиков"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.suppliers_file = os.path.join(data_dir, "suppliers_database.json")
        self._ensure_data_dir()
        self.suppliers = self._load_suppliers()
    
    def _ensure_data_dir(self):
        """Создаёт директорию для данных если не существует"""
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _load_suppliers(self) -> List[Dict[str, Any]]:
        """Загружает поставщиков из файла"""
        if os.path.exists(self.suppliers_file):
            try:
                with open(self.suppliers_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Ошибка при загрузке поставщиков: {e}")
                return []
        return []
    
    def _save_suppliers(self):
        """Сохраняет поставщиков в файл"""
        try:
            with open(self.suppliers_file, 'w', encoding='utf-8') as f:
                json.dump(self.suppliers, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка при сохранении поставщиков: {e}")
    
    def add_supplier(self, supplier_data: Dict[str, Any]) -> str:
        """
        Добавляет поставщика в базу
        
        Args:
            supplier_data: Данные поставщика
            
        Returns:
            ID добавленного поставщика
        """
        supplier_id = f"SUP-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(self.suppliers)}"
        
        supplier = {
            'supplier_id': supplier_id,
            'name': supplier_data.get('name', ''),
            'inn': supplier_data.get('inn', ''),
            'specialization': supplier_data.get('specialization', []),
            'location': supplier_data.get('location', ''),
            'rating': supplier_data.get('rating', 0.0),
            'experience_years': supplier_data.get('experience_years', 0),
            'completed_projects': supplier_data.get('completed_projects', 0),
            'certificates': supplier_data.get('certificates', []),
            'licenses': supplier_data.get('licenses', []),
            'contact_info': supplier_data.get('contact_info', {}),
            'tender_history': [],
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        self.suppliers.append(supplier)
        self._save_suppliers()
        logger.info(f"Добавлен поставщик: {supplier_id}")
        return supplier_id
    
    def find_suppliers(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Находит поставщиков по критериям
        
        Args:
            criteria: Критерии поиска (specialization, location, min_rating, etc.)
            
        Returns:
            Список подходящих поставщиков
        """
        results = []
        
        for supplier in self.suppliers:
            match_score = 0
            matches = True
            
            # Проверка специализации
            if 'specialization' in criteria:
                required_specs = criteria['specialization']
                if isinstance(required_specs, str):
                    required_specs = [required_specs]
                
                supplier_specs = supplier.get('specialization', [])
                if isinstance(supplier_specs, str):
                    supplier_specs = [supplier_specs]
                
                common_specs = set(required_specs) & set(supplier_specs)
                if common_specs:
                    match_score += len(common_specs) * 10
                else:
                    matches = False
            
            # Проверка местоположения
            if 'location' in criteria:
                supplier_location = supplier.get('location', '').lower()
                required_location = criteria['location'].lower()
                if required_location in supplier_location or supplier_location in required_location:
                    match_score += 5
                elif criteria.get('location_strict', False):
                    matches = False
            
            # Проверка рейтинга
            if 'min_rating' in criteria:
                if supplier.get('rating', 0) < criteria['min_rating']:
                    matches = False
            
            # Проверка опыта
            if 'min_experience_years' in criteria:
                if supplier.get('experience_years', 0) < criteria['min_experience_years']:
                    matches = False
            
            # Проверка сертификатов
            if 'required_certificates' in criteria:
                required_certs = criteria['required_certificates']
                if isinstance(required_certs, str):
                    required_certs = [required_certs]
                
                supplier_certs = supplier.get('certificates', [])
                if isinstance(supplier_certs, str):
                    supplier_certs = [supplier_certs]
                
                if not all(cert in supplier_certs for cert in required_certs):
                    if criteria.get('certificates_strict', False):
                        matches = False
                    else:
                        match_score -= 5
            
            if matches:
                supplier_copy = supplier.copy()
                supplier_copy['match_score'] = match_score
                results.append(supplier_copy)
        
        # Сортируем по релевантности
        results.sort(key=lambda x: (x['match_score'], x.get('rating', 0)), reverse=True)
        
        return results
    
    def get_supplier(self, supplier_id: str) -> Optional[Dict[str, Any]]:
        """Получает поставщика по ID"""
        for supplier in self.suppliers:
            if supplier.get('supplier_id') == supplier_id:
                return supplier
        return None
    
    def update_supplier(self, supplier_id: str, updates: Dict[str, Any]) -> bool:
        """
        Обновляет данные поставщика
        
        Args:
            supplier_id: ID поставщика
            updates: Обновления
            
        Returns:
            True если успешно
        """
        for supplier in self.suppliers:
            if supplier.get('supplier_id') == supplier_id:
                supplier.update(updates)
                supplier['updated_at'] = datetime.now().isoformat()
                self._save_suppliers()
                logger.info(f"Обновлён поставщик: {supplier_id}")
                return True
        return False
    
    def add_tender_participation(self, supplier_id: str, tender_info: Dict[str, Any]) -> bool:
        """
        Добавляет информацию об участии в тендере
        
        Args:
            supplier_id: ID поставщика
            tender_info: Информация о тендере
            
        Returns:
            True если успешно
        """
        for supplier in self.suppliers:
            if supplier.get('supplier_id') == supplier_id:
                participation = {
                    'tender_id': tender_info.get('tender_id', ''),
                    'tender_title': tender_info.get('tender_title', ''),
                    'status': tender_info.get('status', 'participated'),  # participated, won, lost
                    'date': datetime.now().isoformat(),
                    'price_offered': tender_info.get('price_offered', 0)
                }
                
                supplier['tender_history'].append(participation)
                
                # Обновляем статистику
                if participation['status'] == 'won':
                    supplier['completed_projects'] = supplier.get('completed_projects', 0) + 1
                
                supplier['updated_at'] = datetime.now().isoformat()
                self._save_suppliers()
                return True
        return False
    
    def get_supplier_statistics(self, supplier_id: str) -> Optional[Dict[str, Any]]:
        """Возвращает статистику поставщика"""
        supplier = self.get_supplier(supplier_id)
        if not supplier:
            return None
        
        history = supplier.get('tender_history', [])
        total_participations = len(history)
        wins = sum(1 for h in history if h.get('status') == 'won')
        losses = sum(1 for h in history if h.get('status') == 'lost')
        
        win_rate = (wins / total_participations * 100) if total_participations > 0 else 0
        
        return {
            'supplier_id': supplier_id,
            'name': supplier.get('name', ''),
            'total_participations': total_participations,
            'wins': wins,
            'losses': losses,
            'win_rate_percent': round(win_rate, 2),
            'completed_projects': supplier.get('completed_projects', 0),
            'rating': supplier.get('rating', 0.0),
            'experience_years': supplier.get('experience_years', 0)
        }
    
    def get_all_suppliers(self) -> List[Dict[str, Any]]:
        """Возвращает всех поставщиков"""
        return self.suppliers.copy()
    
    def delete_supplier(self, supplier_id: str) -> bool:
        """Удаляет поставщика"""
        initial_count = len(self.suppliers)
        self.suppliers = [s for s in self.suppliers if s.get('supplier_id') != supplier_id]
        
        if len(self.suppliers) < initial_count:
            self._save_suppliers()
            logger.info(f"Удалён поставщик: {supplier_id}")
            return True
        return False
    
    def import_suppliers(self, suppliers_data: List[Dict[str, Any]]) -> int:
        """
        Импортирует поставщиков из списка
        
        Args:
            suppliers_data: Список данных поставщиков
            
        Returns:
            Количество импортированных поставщиков
        """
        imported = 0
        for supplier_data in suppliers_data:
            try:
                self.add_supplier(supplier_data)
                imported += 1
            except Exception as e:
                logger.error(f"Ошибка при импорте поставщика: {e}")
        
        logger.info(f"Импортировано поставщиков: {imported}/{len(suppliers_data)}")
        return imported


# AI-Procure Models Package

from .tender_analyzer import TenderAnalyzer
from .supplier_matcher import SupplierMatcher
from .risk_analyzer import RiskAnalyzer
from .report_generator import ReportGenerator
from .beginner_support import BeginnerSupport

# Опциональные импорты новых модулей
try:
    from .data_collector import DataCollector
except ImportError as e:
    DataCollector = None
    import logging
    logging.warning(f"DataCollector недоступен: {e}")

try:
    from .price_analyzer import PriceAnalyzer
except ImportError as e:
    PriceAnalyzer = None
    import logging
    logging.warning(f"PriceAnalyzer недоступен: {e}")

try:
    from .metrics_tracker import MetricsTracker
except ImportError as e:
    MetricsTracker = None
    import logging
    logging.warning(f"MetricsTracker недоступен: {e}")

try:
    from .supplier_database import SupplierDatabase
except ImportError as e:
    SupplierDatabase = None
    import logging
    logging.warning(f"SupplierDatabase недоступен: {e}")

try:
    from .document_parser import DocumentParser
except ImportError as e:
    DocumentParser = None
    import logging
    logging.warning(f"DocumentParser недоступен: {e}")

# Новые модули
try:
    from .notification_system import NotificationSystem
except ImportError as e:
    NotificationSystem = None
    import logging
    logging.warning(f"NotificationSystem недоступен: {e}")

try:
    from .cache_manager import CacheManager
except ImportError as e:
    CacheManager = None
    import logging
    logging.warning(f"CacheManager недоступен: {e}")

try:
    from .async_processor import AsyncProcessor
except ImportError as e:
    AsyncProcessor = None
    import logging
    logging.warning(f"AsyncProcessor недоступен: {e}")

try:
    from .batch_processor import BatchProcessor
except ImportError as e:
    BatchProcessor = None
    import logging
    logging.warning(f"BatchProcessor недоступен: {e}")

try:
    from .metrics_validator import MetricsValidator
except ImportError as e:
    MetricsValidator = None
    import logging
    logging.warning(f"MetricsValidator недоступен: {e}")

try:
    from .risk_confirmation import RiskConfirmation
except ImportError as e:
    RiskConfirmation = None
    import logging
    logging.warning(f"RiskConfirmation недоступен: {e}")

try:
    from .prevention_tracker import PreventionTracker
except ImportError as e:
    PreventionTracker = None
    import logging
    logging.warning(f"PreventionTracker недоступен: {e}")

__all__ = [
    'TenderAnalyzer',
    'SupplierMatcher',
    'RiskAnalyzer',
    'ReportGenerator',
    'BeginnerSupport',
    'DataCollector',
    'PriceAnalyzer',
    'MetricsTracker',
    'SupplierDatabase',
    'DocumentParser',
    'NotificationSystem',
    'CacheManager',
    'AsyncProcessor',
    'BatchProcessor',
    'MetricsValidator',
    'RiskConfirmation',
    'PreventionTracker'
]


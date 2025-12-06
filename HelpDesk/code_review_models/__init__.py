"""
Модули AI-Code Review Assistant
"""
from .architecture_loader import ArchitectureLoader
from .code_analyzer import CodeAnalyzer
from .review_generator import ReviewGenerator
from .report_generator import ReportGenerator
from .gitlab_integration import GitLabIntegration
from .educational_support import EducationalSupport
from .language_detector import LanguageDetector

__all__ = [
    'ArchitectureLoader',
    'CodeAnalyzer',
    'ReviewGenerator',
    'ReportGenerator',
    'GitLabIntegration',
    'EducationalSupport',
    'LanguageDetector'
]


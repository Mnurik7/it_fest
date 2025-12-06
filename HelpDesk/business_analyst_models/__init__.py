# Business Analyst Models
from .document_analyzer import DocumentAnalyzer
from .requirement_extractor import RequirementExtractor
from .document_generator import DocumentGenerator
from .structured_dialog import StructuredDialogManager, DialogStage
from .metrics_tracker import MetricsTracker
from .process_improver import ProcessImprover

try:
    from .smart_answer_analyzer import SmartAnswerAnalyzer
    from .autocomplete_helper import AutocompleteHelper
    __all__ = [
        'DocumentAnalyzer', 
        'RequirementExtractor', 
        'DocumentGenerator',
        'StructuredDialogManager',
        'DialogStage',
        'MetricsTracker',
        'ProcessImprover',
        'SmartAnswerAnalyzer',
        'AutocompleteHelper'
    ]
except ImportError:
    try:
        from .smart_answer_analyzer import SmartAnswerAnalyzer
        __all__ = [
            'DocumentAnalyzer', 
            'RequirementExtractor', 
            'DocumentGenerator',
            'StructuredDialogManager',
            'DialogStage',
            'MetricsTracker',
            'ProcessImprover',
            'SmartAnswerAnalyzer'
        ]
    except ImportError:
        __all__ = [
            'DocumentAnalyzer', 
            'RequirementExtractor', 
            'DocumentGenerator',
            'StructuredDialogManager',
            'DialogStage',
            'MetricsTracker',
            'ProcessImprover'
        ]


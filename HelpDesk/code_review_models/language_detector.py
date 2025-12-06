"""
Модуль для автоматического определения языка программирования
"""
import re
from typing import Optional, Dict


class LanguageDetector:
    """Детектор языка программирования"""
    
    def __init__(self):
        # Расширения файлов по языкам
        self.extensions = {
            'Python': ['.py', '.pyw', '.pyx', '.pyi'],
            'JavaScript': ['.js', '.jsx', '.mjs'],
            'TypeScript': ['.ts', '.tsx'],
            'Java': ['.java'],
            'C++': ['.cpp', '.cxx', '.cc', '.c++', '.hpp', '.hxx', '.h++'],
            'C': ['.c', '.h'],
            'C#': ['.cs'],
            'Go': ['.go'],
            'Rust': ['.rs'],
            'PHP': ['.php', '.phtml', '.php3', '.php4', '.php5'],
            'Ruby': ['.rb', '.rbw'],
            'Swift': ['.swift'],
            'Kotlin': ['.kt', '.kts'],
            'Scala': ['.scala'],
            'R': ['.r', '.R'],
            'MATLAB': ['.m'],
            'Shell': ['.sh', '.bash', '.zsh'],
            'PowerShell': ['.ps1', '.psm1'],
            'HTML': ['.html', '.htm'],
            'CSS': ['.css'],
            'SQL': ['.sql'],
            'Dart': ['.dart'],
            'Lua': ['.lua'],
            'Perl': ['.pl', '.pm'],
            'Objective-C': ['.m', '.mm', '.h'],
            'Vue': ['.vue'],
            'Svelte': ['.svelte']
        }
        
        # Ключевые слова и паттерны для определения языка
        self.patterns = {
            'Python': [
                r'\bdef\s+\w+\s*\(',  # def function
                r'\bimport\s+\w+',  # import module
                r'\bfrom\s+\w+\s+import',  # from module import
                r'\bclass\s+\w+.*:',  # class definition
                r'\bprint\s*\(',  # print statement
                r'\bif\s+__name__\s*==\s*["\']__main__["\']',  # main guard
            ],
            'JavaScript': [
                r'\bfunction\s+\w+\s*\(',  # function declaration
                r'\bconst\s+\w+\s*=',  # const declaration
                r'\blet\s+\w+\s*=',  # let declaration
                r'\bvar\s+\w+\s*=',  # var declaration
                r'\bconsole\.(log|error|warn)',  # console methods
                r'=>\s*{',  # arrow function
                r'\bexport\s+(default\s+)?(function|class|const)',  # ES6 export
            ],
            'TypeScript': [
                r':\s*\w+\s*[=;]',  # type annotations
                r'\binterface\s+\w+',  # interface
                r'\btype\s+\w+\s*=',  # type alias
                r'\benum\s+\w+',  # enum
                r'<[A-Z]\w+>',  # generics
            ],
            'Java': [
                r'\bpublic\s+(static\s+)?(void|int|String|boolean)',  # public method
                r'\bclass\s+\w+\s+(extends|implements)',  # class with inheritance
                r'\b@\w+',  # annotations
                r'\bpackage\s+\w+',  # package declaration
                r'\bimport\s+java\.',  # Java imports
            ],
            'C++': [
                r'#include\s*<[^>]+>',  # C++ includes
                r'\bstd::',  # std namespace
                r'\bnamespace\s+\w+',  # namespace
                r'\btemplate\s*<',  # templates
                r'\busing\s+namespace',  # using namespace
            ],
            'C#': [
                r'\bnamespace\s+\w+',  # namespace
                r'\busing\s+\w+;',  # using directive
                r'\bpublic\s+class\s+\w+',  # public class
                r'\b\[.*\]',  # attributes
                r'\bvar\s+\w+\s*=',  # var keyword
            ],
            'Go': [
                r'\bpackage\s+\w+',  # package declaration
                r'\bfunc\s+\w+\s*\(',  # function declaration
                r':=\s*',  # short variable declaration
                r'\bimport\s*\('  # import block
            ],
            'Rust': [
                r'\bfn\s+\w+\s*\(',  # function declaration
                r'\blet\s+(mut\s+)?\w+',  # let binding
                r'&(mut\s+)?\w+',  # references
                r'->\s*\w+',  # return type
                r'\buse\s+\w+::',  # use statement
            ],
            'PHP': [
                r'<\?php',  # PHP opening tag
                r'\$\w+\s*=',  # PHP variables
                r'\bfunction\s+\w+\s*\(',  # function
                r'\becho\s+',  # echo statement
            ],
            'Ruby': [
                r'\bdef\s+\w+',  # method definition
                r'\bclass\s+\w+',  # class definition
                r'\bmodule\s+\w+',  # module definition
                r'\.each\s+do',  # each block
                r'end\s*$',  # end keyword
            ],
            'SQL': [
                r'\bSELECT\s+.*\bFROM\b',  # SELECT statement
                r'\bINSERT\s+INTO',  # INSERT statement
                r'\bCREATE\s+TABLE',  # CREATE TABLE
                r'\bUPDATE\s+\w+\s+SET',  # UPDATE statement
            ],
            'HTML': [
                r'<!DOCTYPE\s+html>',  # DOCTYPE
                r'<html',  # html tag
                r'<head>',  # head tag
                r'<body>',  # body tag
            ],
            'CSS': [
                r'\w+\s*\{[^}]*\}',  # CSS rule
                r'@(media|import|keyframes)',  # CSS at-rules
                r':\s*[^;]+;',  # CSS property
            ]
        }
    
    def detect_language(self, code: str, file_path: Optional[str] = None) -> str:
        """
        Определяет язык программирования по коду и/или пути к файлу
        
        Args:
            code: Исходный код
            file_path: Путь к файлу (опционально)
        
        Returns:
            Название языка программирования
        """
        # Сначала пытаемся определить по расширению файла
        if file_path:
            detected = self._detect_by_extension(file_path)
            if detected:
                return detected
        
        # Затем пытаемся определить по содержимому кода
        detected = self._detect_by_code(code)
        if detected:
            return detected
        
        # Если не удалось определить, возвращаем "Unknown"
        return 'Unknown'
    
    def _detect_by_extension(self, file_path: str) -> Optional[str]:
        """Определяет язык по расширению файла"""
        import os
        _, ext = os.path.splitext(file_path.lower())
        
        for language, extensions in self.extensions.items():
            if ext in extensions:
                return language
        
        return None
    
    def _detect_by_code(self, code: str) -> Optional[str]:
        """Определяет язык по содержимому кода"""
        if not code or not code.strip():
            return None
        
        # Подсчитываем совпадения для каждого языка
        scores: Dict[str, int] = {}
        
        for language, patterns in self.patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, code, re.IGNORECASE | re.MULTILINE))
                score += matches
            
            if score > 0:
                scores[language] = score
        
        # Возвращаем язык с наибольшим количеством совпадений
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return None
    
    def get_language_info(self, language: str) -> Dict[str, str]:
        """Получает информацию о языке"""
        return {
            'name': language,
            'common_extensions': ', '.join(self.extensions.get(language, [])),
            'detected': True if language != 'Unknown' else False
        }


"""
Модуль для парсинга документов (PDF, Excel, CSV)
"""
from typing import Dict, List, Optional, Any
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Импорты с обработкой ошибок
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("PyPDF2 не установлен. Парсинг PDF недоступен.")

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber не установлен. Расширенный парсинг PDF недоступен.")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning("pandas не установлен. Парсинг Excel/CSV недоступен.")


class DocumentParser:
    """Парсер документов для извлечения текста тендеров"""
    
    def __init__(self):
        self.supported_formats = {
            'pdf': PDF_AVAILABLE or PDFPLUMBER_AVAILABLE,
            'xlsx': PANDAS_AVAILABLE,
            'xls': PANDAS_AVAILABLE,
            'csv': PANDAS_AVAILABLE,
            'txt': True
        }
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Парсит файл и извлекает текст
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Словарь с извлечённым текстом и метаданными
        """
        if not os.path.exists(file_path):
            return {
                'success': False,
                'error': 'Файл не найден',
                'text': ''
            }
        
        file_ext = os.path.splitext(file_path)[1][1:].lower()
        
        if file_ext == 'pdf':
            return self._parse_pdf(file_path)
        elif file_ext in ['xlsx', 'xls']:
            return self._parse_excel(file_path)
        elif file_ext == 'csv':
            return self._parse_csv(file_path)
        elif file_ext == 'txt':
            return self._parse_text(file_path)
        else:
            return {
                'success': False,
                'error': f'Неподдерживаемый формат: {file_ext}',
                'text': ''
            }
    
    def _parse_pdf(self, file_path: str) -> Dict[str, Any]:
        """Парсит PDF файл"""
        text = ""
        pages_count = 0
        
        # Пробуем использовать pdfplumber (более точный)
        if PDFPLUMBER_AVAILABLE:
            try:
                with pdfplumber.open(file_path) as pdf:
                    pages_count = len(pdf.pages)
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n\n"
                
                return {
                    'success': True,
                    'text': text.strip(),
                    'pages_count': pages_count,
                    'format': 'pdf',
                    'method': 'pdfplumber'
                }
            except Exception as e:
                logger.warning(f"Ошибка при парсинге PDF через pdfplumber: {e}")
        
        # Fallback на PyPDF2
        if PDF_AVAILABLE:
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    pages_count = len(pdf_reader.pages)
                    
                    for page_num in range(pages_count):
                        page = pdf_reader.pages[page_num]
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n\n"
                
                return {
                    'success': True,
                    'text': text.strip(),
                    'pages_count': pages_count,
                    'format': 'pdf',
                    'method': 'PyPDF2'
                }
            except Exception as e:
                logger.error(f"Ошибка при парсинге PDF через PyPDF2: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'text': ''
                }
        
        return {
            'success': False,
            'error': 'PDF парсеры не доступны',
            'text': ''
        }
    
    def _parse_excel(self, file_path: str) -> Dict[str, Any]:
        """Парсит Excel файл"""
        if not PANDAS_AVAILABLE:
            return {
                'success': False,
                'error': 'pandas не установлен',
                'text': ''
            }
        
        try:
            # Читаем все листы
            excel_file = pd.ExcelFile(file_path)
            sheets_data = {}
            all_text = []
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                sheets_data[sheet_name] = df.to_dict('records')
                
                # Конвертируем в текст
                sheet_text = f"=== Лист: {sheet_name} ===\n"
                sheet_text += df.to_string(index=False)
                all_text.append(sheet_text)
            
            text = "\n\n".join(all_text)
            
            return {
                'success': True,
                'text': text,
                'sheets': list(excel_file.sheet_names),
                'sheets_data': sheets_data,
                'format': 'excel'
            }
        except Exception as e:
            logger.error(f"Ошибка при парсинге Excel: {e}")
            return {
                'success': False,
                'error': str(e),
                'text': ''
            }
    
    def _parse_csv(self, file_path: str) -> Dict[str, Any]:
        """Парсит CSV файл"""
        if not PANDAS_AVAILABLE:
            return {
                'success': False,
                'error': 'pandas не установлен',
                'text': ''
            }
        
        try:
            # Пробуем разные кодировки
            encodings = ['utf-8', 'cp1251', 'latin-1']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                return {
                    'success': False,
                    'error': 'Не удалось определить кодировку',
                    'text': ''
                }
            
            text = df.to_string(index=False)
            
            return {
                'success': True,
                'text': text,
                'rows_count': len(df),
                'columns': list(df.columns),
                'data': df.to_dict('records'),
                'format': 'csv'
            }
        except Exception as e:
            logger.error(f"Ошибка при парсинге CSV: {e}")
            return {
                'success': False,
                'error': str(e),
                'text': ''
            }
    
    def _parse_text(self, file_path: str) -> Dict[str, Any]:
        """Парсит текстовый файл"""
        try:
            # Пробуем разные кодировки
            encodings = ['utf-8', 'cp1251', 'latin-1']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as file:
                        text = file.read()
                        return {
                            'success': True,
                            'text': text,
                            'format': 'txt',
                            'encoding': encoding
                        }
                except UnicodeDecodeError:
                    continue
            
            return {
                'success': False,
                'error': 'Не удалось определить кодировку',
                'text': ''
            }
        except Exception as e:
            logger.error(f"Ошибка при парсинге текстового файла: {e}")
            return {
                'success': False,
                'error': str(e),
                'text': ''
            }
    
    def is_format_supported(self, file_ext: str) -> bool:
        """Проверяет, поддерживается ли формат файла"""
        return self.supported_formats.get(file_ext.lower(), False)
    
    def get_supported_formats(self) -> List[str]:
        """Возвращает список поддерживаемых форматов"""
        return [fmt for fmt, supported in self.supported_formats.items() if supported]


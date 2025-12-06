"""
Модуль для загрузки и анализа архитектуры проекта
Поддерживает различные форматы: ZIP, PDF, PNG, JPG, DOCX и др.
"""
import os
import zipfile
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
import base64


class ArchitectureLoader:
    """Загрузчик и анализатор архитектуры проекта"""
    
    def __init__(self, model):
        self.model = model
        self.supported_formats = {
            'zip': self._load_zip,
            'pdf': self._load_pdf,
            'png': self._load_image,
            'jpg': self._load_image,
            'jpeg': self._load_image,
            'docx': self._load_docx,
            'txt': self._load_text,
            'md': self._load_text,
            'json': self._load_json
        }
    
    def load_architecture(self, file_path: str, file_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Загружает архитектуру проекта из файла
        
        Args:
            file_path: Путь к файлу
            file_type: Тип файла (если не указан, определяется автоматически)
        
        Returns:
            Словарь с загруженной архитектурой
        """
        if not os.path.exists(file_path):
            return {'error': f'Файл не найден: {file_path}'}
        
        # Определяем тип файла
        if not file_type:
            file_type = self._detect_file_type(file_path)
        
        file_type_lower = file_type.lower()
        
        if file_type_lower not in self.supported_formats:
            return {'error': f'Неподдерживаемый формат файла: {file_type}'}
        
        try:
            loader_func = self.supported_formats[file_type_lower]
            content = loader_func(file_path)
            
            return {
                'file_path': file_path,
                'file_type': file_type,
                'content': content,
                'success': True
            }
        except Exception as e:
            return {'error': f'Ошибка при загрузке файла: {str(e)}'}
    
    def analyze_architecture(self, architecture_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Анализирует архитектуру проекта с помощью AI
        
        Args:
            architecture_data: Данные архитектуры (из load_architecture)
        
        Returns:
            Результат анализа архитектуры
        """
        if architecture_data.get('error'):
            return architecture_data
        
        content = architecture_data.get('content', '')
        file_type = architecture_data.get('file_type', 'unknown')
        
        if not content or not content.strip():
            return {
                'error': 'Содержимое файла пусто или не удалось извлечь текст',
                'file_type': file_type
            }
        
        prompt = f"""Краткий анализ архитектуры. Без лишних слов.

Тип: {file_type}

Архитектура:
{content[:10000] if len(content) > 10000 else content}

Формат:

**ТИП:** [монолит/микросервисы/модульная]

**УЗКИЕ МЕСТА:**
- [Проблема]: [кратко]

**ПРОБЛЕМЫ:**
- [Проблема]: [кратко]

**РЕКОМЕНДАЦИИ:**
- [Рекомендация]: [кратко]

**ОЦЕНКА:** [1-10]

Только факты. Максимум 2 предложения на пункт."""
        
        try:
            response = self.model.generate_content(prompt)
            analysis_text = response.text if hasattr(response, 'text') else str(response)
            
            return {
                'analysis': analysis_text,
                'file_type': file_type,
                'success': True
            }
        except Exception as e:
            return {
                'error': f'Ошибка при анализе архитектуры: {str(e)}',
                'file_type': file_type
            }
    
    def _detect_file_type(self, file_path: str) -> str:
        """Определяет тип файла по расширению"""
        ext = Path(file_path).suffix.lstrip('.').lower()
        return ext if ext else 'txt'
    
    def _load_zip(self, file_path: str) -> str:
        """Загружает содержимое ZIP архива"""
        content_parts = []
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                content_parts.append(f"Список файлов в архиве ({len(file_list)} файлов):\n")
                
                for file_name in file_list[:50]:  # Ограничиваем количество файлов
                    try:
                        if not file_name.endswith('/'):
                            file_content = zip_ref.read(file_name).decode('utf-8', errors='ignore')
                            content_parts.append(f"\n--- Файл: {file_name} ---\n")
                            content_parts.append(file_content[:2000])  # Ограничиваем размер каждого файла
                    except:
                        content_parts.append(f"\n--- Файл: {file_name} (бинарный или нечитаемый) ---\n")
                
                if len(file_list) > 50:
                    content_parts.append(f"\n... и еще {len(file_list) - 50} файлов")
        except Exception as e:
            return f"Ошибка при чтении ZIP: {str(e)}"
        
        return '\n'.join(content_parts)
    
    def _load_pdf(self, file_path: str) -> str:
        """Загружает содержимое PDF файла"""
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text_parts = []
                for page_num, page in enumerate(pdf_reader.pages[:20]):  # Ограничиваем количество страниц
                    text_parts.append(f"--- Страница {page_num + 1} ---\n")
                    text_parts.append(page.extract_text())
                return '\n'.join(text_parts)
        except ImportError:
            return "Для чтения PDF требуется библиотека PyPDF2"
        except Exception as e:
            return f"Ошибка при чтении PDF: {str(e)}"
    
    def _load_image(self, file_path: str) -> str:
        """Загружает изображение (описание для AI)"""
        try:
            with open(file_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
                return f"Изображение архитектуры (base64): {image_data[:500]}..."
        except Exception as e:
            return f"Ошибка при чтении изображения: {str(e)}"
    
    def _load_docx(self, file_path: str) -> str:
        """Загружает содержимое DOCX файла"""
        try:
            from docx import Document
            doc = Document(file_path)
            return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        except ImportError:
            return "Для чтения DOCX требуется библиотека python-docx"
        except Exception as e:
            return f"Ошибка при чтении DOCX: {str(e)}"
    
    def _load_text(self, file_path: str) -> str:
        """Загружает текстовый файл"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            return f"Ошибка при чтении текстового файла: {str(e)}"
    
    def _load_json(self, file_path: str) -> str:
        """Загружает JSON файл"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"Ошибка при чтении JSON: {str(e)}"


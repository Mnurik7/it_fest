"""
Модуль для интеграции с GitLab API (проекты, файлы, MR)
"""
import json
import os
import base64
from typing import Dict, List, Optional, Any
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

# Все функции GitLabIntegration:
# - list_projects() - список проектов
# - get_project() - информация о проекте
# - list_repository_files() - список файлов в репозитории
# - get_file_content() - содержимое файла
# - update_file() - обновить файл
# - create_file() - создать файл
# - get_branches() - список веток
# - get_all_files_recursive() - рекурсивно получить все файлы
# - list_merge_requests() - список MR
# - get_merge_request() - информация о MR
# - get_merge_request_diff() - diff MR
# - update_mr_status() - обновить статус MR
# - get_mr_status() - получить статус MR
# - list_mrs() - список локальных MR
# - add_labels() - добавить метки к MR


class GitLabIntegration:
    """Интеграция с GitLab API для работы с проектами, файлами и MR"""
    
    def __init__(self):
        self.gitlab_url = os.getenv('GITLAB_URL', 'https://gitlab.com')
        self.gitlab_token = os.getenv('GITLAB_TOKEN')
        self.mr_statuses_file = 'data/code_review_mrs.json'
        self._ensure_data_file()
        
        # API endpoint
        self.api_base = f"{self.gitlab_url}/api/v4"
        self.headers = {
            'PRIVATE-TOKEN': self.gitlab_token,
            'Content-Type': 'application/json'
        } if self.gitlab_token else {}
    
    def _ensure_data_file(self):
        """Создаёт файл для хранения статусов MR если его нет"""
        os.makedirs(os.path.dirname(self.mr_statuses_file), exist_ok=True)
        if not os.path.exists(self.mr_statuses_file):
            with open(self.mr_statuses_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Выполняет запрос к GitLab API"""
        if not self.gitlab_token:
            return {'error': 'GitLab токен не настроен. Добавьте GITLAB_TOKEN в .env файл'}
        
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                timeout=30,
                **kwargs
            )
            
            if response.status_code == 401:
                return {'error': 'Неверный GitLab токен или недостаточно прав'}
            elif response.status_code == 404:
                return {'error': 'Ресурс не найден'}
            elif response.status_code >= 400:
                try:
                    error_data = response.json()
                    return {'error': error_data.get('message', f'Ошибка API: {response.status_code}')}
                except:
                    return {'error': f'Ошибка API: {response.status_code} - {response.text[:200]}'}
            
            if response.status_code == 204:  # No Content
                return {'success': True}
            
            return response.json() if response.text else {'success': True}
        except requests.exceptions.Timeout:
            return {'error': 'Тайм-аут при запросе к GitLab API'}
        except requests.exceptions.RequestException as e:
            return {'error': f'Ошибка соединения с GitLab: {str(e)}'}
        except Exception as e:
            return {'error': f'Неожиданная ошибка: {str(e)}'}
    
    # ==================== Проекты ====================
    
    def list_projects(self, search: Optional[str] = None, owned: bool = False, 
                     membership: bool = True, visibility: Optional[str] = None) -> Dict[str, Any]:
        """
        Получает список проектов
        
        Args:
            search: Поисковый запрос (опционально)
            owned: Только собственные проекты (по умолчанию False)
            membership: Включать проекты, где пользователь является участником (по умолчанию True)
            visibility: Фильтр видимости (private, internal, public)
        
        Returns:
            Список проектов
        """
        params = {
            'per_page': 100,
            'simple': False,
            'order_by': 'last_activity_at',
            'sort': 'desc'
        }
        
        if search:
            params['search'] = search
            # GitLab поддерживает поиск по имени, пути и описанию
            params['search_namespaces'] = True
        if owned:
            params['owned'] = 'true'
        if membership:
            params['membership'] = 'true'
        if visibility:
            params['visibility'] = visibility
        
        result = self._make_request('GET', '/projects', params=params)
        
        if 'error' in result:
            return result
        
        projects = result if isinstance(result, list) else []
        
        # Если поиск не дал результатов, попробуем поиск без фильтров
        if search and len(projects) == 0:
            # Пробуем более широкий поиск
            params_broad = {
                'per_page': 100,
                'simple': False,
                'membership': 'true'
            }
            result_broad = self._make_request('GET', '/projects', params=params_broad)
            if not isinstance(result_broad, dict) or 'error' not in result_broad:
                all_projects = result_broad if isinstance(result_broad, list) else []
                # Фильтруем локально по поисковому запросу
                search_lower = search.lower()
                projects = [
                    p for p in all_projects
                    if (search_lower in (p.get('name', '') or '').lower() or
                        search_lower in (p.get('path', '') or '').lower() or
                        search_lower in (p.get('path_with_namespace', '') or '').lower() or
                        search_lower in (p.get('description', '') or '').lower())
                ]
        
        return {
            'projects': projects,
            'count': len(projects),
            'success': True
        }
    
    def get_project(self, project_id: str) -> Dict[str, Any]:
        """
        Получает информацию о проекте
        
        Args:
            project_id: ID или путь проекта (например, '123' или 'group/project')
        
        Returns:
            Информация о проекте
        """
        # URL-кодируем project_id если это путь
        project_id_encoded = requests.utils.quote(str(project_id), safe='')
        return self._make_request('GET', f'/projects/{project_id_encoded}')
    
    # ==================== Файлы и репозиторий ====================
    
    def list_repository_files(self, project_id: str, path: str = '', ref: str = 'main') -> Dict[str, Any]:
        """
        Получает список файлов в репозитории
        
        Args:
            project_id: ID или путь проекта
            path: Путь в репозитории (по умолчанию корень)
            ref: Ветка или тег (по умолчанию 'main')
        
        Returns:
            Список файлов и папок
        """
        project_id_encoded = requests.utils.quote(str(project_id), safe='')
        params = {
            'ref': ref,
            'path': path or '',
            'per_page': 100
        }
        
        result = self._make_request('GET', f'/projects/{project_id_encoded}/repository/tree', params=params)
        
        if 'error' in result:
            return result
        
        return {
            'items': result if isinstance(result, list) else [],
            'count': len(result) if isinstance(result, list) else 0,
            'path': path,
            'ref': ref,
            'success': True
        }
    
    def get_file_content(self, project_id: str, file_path: str, ref: str = 'main') -> Dict[str, Any]:
        """
        Получает содержимое файла
        
        Args:
            project_id: ID или путь проекта
            file_path: Путь к файлу в репозитории
            ref: Ветка или тег (по умолчанию 'main')
        
        Returns:
            Содержимое файла
        """
        project_id_encoded = requests.utils.quote(str(project_id), safe='')
        # GitLab API требует двойное кодирование пути к файлу
        file_path_encoded = requests.utils.quote(file_path, safe='')
        
        params = {
            'ref': ref
        }
        
        result = self._make_request('GET', f'/projects/{project_id_encoded}/repository/files/{file_path_encoded}', params=params)
        
        if 'error' in result:
            return result
        
        # Декодируем содержимое файла (base64)
        content = ''
        encoding = result.get('encoding', 'base64')
        
        if encoding == 'base64':
            try:
                content = base64.b64decode(result.get('content', '')).decode('utf-8')
            except Exception as e:
                return {'error': f'Ошибка декодирования файла: {str(e)}'}
        else:
            content = result.get('content', '')
        
        return {
            'content': content,
            'file_path': file_path,
            'ref': ref,
            'size': result.get('size', 0),
            'encoding': encoding,
            'success': True
        }
    
    def update_file(self, project_id: str, file_path: str, content: str, 
                   branch: str = 'main', commit_message: str = 'Update file') -> Dict[str, Any]:
        """
        Обновляет или создаёт файл в репозитории
        
        Args:
            project_id: ID или путь проекта
            file_path: Путь к файлу
            content: Новое содержимое файла
            branch: Ветка (по умолчанию 'main')
            commit_message: Сообщение коммита
        
        Returns:
            Результат обновления
        """
        project_id_encoded = requests.utils.quote(str(project_id), safe='')
        # GitLab API требует двойное кодирование пути к файлу
        file_path_encoded = requests.utils.quote(file_path, safe='')
        
        # Сначала получаем текущий файл для получения last_commit_id (если файл существует)
        current_file = self.get_file_content(project_id, file_path, branch)
        last_commit_id = current_file.get('last_commit_id') if 'error' not in current_file else None
        
        # Кодируем содержимое в base64
        content_encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        data = {
            'branch': branch,
            'commit_message': commit_message,
            'content': content_encoded,
            'encoding': 'base64'
        }
        
        # Если файл существует, добавляем last_commit_id
        if last_commit_id:
            data['last_commit_id'] = last_commit_id
        
        endpoint = f'/projects/{project_id_encoded}/repository/files/{file_path_encoded}'
        
        # GitLab использует один endpoint для создания и обновления
        method = 'PUT'
        
        result = self._make_request(method, endpoint, json=data)
        
        if 'error' in result:
            return result
        
        return {
            'success': True,
            'file_path': file_path,
            'branch': branch,
            'commit': result
        }
    
    def create_file(self, project_id: str, file_path: str, content: str,
                   branch: str = 'main', commit_message: str = 'Create file') -> Dict[str, Any]:
        """
        Создаёт новый файл в репозитории
        
        Args:
            project_id: ID или путь проекта
            file_path: Путь к новому файлу
            content: Содержимое файла
            branch: Ветка (по умолчанию 'main')
            commit_message: Сообщение коммита
        
        Returns:
            Результат создания
        """
        return self.update_file(project_id, file_path, content, branch, commit_message)
    
    def get_branches(self, project_id: str) -> Dict[str, Any]:
        """
        Получает список веток проекта
        
        Args:
            project_id: ID или путь проекта
        
        Returns:
            Список веток
        """
        project_id_encoded = requests.utils.quote(str(project_id), safe='')
        params = {'per_page': 100}
        
        result = self._make_request('GET', f'/projects/{project_id_encoded}/repository/branches', params=params)
        
        if 'error' in result:
            return result
        
        return {
            'branches': result if isinstance(result, list) else [],
            'count': len(result) if isinstance(result, list) else 0,
            'success': True
        }
    
    def get_all_files_recursive(self, project_id: str, ref: str = 'main', 
                               max_files: int = 50, 
                               extensions: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Рекурсивно получает все файлы проекта для анализа
        
        Args:
            project_id: ID или путь проекта
            ref: Ветка или тег
            max_files: Максимальное количество файлов (по умолчанию 50)
            extensions: Список расширений файлов для фильтрации (опционально)
        
        Returns:
            Список файлов с содержимым
        """
        if extensions is None:
            # Расширяем список поддерживаемых расширений
            extensions = ['.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.h', '.hpp', 
                         '.cs', '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.scala', '.clj',
                         '.html', '.css', '.scss', '.vue', '.xml', '.json', '.yaml', '.yml',
                         '.sh', '.bash', '.sql', '.r', '.m', '.mm']
        
        files_list = []
        errors = []
        
        def _get_files_recursive(path: str = '', depth: int = 0, max_depth: int = 10) -> List[Dict[str, Any]]:
            """Рекурсивно получает файлы"""
            nonlocal files_list
            
            if depth > max_depth:
                return []
            
            if len(files_list) >= max_files:
                return files_list
            
            try:
                tree_result = self.list_repository_files(project_id, path, ref)
                
                if 'error' in tree_result:
                    errors.append(f"Ошибка в {path}: {tree_result.get('error', 'Unknown error')}")
                    return []
                
                items = tree_result.get('items', [])
                
                if not items:
                    return []
                
                for item in items:
                    if len(files_list) >= max_files:
                        break
                        
                    item_type = item.get('type', '')
                    item_path = item.get('path', '') or item.get('name', '')
                    
                    if item_type == 'tree':
                        # Рекурсивно получаем файлы из папки
                        _get_files_recursive(item_path, depth + 1, max_depth)
                    elif item_type == 'blob':
                        # Проверяем расширение файла
                        file_ext = None
                        for ext in extensions:
                            if item_path.endswith(ext):
                                file_ext = ext
                                break
                        
                        # Если расширение не в списке, пропускаем
                        if not file_ext:
                            continue
                        
                        try:
                            # Получаем содержимое файла
                            file_content = self.get_file_content(project_id, item_path, ref)
                            
                            if 'error' in file_content:
                                errors.append(f"Ошибка загрузки {item_path}: {file_content.get('error')}")
                                continue
                            
                            content = file_content.get('content', '')
                            
                            # Пропускаем пустые файлы
                            if not content or len(content.strip()) == 0:
                                continue
                            
                            files_list.append({
                                'path': item_path,
                                'content': content,
                                'size': len(content)
                            })
                            
                            if len(files_list) >= max_files:
                                break
                                
                        except Exception as e:
                            errors.append(f"Исключение при обработке {item_path}: {str(e)}")
                            continue
                            
            except Exception as e:
                errors.append(f"Ошибка при рекурсивном обходе {path}: {str(e)}")
            
            return files_list
        
        try:
            # Начинаем с корня
            _get_files_recursive('', 0, 10)
            
            result = {
                'files': files_list,
                'count': len(files_list),
                'success': len(files_list) > 0
            }
            
            if errors:
                result['warnings'] = errors[:10]  # Ограничиваем количество предупреждений
            
            if len(files_list) == 0:
                error_msg = 'Не найдено файлов для анализа'
                if errors:
                    error_msg += f'. Ошибки: {"; ".join(errors[:3])}'
                result['error'] = error_msg
                result['success'] = False
            
            return result
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return {
                'error': f'Ошибка при загрузке файлов: {str(e)}',
                'details': error_details,
                'files': [],
                'count': 0,
                'success': False
            }
    
    # ==================== Merge Requests ====================
    
    def list_merge_requests(self, project_id: Optional[str] = None, 
                           state: Optional[str] = None) -> Dict[str, Any]:
        """
        Получает список Merge Requests
        
        Args:
            project_id: ID проекта (опционально, если не указан - все проекты)
            state: Фильтр по состоянию (opened, closed, merged, all)
        
        Returns:
            Список MR
        """
        if project_id:
            project_id_encoded = requests.utils.quote(str(project_id), safe='')
            endpoint = f'/projects/{project_id_encoded}/merge_requests'
        else:
            endpoint = '/merge_requests'
        
        params = {'per_page': 100}
        if state:
            params['state'] = state
        
        result = self._make_request('GET', endpoint, params=params)
        
        if 'error' in result:
            return result
        
        return {
            'merge_requests': result if isinstance(result, list) else [],
            'count': len(result) if isinstance(result, list) else 0,
            'success': True
        }
    
    def get_merge_request(self, project_id: str, mr_id: str) -> Dict[str, Any]:
        """
        Получает информацию о Merge Request
        
        Args:
            project_id: ID или путь проекта
            mr_id: ID Merge Request
        
        Returns:
            Информация о MR
        """
        project_id_encoded = requests.utils.quote(str(project_id), safe='')
        return self._make_request('GET', f'/projects/{project_id_encoded}/merge_requests/{mr_id}')
    
    def get_merge_request_diff(self, project_id: str, mr_id: str) -> Dict[str, Any]:
        """
        Получает diff изменений в Merge Request
        
        Args:
            project_id: ID или путь проекта
            mr_id: ID Merge Request
        
        Returns:
            Diff изменений
        """
        project_id_encoded = requests.utils.quote(str(project_id), safe='')
        result = self._make_request('GET', f'/projects/{project_id_encoded}/merge_requests/{mr_id}/diffs')
        
        if 'error' in result:
            return result
        
        return {
            'diffs': result if isinstance(result, list) else [],
            'success': True
        }
    
    # ==================== Локальное управление статусами MR (для совместимости) ====================
    
    def update_mr_status(self, mr_id: str, status: str, 
                        labels: Optional[List[str]] = None,
                        review_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Обновляет локальный статус MR (для совместимости)
        
        Args:
            mr_id: ID Merge Request
            status: Статус (ready-for-merge, needs-review, changes-requested)
            labels: Метки MR (опционально)
            review_data: Данные ревью (опционально)
        
        Returns:
            Результат обновления
        """
        valid_statuses = ['ready-for-merge', 'needs-review', 'changes-requested', 'reject']
        if status not in valid_statuses:
            return {'error': f'Недопустимый статус: {status}. Допустимые: {valid_statuses}'}
        
        try:
            # Загружаем существующие MR
            with open(self.mr_statuses_file, 'r', encoding='utf-8') as f:
                mrs = json.load(f)
            
            # Ищем существующий MR или создаём новый
            mr_found = False
            for mr in mrs:
                if mr.get('mr_id') == mr_id:
                    mr['status'] = status
                    mr['labels'] = labels or mr.get('labels', [])
                    mr['updated_at'] = datetime.now().isoformat()
                    if review_data:
                        mr['review_data'] = review_data
                    mr_found = True
                    break
            
            if not mr_found:
                new_mr = {
                    'mr_id': mr_id,
                    'status': status,
                    'labels': labels or [],
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat(),
                    'review_data': review_data or {}
                }
                mrs.append(new_mr)
            
            # Сохраняем
            with open(self.mr_statuses_file, 'w', encoding='utf-8') as f:
                json.dump(mrs, f, ensure_ascii=False, indent=2)
            
            return {
                'mr_id': mr_id,
                'status': status,
                'labels': labels or [],
                'success': True
            }
        except Exception as e:
            return {'error': f'Ошибка при обновлении статуса MR: {str(e)}'}
    
    def get_mr_status(self, mr_id: str) -> Dict[str, Any]:
        """
        Получает локальный статус MR (для совместимости)
        
        Args:
            mr_id: ID Merge Request
        
        Returns:
            Информация о MR
        """
        try:
            with open(self.mr_statuses_file, 'r', encoding='utf-8') as f:
                mrs = json.load(f)
            
            for mr in mrs:
                if mr.get('mr_id') == mr_id:
                    return mr
            
            return {'error': f'MR {mr_id} не найден'}
        except Exception as e:
            return {'error': f'Ошибка при получении статуса MR: {str(e)}'}
    
    def list_mrs(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Получает локальный список MR (для совместимости)
        
        Args:
            status_filter: Фильтр по статусу (опционально)
        
        Returns:
            Список MR
        """
        try:
            with open(self.mr_statuses_file, 'r', encoding='utf-8') as f:
                mrs = json.load(f)
            
            if status_filter:
                mrs = [mr for mr in mrs if mr.get('status') == status_filter]
            
            return mrs
        except Exception as e:
            return [{'error': f'Ошибка при получении списка MR: {str(e)}'}]
    
    def add_labels(self, mr_id: str, labels: List[str]) -> Dict[str, Any]:
        """
        Добавляет метки к локальному MR (для совместимости)
        
        Args:
            mr_id: ID Merge Request
            labels: Список меток
        
        Returns:
            Результат добавления меток
        """
        try:
            with open(self.mr_statuses_file, 'r', encoding='utf-8') as f:
                mrs = json.load(f)
            
            for mr in mrs:
                if mr.get('mr_id') == mr_id:
                    existing_labels = mr.get('labels', [])
                    new_labels = list(set(existing_labels + labels))
                    mr['labels'] = new_labels
                    mr['updated_at'] = datetime.now().isoformat()
                    
                    with open(self.mr_statuses_file, 'w', encoding='utf-8') as f:
                        json.dump(mrs, f, ensure_ascii=False, indent=2)
                    
                    return {
                        'mr_id': mr_id,
                        'labels': new_labels,
                        'success': True
                    }
            
            return {'error': f'MR {mr_id} не найден'}
        except Exception as e:
            return {'error': f'Ошибка при добавлении меток: {str(e)}'}
    
    def add_mr_comment(self, project_id: str, mr_id: str, comment: str, 
                       position: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Добавляет комментарий к Merge Request в GitLab
        
        Args:
            project_id: ID или путь проекта
            mr_id: ID Merge Request
            comment: Текст комментария
            position: Позиция комментария (опционально, для inline комментариев)
        
        Returns:
            Результат добавления комментария
        """
        project_id_encoded = requests.utils.quote(str(project_id), safe='')
        
        data = {
            'body': comment
        }
        
        if position:
            data['position'] = position
        
        result = self._make_request('POST', 
                                  f'/projects/{project_id_encoded}/merge_requests/{mr_id}/notes', 
                                  json=data)
        
        if 'error' in result:
            return result
        
        return {
            'success': True,
            'comment_id': result.get('id'),
            'comment': result
        }
    
    def add_mr_discussion(self, project_id: str, mr_id: str, body: str) -> Dict[str, Any]:
        """
        Создаёт обсуждение (discussion) в Merge Request
        
        Args:
            project_id: ID или путь проекта
            mr_id: ID Merge Request
            body: Текст обсуждения
        
        Returns:
            Результат создания обсуждения
        """
        project_id_encoded = requests.utils.quote(str(project_id), safe='')
        
        data = {
            'body': body
        }
        
        result = self._make_request('POST', 
                                  f'/projects/{project_id_encoded}/merge_requests/{mr_id}/discussions', 
                                  json=data)
        
        if 'error' in result:
            return result
        
        return {
            'success': True,
            'discussion': result
        }
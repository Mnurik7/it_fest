"""
Модуль управления проектами и командами
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import google.generativeai as genai


class ProjectManager:
    """Управление проектами, командами и сотрудниками"""
    
    def __init__(self, gemini_model, data_dir: str = "data"):
        self.model = gemini_model
        self.data_dir = data_dir
        self.projects_file = os.path.join(data_dir, "scrum_projects.json")
        self.teams_file = os.path.join(data_dir, "scrum_teams.json")
        self.members_file = os.path.join(data_dir, "scrum_members.json")
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """Создаёт директорию для данных если не существует"""
        os.makedirs(self.data_dir, exist_ok=True)
    
    def create_project(self, name: str, description: str, owner: str, deadline: Optional[str] = None) -> Dict[str, Any]:
        """
        Создаёт новый проект
        
        Args:
            name: Название проекта
            description: Описание проекта
            owner: Владелец проекта
            deadline: Дедлайн проекта (опционально)
            
        Returns:
            Созданный проект
        """
        projects = self._load_projects()
        
        project = {
            "project_id": f"PROJ-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "name": name,
            "description": description,
            "owner": owner,
            "status": "active",
            "deadline": deadline,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "sprints": [],
            "team_members": []
        }
        
        projects.append(project)
        self._save_projects(projects)
        return project
    
    def create_team(self, project_id: str, team_name: str, members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Создаёт команду для проекта
        
        Args:
            project_id: ID проекта
            team_name: Название команды
            members: Список участников команды
            
        Returns:
            Созданная команда
        """
        teams = self._load_teams()
        
        team = {
            "team_id": f"TEAM-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "project_id": project_id,
            "name": team_name,
            "members": members,
            "created_at": datetime.now().isoformat()
        }
        
        teams.append(team)
        self._save_teams(teams)
        
        # Обновляем проект
        projects = self._load_projects()
        for project in projects:
            if project["project_id"] == project_id:
                project["team_members"] = members
                project["updated_at"] = datetime.now().isoformat()
                self._save_projects(projects)
                break
        
        return team
    
    def add_member(self, project_id: str, username: str, role: str, workload: float = 1.0) -> Dict[str, Any]:
        """
        Добавляет сотрудника в проект
        
        Args:
            project_id: ID проекта
            username: Имя пользователя
            role: Роль (developer, analyst, po, scrum_master, manager)
            workload: Загрузка (0.0-1.0)
            
        Returns:
            Информация о добавленном участнике
        """
        members = self._load_members()
        
        member = {
            "member_id": f"MEM-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "project_id": project_id,
            "username": username,
            "role": role,
            "workload": workload,
            "active_tasks": [],
            "sprint_participation": [],
            "joined_at": datetime.now().isoformat()
        }
        
        members.append(member)
        self._save_members(members)
        
        # Обновляем проект
        projects = self._load_projects()
        for project in projects:
            if project["project_id"] == project_id:
                if not any(m.get("username") == username for m in project.get("team_members", [])):
                    project.setdefault("team_members", []).append({
                        "username": username,
                        "role": role,
                        "workload": workload
                    })
                    project["updated_at"] = datetime.now().isoformat()
                    self._save_projects(projects)
                break
        
        return member
    
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Получает проект по ID"""
        projects = self._load_projects()
        for project in projects:
            if project["project_id"] == project_id:
                return project
        return None
    
    def get_projects(self, username: Optional[str] = None) -> List[Dict[str, Any]]:
        """Получает список проектов (опционально фильтр по пользователю)"""
        projects = self._load_projects()
        if username:
            return [p for p in projects if username in [m.get("username") for m in p.get("team_members", [])]]
        return projects
    
    def get_team_members(self, project_id: str) -> List[Dict[str, Any]]:
        """Получает участников команды проекта"""
        members = self._load_members()
        return [m for m in members if m.get("project_id") == project_id]
    
    def update_member_workload(self, member_id: str, workload: float):
        """Обновляет загрузку участника"""
        members = self._load_members()
        for member in members:
            if member["member_id"] == member_id:
                member["workload"] = workload
                member["updated_at"] = datetime.now().isoformat()
                self._save_members(members)
                break
    
    def _load_projects(self) -> List[Dict[str, Any]]:
        """Загружает проекты из файла"""
        if os.path.exists(self.projects_file):
            try:
                with open(self.projects_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_projects(self, projects: List[Dict[str, Any]]):
        """Сохраняет проекты в файл"""
        with open(self.projects_file, 'w', encoding='utf-8') as f:
            json.dump(projects, f, ensure_ascii=False, indent=2)
    
    def _load_teams(self) -> List[Dict[str, Any]]:
        """Загружает команды из файла"""
        if os.path.exists(self.teams_file):
            try:
                with open(self.teams_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_teams(self, teams: List[Dict[str, Any]]):
        """Сохраняет команды в файл"""
        with open(self.teams_file, 'w', encoding='utf-8') as f:
            json.dump(teams, f, ensure_ascii=False, indent=2)
    
    def _load_members(self) -> List[Dict[str, Any]]:
        """Загружает участников из файла"""
        if os.path.exists(self.members_file):
            try:
                with open(self.members_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_members(self, members: List[Dict[str, Any]]):
        """Сохраняет участников в файл"""
        with open(self.members_file, 'w', encoding='utf-8') as f:
            json.dump(members, f, ensure_ascii=False, indent=2)


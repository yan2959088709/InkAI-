# 完善版数据管理器
# 包含数据持久化、同步机制、统计分析、备份恢复、查询优化

import json
import os
import shutil
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import uuid

from ..core.base_agent import EnhancedBaseAgent


class EnhancedDataManager(EnhancedBaseAgent):
    """完善版数据管理器 - 智能数据存储和管理系统"""
    
    def __init__(self, data_dir: str = "data"):
        super().__init__("增强数据管理器")
        
        self.data_dir = data_dir
        self.novels_dir = os.path.join(data_dir, "novels")
        self.backup_dir = os.path.join(data_dir, "backups")
        self.temp_dir = os.path.join(data_dir, "temp")
        
        # 创建必要的目录
        self._create_directories()
        
        # 数据版本控制
        self.version_info = {
            "current_version": "2.0.0",
            "compatibility": ["1.0.0", "1.5.0"],
            "last_updated": datetime.now().isoformat()
        }
        
        # 数据统计
        self.stats = {
            "total_novels": 0,
            "total_chapters": 0,
            "total_characters": 0,
            "storage_usage": 0,
            "last_backup": None
        }
        
        # 缓存系统
        self.cache = {}
        self.cache_ttl = 300  # 5分钟缓存
        
        self._log("完善版数据管理器初始化完成", "INFO")
        self._load_statistics()
    
    def _create_directories(self):
        """创建必要的目录结构"""
        directories = [self.data_dir, self.novels_dir, self.backup_dir, self.temp_dir]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            self._log(f"创建目录: {directory}", "DEBUG")
    
    def create_novel_project(self, novel_data: Dict[str, Any]) -> str:
        """创建新的小说项目"""
        self._log("开始创建小说项目", "INFO")
        
        # 生成项目ID
        project_id = str(uuid.uuid4())
        
        # 创建项目目录
        project_dir = os.path.join(self.novels_dir, project_id)
        os.makedirs(project_dir, exist_ok=True)
        
        # 创建子目录
        subdirs = ["chapters", "characters", "storylines", "assessments", "exports"]
        for subdir in subdirs:
            os.makedirs(os.path.join(project_dir, subdir), exist_ok=True)
        
        # 保存项目元数据
        metadata = {
            "id": project_id,
            "title": novel_data.get("title", "未命名小说"),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "version": self.version_info["current_version"],
            "status": "创建中",
            "tags": novel_data.get("tags", {}),
            "characters": [],
            "chapters": [],
            "storyline": {},
            "assessments": {},
            "statistics": {
                "word_count": 0,
                "chapter_count": 0,
                "character_count": 0,
                "last_activity": datetime.now().isoformat()
            }
        }
        
        # 保存元数据文件
        metadata_path = os.path.join(project_dir, "metadata.json")
        self._save_json(metadata_path, metadata)
        
        # 更新统计信息
        self._update_statistics()
        
        self._log(f"小说项目创建完成: {project_id}", "INFO")
        return project_id
    
    def save_novel_data(self, project_id: str, data_type: str, data: Dict[str, Any]) -> bool:
        """保存小说数据"""
        self._log(f"保存{data_type}数据到项目: {project_id}", "INFO")
        
        project_dir = os.path.join(self.novels_dir, project_id)
        if not os.path.exists(project_dir):
            self._log(f"项目目录不存在: {project_id}", "ERROR")
            return False
        
        try:
            # 根据数据类型选择保存路径
            if data_type == "metadata":
                file_path = os.path.join(project_dir, "metadata.json")
            elif data_type == "characters":
                file_path = os.path.join(project_dir, "characters", "characters.json")
            elif data_type == "storyline":
                file_path = os.path.join(project_dir, "storylines", "storyline.json")
            elif data_type == "chapter":
                chapter_id = data.get("id", str(uuid.uuid4()))
                file_path = os.path.join(project_dir, "chapters", f"chapter_{chapter_id}.json")
            elif data_type == "assessment":
                assessment_type = data.get("type", "general")
                file_path = os.path.join(project_dir, "assessments", f"{assessment_type}_assessment.json")
            else:
                file_path = os.path.join(project_dir, f"{data_type}.json")
            
            # 保存数据
            success = self._save_json(file_path, data)
            
            if success:
                # 更新项目元数据
                self._update_project_metadata(project_id, data_type, data)
                
                # 更新缓存
                cache_key = f"{project_id}_{data_type}"
                self.cache[cache_key] = {
                    "data": data,
                    "timestamp": datetime.now(),
                    "file_path": file_path
                }
            
            return success
            
        except Exception as e:
            self._log(f"保存数据失败: {e}", "ERROR")
            return False
    
    def load_novel_data(self, project_id: str, data_type: str) -> Optional[Dict[str, Any]]:
        """加载小说数据"""
        self._log(f"加载{data_type}数据从项目: {project_id}", "INFO")
        
        # 检查缓存
        cache_key = f"{project_id}_{data_type}"
        if cache_key in self.cache:
            cache_data = self.cache[cache_key]
            if datetime.now() - cache_data["timestamp"] < timedelta(seconds=self.cache_ttl):
                self._log("从缓存加载数据", "DEBUG")
                return cache_data["data"]
        
        project_dir = os.path.join(self.novels_dir, project_id)
        if not os.path.exists(project_dir):
            self._log(f"项目目录不存在: {project_id}", "ERROR")
            return None
        
        try:
            # 根据数据类型选择加载路径
            if data_type == "metadata":
                file_path = os.path.join(project_dir, "metadata.json")
            elif data_type == "characters":
                file_path = os.path.join(project_dir, "characters", "characters.json")
            elif data_type == "storyline":
                file_path = os.path.join(project_dir, "storylines", "storyline.json")
            elif data_type == "chapters":
                # 加载所有章节
                chapters_dir = os.path.join(project_dir, "chapters")
                chapters = []
                if os.path.exists(chapters_dir):
                    for filename in os.listdir(chapters_dir):
                        if filename.endswith(".json"):
                            chapter_path = os.path.join(chapters_dir, filename)
                            chapter_data = self._load_json(chapter_path)
                            if chapter_data:
                                chapters.append(chapter_data)
                return {"chapters": chapters}
            elif data_type == "assessments":
                # 加载所有评估
                assessments_dir = os.path.join(project_dir, "assessments")
                assessments = {}
                if os.path.exists(assessments_dir):
                    for filename in os.listdir(assessments_dir):
                        if filename.endswith(".json"):
                            assessment_path = os.path.join(assessments_dir, filename)
                            assessment_data = self._load_json(assessment_path)
                            if assessment_data:
                                assessment_type = filename.replace("_assessment.json", "")
                                assessments[assessment_type] = assessment_data
                return assessments
            else:
                file_path = os.path.join(project_dir, f"{data_type}.json")
            
            # 加载数据
            data = self._load_json(file_path)
            
            if data:
                # 更新缓存
                self.cache[cache_key] = {
                    "data": data,
                    "timestamp": datetime.now(),
                    "file_path": file_path
                }
            
            return data
            
        except Exception as e:
            self._log(f"加载数据失败: {e}", "ERROR")
            return None
    
    def load_novel_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """加载完整的小说项目数据"""
        self._log(f"加载完整项目: {project_id}", "INFO")
        
        # 加载元数据
        metadata = self.load_novel_data(project_id, "metadata")
        if not metadata:
            return None
        
        # 加载其他数据
        characters = self.load_novel_data(project_id, "characters")
        storyline = self.load_novel_data(project_id, "storyline")
        chapters_data = self.load_novel_data(project_id, "chapters")
        
        # 组合完整数据
        project_data = metadata.copy()
        if characters:
            project_data["characters"] = characters
        if storyline:
            project_data["storyline"] = storyline
        if chapters_data:
            project_data["chapters"] = chapters_data.get("chapters", [])
        
        return project_data
    
    def save_novel_project(self, project_id: str, project_data: Dict[str, Any]) -> bool:
        """保存完整的小说项目数据"""
        self._log(f"保存完整项目: {project_id}", "INFO")
        
        try:
            # 保存元数据
            metadata = {k: v for k, v in project_data.items() 
                       if k not in ["characters", "storyline", "chapters"]}
            metadata["updated_at"] = datetime.now().isoformat()
            
            success = self.save_novel_data(project_id, "metadata", metadata)
            if not success:
                return False
            
            # 保存其他数据
            if "characters" in project_data:
                success = self.save_novel_data(project_id, "characters", project_data["characters"])
                if not success:
                    return False
            
            if "storyline" in project_data:
                success = self.save_novel_data(project_id, "storyline", project_data["storyline"])
                if not success:
                    return False
            
            # 保存章节数据
            if "chapters" in project_data:
                for chapter in project_data["chapters"]:
                    chapter_data = chapter.copy()
                    chapter_data["id"] = chapter_data.get("id", str(uuid.uuid4()))
                    success = self.save_novel_data(project_id, "chapter", chapter_data)
                    if not success:
                        self._log(f"保存章节失败: {chapter_data.get('title', '未知')}", "ERROR")
            
            return True
            
        except Exception as e:
            self._log(f"保存项目失败: {e}", "ERROR")
            return False
    
    def list_novel_projects(self) -> List[str]:
        """列出所有小说项目ID"""
        projects = []
        
        if os.path.exists(self.novels_dir):
            for item in os.listdir(self.novels_dir):
                item_path = os.path.join(self.novels_dir, item)
                if os.path.isdir(item_path):
                    # 检查是否有元数据文件
                    metadata_path = os.path.join(item_path, "metadata.json")
                    if os.path.exists(metadata_path):
                        projects.append(item)
        
        return projects
    
    def _save_json(self, file_path: str, data: Dict[str, Any]) -> bool:
        """保存JSON数据"""
        try:
            # 创建备份
            if os.path.exists(file_path):
                backup_path = f"{file_path}.backup"
                shutil.copy2(file_path, backup_path)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 保存数据
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self._log(f"数据保存成功: {file_path}", "DEBUG")
            return True
            
        except Exception as e:
            self._log(f"保存JSON失败: {e}", "ERROR")
            return False
    
    def _load_json(self, file_path: str) -> Optional[Dict[str, Any]]:
        """加载JSON数据"""
        try:
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._log(f"数据加载成功: {file_path}", "DEBUG")
            return data
            
        except Exception as e:
            self._log(f"加载JSON失败: {e}", "ERROR")
            return None
    
    def _update_project_metadata(self, project_id: str, data_type: str, data: Dict[str, Any]):
        """更新项目元数据"""
        metadata_path = os.path.join(self.novels_dir, project_id, "metadata.json")
        metadata = self._load_json(metadata_path)
        
        if metadata:
            metadata["updated_at"] = datetime.now().isoformat()
            metadata["statistics"]["last_activity"] = datetime.now().isoformat()
            
            # 保存更新的元数据
            self._save_json(metadata_path, metadata)
    
    def _load_statistics(self):
        """加载统计信息"""
        stats_path = os.path.join(self.data_dir, "statistics.json")
        if os.path.exists(stats_path):
            stats_data = self._load_json(stats_path)
            if stats_data:
                self.stats.update(stats_data)
    
    def _save_statistics(self):
        """保存统计信息"""
        stats_path = os.path.join(self.data_dir, "statistics.json")
        self._save_json(stats_path, self.stats)
    
    def _update_statistics(self):
        """更新统计信息"""
        projects = self.list_novel_projects()
        self.stats["total_novels"] = len(projects)
        
        total_chapters = 0
        total_characters = 0
        
        for project_id in projects:
            chapters_data = self.load_novel_data(project_id, "chapters")
            if chapters_data:
                total_chapters += len(chapters_data.get("chapters", []))
            
            characters_data = self.load_novel_data(project_id, "characters")
            if characters_data:
                # 简单计数，实际可能需要更复杂的逻辑
                total_characters += 1
        
        self.stats["total_chapters"] = total_chapters
        self.stats["total_characters"] = total_characters
        self.stats["storage_usage"] = self._get_directory_size(self.data_dir)
        
        self._save_statistics()
    
    def _get_directory_size(self, directory: str) -> int:
        """获取目录大小"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except Exception as e:
            self._log(f"计算目录大小失败: {e}", "ERROR")
        
        return total_size
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        self._update_statistics()
        return self.stats.copy()
    
    def backup_project(self, project_id: str, backup_name: str = None) -> str:
        """备份项目"""
        self._log(f"开始备份项目: {project_id}", "INFO")
        
        if not backup_name:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        project_dir = os.path.join(self.novels_dir, project_id)
        backup_path = os.path.join(self.backup_dir, f"{project_id}_{backup_name}")
        
        try:
            # 创建备份目录
            os.makedirs(backup_path, exist_ok=True)
            
            # 复制项目文件
            shutil.copytree(project_dir, backup_path, dirs_exist_ok=True)
            
            # 创建备份信息文件
            backup_info = {
                "project_id": project_id,
                "backup_name": backup_name,
                "backup_time": datetime.now().isoformat(),
                "backup_size": self._get_directory_size(backup_path),
                "version": self.version_info["current_version"]
            }
            
            backup_info_path = os.path.join(backup_path, "backup_info.json")
            self._save_json(backup_info_path, backup_info)
            
            # 更新统计信息
            self.stats["last_backup"] = datetime.now().isoformat()
            self._save_statistics()
            
            self._log(f"项目备份完成: {backup_path}", "INFO")
            return backup_path
            
        except Exception as e:
            self._log(f"备份项目失败: {e}", "ERROR")
            return ""

"""
[DEPRECATED] 核心知识管理器（旧流水线遗留）

⚠ 本模块属于 InkAI 旧版状态机式 workflow（inkai_workflow_optimized.py）的产物，
   已被新流水线（run_init_novel/run_outline_demo/run_chapter_demo）完全取代。
   - 旧"核心知识"已被 characters.json + storyline.json 直接承载
   - 新代码请勿 import 本模块；保留它仅为兼容历史 novel_dir 中残留的
     core_knowledge.json 文件不被误读。

详见：docs/development/data_files_catalog.md
"""
import warnings as _warnings
_warnings.warn(
    "core.core_knowledge_manager 已废弃；新流水线请使用 characters.json + storyline.json。"
    "详见 docs/development/data_files_catalog.md",
    DeprecationWarning,
    stacklevel=2,
)

from typing import Dict, List, Any, Optional
import json
import os
from datetime import datetime
from utils.logger import get_logger
logger = get_logger("core_knowledge_manager")


class CoreKnowledgeManager:
    """核心知识管理器"""
    
    def __init__(self, data_manager=None):
        self.data_manager = data_manager
        self.core_knowledge_cache = {}
        self.knowledge_file = "core_knowledge.json"
    
    def initialize_core_knowledge(self, novel_id: str, novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """初始化核心知识"""
        try:
            # 从小说数据中提取核心知识
            core_knowledge = {
                "novel_id": novel_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "novel_info": {
                    "title": novel_data.get("metadata", {}).get("title", ""),
                    "author": novel_data.get("metadata", {}).get("author", ""),
                    "description": novel_data.get("metadata", {}).get("description", ""),
                    "tags": novel_data.get("tags", {}),
                    "user_requirements": novel_data.get("user_requirements", "")
                },
                "character_profiles": self._extract_character_profiles(novel_data),
                "world_setting": self._extract_world_setting(novel_data),
                "story_themes": self._extract_story_themes(novel_data),
                "basic_rules": self._extract_basic_rules(novel_data)
            }
            
            # 缓存核心知识
            self.core_knowledge_cache[novel_id] = core_knowledge
            
            # 保存到文件
            self._save_core_knowledge(novel_id, core_knowledge)
            
            return core_knowledge
            
        except Exception as e:
            logger.error(f"初始化核心知识失败: {e}")
            return {}
    
    def get_core_knowledge(self, novel_id: str) -> Dict[str, Any]:
        """获取核心知识"""
        # 先检查缓存
        if novel_id in self.core_knowledge_cache:
            return self.core_knowledge_cache[novel_id]
        
        # 从文件加载
        core_knowledge = self._load_core_knowledge(novel_id)
        if core_knowledge:
            self.core_knowledge_cache[novel_id] = core_knowledge
        
        return core_knowledge
    
    def update_core_knowledge(self, novel_id: str, updates: Dict[str, Any]) -> bool:
        """更新核心知识"""
        try:
            core_knowledge = self.get_core_knowledge(novel_id)
            if not core_knowledge:
                return False
            
            # 更新核心知识
            for key, value in updates.items():
                if key in core_knowledge:
                    core_knowledge[key] = value
            
            core_knowledge["updated_at"] = datetime.now().isoformat()
            
            # 更新缓存
            self.core_knowledge_cache[novel_id] = core_knowledge
            
            # 保存到文件
            self._save_core_knowledge(novel_id, core_knowledge)
            
            return True
            
        except Exception as e:
            logger.error(f"更新核心知识失败: {e}")
            return False
    
    def _extract_character_profiles(self, novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取人物档案"""
        characters = novel_data.get("characters", {})
        
        # 提取主角档案
        main_character = characters.get("main_character", {})
        main_profile = {
            "name": main_character.get("basic_info", {}).get("name", ""),
            "age": main_character.get("basic_info", {}).get("age", 0),
            "gender": main_character.get("basic_info", {}).get("gender", ""),
            "occupation": main_character.get("basic_info", {}).get("occupation", ""),
            "personality": main_character.get("personality", {}),
            "background": main_character.get("background", {}),
            "skills": main_character.get("skills", []),
            "relationships": main_character.get("relationships", {})
        }
        
        # 提取配角档案
        supporting_characters = characters.get("supporting_characters", [])
        supporting_profiles = []
        
        for char in supporting_characters:
            if isinstance(char, dict):
                profile = {
                    "name": char.get("basic_info", {}).get("name", ""),
                    "age": char.get("basic_info", {}).get("age", 0),
                    "gender": char.get("basic_info", {}).get("gender", ""),
                    "occupation": char.get("basic_info", {}).get("occupation", ""),
                    "role": char.get("role", ""),
                    "personality": char.get("personality", ""),
                    "relationship_with_main": char.get("relationship_with_main", "")
                }
                supporting_profiles.append(profile)
        
        return {
            "main_character": main_profile,
            "supporting_characters": supporting_profiles,
            "character_relationships": characters.get("character_relationships", {})
        }
    
    def _extract_world_setting(self, novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取世界观设定"""
        storyline = novel_data.get("storyline", {})
        overall_storyline = storyline.get("overall_storyline", {})
        
        world_setting = overall_storyline.get("world_setting", {})
        
        # 如果world_setting是字符串，尝试解析
        if isinstance(world_setting, str):
            return {"description": world_setting}
        
        # 如果是字典，直接返回
        if isinstance(world_setting, dict):
            return world_setting
        
        return {"description": "未知世界观"}
    
    def _extract_story_themes(self, novel_data: Dict[str, Any]) -> List[str]:
        """提取故事主题"""
        storyline = novel_data.get("storyline", {})
        overall_storyline = storyline.get("overall_storyline", {})
        
        themes = overall_storyline.get("themes", [])
        if isinstance(themes, list):
            return themes
        
        return []
    
    def _extract_basic_rules(self, novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取基础规则"""
        return {
            "story_structure": novel_data.get("storyline", {}).get("story_structure", {}),
            "writing_style": novel_data.get("metadata", {}).get("writing_style", ""),
            "target_audience": novel_data.get("metadata", {}).get("target_audience", ""),
            "content_rating": novel_data.get("metadata", {}).get("content_rating", "")
        }
    
    def _save_core_knowledge(self, novel_id: str, core_knowledge: Dict[str, Any]) -> bool:
        """保存核心知识到文件"""
        try:
            if self.data_manager and hasattr(self.data_manager, 'novels_dir'):
                # 使用数据管理器保存
                novel_dir = os.path.join(self.data_manager.novels_dir, novel_id)
                os.makedirs(novel_dir, exist_ok=True)
                
                file_path = os.path.join(novel_dir, self.knowledge_file)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(core_knowledge, f, ensure_ascii=False, indent=2)
            else:
                # 使用当前目录作为备选
                os.makedirs("core_knowledge", exist_ok=True)
                file_path = os.path.join("core_knowledge", f"{novel_id}_{self.knowledge_file}")
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(core_knowledge, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"保存核心知识失败: {e}")
            return False
    
    def _load_core_knowledge(self, novel_id: str) -> Optional[Dict[str, Any]]:
        """从文件加载核心知识"""
        try:
            if self.data_manager:
                # 使用数据管理器加载
                novel_dir = os.path.join(self.data_manager.novels_dir, novel_id)
                file_path = os.path.join(novel_dir, self.knowledge_file)
            else:
                # 从当前目录加载
                file_path = self.knowledge_file
            
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            return None
            
        except Exception as e:
            logger.error(f"加载核心知识失败: {e}")
            return None
    
    def clear_cache(self, novel_id: str = None):
        """清理缓存"""
        if novel_id:
            self.core_knowledge_cache.pop(novel_id, None)
        else:
            self.core_knowledge_cache.clear()
    
    def get_knowledge_summary(self, novel_id: str) -> Dict[str, Any]:
        """获取知识摘要"""
        core_knowledge = self.get_core_knowledge(novel_id)
        if not core_knowledge:
            return {}
        
        return {
            "novel_title": core_knowledge.get("novel_info", {}).get("title", ""),
            "main_character": core_knowledge.get("character_profiles", {}).get("main_character", {}).get("name", ""),
            "supporting_characters_count": len(core_knowledge.get("character_profiles", {}).get("supporting_characters", [])),
            "world_setting": core_knowledge.get("world_setting", {}),
            "themes": core_knowledge.get("story_themes", []),
            "last_updated": core_knowledge.get("updated_at", "")
        }

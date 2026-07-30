"""
增强角色状态追踪器
提供多维度的角色状态管理，包括情感、能力、心理和社交状态
"""

from typing import Dict, List, Any, Optional
import json
import os
from datetime import datetime
from utils.logger import get_logger
logger = get_logger("enhanced_character_tracker")


class EnhancedCharacterTracker:
    """增强角色状态追踪器"""
    
    def __init__(self, data_manager=None):
        self.data_manager = data_manager
        self.character_states_cache = {}
        self.states_file = "enhanced_character_states.json"
    
    def initialize_character_states(self, novel_id: str) -> Dict[str, Any]:
        """初始化角色状态"""
        try:
            character_states = {
                "novel_id": novel_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "character_states": {}  # {character_name: {emotional_state, ability_state, etc.}}
            }
            
            # 缓存状态数据
            self.character_states_cache[novel_id] = character_states
            
            # 保存到文件
            self._save_character_states(novel_id, character_states)
            
            return character_states
            
        except Exception as e:
            logger.error(f"初始化角色状态失败: {e}")
            return {}
    
    def get_character_states(self, novel_id: str) -> Dict[str, Any]:
        """获取角色状态"""
        # 先检查缓存
        if novel_id in self.character_states_cache:
            return self.character_states_cache[novel_id]
        
        # 从文件加载
        character_states = self._load_character_states(novel_id)
        if character_states:
            self.character_states_cache[novel_id] = character_states
        else:
            character_states = self.initialize_character_states(novel_id)
        
        return character_states
    
    def update_emotional_state(self, novel_id: str, chapter_number: int, 
                             character_name: str, emotional_changes: Dict[str, Any]) -> bool:
        """更新角色情感状态"""
        try:
            character_states = self.get_character_states(novel_id)
            
            # 初始化角色状态
            if character_name not in character_states["character_states"]:
                character_states["character_states"][character_name] = {
                    "emotional_state": {},
                    "ability_state": {},
                    "psychological_state": {},
                    "social_state": {}
                }
            
            character_data = character_states["character_states"][character_name]
            
            # 更新情感状态
            if "emotional_state" not in character_data:
                character_data["emotional_state"] = {}
            
            emotional_state = character_data["emotional_state"]
            
            # 记录情感变化历史
            if "emotion_history" not in emotional_state:
                emotional_state["emotion_history"] = []
            
            # 添加新的情感记录
            emotion_record = {
                "chapter_number": chapter_number,
                "timestamp": datetime.now().isoformat(),
                "primary_emotion": emotional_changes.get("primary_emotion", "neutral"),
                "intensity": emotional_changes.get("intensity", 5),
                "triggers": emotional_changes.get("triggers", []),
                "description": emotional_changes.get("description", "")
            }
            
            emotional_state["emotion_history"].append(emotion_record)
            
            # 更新当前情感状态
            emotional_state["current_emotion"] = emotional_changes.get("primary_emotion", "neutral")
            emotional_state["current_intensity"] = emotional_changes.get("intensity", 5)
            emotional_state["last_updated"] = chapter_number
            
            # 分析情感趋势
            emotional_state["emotion_trend"] = self._analyze_emotion_trend(
                emotional_state["emotion_history"]
            )
            
            character_states["updated_at"] = datetime.now().isoformat()
            
            # 更新缓存和文件
            self.character_states_cache[novel_id] = character_states
            self._save_character_states(novel_id, character_states)
            
            return True
            
        except Exception as e:
            logger.error(f"更新情感状态失败: {e}")
            return False
    
    def update_ability_state(self, novel_id: str, chapter_number: int,
                           character_name: str, ability_changes: Dict[str, Any]) -> bool:
        """更新角色能力状态"""
        try:
            character_states = self.get_character_states(novel_id)
            
            if character_name not in character_states["character_states"]:
                character_states["character_states"][character_name] = {
                    "emotional_state": {},
                    "ability_state": {},
                    "psychological_state": {},
                    "social_state": {}
                }
            
            character_data = character_states["character_states"][character_name]
            
            # 更新能力状态
            if "ability_state" not in character_data:
                character_data["ability_state"] = {
                    "combat_level": 1,
                    "skills": {},
                    "growth_history": [],
                    "breakthroughs": []
                }
            
            # 确保必要的字段存在
            if "breakthroughs" not in character_data["ability_state"]:
                character_data["ability_state"]["breakthroughs"] = []
            if "growth_history" not in character_data["ability_state"]:
                character_data["ability_state"]["growth_history"] = []
            if "skills" not in character_data["ability_state"]:
                character_data["ability_state"]["skills"] = {}
            
            ability_state = character_data["ability_state"]
            
            # 更新战斗力等级
            if "combat_level" in ability_changes:
                old_level = ability_state.get("combat_level", 1)
                new_level = ability_changes["combat_level"]
                ability_state["combat_level"] = new_level
                
                if new_level > old_level:
                    ability_state["breakthroughs"].append({
                        "chapter_number": chapter_number,
                        "type": "combat_level",
                        "from": old_level,
                        "to": new_level,
                        "timestamp": datetime.now().isoformat()
                    })
            
            # 更新技能
            if "skills" in ability_changes:
                for skill_name, skill_level in ability_changes["skills"].items():
                    old_skill_level = ability_state["skills"].get(skill_name, 0)
                    ability_state["skills"][skill_name] = skill_level
                    
                    if skill_level > old_skill_level:
                        ability_state["breakthroughs"].append({
                            "chapter_number": chapter_number,
                            "type": "skill",
                            "skill_name": skill_name,
                            "from": old_skill_level,
                            "to": skill_level,
                            "timestamp": datetime.now().isoformat()
                        })
            
            # 记录成长历史
            growth_record = {
                "chapter_number": chapter_number,
                "timestamp": datetime.now().isoformat(),
                "changes": ability_changes,
                "description": ability_changes.get("description", "能力提升")
            }
            
            ability_state["growth_history"].append(growth_record)
            ability_state["last_updated"] = chapter_number
            
            # 分析成长趋势
            ability_state["growth_trend"] = self._analyze_growth_trend(
                ability_state["growth_history"]
            )
            
            character_states["updated_at"] = datetime.now().isoformat()
            
            # 更新缓存和文件
            self.character_states_cache[novel_id] = character_states
            self._save_character_states(novel_id, character_states)
            
            return True
            
        except Exception as e:
            logger.error(f"更新能力状态失败: {e}")
            return False
    
    def update_psychological_state(self, novel_id: str, chapter_number: int,
                                 character_name: str, psychological_changes: Dict[str, Any]) -> bool:
        """更新角色心理状态"""
        try:
            character_states = self.get_character_states(novel_id)
            
            if character_name not in character_states["character_states"]:
                character_states["character_states"][character_name] = {
                    "emotional_state": {},
                    "ability_state": {},
                    "psychological_state": {},
                    "social_state": {}
                }
            
            character_data = character_states["character_states"][character_name]
            
            # 更新心理状态
            if "psychological_state" not in character_data:
                character_data["psychological_state"] = {
                    "belief_strength": 50,
                    "trauma_level": 0,
                    "recovery_progress": 100,
                    "mental_stability": 50,
                    "core_beliefs": [],
                    "psychological_history": []
                }
            
            # 确保必要的字段存在
            if "psychological_history" not in character_data["psychological_state"]:
                character_data["psychological_state"]["psychological_history"] = []
            
            psychological_state = character_data["psychological_state"]
            
            # 更新心理指标
            for key in ["belief_strength", "trauma_level", "recovery_progress", "mental_stability"]:
                if key in psychological_changes:
                    psychological_state[key] = psychological_changes[key]
            
            # 更新核心信念
            if "core_beliefs" in psychological_changes:
                psychological_state["core_beliefs"] = psychological_changes["core_beliefs"]
            
            # 记录心理变化历史
            psychological_record = {
                "chapter_number": chapter_number,
                "timestamp": datetime.now().isoformat(),
                "changes": psychological_changes,
                "description": psychological_changes.get("description", "心理状态变化")
            }
            
            psychological_state["psychological_history"].append(psychological_record)
            psychological_state["last_updated"] = chapter_number
            
            character_states["updated_at"] = datetime.now().isoformat()
            
            # 更新缓存和文件
            self.character_states_cache[novel_id] = character_states
            self._save_character_states(novel_id, character_states)
            
            return True
            
        except Exception as e:
            logger.error(f"更新心理状态失败: {e}")
            return False
    
    def update_social_state(self, novel_id: str, chapter_number: int,
                          character_name: str, social_changes: Dict[str, Any]) -> bool:
        """更新角色社交状态"""
        try:
            character_states = self.get_character_states(novel_id)
            
            if character_name not in character_states["character_states"]:
                character_states["character_states"][character_name] = {
                    "emotional_state": {},
                    "ability_state": {},
                    "psychological_state": {},
                    "social_state": {}
                }
            
            character_data = character_states["character_states"][character_name]
            
            # 更新社交状态
            if "social_state" not in character_data:
                character_data["social_state"] = {
                    "reputation": 50,
                    "influence_level": 1,
                    "relationships": {},
                    "social_history": []
                }
            
            social_state = character_data["social_state"]
            
            # 更新社交指标
            for key in ["reputation", "influence_level"]:
                if key in social_changes:
                    social_state[key] = social_changes[key]
            
            # 更新关系网络
            if "relationships" in social_changes:
                for other_char, relationship_data in social_changes["relationships"].items():
                    social_state["relationships"][other_char] = relationship_data
            
            # 记录社交变化历史
            social_record = {
                "chapter_number": chapter_number,
                "timestamp": datetime.now().isoformat(),
                "changes": social_changes,
                "description": social_changes.get("description", "社交状态变化")
            }
            
            social_state["social_history"].append(social_record)
            social_state["last_updated"] = chapter_number
            
            character_states["updated_at"] = datetime.now().isoformat()
            
            # 更新缓存和文件
            self.character_states_cache[novel_id] = character_states
            self._save_character_states(novel_id, character_states)
            
            return True
            
        except Exception as e:
            logger.error(f"更新社交状态失败: {e}")
            return False
    
    def get_character_full_profile(self, novel_id: str, character_name: str, 
                                 chapter_number: int) -> Dict[str, Any]:
        """获取角色完整档案"""
        try:
            character_states = self.get_character_states(novel_id)
            
            if character_name not in character_states["character_states"]:
                return {}
            
            character_data = character_states["character_states"][character_name]
            
            # 构建完整档案
            full_profile = {
                "character_name": character_name,
                "current_chapter": chapter_number,
                "last_updated": character_data.get("last_updated", 1),
                "emotional_profile": self._get_current_emotional_state(
                    character_data.get("emotional_state", {}), chapter_number
                ),
                "ability_profile": self._get_current_ability_state(
                    character_data.get("ability_state", {}), chapter_number
                ),
                "psychological_profile": self._get_current_psychological_state(
                    character_data.get("psychological_state", {}), chapter_number
                ),
                "social_profile": self._get_current_social_state(
                    character_data.get("social_state", {}), chapter_number
                )
            }
            
            return full_profile
            
        except Exception as e:
            logger.error(f"获取角色完整档案失败: {e}")
            return {}
    
    def get_all_character_states(self, novel_id: str, chapter_number: int) -> Dict[str, Any]:
        """获取所有角色的当前状态"""
        try:
            character_states = self.get_character_states(novel_id)
            all_states = {}
            
            for character_name in character_states["character_states"]:
                all_states[character_name] = self.get_character_full_profile(
                    novel_id, character_name, chapter_number
                )
            
            return all_states
            
        except Exception as e:
            logger.error(f"获取所有角色状态失败: {e}")
            return {}
    
    def _analyze_emotion_trend(self, emotion_history: List[Dict]) -> str:
        """分析情感趋势"""
        if len(emotion_history) < 2:
            return "stable"
        
        recent_emotions = emotion_history[-3:]
        intensities = [e.get("intensity", 5) for e in recent_emotions]
        
        if len(intensities) >= 2:
            if intensities[-1] > intensities[-2]:
                return "intensifying"
            elif intensities[-1] < intensities[-2]:
                return "diminishing"
        
        return "stable"
    
    def _analyze_growth_trend(self, growth_history: List[Dict]) -> str:
        """分析成长趋势"""
        if len(growth_history) < 2:
            return "stable"
        
        recent_growth = growth_history[-3:]
        
        # 简单分析：如果最近有突破，认为是快速成长
        for growth in recent_growth:
            if "combat_level" in growth.get("changes", {}):
                return "rapid"
        
        return "steady"
    
    def _get_current_emotional_state(self, emotional_state: Dict, chapter_number: int) -> Dict[str, Any]:
        """获取当前情感状态"""
        return {
            "current_emotion": emotional_state.get("current_emotion", "neutral"),
            "current_intensity": emotional_state.get("current_intensity", 5),
            "emotion_trend": emotional_state.get("emotion_trend", "stable"),
            "last_updated": emotional_state.get("last_updated", 1),
            "recent_triggers": self._get_recent_triggers(emotional_state.get("emotion_history", []))
        }
    
    def _get_current_ability_state(self, ability_state: Dict, chapter_number: int) -> Dict[str, Any]:
        """获取当前能力状态"""
        return {
            "combat_level": ability_state.get("combat_level", 1),
            "skills": ability_state.get("skills", {}),
            "growth_trend": ability_state.get("growth_trend", "stable"),
            "recent_breakthroughs": ability_state.get("breakthroughs", [])[-3:],
            "last_updated": ability_state.get("last_updated", 1)
        }
    
    def _get_current_psychological_state(self, psychological_state: Dict, chapter_number: int) -> Dict[str, Any]:
        """获取当前心理状态"""
        return {
            "belief_strength": psychological_state.get("belief_strength", 50),
            "trauma_level": psychological_state.get("trauma_level", 0),
            "recovery_progress": psychological_state.get("recovery_progress", 100),
            "mental_stability": psychological_state.get("mental_stability", 50),
            "core_beliefs": psychological_state.get("core_beliefs", []),
            "last_updated": psychological_state.get("last_updated", 1)
        }
    
    def _get_current_social_state(self, social_state: Dict, chapter_number: int) -> Dict[str, Any]:
        """获取当前社交状态"""
        return {
            "reputation": social_state.get("reputation", 50),
            "influence_level": social_state.get("influence_level", 1),
            "key_relationships": social_state.get("relationships", {}),
            "last_updated": social_state.get("last_updated", 1)
        }
    
    def _get_recent_triggers(self, emotion_history: List[Dict]) -> List[str]:
        """获取最近的情感触发因素"""
        recent_triggers = []
        for emotion in emotion_history[-3:]:
            triggers = emotion.get("triggers", [])
            recent_triggers.extend(triggers)
        
        return list(set(recent_triggers))  # 去重
    
    def _save_character_states(self, novel_id: str, character_states: Dict[str, Any]) -> bool:
        """保存角色状态到文件"""
        try:
            if self.data_manager and hasattr(self.data_manager, 'novels_dir'):
                novel_dir = os.path.join(self.data_manager.novels_dir, novel_id)
                os.makedirs(novel_dir, exist_ok=True)
                
                file_path = os.path.join(novel_dir, self.states_file)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(character_states, f, ensure_ascii=False, indent=2)
            else:
                os.makedirs("character_states", exist_ok=True)
                file_path = os.path.join("character_states", f"{novel_id}_{self.states_file}")
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(character_states, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"保存角色状态失败: {e}")
            return False
    
    def _load_character_states(self, novel_id: str) -> Optional[Dict[str, Any]]:
        """从文件加载角色状态"""
        try:
            if self.data_manager:
                novel_dir = os.path.join(self.data_manager.novels_dir, novel_id)
                file_path = os.path.join(novel_dir, self.states_file)
            else:
                file_path = os.path.join("character_states", f"{novel_id}_{self.states_file}")
            
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            return None
            
        except Exception as e:
            logger.error(f"加载角色状态失败: {e}")
            return None
    
    def clear_cache(self, novel_id: str = None):
        """清理缓存"""
        if novel_id:
            self.character_states_cache.pop(novel_id, None)
        else:
            self.character_states_cache.clear()

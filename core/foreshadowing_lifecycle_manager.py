"""
[DEPRECATED] 伏笔生命周期管理器（旧流水线遗留）

⚠ 本模块属于 InkAI 旧版 workflow 的产物，已被新流水线完全取代：
   - 全局伏笔账本（plant→payoff）已由 OutlinePlanner 在 blueprint.json
     的 ledger 字段中统一管理；
   - 单卷伏笔覆盖率由 VolumeValidator 校验。
   - 新代码请勿 import 本模块；保留它仅为兼容历史 novel_dir 中残留的
     foreshadowing_lifecycle.json 文件不被误读。

详见：docs/development/data_files_catalog.md
"""
import warnings as _warnings
_warnings.warn(
    "core.foreshadowing_lifecycle_manager 已废弃；新流水线请使用 OutlinePlanner 的"
    "全局伏笔账本（blueprint.json::ledger）+ VolumeValidator。"
    "详见 docs/development/data_files_catalog.md",
    DeprecationWarning,
    stacklevel=2,
)

from typing import Dict, List, Any, Optional, Tuple
import json
import os
from datetime import datetime
from utils.logger import get_logger
logger = get_logger("foreshadowing_lifecycle_manager")


class ForeshadowingLifecycleManager:
    """伏笔生命周期管理器"""
    
    # 伏笔分层定义（按照用户标准）
    FORESHADOWING_LAYERS = {
        "short": {
            "name": "短伏笔",
            "max_chapters": 3,
            "description": "2-3章回收，维持单章/小阶段的爽感"
        },
        "medium": {
            "name": "中伏笔", 
            "max_chapters": 20,
            "description": "10-20章回收，推动阶段高潮"
        },
        "long": {
            "name": "长伏笔",
            "max_chapters": 999,
            "description": "全书回收，完成全书的闭环"
        }
    }
    
    def __init__(self, data_manager=None):
        self.data_manager = data_manager
        self.foreshadowing_cache = {}
        self.lifecycle_file = "foreshadowing_lifecycle.json"
        
        # 伏笔重要性等级
        self.importance_levels = {
            "S": {"name": "主线核心", "priority": 100, "max_delay": 10},
            "A": {"name": "重要支线", "priority": 80, "max_delay": 15},
            "B": {"name": "角色发展", "priority": 60, "max_delay": 20},
            "C": {"name": "氛围营造", "priority": 40, "max_delay": 30}
        }
        
        # 伏笔状态
        self.foreshadowing_statuses = [
            "planned",      # 计划中
            "planted",      # 已埋设
            "developing",   # 发展中
            "ready",        # 准备揭示
            "revealing",    # 揭示中
            "revealed",     # 已揭示
            "closed"        # 已结束
        ]
    
    def get_layer_by_chapters(self, chapters_until_reveal: int) -> str:
        """根据回收章节数确定伏笔层级"""
        if chapters_until_reveal <= self.FORESHADOWING_LAYERS["short"]["max_chapters"]:
            return "short"
        elif chapters_until_reveal <= self.FORESHADOWING_LAYERS["medium"]["max_chapters"]:
            return "medium"
        else:
            return "long"
    
    def get_foreshadowing_by_layer(self, novel_id: str, current_chapter: int) -> Dict[str, List]:
        """按层级获取伏笔"""
        foreshadowing_system = self.get_foreshadowing_system(novel_id)
        chains = foreshadowing_system.get("foreshadowing_chains", {})
        
        result = {
            "short": [],
            "medium": [],
            "long": []
        }
        
        for fs_id, fs_data in chains.items():
            # 只处理活跃的伏笔
            if fs_data.get("current_status") in ["planted", "developing", "ready"]:
                planted_chapter = fs_data.get("lifecycle", {}).get("planted", current_chapter)
                revelation_chapter = fs_data.get("lifecycle", {}).get("revelation")
                
                if revelation_chapter:
                    chapters_until_reveal = revelation_chapter - current_chapter
                    layer = self.get_layer_by_chapters(chapters_until_reveal)
                    result[layer].append({
                        "id": fs_id,
                        "content": fs_data.get("content", ""),
                        "chapters_until_reveal": chapters_until_reveal,
                        "status": fs_data.get("current_status")
                    })
        
        return result
    
    def initialize_foreshadowing_system(self, novel_id: str) -> Dict[str, Any]:
        """初始化伏笔系统"""
        try:
            foreshadowing_system = {
                "novel_id": novel_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "foreshadowing_chains": {},  # {foreshadowing_id: foreshadowing_data}
                "revelation_schedule": {},   # {chapter_number: [foreshadowing_ids]}
                "dependency_graph": {},      # {foreshadowing_id: [dependent_ids]}
                "conflict_matrix": {},       # {foreshadowing_id: [conflicting_ids]}
                "statistics": {
                    "total_foreshadowing": 0,
                    "active_foreshadowing": 0,
                    "revealed_foreshadowing": 0,
                    "overdue_foreshadowing": 0
                }
            }
            
            # 缓存数据
            self.foreshadowing_cache[novel_id] = foreshadowing_system
            
            # 保存到文件
            self._save_foreshadowing_system(novel_id, foreshadowing_system)
            
            return foreshadowing_system
            
        except Exception as e:
            logger.error(f"初始化伏笔系统失败: {e}")
            return {}
    
    def get_foreshadowing_system(self, novel_id: str) -> Dict[str, Any]:
        """获取伏笔系统"""
        # 先检查缓存
        if novel_id in self.foreshadowing_cache:
            return self.foreshadowing_cache[novel_id]
        
        # 从文件加载
        foreshadowing_system = self._load_foreshadowing_system(novel_id)
        if foreshadowing_system:
            self.foreshadowing_cache[novel_id] = foreshadowing_system
        else:
            foreshadowing_system = self.initialize_foreshadowing_system(novel_id)
        
        return foreshadowing_system
    
    def create_foreshadowing(self, novel_id: str, foreshadowing_data: Dict[str, Any]) -> str:
        """创建新伏笔"""
        try:
            foreshadowing_system = self.get_foreshadowing_system(novel_id)
            
            # 生成伏笔ID
            foreshadowing_id = f"foreshadow_{len(foreshadowing_system['foreshadowing_chains']) + 1:03d}"
            
            # 构建伏笔数据
            foreshadowing = {
                "id": foreshadowing_id,
                "title": foreshadowing_data.get("title", "未命名伏笔"),
                "content": foreshadowing_data.get("content", ""),
                "importance": foreshadowing_data.get("importance", "B"),
                "type": foreshadowing_data.get("type", "plot"),
                "lifecycle": {
                    "planted": foreshadowing_data.get("planted_chapter", None),
                    "development": foreshadowing_data.get("development_chapters", []),
                    "revelation": foreshadowing_data.get("revelation_chapter", None),
                    "aftermath": foreshadowing_data.get("aftermath_chapters", [])
                },
                "current_status": "planned",
                "dependencies": foreshadowing_data.get("dependencies", []),
                "related_characters": foreshadowing_data.get("related_characters", []),
                "revelation_methods": foreshadowing_data.get("revelation_methods", []),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # 添加到系统
            foreshadowing_system["foreshadowing_chains"][foreshadowing_id] = foreshadowing
            
            # 更新统计
            foreshadowing_system["statistics"]["total_foreshadowing"] += 1
            foreshadowing_system["statistics"]["active_foreshadowing"] += 1
            
            # 更新揭示计划
            revelation_chapter = foreshadowing["lifecycle"]["revelation"]
            if revelation_chapter:
                if revelation_chapter not in foreshadowing_system["revelation_schedule"]:
                    foreshadowing_system["revelation_schedule"][revelation_chapter] = []
                foreshadowing_system["revelation_schedule"][revelation_chapter].append(foreshadowing_id)
            
            foreshadowing_system["updated_at"] = datetime.now().isoformat()
            
            # 更新缓存和文件
            self.foreshadowing_cache[novel_id] = foreshadowing_system
            self._save_foreshadowing_system(novel_id, foreshadowing_system)
            
            return foreshadowing_id
            
        except Exception as e:
            logger.error(f"创建伏笔失败: {e}")
            return ""
    
    def update_foreshadowing_status(self, novel_id: str, foreshadowing_id: str, 
                                  new_status: str, chapter_number: int) -> bool:
        """更新伏笔状态"""
        try:
            foreshadowing_system = self.get_foreshadowing_system(novel_id)
            
            if foreshadowing_id not in foreshadowing_system["foreshadowing_chains"]:
                return False
            
            foreshadowing = foreshadowing_system["foreshadowing_chains"][foreshadowing_id]
            old_status = foreshadowing["current_status"]
            
            # 更新状态
            foreshadowing["current_status"] = new_status
            foreshadowing["updated_at"] = datetime.now().isoformat()
            
            # 记录状态变化历史
            if "status_history" not in foreshadowing:
                foreshadowing["status_history"] = []
            
            foreshadowing["status_history"].append({
                "chapter_number": chapter_number,
                "from_status": old_status,
                "to_status": new_status,
                "timestamp": datetime.now().isoformat()
            })
            
            # 更新统计
            if old_status in ["planned", "planted", "developing"] and new_status == "revealed":
                foreshadowing_system["statistics"]["active_foreshadowing"] -= 1
                foreshadowing_system["statistics"]["revealed_foreshadowing"] += 1
            
            foreshadowing_system["updated_at"] = datetime.now().isoformat()
            
            # 更新缓存和文件
            self.foreshadowing_cache[novel_id] = foreshadowing_system
            self._save_foreshadowing_system(novel_id, foreshadowing_system)
            
            return True
            
        except Exception as e:
            logger.error(f"更新伏笔状态失败: {e}")
            return False
    
    def check_revelation_urgency(self, novel_id: str, current_chapter: int) -> List[Dict[str, Any]]:
        """检查伏笔揭示紧急度"""
        try:
            foreshadowing_system = self.get_foreshadowing_system(novel_id)
            urgent_foreshadowing = []
            
            for foreshadowing_id, foreshadowing in foreshadowing_system["foreshadowing_chains"].items():
                if foreshadowing["current_status"] in ["planted", "developing"]:
                    revelation_chapter = foreshadowing["lifecycle"]["revelation"]
                    
                    if revelation_chapter:
                        chapters_left = revelation_chapter - current_chapter
                        importance = foreshadowing["importance"]
                        max_delay = self.importance_levels[importance]["max_delay"]
                        
                        # 计算紧急度
                        if chapters_left <= 2:
                            urgency = "critical"
                        elif chapters_left <= 5:
                            urgency = "high"
                        elif chapters_left <= max_delay // 2:
                            urgency = "medium"
                        else:
                            urgency = "low"
                        
                        if urgency in ["critical", "high"]:
                            urgent_foreshadowing.append({
                                "id": foreshadowing_id,
                                "title": foreshadowing["title"],
                                "content": foreshadowing["content"],
                                "importance": importance,
                                "urgency": urgency,
                                "chapters_left": chapters_left,
                                "revelation_methods": foreshadowing["revelation_methods"],
                                "related_characters": foreshadowing["related_characters"]
                            })
            
            # 按紧急度和重要性排序
            urgent_foreshadowing.sort(key=lambda x: (
                x["urgency"] == "critical",
                x["urgency"] == "high", 
                self.importance_levels[x["importance"]]["priority"]
            ), reverse=True)
            
            return urgent_foreshadowing
            
        except Exception as e:
            logger.error(f"检查伏笔紧急度失败: {e}")
            return []
    
    def get_active_foreshadowing(self, novel_id: str, current_chapter: int) -> List[Dict[str, Any]]:
        """获取当前活跃的伏笔"""
        try:
            foreshadowing_system = self.get_foreshadowing_system(novel_id)
            active_foreshadowing = []
            
            for foreshadowing_id, foreshadowing in foreshadowing_system["foreshadowing_chains"].items():
                if foreshadowing["current_status"] in ["planted", "developing"]:
                    planted_chapter = foreshadowing["lifecycle"]["planted"]
                    
                    # 只返回已经埋设且在当前章节之前的伏笔
                    if planted_chapter and planted_chapter <= current_chapter:
                        active_foreshadowing.append({
                            "id": foreshadowing_id,
                            "title": foreshadowing["title"],
                            "content": foreshadowing["content"],
                            "importance": foreshadowing["importance"],
                            "chapters_ago": current_chapter - planted_chapter,
                            "status": foreshadowing["current_status"]
                        })
            
            # 按重要性和埋设时间排序
            active_foreshadowing.sort(key=lambda x: (
                self.importance_levels[x["importance"]]["priority"],
                -x["chapters_ago"]
            ), reverse=True)
            
            return active_foreshadowing
            
        except Exception as e:
            logger.error(f"获取活跃伏笔失败: {e}")
            return []
    
    def detect_new_foreshadowing(self, chapter_content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检测章节中的新伏笔"""
        try:
            new_foreshadowing = []
            
            # 从章节内容中提取伏笔
            foreshadowing_list = chapter_content.get("foreshadowing", [])
            if not foreshadowing_list:
                foreshadowing_list = chapter_content.get("new_foreshadowing", [])
            
            for foreshadow_content in foreshadowing_list:
                if isinstance(foreshadow_content, str) and foreshadow_content.strip():
                    new_foreshadowing.append({
                        "content": foreshadow_content,
                        "type": "auto_detected",
                        "importance": self._estimate_importance(foreshadow_content),
                        "suggested_revelation": self._suggest_revelation_timing(foreshadow_content)
                    })
            
            return new_foreshadowing
            
        except Exception as e:
            logger.error(f"检测新伏笔失败: {e}")
            return []
    
    def update_foreshadowing_lifecycle(self, novel_id: str, chapter_number: int, 
                                     chapter_content: Dict[str, Any]) -> bool:
        """更新伏笔生命周期"""
        try:
            foreshadowing_system = self.get_foreshadowing_system(novel_id)
            
            # 1. 检测新伏笔
            new_foreshadowing = self.detect_new_foreshadowing(chapter_content)
            for new_foreshadow in new_foreshadowing:
                # 自动创建伏笔记录
                self.create_foreshadowing(novel_id, {
                    "title": f"第{chapter_number}章伏笔",
                    "content": new_foreshadow["content"],
                    "importance": new_foreshadow["importance"],
                    "type": new_foreshadow["type"],
                    "planted_chapter": chapter_number,
                    "revelation_chapter": chapter_number + new_foreshadow["suggested_revelation"]
                })
            
            # 2. 检查已揭示的伏笔
            revealed_foreshadowing = self._detect_revealed_foreshadowing(
                chapter_content, foreshadowing_system, chapter_number
            )
            
            for foreshadowing_id in revealed_foreshadowing:
                self.update_foreshadowing_status(novel_id, foreshadowing_id, "revealed", chapter_number)
            
            # 3. 更新发展中的伏笔
            self._update_developing_foreshadowing(foreshadowing_system, chapter_number)
            
            return True
            
        except Exception as e:
            logger.error(f"更新伏笔生命周期失败: {e}")
            return False
    
    def get_revelation_suggestions(self, novel_id: str, current_chapter: int) -> List[Dict[str, Any]]:
        """获取伏笔揭示建议"""
        try:
            urgent_foreshadowing = self.check_revelation_urgency(novel_id, current_chapter)
            suggestions = []
            
            for foreshadow in urgent_foreshadowing:
                if foreshadow["urgency"] in ["critical", "high"]:
                    suggestion = {
                        "foreshadowing_id": foreshadow["id"],
                        "title": foreshadow["title"],
                        "urgency": foreshadow["urgency"],
                        "chapters_left": foreshadow["chapters_left"],
                        "suggested_methods": foreshadow["revelation_methods"],
                        "timing_advice": self._get_timing_advice(foreshadow),
                        "integration_tips": self._get_integration_tips(foreshadow)
                    }
                    suggestions.append(suggestion)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"获取揭示建议失败: {e}")
            return []
    
    def validate_foreshadowing_consistency(self, novel_id: str, 
                                         new_foreshadowing: Dict[str, Any]) -> Dict[str, Any]:
        """验证伏笔一致性"""
        try:
            foreshadowing_system = self.get_foreshadowing_system(novel_id)
            
            conflicts = []
            dependencies = []
            suggestions = []
            
            # 检查与现有伏笔的冲突
            for existing_id, existing_foreshadow in foreshadowing_system["foreshadowing_chains"].items():
                # 内容相似性检查
                if self._check_content_similarity(
                    new_foreshadowing.get("content", ""), 
                    existing_foreshadow["content"]
                ) > 0.8:
                    conflicts.append({
                        "type": "content_similarity",
                        "existing_id": existing_id,
                        "description": f"与现有伏笔'{existing_foreshadow['title']}'内容过于相似"
                    })
                
                # 时间冲突检查
                new_revelation = new_foreshadowing.get("revelation_chapter")
                existing_revelation = existing_foreshadow["lifecycle"]["revelation"]
                
                if (new_revelation and existing_revelation and 
                    abs(new_revelation - existing_revelation) <= 2 and
                    existing_foreshadow["importance"] == new_foreshadowing.get("importance")):
                    conflicts.append({
                        "type": "timing_conflict",
                        "existing_id": existing_id,
                        "description": f"与伏笔'{existing_foreshadow['title']}'揭示时间过于接近"
                    })
            
            # 生成建议
            if conflicts:
                suggestions.append("建议调整伏笔内容或揭示时机以避免冲突")
            
            if not conflicts:
                suggestions.append("伏笔一致性检查通过，可以安全添加")
            
            return {
                "is_valid": len(conflicts) == 0,
                "conflicts": conflicts,
                "dependencies": dependencies,
                "suggestions": suggestions
            }
            
        except Exception as e:
            logger.error(f"验证伏笔一致性失败: {e}")
            return {"is_valid": False, "error": str(e)}
    
    def _estimate_importance(self, foreshadow_content: str) -> str:
        """估计伏笔重要性"""
        # 简单的重要性估计
        high_importance_keywords = ["系统", "真相", "身份", "秘密", "命运", "使命"]
        medium_importance_keywords = ["力量", "能力", "关系", "过去", "未来"]
        
        content_lower = foreshadow_content.lower()
        
        if any(keyword in content_lower for keyword in high_importance_keywords):
            return "A"
        elif any(keyword in content_lower for keyword in medium_importance_keywords):
            return "B"
        else:
            return "C"
    
    def _suggest_revelation_timing(self, foreshadow_content: str) -> int:
        """建议伏笔揭示时机（相对章节数）"""
        # 根据重要性建议揭示时机
        importance = self._estimate_importance(foreshadow_content)
        
        if importance == "A":
            return 15  # 15章后揭示
        elif importance == "B":
            return 10  # 10章后揭示
        else:
            return 5   # 5章后揭示
    
    def _detect_revealed_foreshadowing(self, chapter_content: Dict[str, Any], 
                                     foreshadowing_system: Dict[str, Any], 
                                     chapter_number: int) -> List[str]:
        """检测已揭示的伏笔"""
        revealed_ids = []
        
        try:
            # 从章节内容中查找可能的揭示
            content = chapter_content.get("content", "")
            revealed_list = chapter_content.get("revealed_foreshadowing", [])
            
            # 检查明确标记的揭示
            for revealed_content in revealed_list:
                for foreshadowing_id, foreshadowing in foreshadowing_system["foreshadowing_chains"].items():
                    if (foreshadowing["current_status"] in ["planted", "developing"] and
                        self._check_content_similarity(revealed_content, foreshadowing["content"]) > 0.6):
                        revealed_ids.append(foreshadowing_id)
            
            # 检查计划中的揭示
            scheduled_revelations = foreshadowing_system["revelation_schedule"].get(str(chapter_number), [])
            for foreshadowing_id in scheduled_revelations:
                if foreshadowing_id in foreshadowing_system["foreshadowing_chains"]:
                    foreshadowing = foreshadowing_system["foreshadowing_chains"][foreshadowing_id]
                    if foreshadowing["current_status"] in ["planted", "developing"]:
                        revealed_ids.append(foreshadowing_id)
            
            return list(set(revealed_ids))  # 去重
            
        except Exception as e:
            logger.error(f"检测已揭示伏笔失败: {e}")
            return []
    
    def _update_developing_foreshadowing(self, foreshadowing_system: Dict[str, Any], 
                                       chapter_number: int):
        """更新发展中的伏笔"""
        for foreshadowing_id, foreshadowing in foreshadowing_system["foreshadowing_chains"].items():
            if foreshadowing["current_status"] == "planted":
                development_chapters = foreshadowing["lifecycle"]["development"]
                if development_chapters and chapter_number in development_chapters:
                    foreshadowing["current_status"] = "developing"
                    foreshadowing["updated_at"] = datetime.now().isoformat()
    
    def _check_content_similarity(self, content1: str, content2: str) -> float:
        """检查内容相似度"""
        if not content1 or not content2:
            return 0.0
        
        # 简单的相似度计算
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _get_timing_advice(self, foreshadow: Dict[str, Any]) -> str:
        """获取时机建议"""
        urgency = foreshadow["urgency"]
        chapters_left = foreshadow["chapters_left"]
        
        if urgency == "critical":
            return f"必须在{chapters_left}章内揭示，建议在本章或下章处理"
        elif urgency == "high":
            return f"建议在{chapters_left}章内揭示，可在高潮或转折点处理"
        else:
            return f"还有{chapters_left}章时间，可适当发展后再揭示"
    
    def _get_integration_tips(self, foreshadow: Dict[str, Any]) -> List[str]:
        """获取整合建议"""
        tips = []
        
        # 根据重要性给出建议
        importance = foreshadow["importance"]
        if importance == "S":
            tips.append("作为章节核心内容处理")
            tips.append("确保有足够的情感铺垫")
        elif importance == "A":
            tips.append("作为重要情节点处理")
            tips.append("可与角色发展结合")
        else:
            tips.append("可作为背景信息自然融入")
        
        # 根据相关角色给出建议
        related_chars = foreshadow.get("related_characters", [])
        if related_chars:
            tips.append(f"重点刻画{', '.join(related_chars)}的反应")
        
        return tips
    
    def _save_foreshadowing_system(self, novel_id: str, foreshadowing_system: Dict[str, Any]) -> bool:
        """保存伏笔系统到文件"""
        try:
            if self.data_manager and hasattr(self.data_manager, 'novels_dir'):
                novel_dir = os.path.join(self.data_manager.novels_dir, novel_id)
                os.makedirs(novel_dir, exist_ok=True)
                
                file_path = os.path.join(novel_dir, self.lifecycle_file)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(foreshadowing_system, f, ensure_ascii=False, indent=2)
            else:
                os.makedirs("foreshadowing_systems", exist_ok=True)
                file_path = os.path.join("foreshadowing_systems", f"{novel_id}_{self.lifecycle_file}")
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(foreshadowing_system, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"保存伏笔系统失败: {e}")
            return False
    
    def _load_foreshadowing_system(self, novel_id: str) -> Optional[Dict[str, Any]]:
        """从文件加载伏笔系统"""
        try:
            if self.data_manager:
                novel_dir = os.path.join(self.data_manager.novels_dir, novel_id)
                file_path = os.path.join(novel_dir, self.lifecycle_file)
            else:
                file_path = os.path.join("foreshadowing_systems", f"{novel_id}_{self.lifecycle_file}")
            
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            return None
            
        except Exception as e:
            logger.error(f"加载伏笔系统失败: {e}")
            return None
    
    def get_system_statistics(self, novel_id: str) -> Dict[str, Any]:
        """获取伏笔系统统计信息"""
        try:
            foreshadowing_system = self.get_foreshadowing_system(novel_id)
            return foreshadowing_system.get("statistics", {})
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}

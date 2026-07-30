"""
整合知识系统
统一管理所有知识库模块，确保它们在续写流程中被正确使用
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Any, Optional
from data_manager import DataManager
from utils.logger import get_logger

logger = get_logger("integrated_knowledge")


class IntegratedKnowledgeSystem:
    """整合知识系统 - 统一管理所有知识库模块"""
    
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
        self.knowledge_graph = None  # 延迟初始化，需要novel_id
        
        # 初始化其他知识库模块
        self._init_modules()
        
    def _init_modules(self):
        """初始化所有知识库模块"""
        # 知识图谱需要novel_id，延迟初始化
        self.knowledge_graph = None
        
        try:
            # 2. 双层故事线管理
            from core.dual_layer_storyline_manager import DualLayerStorylineManager
            self.storyline_manager = DualLayerStorylineManager(self.data_manager)
            logger.info("[OK] 双层故事线管理已初始化")
        except Exception as e:
            logger.error(f"[FAIL] 双层故事线管理初始化失败: {e}")
            self.storyline_manager = None
        
        try:
            # 3. 伏笔生命周期管理
            from core.foreshadowing_lifecycle_manager import ForeshadowingLifecycleManager
            self.foreshadowing_manager = ForeshadowingLifecycleManager(self.data_manager)
            logger.info("[OK] 伏笔生命周期管理已初始化")
        except Exception as e:
            logger.error(f"[FAIL] 伏笔生命周期管理初始化失败: {e}")
            self.foreshadowing_manager = None
        
        try:
            # 4. 角色状态追踪
            from core.enhanced_character_tracker import EnhancedCharacterTracker
            self.character_tracker = EnhancedCharacterTracker(self.data_manager)
            logger.info("[OK] 角色状态追踪已初始化")
        except Exception as e:
            logger.error(f"[FAIL] 角色状态追踪初始化失败: {e}")
            self.character_tracker = None
    
    def update_knowledge_after_chapter(self, novel_id: str, chapter_number: int, 
                                      chapter_content: Dict[str, Any]) -> bool:
        """
        在章节完成后更新所有知识库
        
        Args:
            novel_id: 小说ID
            chapter_number: 章节号
            chapter_content: 章节内容
        
        Returns:
            bool: 是否成功更新
        """
        success = True
        
        # 1. 延迟初始化并更新动态知识图谱
        if self.knowledge_graph is None:
            try:
                from core.dynamic_knowledge_graph import DynamicKnowledgeGraph
                self.knowledge_graph = DynamicKnowledgeGraph(novel_id, self.data_manager)
                logger.info(f"[OK] 动态知识图谱已初始化 (小说: {novel_id})")
            except Exception as e:
                logger.error(f"[FAIL] 动态知识图谱初始化失败: {e}")
        
        if self.knowledge_graph:
            try:
                self.knowledge_graph.update_from_chapter(chapter_number, chapter_content)
                logger.info(f"[OK] 动态知识图谱已更新 (章节{chapter_number})")
            except Exception as e:
                logger.error(f"[FAIL] 动态知识图谱更新失败: {e}")
                success = False
        
        # 2. 更新双层故事线进度
        if self.storyline_manager:
            try:
                self.storyline_manager.update_progress(novel_id, chapter_number, chapter_content)
                logger.info(f"[OK] 双层故事线进度已更新 (章节{chapter_number})")
            except Exception as e:
                logger.error(f"[FAIL] 双层故事线更新失败: {e}")
                success = False
        
        # 3. 更新伏笔生命周期
        if self.foreshadowing_manager:
            try:
                # 检测新伏笔
                new_foreshadowing = self.foreshadowing_manager.detect_new_foreshadowing(chapter_content)
                if new_foreshadowing:
                    logger.info(f"[OK] 检测到 {len(new_foreshadowing)} 个新伏笔")
                
                # 更新伏笔状态
                self.foreshadowing_manager.update_foreshadowing_lifecycle(
                    novel_id, chapter_number, chapter_content
                )
                logger.info(f"[OK] 伏笔生命周期已更新 (章节{chapter_number})")
            except Exception as e:
                logger.error(f"[FAIL] 伏笔更新失败: {e}")
                success = False
        
        # 4. 更新角色状态
        if self.character_tracker:
            try:
                # 从章节内容中提取角色状态变化
                character_states = self._extract_character_states(chapter_content)
                for char_name, states in character_states.items():
                    if 'emotional' in states:
                        self.character_tracker.update_emotional_state(
                            novel_id, chapter_number, char_name, states['emotional']
                        )
                    if 'ability' in states:
                        self.character_tracker.update_ability_state(
                            novel_id, chapter_number, char_name, states['ability']
                        )
                logger.info(f"[OK] 角色状态已更新 (章节{chapter_number})")
            except Exception as e:
                logger.error(f"[FAIL] 角色状态更新失败: {e}")
                success = False
        
        return success
    
    def get_context_for_next_chapter(self, novel_id: str, chapter_number: int) -> Dict[str, Any]:
        """
        获取下一章的上下文信息
        
        Args:
            novel_id: 小说ID
            chapter_number: 下一章章节号
        
        Returns:
            Dict: 包含所有知识库信息的上下文
        """
        context = {
            "chapter_number": chapter_number,
            "knowledge_graph": None,
            "storyline_constraints": None,
            "active_foreshadowing": [],
            "character_states": {},
            "revelation_suggestions": []
        }
        
        # 1. 从知识图谱获取上下文
        if self.knowledge_graph:
            try:
                context["knowledge_graph"] = self.knowledge_graph.get_context_for_generation(chapter_number)
            except Exception as e:
                logger.error(f"获取知识图谱上下文失败: {e}")
        
        # 2. 获取故事线约束
        if self.storyline_manager:
            try:
                context["storyline_constraints"] = self.storyline_manager.get_constraints_for_chapter(chapter_number)
                context["current_phase"] = self.storyline_manager.get_current_phase(chapter_number)
            except Exception as e:
                logger.error(f"获取故事线约束失败: {e}")
        
        # 3. 获取活跃伏笔
        if self.foreshadowing_manager:
            try:
                context["active_foreshadowing"] = self.foreshadowing_manager.get_active_foreshadowing(
                    novel_id, chapter_number
                )
                context["revelation_suggestions"] = self.foreshadowing_manager.get_revelation_suggestions(
                    novel_id, chapter_number
                )
            except Exception as e:
                logger.error(f"获取伏笔信息失败: {e}")
        
        # 4. 获取角色状态
        if self.character_tracker:
            try:
                context["character_states"] = self.character_tracker.get_all_character_states(
                    novel_id, chapter_number
                )
            except Exception as e:
                logger.error(f"获取角色状态失败: {e}")
        
        return context
    
    def _extract_character_states(self, chapter_content: Dict[str, Any]) -> Dict[str, Dict]:
        """从章节内容中提取角色状态变化"""
        # 这里可以使用NLP或规则提取角色状态
        # 暂时返回空字典，后续可以实现
        return {}
    
    def get_storyline_progress(self, novel_id: str) -> Dict[str, Any]:
        """获取故事线进度"""
        if self.storyline_manager:
            try:
                return self.storyline_manager.get_progress(novel_id)
            except Exception as e:
                logger.error(f"获取故事线进度失败: {e}")
        return {}
    
    def get_foreshadowing_report(self, novel_id: str, current_chapter: int) -> Dict[str, Any]:
        """获取伏笔报告"""
        if self.foreshadowing_manager:
            try:
                active = self.foreshadowing_manager.get_active_foreshadowing(novel_id, current_chapter)
                suggestions = self.foreshadowing_manager.get_revelation_suggestions(novel_id, current_chapter)
                return {
                    "active_foreshadowing": active,
                    "revelation_suggestions": suggestions,
                    "total_active": len(active),
                    "urgent_count": len([f for f in active if f.get("urgency") == "high"])
                }
            except Exception as e:
                logger.error(f"获取伏笔报告失败: {e}")
        return {}

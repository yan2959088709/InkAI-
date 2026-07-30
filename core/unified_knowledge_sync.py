"""
统一知识同步器
同步动态知识库和动态知识图谱，确保数据一致

核心功能：
1. 同步角色信息
2. 同步情节进展
3. 同步伏笔状态
4. 提供统一查询接口
"""

from typing import Dict, List, Any, Optional
from utils.logger import get_logger

logger = get_logger("unified_knowledge_sync")


class UnifiedKnowledgeSync:
    """统一知识同步器"""
    
    def __init__(self, data_manager=None, 
                 dynamic_knowledge_manager=None,
                 dynamic_knowledge_graph=None):
        self.data_manager = data_manager
        self.dynamic_knowledge_manager = dynamic_knowledge_manager
        self.dynamic_knowledge_graph = dynamic_knowledge_graph
        
        # 统一知识缓存
        self.unified_cache = {
            "characters": {},
            "plot_progress": {},
            "foreshadowing": {},
            "world_state": {}
        }
    
    def sync_after_chapter(self, novel_id: str, chapter_number: int,
                          chapter_content: Dict[str, Any]) -> bool:
        """
        每章完成后同步知识
        
        Args:
            novel_id: 小说ID
            chapter_number: 章节号
            chapter_content: 章节内容
        
        Returns:
            是否同步成功
        """
        try:
            logger.info(f"开始同步第{chapter_number}章知识...")
            
            # 1. 提取章节信息
            info = self._extract_chapter_info(chapter_content)
            
            # 2. 同步角色信息
            self._sync_characters(novel_id, chapter_number, info)
            
            # 3. 同步情节进展
            self._sync_plot(novel_id, chapter_number, info)
            
            # 4. 同步伏笔状态
            self._sync_foreshadowing(novel_id, chapter_number, info)
            
            # 5. 更新统一缓存
            self._update_unified_cache(novel_id, chapter_number, info)
            
            logger.info(f"第{chapter_number}章知识同步完成")
            return True
            
        except Exception as e:
            logger.error(f"同步第{chapter_number}章知识失败: {e}")
            return False
    
    def _extract_chapter_info(self, chapter_content: Dict[str, Any]) -> Dict[str, Any]:
        """从章节内容中提取信息"""
        content = chapter_content.get("content", "")
        
        return {
            "content": content,
            "title": chapter_content.get("title", ""),
            "summary": chapter_content.get("summary", ""),
            "key_events": chapter_content.get("key_events", []),
            "character_development": chapter_content.get("character_development", ""),
            "foreshadowing": chapter_content.get("foreshadowing", []),
            "next_chapter_hint": chapter_content.get("next_chapter_hint", "")
        }
    
    def _sync_characters(self, novel_id: str, chapter_number: int,
                        info: Dict[str, Any]):
        """同步角色信息"""
        try:
            # 更新统一缓存中的角色信息
            character_dev = info.get("character_development", "")
            if character_dev:
                self.unified_cache["characters"][chapter_number] = {
                    "development": character_dev,
                    "chapter": chapter_number
                }
            
            # 如果有动态知识图谱，添加角色节点
            if self.dynamic_knowledge_graph:
                # TODO: 添加角色节点和关系
                pass
                
        except Exception as e:
            logger.error(f"同步角色信息失败: {e}")
    
    def _sync_plot(self, novel_id: str, chapter_number: int,
                  info: Dict[str, Any]):
        """同步情节进展"""
        try:
            key_events = info.get("key_events", [])
            
            # 更新统一缓存
            self.unified_cache["plot_progress"][chapter_number] = {
                "key_events": key_events,
                "chapter": chapter_number
            }
            
            # 如果有动态知识图谱，添加事件节点
            if self.dynamic_knowledge_graph:
                for event in key_events:
                    if isinstance(event, str):
                        # TODO: 添加事件节点
                        pass
                        
        except Exception as e:
            logger.error(f"同步情节进展失败: {e}")
    
    def _sync_foreshadowing(self, novel_id: str, chapter_number: int,
                           info: Dict[str, Any]):
        """同步伏笔状态"""
        try:
            foreshadowing = info.get("foreshadowing", [])
            
            # 更新统一缓存
            for fs in foreshadowing:
                if isinstance(fs, str):
                    self.unified_cache["foreshadowing"][fs] = {
                        "planted_chapter": chapter_number,
                        "status": "active",
                        "content": fs
                    }
                    
        except Exception as e:
            logger.error(f"同步伏笔状态失败: {e}")
    
    def _update_unified_cache(self, novel_id: str, chapter_number: int,
                             info: Dict[str, Any]):
        """更新统一缓存"""
        # 保存缓存到文件
        try:
            if self.data_manager:
                cache_data = {
                    "novel_id": novel_id,
                    "last_chapter": chapter_number,
                    "unified_cache": self.unified_cache,
                    "updated_at": str(datetime.now())
                }
                
                # TODO: 保存到文件
                
        except Exception as e:
            logger.error(f"更新统一缓存失败: {e}")
    
    def get_unified_context(self, novel_id: str, chapter_number: int) -> Dict[str, Any]:
        """
        获取统一的知识上下文
        
        用于续写时提供完整的历史信息
        """
        context = {
            "chapter_number": chapter_number,
            "characters": {},
            "plot_progress": {},
            "active_foreshadowing": [],
            "recent_events": []
        }
        
        try:
            # 1. 获取角色信息
            context["characters"] = self._get_character_context(novel_id, chapter_number)
            
            # 2. 获取情节进度
            context["plot_progress"] = self._get_plot_context(novel_id, chapter_number)
            
            # 3. 获取活跃伏笔
            context["active_foreshadowing"] = self._get_active_foreshadowing(chapter_number)
            
            # 4. 获取最近事件
            context["recent_events"] = self._get_recent_events(chapter_number)
            
            return context
            
        except Exception as e:
            logger.error(f"获取统一上下文失败: {e}")
            return context
    
    def _get_character_context(self, novel_id: str, chapter_number: int) -> Dict:
        """获取角色上下文"""
        characters = {}
        
        # 从统一缓存获取
        for ch_num, char_info in self.unified_cache["characters"].items():
            if ch_num <= chapter_number:
                characters[ch_num] = char_info
        
        return characters
    
    def _get_plot_context(self, novel_id: str, chapter_number: int) -> Dict:
        """获取情节上下文"""
        plot = {}
        
        # 获取最近10章的情节
        for ch_num, plot_info in self.unified_cache["plot_progress"].items():
            if chapter_number - 10 <= ch_num <= chapter_number:
                plot[ch_num] = plot_info
        
        return plot
    
    def _get_active_foreshadowing(self, chapter_number: int) -> List[Dict]:
        """获取活跃伏笔"""
        active = []
        
        for fs_content, fs_info in self.unified_cache["foreshadowing"].items():
            if fs_info["status"] == "active":
                planted = fs_info["planted_chapter"]
                # 检查是否应该回收
                if chapter_number - planted <= 3:  # 短伏笔
                    fs_info["status"] = "should_recycle"
                active.append(fs_info)
        
        return active
    
    def _get_recent_events(self, chapter_number: int) -> List[str]:
        """获取最近事件"""
        events = []
        
        # 获取最近5章的事件
        for ch_num in range(max(1, chapter_number - 5), chapter_number + 1):
            if ch_num in self.unified_cache["plot_progress"]:
                chapter_events = self.unified_cache["plot_progress"][ch_num].get("key_events", [])
                events.extend(chapter_events)
        
        return events[-10:]  # 最多返回10个事件
    
    def validate_consistency(self, novel_id: str, chapter_number: int) -> Dict[str, Any]:
        """
        验证知识一致性
        
        检查动态知识库和动态知识图谱是否同步
        """
        result = {
            "is_consistent": True,
            "issues": []
        }
        
        try:
            # TODO: 实现一致性检查
            pass
            
        except Exception as e:
            logger.error(f"验证一致性失败: {e}")
            result["is_consistent"] = False
            result["issues"].append(str(e))
        
        return result


def sync_knowledge_after_chapter(novel_id: str, chapter_number: int,
                                chapter_content: Dict[str, Any],
                                data_manager=None) -> bool:
    """同步知识的便捷函数"""
    sync = UnifiedKnowledgeSync(data_manager)
    return sync.sync_after_chapter(novel_id, chapter_number, chapter_content)

"""
上下文切片优化器
只传本章相关的伏笔+人物+事件，避免LLM遗忘

解决专家提出的问题：
- 千章后知识体量巨大
- 需要只抽本章相关的伏笔+人物+事件
"""

from typing import Dict, List, Any, Optional
from utils.logger import get_logger

logger = get_logger("context_slicer")


class ContextSlicer:
    """上下文切片器"""
    
    def __init__(self, max_context_tokens: int = 4000):
        """
        初始化切片器
        
        Args:
            max_context_tokens: 最大上下文token数（约4k/8k）
        """
        self.max_context_tokens = max_context_tokens
    
    def slice_context(self, novel_id: str, chapter_number: int,
                     full_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        切片上下文，只保留本章相关的信息
        
        Args:
            novel_id: 小说ID
            chapter_number: 当前章节号
            full_context: 完整上下文
        
        Returns:
            切片后的上下文
        """
        sliced = {
            "chapter_number": chapter_number,
            "novel_info": full_context.get("novel_info", {}),
            "world_setting": full_context.get("world_setting", ""),
            "story_tone": full_context.get("story_tone", "")
        }
        
        # 1. 切片上一章结尾（2500字）
        sliced["last_chapter_ending"] = self._slice_last_chapter_ending(
            full_context.get("last_chapter_summary", {})
        )
        
        # 2. 切片前3章摘要
        sliced["previous_summaries"] = self._slice_previous_summaries(
            full_context.get("previous_summaries", [])
        )
        
        # 3. 切片卷摘要（仅在新卷开始时）
        sliced["volume_summary"] = self._slice_volume_summary(
            full_context.get("volume_summary")
        )
        
        # 4. 切片相关伏笔（本章应该回收的）
        sliced["relevant_foreshadowing"] = self._slice_relevant_foreshadowing(
            full_context.get("chapters", []),
            chapter_number
        )
        
        # 5. 切片人物信息（只保留活跃角色）
        sliced["active_characters"] = self._slice_active_characters(
            full_context.get("character_profiles", {}),
            full_context.get("chapters", [])
        )
        
        # 6. 切片最近事件（最近5章的关键事件）
        sliced["recent_events"] = self._slice_recent_events(
            full_context.get("chapters", []),
            chapter_number
        )
        
        return sliced
    
    def _slice_last_chapter_ending(self, last_chapter: Dict) -> str:
        """切片上一章结尾"""
        content = last_chapter.get("content_ending", "")
        # 已经是2500字，直接返回
        return content[-2500:] if content else ""
    
    def _slice_previous_summaries(self, summaries: List[Dict]) -> List[Dict]:
        """切片前3章摘要"""
        # 只保留最近3章
        return summaries[-3:] if summaries else []
    
    def _slice_volume_summary(self, volume_summary: Optional[Dict]) -> Optional[Dict]:
        """切片卷摘要"""
        # 如果有卷摘要，保留关键信息
        if not volume_summary:
            return None
        
        return {
            "volume_number": volume_summary.get("volume_number"),
            "key_events": volume_summary.get("key_events", [])[:5],  # 只保留前5个事件
            "character_developments": volume_summary.get("character_developments", [])[:3]
        }
    
    def _slice_relevant_foreshadowing(self, chapters: List[Dict], 
                                     current_chapter: int) -> List[Dict]:
        """
        切片相关伏笔
        
        只保留：
        1. 短伏笔（3章内应该回收的）
        2. 中伏笔（20章内应该回收的）
        3. 本章应该回收的
        """
        relevant = []
        
        for ch in chapters:
            chapter_num = ch.get("chapter_number", 0)
            foreshadowing = ch.get("foreshadowing", [])
            
            for fs in foreshadowing:
                if isinstance(fs, str):
                    age = current_chapter - chapter_num
                    
                    # 短伏笔（3章内）
                    if 0 < age <= 3:
                        relevant.append({
                            "content": fs,
                            "planted_chapter": chapter_num,
                            "age": age,
                            "type": "short",
                            "should_recycle": age >= 2  # 快到回收点了
                        })
                    # 中伏笔（接近回收点）
                    elif 15 <= age <= 20:
                        relevant.append({
                            "content": fs,
                            "planted_chapter": chapter_num,
                            "age": age,
                            "type": "medium",
                            "should_recycle": age >= 18
                        })
        
        # 按should_recycle排序，优先回收
        relevant.sort(key=lambda x: (x["should_recycle"], x["age"]), reverse=True)
        
        return relevant[:5]  # 最多保留5个相关伏笔
    
    def _slice_active_characters(self, character_profiles: Dict,
                                chapters: List[Dict]) -> Dict:
        """切片活跃角色（最近出现过的角色）"""
        # 获取最近5章中出现的角色
        recent_chapters = chapters[-5:] if len(chapters) >= 5 else chapters
        
        active_names = set()
        for ch in recent_chapters:
            content = ch.get("content", "")
            # 简单检查：如果角色名字在内容中出现
            main_char = character_profiles.get("main_character", {})
            main_name = main_char.get("basic_info", {}).get("name", "")
            if main_name and main_name in content:
                active_names.add(main_name)
            
            for char in character_profiles.get("supporting_characters", []):
                char_name = char.get("basic_info", {}).get("name", "")
                if char_name and char_name in content:
                    active_names.add(char_name)
        
        # 只返回活跃角色的信息
        result = {
            "main_character": character_profiles.get("main_character", {}),
            "active_supporting": []
        }
        
        for char in character_profiles.get("supporting_characters", []):
            char_name = char.get("basic_info", {}).get("name", "")
            if char_name in active_names:
                result["active_supporting"].append(char)
        
        return result
    
    def _slice_recent_events(self, chapters: List[Dict],
                            current_chapter: int) -> List[str]:
        """切片最近事件（最近5章）"""
        events = []
        
        recent_chapters = chapters[-5:] if len(chapters) >= 5 else chapters
        
        for ch in recent_chapters:
            key_events = ch.get("key_events", [])
            for event in key_events[:2]:  # 每章只取前2个事件
                if isinstance(event, str):
                    events.append({
                        "event": event,
                        "chapter": ch.get("chapter_number", 0)
                    })
        
        return events[-10:]  # 最多返回10个事件
    
    def estimate_tokens(self, context: Dict) -> int:
        """估算上下文token数"""
        total_chars = 0
        
        # 估算各部分字符数
        total_chars += len(str(context.get("novel_info", {})))
        total_chars += len(context.get("world_setting", ""))
        total_chars += len(context.get("story_tone", ""))
        total_chars += len(context.get("last_chapter_ending", ""))
        
        for summary in context.get("previous_summaries", []):
            total_chars += len(str(summary))
        
        if context.get("volume_summary"):
            total_chars += len(str(context["volume_summary"]))
        
        for fs in context.get("relevant_foreshadowing", []):
            total_chars += len(str(fs))
        
        total_chars += len(str(context.get("active_characters", {})))
        
        for event in context.get("recent_events", []):
            total_chars += len(str(event))
        
        # 粗略估算：1个token约等于2个中文字符
        return total_chars // 2


def slice_context_for_chapter(novel_id: str, chapter_number: int,
                             full_context: Dict[str, Any]) -> Dict[str, Any]:
    """切片上下文的便捷函数"""
    slicer = ContextSlicer()
    return slicer.slice_context(novel_id, chapter_number, full_context)

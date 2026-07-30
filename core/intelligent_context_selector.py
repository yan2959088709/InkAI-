"""
智能上下文选择器
根据当前章节需求，从知识库中智能选择最相关的历史信息
解决token限制问题，确保关键信息传递
"""

from typing import Dict, List, Any, Optional
import json
import re
from datetime import datetime
from utils.logger import get_logger

logger = get_logger("intelligent_context_selector")


class IntelligentContextSelector:
    """智能上下文选择器"""
    
    def __init__(self, data_manager=None, dynamic_knowledge_manager=None, 
                 core_knowledge_manager=None, embedding_service=None, vector_database=None,
                 cache_manager=None):
        self.data_manager = data_manager
        self.dynamic_knowledge_manager = dynamic_knowledge_manager
        self.core_knowledge_manager = core_knowledge_manager  # [NEW] 添加核心知识库管理器
        self.embedding_service = embedding_service  # [NEW] 添加嵌入服务
        self.vector_database = vector_database  # [NEW] 添加向量数据库
        self.cache_manager = cache_manager  # [NEW] 添加缓存管理器
        
        # [OPTIMIZED] 增加上下文窗口，支持长上下文模型（如Kimi K2.5）
        import config
        self.max_context_tokens = getattr(config, 'MAX_CONTEXT_TOKENS', 100000)  # 使用配置中的最大上下文token数
        self.use_semantic_search = embedding_service is not None and vector_database is not None  # [NEW] 是否使用语义搜索
        
        # 初始化伏笔生命周期管理器
        from core.foreshadowing_lifecycle_manager import ForeshadowingLifecycleManager
        self.foreshadowing_manager = ForeshadowingLifecycleManager(data_manager)
        
    def select_context(self, novel_id: str, current_chapter: int, 
                      user_requirements: str = "") -> Dict[str, Any]:
        """
        为指定章节智能选择上下文
        
        Args:
            novel_id: 小说ID
            current_chapter: 当前章节号
            user_requirements: 用户需求
            
        Returns:
            精选的上下文信息
        """
        # [NEW] 尝试从缓存获取
        if self.cache_manager:
            try:
                cached_context = self.cache_manager.get_context_cache(novel_id, current_chapter)
                if cached_context:
                    logger.info(f"[OK] 从缓存获取上下文（小说: {novel_id}, 章节: {current_chapter}）")
                    return cached_context
            except Exception as e:
                logger.error(f"[WARN] 获取上下文缓存失败: {e}，继续生成新上下文")
        
        try:
            # [NEW] 获取核心知识库（双层知识库的上层）
            core_knowledge = None
            if self.core_knowledge_manager:
                core_knowledge = self.core_knowledge_manager.get_core_knowledge(novel_id)
                if core_knowledge:
                    logger.info(f"[OK] 已获取核心知识库（小说: {novel_id}）")
                else:
                    logger.warning(f"[WARN] 核心知识库不存在（小说: {novel_id}），可能还未初始化")
            
            # 获取动态知识（双层知识库的下层）
            dynamic_knowledge = None
            if self.dynamic_knowledge_manager:
                dynamic_knowledge = self.dynamic_knowledge_manager.get_dynamic_knowledge(novel_id)
                if dynamic_knowledge:
                    logger.info(f"[OK] 已获取动态知识库（小说: {novel_id}）")
                else:
                    logger.warning(f"[WARN] 动态知识库不存在（小说: {novel_id}），可能还未初始化")
            
            # 如果两个知识库都不存在，使用备用上下文
            if not core_knowledge and not dynamic_knowledge:
                return self._fallback_context(novel_id, current_chapter)
            
            # [NEW] 语义搜索相关章节和内容
            semantic_results = []
            if self.use_semantic_search and user_requirements:
                try:
                    # 构建查询文本（结合用户需求和当前章节信息）
                    query_text = f"{user_requirements} 第{current_chapter}章"
                    semantic_results = self.vector_database.search_similar(
                        novel_id, query_text, top_k=5, threshold=0.6
                    )
                    if semantic_results:
                        logger.info(f"[OK] 语义搜索找到 {len(semantic_results)} 个相关文档")
                except Exception as e:
                    logger.error(f"[WARN] 语义搜索失败: {e}，继续使用规则选择")
            
            # 构建智能上下文（整合核心知识和动态知识）
            context = {
                "narrative_phase": self._determine_narrative_phase(current_chapter),
                # [NEW] 核心知识库内容
                "core_knowledge": self._get_core_knowledge_summary(core_knowledge) if core_knowledge else {},
                # [NEW] 语义搜索结果
                "semantic_search_results": self._format_semantic_results(semantic_results) if semantic_results else [],
                # 动态知识库内容
                "character_states": self._get_relevant_character_states(
                    dynamic_knowledge, current_chapter
                ) if dynamic_knowledge else {},
                "plot_summary": self._get_compressed_plot_summary(
                    dynamic_knowledge, current_chapter
                ) if dynamic_knowledge else "无可用情节摘要",
                "active_foreshadowing": self._get_active_foreshadowing(
                    dynamic_knowledge, current_chapter
                ) if dynamic_knowledge else [],
                "recent_developments": self._get_recent_developments(
                    dynamic_knowledge, current_chapter
                ) if dynamic_knowledge else {"summary": "无最近发展信息"},
                "world_state": self._get_current_world_state(
                    dynamic_knowledge, current_chapter
                ) if dynamic_knowledge else {},
                "quality_feedback": self._get_quality_feedback_summary(
                    novel_id, current_chapter
                ),
                "user_context": self._analyze_user_requirements(user_requirements),
                # 新增：伏笔生命周期管理
                "foreshadowing_guidance": self._get_foreshadowing_guidance(
                    novel_id, current_chapter
                )
            }
            
            # 压缩上下文到token限制内
            compressed_context = self._compress_context(context)
            
            # [NEW] 缓存上下文结果
            if self.cache_manager:
                try:
                    self.cache_manager.set_context_cache(
                        novel_id, current_chapter, compressed_context, ttl=1800
                    )
                except Exception as e:
                    logger.error(f"[WARN] 设置上下文缓存失败: {e}")
            
            return compressed_context
            
        except Exception as e:
            logger.error(f"智能上下文选择失败: {e}")
            return self._fallback_context(novel_id, current_chapter)
    
    def _determine_narrative_phase(self, current_chapter: int) -> Dict[str, Any]:
        """确定叙事阶段（基于50章小说）"""
        if current_chapter <= 10:
            phase = "opening"
            mission = "建立世界观，介绍主要角色，设置初始冲突"
            emotional_arc = "好奇与期待"
        elif current_chapter <= 20:
            phase = "rising_action"
            mission = "发展角色关系，加深冲突，推进主线"
            emotional_arc = "紧张与投入"
        elif current_chapter <= 35:
            phase = "climax_approach"
            mission = "准备高潮，角色面临重大选择，伏笔开始揭示"
            emotional_arc = "焦虑与期待"
        elif current_chapter <= 45:
            phase = "climax"
            mission = "高潮决战，角色蜕变，核心冲突解决"
            emotional_arc = "激动与震撼"
        else:
            phase = "resolution"
            mission = "收束情节，角色成长总结，新平衡建立"
            emotional_arc = "满足与思考"
        
        return {
            "phase": phase,
            "mission": mission,
            "emotional_arc": emotional_arc,
            "chapter_position": f"第{current_chapter}章（共50章左右）",
            "urgency_level": self._calculate_urgency(current_chapter, phase)
        }
    
    def _get_relevant_character_states(self, dynamic_knowledge: Dict, 
                                     current_chapter: int) -> Dict[str, Any]:
        """获取相关角色状态"""
        character_states = {}
        character_evolution = dynamic_knowledge.get("character_evolution", {})
        
        for character_name, evolution_list in character_evolution.items():
            # 获取最新状态
            latest_state = {}
            for evolution in evolution_list:
                if evolution["chapter_number"] <= current_chapter:
                    latest_state.update(evolution["changes"])
            
            if latest_state:
                character_states[character_name] = {
                    "current_state": latest_state,
                    "recent_changes": self._get_recent_character_changes(
                        evolution_list, current_chapter
                    )
                }
        
        return character_states
    
    def _get_compressed_plot_summary(self, dynamic_knowledge: Dict, 
                                   current_chapter: int) -> str:
        """获取压缩的情节摘要"""
        plot_timeline = dynamic_knowledge.get("plot_timeline", [])
        
        # 按重要性和时间筛选事件
        important_events = []
        recent_events = []
        
        for event in plot_timeline:
            if event["chapter_number"] <= current_chapter:
                if event.get("importance") == "high":
                    important_events.append(event)
                elif current_chapter - event["chapter_number"] <= 5:
                    recent_events.append(event)
        
        # 构建摘要
        summary_parts = []
        
        if important_events:
            summary_parts.append("【关键事件】")
            for event in important_events[-3:]:  # 最多3个关键事件
                summary_parts.append(f"第{event['chapter_number']}章: {event['description']}")
        
        if recent_events:
            summary_parts.append("【近期发展】")
            for event in recent_events[-2:]:  # 最多2个近期事件
                summary_parts.append(f"第{event['chapter_number']}章: {event['description']}")
        
        return "\n".join(summary_parts) if summary_parts else "暂无重要情节发展"
    
    def _get_active_foreshadowing(self, dynamic_knowledge: Dict, 
                                current_chapter: int) -> List[str]:
        """获取活跃的伏笔"""
        active_foreshadowing = []
        foreshadowing_tracking = dynamic_knowledge.get("foreshadowing_tracking", {})
        
        for foreshadowing_type, foreshadowing_list in foreshadowing_tracking.items():
            for foreshadowing in foreshadowing_list:
                if (foreshadowing["status"] == "active" and 
                    foreshadowing["chapter_number"] <= current_chapter):
                    active_foreshadowing.append({
                        "content": foreshadowing["content"],
                        "importance": foreshadowing["importance"],
                        "chapters_ago": current_chapter - foreshadowing["chapter_number"]
                    })
        
        # 按重要性排序，返回最重要的5个
        active_foreshadowing.sort(key=lambda x: (
            x["importance"] == "high", 
            -x["chapters_ago"]
        ), reverse=True)
        
        return [f["content"] for f in active_foreshadowing[:5]]
    
    def _get_recent_developments(self, dynamic_knowledge: Dict, 
                               current_chapter: int) -> Dict[str, Any]:
        """获取最近的发展"""
        chapter_summaries = dynamic_knowledge.get("chapter_summaries", {})
        
        recent_chapters = []
        for i in range(max(1, current_chapter - 3), current_chapter):
            chapter_key = str(i)
            if chapter_key in chapter_summaries:
                recent_chapters.append(chapter_summaries[chapter_key])
        
        if not recent_chapters:
            return {"summary": "无最近章节信息"}
        
        # 提取关键信息
        key_developments = []
        character_changes = {}
        
        for chapter in recent_chapters:
            if chapter.get("key_events"):
                key_developments.extend(chapter["key_events"])
            if chapter.get("character_development"):
                character_changes.update(chapter["character_development"])
        
        return {
            "key_developments": key_developments[-3:],  # 最多3个关键发展
            "character_changes": character_changes,
            "last_chapter_summary": recent_chapters[-1].get("summary", "") if recent_chapters else ""
        }
    
    def _get_current_world_state(self, dynamic_knowledge: Dict, 
                               current_chapter: int) -> Dict[str, Any]:
        """获取当前世界状态"""
        world_changes = dynamic_knowledge.get("world_changes", [])
        
        current_state = {}
        for change in world_changes:
            if (change["chapter_number"] <= current_chapter and 
                change.get("permanence") == "permanent"):
                change_type = change.get("change_type", "general")
                if change_type not in current_state:
                    current_state[change_type] = []
                current_state[change_type].append(change["description"])
        
        return current_state
    
    def _get_quality_feedback_summary(self, novel_id: str, 
                                    current_chapter: int) -> Dict[str, Any]:
        """获取质量反馈摘要"""
        # 这里可以集成质量评估历史，暂时返回空
        return {
            "recurring_issues": [],
            "improvement_suggestions": [],
            "successful_patterns": []
        }
    
    def _analyze_user_requirements(self, user_requirements: str) -> Dict[str, Any]:
        """分析用户需求"""
        if not user_requirements:
            return {"priority": "normal", "specific_requests": []}
        
        # 简单的关键词分析
        high_priority_keywords = ["重要", "关键", "必须", "急需"]
        specific_requests = []
        
        priority = "high" if any(keyword in user_requirements for keyword in high_priority_keywords) else "normal"
        
        # 提取具体要求
        if "角色" in user_requirements or "人物" in user_requirements:
            specific_requests.append("character_focus")
        if "情节" in user_requirements or "剧情" in user_requirements:
            specific_requests.append("plot_focus")
        if "伏笔" in user_requirements or "悬念" in user_requirements:
            specific_requests.append("foreshadowing_focus")
        
        return {
            "priority": priority,
            "specific_requests": specific_requests,
            "raw_text": user_requirements
        }
    
    def _compress_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """压缩上下文到token限制内"""
        # 简单的压缩策略：优先保留最重要的信息
        compressed = {
            "narrative_phase": context.get("narrative_phase", {}),
            # [NEW] 核心知识库摘要（压缩版）
            "core_knowledge": self._compress_core_knowledge(context.get("core_knowledge", {})),
            "character_states": self._compress_character_states(context.get("character_states", {})),
            "plot_summary": self._truncate_text(context.get("plot_summary", ""), 300),
            "active_foreshadowing": context.get("active_foreshadowing", [])[:3],  # 最多3个伏笔
            "recent_developments": context.get("recent_developments", {}),
            "user_context": context.get("user_context", {})
        }
        
        return compressed
    
    def _compress_core_knowledge(self, core_knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """压缩核心知识库信息"""
        if not core_knowledge:
            return {}
        
        try:
            # 只保留最关键的信息
            main_char = core_knowledge.get("main_character", {})
            compressed = {
                "main_character": {
                    "name": main_char.get("name", ""),
                    "personality": str(main_char.get("personality", ""))[:200] if main_char.get("personality") else ""  # 限制长度
                },
                "world_setting": str(core_knowledge.get("world_setting", ""))[:300] if core_knowledge.get("world_setting") else "",  # 限制长度
                "story_themes": core_knowledge.get("story_themes", [])[:3]  # 最多3个主题
            }
            return compressed
        except Exception as e:
            logger.info(f"压缩核心知识库时出错: {e}")
            return {}
    
    def _compress_character_states(self, character_states: Dict) -> Dict:
        """压缩角色状态信息"""
        compressed = {}
        for char_name, state_info in character_states.items():
            compressed[char_name] = {
                "key_traits": self._extract_key_traits(state_info["current_state"]),
                "recent_change": state_info["recent_changes"][-1] if state_info["recent_changes"] else None
            }
        return compressed
    
    def _extract_key_traits(self, state: Dict) -> List[str]:
        """提取关键特征"""
        # 简单提取，实际可以更智能
        key_traits = []
        for key, value in state.items():
            if isinstance(value, str) and len(value) < 50:
                key_traits.append(f"{key}: {value}")
        return key_traits[:3]  # 最多3个特征
    
    def _get_recent_character_changes(self, evolution_list: List, 
                                    current_chapter: int) -> List[Dict]:
        """获取角色最近变化"""
        recent_changes = []
        for evolution in evolution_list:
            if current_chapter - evolution["chapter_number"] <= 5:
                recent_changes.append({
                    "chapter": evolution["chapter_number"],
                    "change": evolution["changes"],
                    "description": evolution.get("description", "")
                })
        return recent_changes
    
    def _calculate_urgency(self, current_chapter: int, phase: str) -> str:
        """计算紧急程度（基于50章小说）"""
        if phase == "climax" or current_chapter > 40:
            return "high"
        elif phase == "climax_approach" or current_chapter > 30:
            return "medium"
        else:
            return "low"
    
    def _truncate_text(self, text: str, max_chars: int) -> str:
        """截断文本"""
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "..."
    
    def _get_core_knowledge_summary(self, core_knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """从核心知识库提取摘要信息"""
        if not core_knowledge:
            return {}
        
        try:
            character_profiles = core_knowledge.get("character_profiles", {})
            world_setting = core_knowledge.get("world_setting", {})
            story_themes = core_knowledge.get("story_themes", [])
            basic_rules = core_knowledge.get("basic_rules", {})
            
            # 提取主要角色信息
            main_character = character_profiles.get("main_character", {})
            main_char_summary = {
                "name": main_character.get("name", ""),
                "age": main_character.get("age", 0),
                "personality": main_character.get("personality", {}),
                "background": main_character.get("background", {})
            }
            
            # 提取配角信息（简化）
            supporting_characters = character_profiles.get("supporting_characters", [])
            supporting_chars_summary = [
                {
                    "name": char.get("name", ""),
                    "role": char.get("role", ""),
                    "relationship_with_main": char.get("relationship_with_main", "")
                }
                for char in supporting_characters[:5]  # 最多5个配角
            ]
            
            return {
                "main_character": main_char_summary,
                "supporting_characters": supporting_chars_summary,
                "world_setting": world_setting,
                "story_themes": story_themes,
                "writing_rules": basic_rules.get("writing_style", ""),
                "target_audience": basic_rules.get("target_audience", "")
            }
        except Exception as e:
            logger.info(f"提取核心知识库摘要时出错: {e}")
            return {}
    
    def _fallback_context(self, novel_id: str, current_chapter: int) -> Dict[str, Any]:
        """备用上下文（当知识库不可用时）"""
        # [NEW] 尝试获取核心知识库作为备用
        core_knowledge = None
        if self.core_knowledge_manager:
            try:
                core_knowledge = self.core_knowledge_manager.get_core_knowledge(novel_id)
            except Exception as e:
                logger.info(f"获取核心知识库作为备用时出错: {e}")
        
        return {
            "narrative_phase": self._determine_narrative_phase(current_chapter),
            "core_knowledge": self._get_core_knowledge_summary(core_knowledge) if core_knowledge else {},
            "character_states": {},
            "plot_summary": "无可用情节摘要",
            "active_foreshadowing": [],
            "recent_developments": {"summary": "无最近发展信息"},
            "world_state": {},
            "quality_feedback": {"recurring_issues": []},
            "user_context": {"priority": "normal", "specific_requests": []},
            "foreshadowing_guidance": {"urgent_revelations": [], "revelation_suggestions": []}
        }
    
    def _format_semantic_results(self, semantic_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """格式化语义搜索结果"""
        formatted = []
        for result in semantic_results:
            formatted.append({
                "doc_id": result.get("doc_id", ""),
                "text": result.get("text", "")[:500],  # 限制长度
                "similarity": result.get("similarity", 0.0),
                "metadata": result.get("metadata", {})
            })
        return formatted
    
    def _get_foreshadowing_guidance(self, novel_id: str, current_chapter: int) -> Dict[str, Any]:
        """获取伏笔指导信息"""
        try:
            # 检查紧急伏笔
            urgent_foreshadowing = self.foreshadowing_manager.check_revelation_urgency(
                novel_id, current_chapter
            )
            
            # 获取活跃伏笔
            active_foreshadowing = self.foreshadowing_manager.get_active_foreshadowing(
                novel_id, current_chapter
            )
            
            # 获取揭示建议
            revelation_suggestions = self.foreshadowing_manager.get_revelation_suggestions(
                novel_id, current_chapter
            )
            
            return {
                "urgent_revelations": urgent_foreshadowing,
                "active_foreshadowing": active_foreshadowing,
                "revelation_suggestions": revelation_suggestions,
                "foreshadowing_count": len(active_foreshadowing),
                "urgent_count": len(urgent_foreshadowing)
            }
            
        except Exception as e:
            logger.error(f"获取伏笔指导失败: {e}")
            return {
                "urgent_revelations": [],
                "active_foreshadowing": [],
                "revelation_suggestions": [],
                "foreshadowing_count": 0,
                "urgent_count": 0
            }
    
    def select_context_long_context(self, novel_id: str, current_chapter: int,
                                    user_requirements: str = "",
                                    recent_chapters_count: int = 10) -> Dict[str, Any]:
        """
        [OPTIMIZED] 长上下文模式：为支持长上下文的模型（如Kimi K2.5）优化的上下文选择
        
        与传统模式的区别：
        1. 直接传入最近N章的完整原文（而非压缩摘要）
        2. 保留第1章开头作为风格锚点
        3. 使用自然语言描述角色状态（而非JSON结构）
        4. 传入更多章节，充分利用长上下文窗口
        
        Args:
            novel_id: 小说ID
            current_chapter: 当前章节号
            user_requirements: 用户需求
            recent_chapters_count: 最近章节的数量（默认10章）
            
        Returns:
            包含完整原文的上下文信息
        """
        if not self.data_manager:
            logger.error("DataManager未初始化")
            return self._fallback_context(novel_id, current_chapter)
        
        try:
            # 获取所有章节
            chapters = self.data_manager.get_chapters(novel_id)
            if not chapters:
                logger.warning("没有找到章节数据")
                return self._fallback_context(novel_id, current_chapter)
            
            # 获取核心知识库
            core_knowledge = None
            if self.core_knowledge_manager:
                core_knowledge = self.core_knowledge_manager.get_core_knowledge(novel_id)
            
            # 构建长上下文
            context = {
                "mode": "long_context",
                "current_chapter": current_chapter,
                
                # 1. 全书大纲摘要（自然语言）
                "book_summary": self._generate_book_summary_natural(chapters, core_knowledge),
                
                # 2. 风格锚点：第1章开头（保留原始文风）
                "style_anchor": self._get_style_anchor(chapters),
                
                # 3. 最近N章完整原文
                "recent_chapters_text": self._get_recent_chapters_full_text(
                    chapters, current_chapter, recent_chapters_count
                ),
                
                # 4. 角色状态（自然语言描述）
                "character_status_natural": self._get_character_status_natural(
                    novel_id, current_chapter, core_knowledge
                ),
                
                # 5. 活跃伏笔（自然语言）
                "active_foreshadowing_natural": self._get_foreshadowing_natural(
                    novel_id, current_chapter
                ),
                
                # 6. 叙事阶段
                "narrative_phase": self._determine_narrative_phase(current_chapter),
                
                # 7. 用户需求
                "user_requirements": user_requirements
            }
            
            logger.info(f"[OK] 长上下文模式：已构建包含{recent_chapters_count}章原文的上下文")
            return context
            
        except Exception as e:
            logger.error(f"长上下文模式失败: {e}")
            return self._fallback_context(novel_id, current_chapter)
    
    def _generate_book_summary_natural(self, chapters: List[Dict],
                                       core_knowledge: Dict = None) -> str:
        """生成自然语言风格的全书摘要"""
        summary_parts = []

        # 从核心知识库获取基本信息
        if core_knowledge:
            novel_info = core_knowledge.get("novel_info", {})
            title = novel_info.get("title", "未知标题")
            user_req = novel_info.get("user_requirements", "")

            summary_parts.append(f"《{title}》")

            # 提取并添加世界观设定 [BUG FIX]
            world_setting = core_knowledge.get("world_setting", {})
            if world_setting and isinstance(world_setting, dict):
                time_period = world_setting.get("time_period", "")
                location = world_setting.get("location", "")
                atmosphere = world_setting.get("atmosphere", "")
                if time_period:
                    summary_parts.append(f"时代背景：{time_period}")
                if location:
                    summary_parts.append(f"故事地点：{location}")
                if atmosphere:
                    summary_parts.append(f"社会氛围：{atmosphere}")

            # 提取核心设定
            if user_req:
                # 提取用户需求中的关键信息
                lines = user_req.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('我想') and len(line) > 10:
                        summary_parts.append(line)
            
            # 角色概览
            char_profiles = core_knowledge.get("character_profiles", {})
            main_char = char_profiles.get("main_character", {})
            if main_char:
                name = main_char.get("name", "").split("（")[0]  # 去掉括号注释
                background = main_char.get("background", {})
                core_desire = background.get("core_desire", "")
                if name and core_desire:
                    summary_parts.append(f"主角{name}：{core_desire}")
            
            # 配角概览
            supporting = char_profiles.get("supporting_characters", [])
            for char in supporting[:3]:
                char_name = char.get("name", "")
                char_role = char.get("role", "")
                if char_name and char_role:
                    summary_parts.append(f"{char_name}（{char_role}）")
        
        # 章节统计
        if chapters:
            summary_parts.append(f"当前共{len(chapters)}章")
        
        return "\n".join(summary_parts) if summary_parts else "暂无全书摘要"
    
    def _get_style_anchor(self, chapters: List[Dict]) -> str:
        """获取风格锚点：第1章的开头部分"""
        if not chapters:
            return ""
        
        # 找到第1章
        first_chapter = None
        for ch in chapters:
            if ch.get("chapter_number") == 1:
                first_chapter = ch
                break
        
        if not first_chapter:
            first_chapter = chapters[0]
        
        content = first_chapter.get("content", "")
        # 取前1500字作为风格锚点
        if len(content) > 1500:
            return content[:1500] + "\n...(第1章风格锚点，用于保持文风一致)"
        return content
    
    def _get_recent_chapters_full_text(self, chapters: List[Dict], 
                                       current_chapter: int,
                                       count: int) -> str:
        """获取最近N章的完整原文"""
        if not chapters:
            return ""
        
        # 筛选出当前章节之前的章节
        prev_chapters = [
            ch for ch in chapters 
            if ch.get("chapter_number", 0) < current_chapter
        ]
        
        # 按章节号排序
        prev_chapters.sort(key=lambda x: x.get("chapter_number", 0))
        
        # 取最近N章
        recent = prev_chapters[-count:] if len(prev_chapters) > count else prev_chapters
        
        if not recent:
            return "（这是第1章，无前文章节）"
        
        # 拼接完整原文
        result_parts = []
        for ch in recent:
            ch_num = ch.get("chapter_number", "?")
            ch_title = ch.get("title", "无标题")
            ch_content = ch.get("content", "")
            result_parts.append(f"【第{ch_num}章 {ch_title}】\n{ch_content}")
        
        return "\n\n".join(result_parts)
    
    def _get_character_status_natural(self, novel_id: str, current_chapter: int,
                                      core_knowledge: Dict = None) -> str:
        """获取自然语言风格的角色状态描述"""
        status_parts = []
        
        # 从核心知识库获取角色基本信息
        if core_knowledge:
            char_profiles = core_knowledge.get("character_profiles", {})
            main_char = char_profiles.get("main_character", {})
            if main_char:
                name = main_char.get("name", "").split("（")[0]
                personality = main_char.get("personality", {})
                desc = personality.get("description", "")[:200] if personality else ""
                if name:
                    status_parts.append(f"【{name}】{desc}")
        
        # 从动态知识库获取最新状态
        if self.dynamic_knowledge_manager:
            dynamic_knowledge = self.dynamic_knowledge_manager.get_dynamic_knowledge(novel_id)
            if dynamic_knowledge:
                char_evolution = dynamic_knowledge.get("character_evolution", {})
                for char_name, evolution_list in char_evolution.items():
                    # 获取最近的变化
                    recent_changes = [
                        e for e in evolution_list 
                        if current_chapter - e.get("chapter_number", 0) <= 3
                    ]
                    if recent_changes:
                        latest = recent_changes[-1]
                        changes = latest.get("changes", {})
                        overall = changes.get("overall_development", "")
                        if overall:
                            status_parts.append(f"【{char_name}近期发展】{overall[:150]}")
        
        return "\n".join(status_parts) if status_parts else "暂无角色状态信息"
    
    def _get_foreshadowing_natural(self, novel_id: str, current_chapter: int) -> str:
        """获取自然语言风格的伏笔描述"""
        try:
            if not self.foreshadowing_manager:
                return ""
            
            active_foreshadowing = self.foreshadowing_manager.get_active_foreshadowing(
                novel_id, current_chapter
            )
            
            if not active_foreshadowing:
                return ""
            
            result_parts = ["【活跃伏笔】"]
            for i, foreshadowing in enumerate(active_foreshadowing[:5], 1):
                content = foreshadowing.get("content", "")
                chapter = foreshadowing.get("chapter_number", 0)
                if content:
                    result_parts.append(f"{i}. 第{chapter}章埋下：{content}")
            
            return "\n".join(result_parts)
            
        except Exception as e:
            logger.error(f"获取伏笔信息失败: {e}")
            return ""
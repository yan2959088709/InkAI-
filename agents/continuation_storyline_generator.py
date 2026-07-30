"""
续写故事线生成智能体
负责生成下一章的故事线进度逻辑
"""

from base_agent import BaseAgent
from typing import Dict, List, Any, Optional
import config
from utils.logger import get_logger
logger = get_logger("continuation_storyline_generator")


class ContinuationStorylineGenerator(BaseAgent):
    """续写故事线生成智能体"""
    
    # 预计总章节数（可配置）
    DEFAULT_TOTAL_CHAPTERS = 40
    
    def __init__(self, novel_type: str = "都市"):
        super().__init__("续写故事线生成智能体")
        self.progression_planner = None  # 延迟初始化
        self.novel_type = novel_type
        self.rhythm_config = None  # 延迟初始化
        self.dual_checker = None  # 延迟初始化
    
    def _get_rhythm_config(self):
        """获取节奏配置"""
        if self.rhythm_config is None:
            from core.rhythm_config import RhythmConfig
            self.rhythm_config = RhythmConfig(self.novel_type)
        return self.rhythm_config
    
    def _get_dual_checker(self):
        """获取双线检查器"""
        if self.dual_checker is None:
            from core.dual_storyline_checker import DualStorylineChecker
            self.dual_checker = DualStorylineChecker()
        return self.dual_checker
    
    def _get_foreshadowing_recycler(self):
        """获取伏笔回收器"""
        if not hasattr(self, 'foreshadowing_recycler') or self.foreshadowing_recycler is None:
            from core.foreshadowing_recycler import ForeshadowingRecycler
            self.foreshadowing_recycler = ForeshadowingRecycler()
        return self.foreshadowing_recycler
    
    def _get_slim_context(self, knowledge_base: Dict[str, Any], 
                         chapter_number: int) -> str:
        """
        获取精简的上下文切片
        
        优化：只传本章相关的信息，避免信息过载
        """
        chapters = knowledge_base.get("chapters", [])
        character_profiles = knowledge_base.get("character_profiles", {})
        
        # 1. 上一章结尾（最后500字）
        last_chapter_ending = ""
        if chapters:
            last_content = chapters[-1].get("content", "")
            last_chapter_ending = last_content[-500:] if last_content else ""
        
        # 2. 前3章标题
        recent_titles = []
        for ch in chapters[-3:]:
            title = ch.get("title", "")
            if title:
                recent_titles.append(f"第{ch.get('chapter_number', '?')}章: {title}")
        
        # 3. 主要人物（只取名字和关键特征）
        main_chars = []
        main_char = character_profiles.get("main_character", {})
        if main_char:
            name = main_char.get("basic_info", {}).get("name", "")
            if name:
                main_chars.append(name)
        
        supporting = character_profiles.get("supporting_characters", [])
        for char in supporting[:2]:  # 只取前2个配角
            name = char.get("basic_info", {}).get("name", "")
            if name:
                main_chars.append(name)
        
        # 构建精简上下文
        context = f"""
【上一章结尾】：
{last_chapter_ending if last_chapter_ending else "无"}

【近期章节】：
{chr(10).join(recent_titles) if recent_titles else "无"}

【主要人物】：
{', '.join(main_chars) if main_chars else "无"}
"""
        
        return context
    
    def set_novel_type(self, novel_type: str):
        """设置小说类型"""
        self.novel_type = novel_type
        self.rhythm_config = None  # 重置，下次使用时重新加载
    
    def _get_progression_planner(self, total_chapters: int = None):
        """获取推进规划器"""
        if self.progression_planner is None or total_chapters:
            from core.storyline_progression_planner import StorylineProgressionPlanner
            self.progression_planner = StorylineProgressionPlanner(
                total_chapters or self.DEFAULT_TOTAL_CHAPTERS
            )
        return self.progression_planner
    
    def _get_volume_connection(self, knowledge_base: Dict[str, Any], 
                              chapter_number: int) -> str:
        """获取卷间关联信息"""
        try:
            from core.volume_connection_manager import VolumeConnectionManager
            
            # 获取小说ID
            novel_info = knowledge_base.get("novel_info", {})
            chapters = knowledge_base.get("chapters", [])
            
            # 构建卷间关联上下文
            connection_manager = VolumeConnectionManager()
            
            # 简化版：直接生成卷间关联指导
            volume_number = ((chapter_number - 1) // 40) + 1
            chapter_in_volume = ((chapter_number - 1) % 40) + 1
            
            # 确定冲突级别
            if volume_number <= 3:
                conflict_level = "个人危机"
                stakes_level = "个人安危"
            elif volume_number <= 15:
                conflict_level = "局部危机"
                stakes_level = "团队生存"
            else:
                conflict_level = "全局危机"
                stakes_level = "世界命运"
            
            # 获取上卷摘要（如果是新卷开始）
            volume_summary = knowledge_base.get("volume_summary")
            previous_summaries = knowledge_base.get("previous_summaries", [])
            
            guidance = f"""
【卷间关联信息】：
- 当前：第{volume_number}卷，卷内第{chapter_in_volume}章
- 冲突级别：{conflict_level}
- 赌注级别：{stakes_level}
"""
            
            # 如果是新卷开始，添加上卷回顾
            if chapter_in_volume == 1 and volume_number > 1 and volume_summary:
                key_events = volume_summary.get("key_events", [])
                guidance += f"""
【上卷回顾】：
- 关键事件：{', '.join(key_events[:3]) if key_events else '无'}
- 本卷需要延续上卷的人物发展和剧情走向
"""
            
            # 添加前3章摘要
            if previous_summaries:
                guidance += """
【前文摘要】：
"""
                for summary in previous_summaries[-3:]:
                    guidance += f"- 第{summary.get('chapter_number', '?')}章: {summary.get('title', '')}\n"
            
            guidance += """
【卷间关联要求】：
1. 人物状态必须延续，不能突变
2. 未完成的伏笔必须推进
3. 冲突赌注必须升级
4. 为本卷高潮做铺垫
"""
            
            return guidance
            
        except Exception as e:
            self.log(f"获取卷间关联信息失败: {e}")
            return ""
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成续写故事线"""
        knowledge_base = input_data.get("knowledge_base", {})
        user_requirements = input_data.get("user_requirements", "")
        intelligent_context = input_data.get("intelligent_context")
        
        if not knowledge_base and not intelligent_context:
            return {"error": "缺少知识库数据或智能上下文"}
        
        # 生成下一章的故事线
        if intelligent_context:
            # 使用智能上下文生成
            next_chapter_storyline = self._generate_with_intelligent_context(
                intelligent_context, user_requirements
            )
        else:
            # 使用传统知识库生成
            next_chapter_storyline = self._generate_next_chapter_storyline(knowledge_base, user_requirements)
        
        return {
            "success": True,
            "status": "success",
            "next_chapter_storyline": next_chapter_storyline,
            "next_step": "chapter_writing"
        }
    
    def _generate_next_chapter_storyline(self, knowledge_base: Dict[str, Any], 
                                       user_requirements: str) -> Dict[str, Any]:
        """生成下一章故事线"""
        try:
            # 获取基本信息
            novel_info = knowledge_base.get("novel_info", {})
            chapters = knowledge_base.get("chapters", [])
            character_profiles = knowledge_base.get("character_profiles", {})
            plot_lines = knowledge_base.get("plot_lines", {})
            last_chapter = knowledge_base.get("last_chapter_summary", {})
            world_setting = knowledge_base.get("world_setting", "")
            story_tone = knowledge_base.get("story_tone", "")
            tags = knowledge_base.get("tags", {})
            
            # 确定下一章号
            next_chapter_number = len(chapters) + 1
            
            # [NEW] 获取节奏配置
            rhythm_cfg = self._get_rhythm_config()
            rhythm_info = rhythm_cfg.get_rhythm_for_chapter(next_chapter_number)
            total_chapters = rhythm_cfg.get_volume_chapters() * 25  # 假设25卷
            
            # [NEW] 获取双线咬合检查
            dual_checker = self._get_dual_checker()
            dual_check = dual_checker.check_intersection_point(
                next_chapter_number, total_chapters, ""
            )
            
            # [NEW] 检查到期伏笔
            foreshadowing_recycler = self._get_foreshadowing_recycler()
            overdue_foreshadowing = foreshadowing_recycler.check_overdue_foreshadowing(
                novel_info.get("novel_id", ""), next_chapter_number, chapters
            )
            recycle_guidance = foreshadowing_recycler.generate_recycle_guidance(overdue_foreshadowing)
            force_recycle = foreshadowing_recycler.should_force_recycle(overdue_foreshadowing)
            
            # 获取推进规划信息
            planner = self._get_progression_planner()
            phase_info = planner.get_current_phase(next_chapter_number)
            dual_plan = planner.get_dual_storyline_plan(next_chapter_number)
            
            # 获取卷间关联信息
            volume_connection = self._get_volume_connection(
                knowledge_base, next_chapter_number
            )
            
            # [NEW] 获取精简的上下文切片
            slim_context = self._get_slim_context(knowledge_base, next_chapter_number)
            
            # 构建生成提示
            prompt = f"""
请为小说《{novel_info.get('title', '未知标题')}》生成第{next_chapter_number}章的故事线。

【节奏配置】：
- 小说类型：{rhythm_cfg.config['name']}
- 章节类型：{rhythm_info['name']}
- 节奏循环：{rhythm_info['cycle_position']}/{rhythm_info['cycle_total']}
- 节奏速度：{rhythm_info['pacing']}
- 冲突强度：{rhythm_info['conflict_intensity']}

【双线咬合】：
- 咬合强度：{dual_check['link_strength']}
- 是否检查点：{'是' if dual_check['should_check'] else '否'}
{dual_check['guidance']}

{recycle_guidance}

【剧情阶段信息】：
- 当前阶段：{phase_info['name']}（占全书{phase_info['chapters_ratio']*100:.0f}%）
- 阶段描述：{phase_info['description']}
- 冲突级别：{phase_info['conflict_level']}
- 赌注范围：{phase_info['stakes']}

{volume_connection}

【精简上下文】：
{slim_context}

【用户需求】：{user_requirements if user_requirements else "无特殊要求"}

【原文信息】：
1. 世界观设定：{world_setting}
2. 故事基调：{story_tone}
3. 故事标签：{self._format_tags(tags)}

4. 人物设定：
{self._format_character_profiles(character_profiles)}

5. 整体故事线：
{self._format_plot_lines(plot_lines)}

6. 上一章信息：
{self._format_last_chapter(last_chapter)}

7. 用户续写需求：{user_requirements if user_requirements else "无特殊要求"}

【重要写作规则】：
1. 【禁止重复】：不要重复上一章已经写过的情节、对话或场景
2. 【剧情推进】：本章必须有新的剧情发展，不能停留在原地
3. 【时间推进】：故事时间应该向前推进，不能回到过去
4. 【新事件】：必须有新的关键事件发生
5. 【角色发展】：角色应该有新的变化或成长
6. 【阶段推进】：本章的冲突和赌注必须符合当前阶段的升级要求
7. 【双线咬合】：如果是交汇章，必须包含明暗线的交叉点
8. 【人物弧光】：人物成长必须与剧情发展同步，不能突变
9. 【伏笔管理】：推进或回收活跃伏笔，保持长线连贯

请生成第{next_chapter_number}章的详细故事线，返回JSON格式：
{{
    "chapter_number": {next_chapter_number},
    "chapter_title": "章节标题（必须是新标题，不能与前几章重复）",
    "scene_setting": {{
        "time": "时间设定（必须在上一章之后）",
        "location": "地点设定",
        "atmosphere": "氛围描述",
        "weather": "天气状况"
    }},
    "plot_points": [
        "情节要点1（必须是新情节）",
        "情节要点2",
        "情节要点3"
    ],
    "character_interactions": [
        {{
            "characters": ["角色1", "角色2"],
            "interaction_type": "对话/冲突/合作",
            "purpose": "互动目的"
        }}
    ],
    "key_events": [
        "关键事件1（必须是新事件，不能与前几章重复）",
        "关键事件2"
    ],
    "conflicts": [
        {{
            "type": "内心冲突/外部冲突/人际冲突",
            "description": "冲突描述",
            "resolution": "解决方式"
        }}
    ],
    "foreshadowing": [
        "伏笔1（新伏笔）",
        "伏笔2"
    ],
    "character_development": {{
        "main_character": "主角在本章的新发展",
        "supporting_characters": "配角的新发展"
    }},
    "chapter_ending": "章节结尾描述（为下章留下悬念）",
    "next_chapter_hint": "下章预告（暗示新的发展方向）",
    "writing_notes": "写作注意事项"
}}
"""
            
            messages = [
                {"role": "system", "content": "你是一个专业的故事策划师，擅长创作连贯且引人入胜的故事线。"},
                {"role": "user", "content": prompt}
            ]
            
            response = self.call_llm(messages)
            result = self.parse_json_response(response)
            
            # 检查解析结果
            if not result or not isinstance(result, dict):
                self.log(f"JSON解析结果无效: {result}")
                return self._create_default_storyline(next_chapter_number)
            
            # 验证和补充结果
            return self._validate_storyline_result(result, next_chapter_number)
            
        except Exception as e:
            self.log(f"生成故事线失败: {e}")
            return self._create_default_storyline(len(chapters) + 1)
    
    def _validate_storyline_result(self, result: Dict[str, Any], chapter_number: int) -> Dict[str, Any]:
        """验证故事线结果"""
        try:
            # 确保result是字典类型
            if not isinstance(result, dict):
                self.log(f"故事线结果不是字典类型: {type(result)}")
                return self._create_default_storyline(chapter_number)
            
            # 确保必要字段存在
            required_fields = {
                "chapter_number": chapter_number,
                "chapter_title": f"第{chapter_number}章",
                "scene_setting": {
                    "time": "待设定",
                    "location": "待设定",
                    "atmosphere": "待设定",
                    "weather": "待设定"
                },
                "plot_points": [],
                "character_interactions": [],
                "key_events": [],
                "conflicts": [],
                "foreshadowing": [],
                "character_development": {
                    "main_character": "待补充",
                    "supporting_characters": "待补充"
                },
                "chapter_ending": "待补充",
                "next_chapter_hint": "待补充",
                "writing_notes": "待补充"
            }
            
            # 补充缺失字段
            for field, default_value in required_fields.items():
                if field not in result:
                    result[field] = default_value
            
            return result
            
        except Exception as e:
            self.log(f"验证故事线结果失败: {e}")
            return self._create_default_storyline(chapter_number)
    
    def _create_default_storyline(self, chapter_number: int) -> Dict[str, Any]:
        """创建默认故事线"""
        return {
            "chapter_number": chapter_number,
            "chapter_title": f"第{chapter_number}章",
            "scene_setting": {
                "time": "待设定",
                "location": "待设定",
                "atmosphere": "待设定",
                "weather": "待设定"
            },
            "plot_points": ["情节发展待补充"],
            "character_interactions": [],
            "key_events": ["关键事件待补充"],
            "conflicts": [],
            "foreshadowing": [],
            "character_development": {
                "main_character": "待补充",
                "supporting_characters": "待补充"
            },
            "chapter_ending": "待补充",
            "next_chapter_hint": "待补充",
            "writing_notes": "请根据原文设定补充具体内容"
        }
    
    def _format_character_profiles(self, character_profiles: Dict[str, Any]) -> str:
        """格式化人物档案"""
        if not character_profiles:
            return "无人物档案"
        
        formatted = ""
        main_character = character_profiles.get("main_character", {})
        if main_character:
            basic_info = main_character.get("basic_info", {})
            personality = main_character.get("personality", {})
            background = main_character.get("background", {})
            
            formatted += f"主角：{basic_info.get('name', '未知')}\n"
            formatted += f"  年龄：{basic_info.get('age', '未知')}\n"
            formatted += f"  职业：{basic_info.get('occupation', '未知')}\n"
            formatted += f"  性格：{personality.get('description', '未知')}\n"
            formatted += f"  核心欲望：{background.get('core_desire', '未知')}\n"
            formatted += f"  主要恐惧：{background.get('fear', '未知')}\n\n"
        
        supporting_characters = character_profiles.get("supporting_characters", [])
        for char in supporting_characters:
            basic_info = char.get("basic_info", {})
            formatted += f"配角：{basic_info.get('name', '未知')} ({char.get('role', '未知角色')})\n"
            formatted += f"  性格：{char.get('personality', '未知')}\n"
            formatted += f"  与主角关系：{char.get('relationship_with_main', '未知')}\n\n"
        
        return formatted
    
    def _format_plot_lines(self, plot_lines: Dict[str, Any]) -> str:
        """格式化故事线"""
        if not plot_lines:
            return "无故事线信息"
        
        formatted = "主线：\n"
        main_line = plot_lines.get("main_line", [])
        for i, line in enumerate(main_line, 1):
            formatted += f"  {i}. {line}\n"
        
        sub_lines = plot_lines.get("sub_lines", [])
        if sub_lines:
            formatted += "\n支线：\n"
            for i, line in enumerate(sub_lines, 1):
                formatted += f"  {i}. {line}\n"
        
        return formatted
    
    def _format_last_chapter(self, last_chapter: Dict[str, Any]) -> str:
        """格式化上一章信息 - 修复：添加实际结尾内容"""
        if not last_chapter:
            return "无上一章信息"
        
        formatted = f"第{last_chapter.get('chapter_number', 0)}章：{last_chapter.get('title', '未知标题')}\n"
        formatted += f"概要：{last_chapter.get('summary', '无概要')}\n"
        
        # [FIX] 添加上一章实际结尾内容（最后500字）
        content_ending = last_chapter.get("content_ending", "")
        if content_ending:
            formatted += f"\n【上一章结尾内容】（请从这里开始续写，不要重复）：\n{content_ending[-500:]}\n"
        
        key_events = last_chapter.get("key_events", [])
        if key_events:
            formatted += f"关键事件：{', '.join(key_events)}\n"
        
        foreshadowing = last_chapter.get("foreshadowing", [])
        if foreshadowing:
            formatted += f"伏笔：{', '.join(foreshadowing)}\n"
        
        next_hint = last_chapter.get("next_chapter_hint", "")
        if next_hint:
            formatted += f"下章预告：{next_hint}\n"
        
        return formatted
    
    def _format_tags(self, tags: Dict[str, Any]) -> str:
        """格式化标签信息"""
        if not tags:
            return "无标签信息"
        
        formatted = ""
        selected_tags = tags.get("selected_tags", {})
        for category, tag_list in selected_tags.items():
            if tag_list and isinstance(tag_list, list):
                formatted += f"{category}: {', '.join(tag_list)}\n"
            else:
                formatted += f"{category}: 无标签\n"
        return formatted
    
    def _generate_with_intelligent_context(self, intelligent_context: Dict[str, Any], 
                                         user_requirements: str) -> Dict[str, Any]:
        """使用智能上下文生成故事线"""
        try:
            # 获取叙事阶段信息
            narrative_phase = intelligent_context.get("narrative_phase", {})
            character_states = intelligent_context.get("character_states", {})
            plot_summary = intelligent_context.get("plot_summary", "")
            active_foreshadowing = intelligent_context.get("active_foreshadowing", [])
            recent_developments = intelligent_context.get("recent_developments", {})
            world_state = intelligent_context.get("world_state", {})
            user_context = intelligent_context.get("user_context", {})
            
            # 构建增强版Prompt
            prompt = f"""你是一名资深小说架构师，请基于智能上下文为小说生成下一章的故事线。

## 当前叙事阶段
阶段: {narrative_phase.get('phase', '未知')}
任务: {narrative_phase.get('mission', '推进故事发展')}
情感弧线: {narrative_phase.get('emotional_arc', '保持节奏')}
紧急程度: {narrative_phase.get('urgency_level', '中等')}

## 角色当前状态
{self._format_character_states(character_states)}

## 情节发展摘要
{plot_summary}

## 活跃伏笔
{self._format_active_foreshadowing(active_foreshadowing)}

## 最近发展
{self._format_recent_developments(recent_developments)}

## 世界状态变化
{self._format_world_state(world_state)}

## 伏笔指导
{self._format_foreshadowing_guidance(intelligent_context.get('foreshadowing_guidance', {}))}

## 用户需求
{user_requirements if user_requirements else "无特殊要求"}

## 生成要求
1. 严格按照当前叙事阶段的任务要求推进情节
2. 体现角色的当前状态和最新发展
3. 合理运用或推进活跃的伏笔
4. 确保与最近章节的连贯性
5. 根据紧急程度调整情节节奏
6. 避免重复已用过的情节模式
7. 为下一阶段的发展做好铺垫

请返回JSON格式的故事线：
{{
    "chapter_number": 章节号,
    "chapter_title": "章节标题",
    "scene_setting": {{
        "location": "场景地点",
        "time": "时间",
        "atmosphere": "氛围描述"
    }},
    "plot_points": [
        "主要情节点1",
        "主要情节点2",
        "主要情节点3"
    ],
    "character_interactions": [
        "角色互动1",
        "角色互动2"
    ],
    "key_events": [
        "关键事件1",
        "关键事件2"
    ],
    "conflicts": [
        "冲突1",
        "冲突2"
    ],
    "foreshadowing": [
        "新伏笔1",
        "新伏笔2"
    ],
    "character_development": {{
        "角色名": "发展描述"
    }},
    "chapter_ending": "章节结尾描述",
    "next_chapter_hint": "下章预告",
    "writing_notes": "写作注意事项",
    "narrative_progress": "本章在整体叙事中的作用"
}}"""
            
            # 调用LLM生成
            response = self.call_llm([{"role": "user", "content": prompt}])
            result = self.parse_json_response(response)
            
            if "error" in result:
                logger.error(f"智能上下文故事线生成失败: {result['error']}")
                return self._create_fallback_storyline()
            
            return result
            
        except Exception as e:
            logger.info(f"使用智能上下文生成故事线时出错: {e}")
            return self._create_fallback_storyline()
    
    def _format_character_states(self, character_states: Dict[str, Any]) -> str:
        """格式化角色状态"""
        if not character_states:
            return "无角色状态信息"
        
        formatted_parts = []
        for char_name, state_info in character_states.items():
            key_traits = state_info.get("key_traits", [])
            recent_change = state_info.get("recent_change")
            
            char_desc = f"【{char_name}】"
            if key_traits:
                char_desc += f" 当前特征: {', '.join(key_traits)}"
            if recent_change:
                char_desc += f" | 最近变化: {recent_change.get('description', '无')}"
            
            formatted_parts.append(char_desc)
        
        return "\n".join(formatted_parts)
    
    def _format_active_foreshadowing(self, active_foreshadowing: List[str]) -> str:
        """格式化活跃伏笔"""
        if not active_foreshadowing:
            return "无活跃伏笔"
        
        return "\n".join([f"- {foreshadow}" for foreshadow in active_foreshadowing])
    
    def _format_recent_developments(self, recent_developments: Dict[str, Any]) -> str:
        """格式化最近发展"""
        if not recent_developments:
            return "无最近发展信息"
        
        formatted_parts = []
        
        key_developments = recent_developments.get("key_developments", [])
        if key_developments:
            formatted_parts.append("关键发展:")
            formatted_parts.extend([f"- {dev}" for dev in key_developments])
        
        last_chapter_summary = recent_developments.get("last_chapter_summary", "")
        if last_chapter_summary:
            formatted_parts.append(f"上章摘要: {last_chapter_summary}")
        
        return "\n".join(formatted_parts) if formatted_parts else "无发展信息"
    
    def _format_world_state(self, world_state: Dict[str, Any]) -> str:
        """格式化世界状态"""
        if not world_state:
            return "无世界状态变化"
        
        formatted_parts = []
        for change_type, changes in world_state.items():
            if changes:
                formatted_parts.append(f"{change_type}: {', '.join(changes)}")
        
        return "\n".join(formatted_parts) if formatted_parts else "无世界状态变化"
    
    def _format_foreshadowing_guidance(self, foreshadowing_guidance: Dict[str, Any]) -> str:
        """格式化伏笔指导信息"""
        if not foreshadowing_guidance:
            return "无伏笔指导信息"
        
        formatted_parts = []
        
        # 紧急伏笔
        urgent_revelations = foreshadowing_guidance.get("urgent_revelations", [])
        if urgent_revelations:
            formatted_parts.append("🚨 紧急伏笔（必须处理）:")
            for urgent in urgent_revelations:
                urgency_emoji = "🔴" if urgent["urgency"] == "critical" else "🟡"
                formatted_parts.append(
                    f"  {urgency_emoji} {urgent['title']}: {urgent['content']} "
                    f"(还有{urgent['chapters_left']}章)"
                )
        
        # 活跃伏笔
        active_foreshadowing = foreshadowing_guidance.get("active_foreshadowing", [])
        if active_foreshadowing:
            formatted_parts.append("📝 活跃伏笔（可选发展）:")
            for active in active_foreshadowing[:3]:  # 最多显示3个
                formatted_parts.append(f"  • {active['title']}: {active['content']}")
        
        # 揭示建议
        revelation_suggestions = foreshadowing_guidance.get("revelation_suggestions", [])
        if revelation_suggestions:
            formatted_parts.append("💡 揭示建议:")
            for suggestion in revelation_suggestions[:2]:  # 最多显示2个
                formatted_parts.append(
                    f"  • {suggestion['title']}: {suggestion['timing_advice']}"
                )
        
        # 统计信息
        foreshadowing_count = foreshadowing_guidance.get("foreshadowing_count", 0)
        urgent_count = foreshadowing_guidance.get("urgent_count", 0)
        
        if foreshadowing_count > 0:
            formatted_parts.append(f"📊 伏笔状态: 总计{foreshadowing_count}个，紧急{urgent_count}个")
        
        return "\n".join(formatted_parts) if formatted_parts else "无伏笔指导信息"
    
    def _create_fallback_storyline(self) -> Dict[str, Any]:
        """创建备用故事线"""
        return {
            "chapter_number": 1,
            "chapter_title": "新的开始",
            "scene_setting": {
                "location": "未知地点",
                "time": "当前时间",
                "atmosphere": "平静"
            },
            "plot_points": ["推进主线情节", "角色发展", "设置新的挑战"],
            "character_interactions": ["主角内心独白", "与重要角色对话"],
            "key_events": ["重要决定", "新发现"],
            "conflicts": ["内心冲突", "外部阻碍"],
            "foreshadowing": ["为未来发展埋下伏笔"],
            "character_development": {"主角": "面临新的成长机会"},
            "chapter_ending": "留下悬念",
            "next_chapter_hint": "更大的挑战即将到来",
            "writing_notes": "注重角色情感描写",
            "narrative_progress": "推进整体故事发展"
        }

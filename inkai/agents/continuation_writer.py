# 续写写作智能体
# 基于分析结果进行智能续写，保持内容连贯性

import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from ..core.base_agent import EnhancedBaseAgent


class ContinuationWriterAgent(EnhancedBaseAgent):
    """续写写作智能体 - 基于分析结果进行智能续写"""
    
    def __init__(self):
        super().__init__("续写写作智能体")
        
        # 续写模式
        self.continuation_modes = {
            "seamless": "无缝续写",
            "new_chapter": "新章节",
            "scene_continuation": "场景续写",
            "time_skip": "时间跳跃",
            "perspective_shift": "视角转换"
        }
        
        # 写作风格
        self.writing_styles = {
            "narrative": "叙述性",
            "descriptive": "描述性",
            "dialogue_heavy": "对话为主",
            "action_oriented": "动作导向",
            "introspective": "内省型"
        }
        
        # 连贯性检查点
        self.consistency_checkpoints = [
            "character_consistency",
            "plot_consistency", 
            "world_consistency",
            "tone_consistency",
            "style_consistency"
        ]
        
        self._log("续写写作智能体初始化完成", "INFO")
    
    def write_continuation(self, novel_data: Dict[str, Any], analysis_result: Dict[str, Any], 
                          continuation_requirements: str = "") -> Dict[str, Any]:
        """执行续写"""
        self._log("开始续写写作", "INFO")
        
        # 确定续写模式
        continuation_mode = self._determine_continuation_mode(analysis_result, continuation_requirements)
        
        # 构建续写上下文
        continuation_context = self._build_continuation_context(novel_data, analysis_result, continuation_mode)
        
        # 生成续写内容
        continuation_content = self._generate_continuation_content(continuation_context)
        
        # 验证连贯性
        consistency_check = self._check_consistency(continuation_content, novel_data)
        
        # 优化内容
        optimized_content = self._optimize_content(continuation_content, consistency_check)
        
        # 生成章节信息
        chapter_info = self._generate_chapter_info(optimized_content, analysis_result, continuation_mode)
        
        continuation_result = {
            "chapter_info": chapter_info,
            "content": optimized_content,
            "continuation_mode": continuation_mode,
            "consistency_check": consistency_check,
            "writing_metadata": {
                "word_count": self._count_words(optimized_content.get("content", "")),
                "writing_time": datetime.now().isoformat(),
                "continuation_type": analysis_result.get("continuation_direction", {}).get("continuation_type", "plot_advancement")
            }
        }
        
        self._log("续写写作完成", "INFO")
        return continuation_result
    
    def _determine_continuation_mode(self, analysis_result: Dict[str, Any], requirements: str) -> str:
        """确定续写模式"""
        # 默认模式
        mode = "new_chapter"
        
        # 根据分析结果调整
        continuation_type = analysis_result.get("continuation_direction", {}).get("continuation_type", "plot_advancement")
        
        if continuation_type == "character_development":
            mode = "introspective"
        elif continuation_type == "conflict_escalation":
            mode = "action_oriented"
        elif continuation_type == "world_building":
            mode = "descriptive"
        elif continuation_type == "mystery_revelation":
            mode = "narrative"
        
        # 根据用户需求调整
        if requirements:
            if "无缝" in requirements or "连续" in requirements:
                mode = "seamless"
            elif "新章节" in requirements:
                mode = "new_chapter"
            elif "时间跳跃" in requirements:
                mode = "time_skip"
            elif "视角" in requirements:
                mode = "perspective_shift"
        
        return mode
    
    def _build_continuation_context(self, novel_data: Dict[str, Any], analysis_result: Dict[str, Any], 
                                   continuation_mode: str) -> Dict[str, Any]:
        """构建续写上下文"""
        context = {
            "novel_info": {
                "title": novel_data.get("title", "未命名小说"),
                "total_chapters": len(novel_data.get("chapters", [])),
                "last_chapter": novel_data.get("chapters", [])[-1] if novel_data.get("chapters") else {}
            },
            "character_context": analysis_result.get("character_analysis", {}),
            "plot_context": analysis_result.get("plot_analysis", {}),
            "continuation_direction": analysis_result.get("continuation_direction", {}),
            "continuation_mode": continuation_mode,
            "key_information": analysis_result.get("key_information", {}),
            "suggestions": analysis_result.get("continuation_suggestions", {})
        }
        
        return context
    
    def _generate_continuation_content(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """生成续写内容"""
        # 构建提示词
        prompt = self._build_continuation_prompt(context)
        
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的小说续写专家，擅长保持故事的连贯性和吸引力。你能够基于现有内容进行自然流畅的续写，同时推进情节发展和人物成长。"
            },
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        # 确保返回格式正确
        if not isinstance(result, dict):
            result = {"content": str(result), "title": "续写章节"}
        
        # 确保必要字段存在
        if "content" not in result:
            result["content"] = "续写内容生成失败，请检查API配置。"
        if "title" not in result:
            result["title"] = f"第{context['novel_info']['total_chapters'] + 1}章"
        
        return result
    
    def _build_continuation_prompt(self, context: Dict[str, Any]) -> str:
        """构建续写提示词"""
        novel_info = context["novel_info"]
        continuation_direction = context["continuation_direction"]
        key_info = context["key_information"]
        suggestions = context["suggestions"]
        
        # 获取最后一章信息
        last_chapter = novel_info.get("last_chapter", {})
        last_chapter_title = last_chapter.get("title", "前一章")
        last_chapter_summary = last_chapter.get("summary", "无摘要")
        
        # 获取主要人物信息
        main_characters = key_info.get("main_characters", [])
        main_char_info = ""
        if main_characters:
            main_char = main_characters[0]
            main_char_info = f"主角：{main_char.get('name', '未知')}，{main_char.get('key_traits', '')}"
        
        # 获取续写建议
        plot_suggestions = suggestions.get("plot_suggestions", [])
        character_suggestions = suggestions.get("character_suggestions", [])
        
        prompt = f"""
        请基于以下信息进行小说续写：
        
        小说信息：
        - 标题：{novel_info.get('title', '未命名小说')}
        - 当前章节数：{novel_info.get('total_chapters', 0)}
        - 上一章标题：{last_chapter_title}
        - 上一章摘要：{last_chapter_summary}
        
        人物信息：
        {main_char_info}
        
        续写方向：
        - 主要焦点：{continuation_direction.get('primary_focus', '情节推进')}
        - 续写类型：{continuation_direction.get('continuation_type', 'plot_advancement')}
        - 目标字数：{continuation_direction.get('target_length', 2500)}字
        
        续写建议：
        - 情节建议：{', '.join(plot_suggestions[:3]) if plot_suggestions else '无'}
        - 人物建议：{', '.join(character_suggestions[:3]) if character_suggestions else '无'}
        
        续写要求：
        1. 保持与前面章节的连贯性
        2. 推进故事情节发展
        3. 展现人物成长和变化
        4. 保持原有的写作风格
        5. 为后续章节留下伏笔
        6. 确保内容生动有趣
        
        请返回JSON格式：
        {{
            "title": "章节标题",
            "content": "章节正文内容（详细完整）",
            "summary": "章节概要",
            "key_events": ["关键事件1", "关键事件2"],
            "foreshadowing": ["伏笔1", "伏笔2"],
            "character_development": "人物发展描述",
            "plot_advancement": "情节推进描述"
        }}
        """
        
        return prompt
    
    def _check_consistency(self, content: Dict[str, Any], novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查连贯性"""
        consistency_check = {
            "overall_score": 0,
            "character_consistency": {"score": 0, "issues": []},
            "plot_consistency": {"score": 0, "issues": []},
            "world_consistency": {"score": 0, "issues": []},
            "tone_consistency": {"score": 0, "issues": []},
            "style_consistency": {"score": 0, "issues": []}
        }
        
        # 检查人物一致性
        character_check = self._check_character_consistency(content, novel_data)
        consistency_check["character_consistency"] = character_check
        
        # 检查情节一致性
        plot_check = self._check_plot_consistency(content, novel_data)
        consistency_check["plot_consistency"] = plot_check
        
        # 检查世界观一致性
        world_check = self._check_world_consistency(content, novel_data)
        consistency_check["world_consistency"] = world_check
        
        # 检查语调一致性
        tone_check = self._check_tone_consistency(content, novel_data)
        consistency_check["tone_consistency"] = tone_check
        
        # 检查风格一致性
        style_check = self._check_style_consistency(content, novel_data)
        consistency_check["style_consistency"] = style_check
        
        # 计算总体得分
        scores = [
            character_check["score"],
            plot_check["score"],
            world_check["score"],
            tone_check["score"],
            style_check["score"]
        ]
        consistency_check["overall_score"] = sum(scores) / len(scores)
        
        return consistency_check
    
    def _check_character_consistency(self, content: Dict[str, Any], novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查人物一致性"""
        check = {"score": 80, "issues": []}
        
        # 检查主角姓名是否一致
        characters = novel_data.get("characters", {})
        if "basic_info" in characters:
            main_char_name = characters["basic_info"].get("name", "")
            content_text = content.get("content", "")
            
            if main_char_name and main_char_name not in content_text:
                check["score"] -= 20
                check["issues"].append(f"主角姓名{main_char_name}未在续写中出现")
        
        return check
    
    def _check_plot_consistency(self, content: Dict[str, Any], novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查情节一致性"""
        check = {"score": 75, "issues": []}
        
        # 检查是否有情节推进
        key_events = content.get("key_events", [])
        if key_events:
            check["score"] += 15
        else:
            check["issues"].append("缺少关键事件")
        
        # 检查是否有伏笔
        foreshadowing = content.get("foreshadowing", [])
        if foreshadowing:
            check["score"] += 10
        else:
            check["issues"].append("缺少伏笔设置")
        
        return check
    
    def _check_world_consistency(self, content: Dict[str, Any], novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查世界观一致性"""
        check = {"score": 70, "issues": []}
        
        # 检查是否与现有世界观冲突
        storyline = novel_data.get("storyline", {})
        if "world_setting" in storyline:
            check["score"] += 20
        else:
            check["issues"].append("世界观设定不明确")
        
        return check
    
    def _check_tone_consistency(self, content: Dict[str, Any], novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查语调一致性"""
        check = {"score": 80, "issues": []}
        
        # 简单检查：确保内容不为空
        content_text = content.get("content", "")
        if content_text and len(content_text) > 100:
            check["score"] += 10
        else:
            check["issues"].append("内容过短或为空")
        
        return check
    
    def _check_style_consistency(self, content: Dict[str, Any], novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查风格一致性"""
        check = {"score": 75, "issues": []}
        
        # 检查是否有标题
        if content.get("title"):
            check["score"] += 15
        else:
            check["issues"].append("缺少章节标题")
        
        # 检查是否有摘要
        if content.get("summary"):
            check["score"] += 10
        else:
            check["issues"].append("缺少章节摘要")
        
        return check
    
    def _optimize_content(self, content: Dict[str, Any], consistency_check: Dict[str, Any]) -> Dict[str, Any]:
        """优化内容"""
        optimized = content.copy()
        
        # 根据连贯性检查结果进行优化
        overall_score = consistency_check.get("overall_score", 0)
        
        if overall_score < 70:
            # 如果连贯性得分较低，添加一些改进
            if not optimized.get("summary"):
                optimized["summary"] = "本章继续推进故事情节，展现人物发展。"
            
            if not optimized.get("key_events"):
                optimized["key_events"] = ["情节推进", "人物发展"]
            
            if not optimized.get("foreshadowing"):
                optimized["foreshadowing"] = ["为后续情节做铺垫"]
        
        # 确保内容完整性
        if not optimized.get("content"):
            optimized["content"] = "续写内容生成中，请稍后查看。"
        
        if not optimized.get("title"):
            optimized["title"] = "续写章节"
        
        return optimized
    
    def _generate_chapter_info(self, content: Dict[str, Any], analysis_result: Dict[str, Any], 
                              continuation_mode: str) -> Dict[str, Any]:
        """生成章节信息"""
        key_info = analysis_result.get("key_information", {})
        total_chapters = key_info.get("total_chapters", 0)
        
        chapter_info = {
            "chapter_number": total_chapters + 1,
            "title": content.get("title", f"第{total_chapters + 1}章"),
            "summary": content.get("summary", "章节摘要"),
            "word_count": self._count_words(content.get("content", "")),
            "continuation_mode": continuation_mode,
            "created_at": datetime.now().isoformat(),
            "key_events": content.get("key_events", []),
            "foreshadowing": content.get("foreshadowing", []),
            "character_development": content.get("character_development", ""),
            "plot_advancement": content.get("plot_advancement", "")
        }
        
        return chapter_info
    
    def _count_words(self, text: str) -> int:
        """统计字数"""
        if not text:
            return 0
        return len(text.replace(' ', '').replace('\n', ''))

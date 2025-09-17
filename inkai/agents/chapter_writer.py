# 增强版章节写作智能体
# 基于写作理论和技巧的内容生成

import random
from datetime import datetime
from typing import Dict, List, Any, Optional

from ..core.base_agent import EnhancedBaseAgent
from ..utils.text_processor import TextProcessor


class EnhancedChapterWriterAgent(EnhancedBaseAgent):
    """增强版章节写作智能体 - 基于写作理论和技巧的内容生成"""
    
    def __init__(self):
        super().__init__("增强章节写作智能体")
        
        # 写作技巧库
        self.writing_techniques = {
            "开头技巧": [
                "动作开头", "对话开头", "场景描写开头", "内心独白开头", "悬念开头"
            ],
            "情节推进": [
                "冲突升级", "转折点设置", "伏笔埋设", "悬念营造", "节奏控制"
            ],
            "人物塑造": [
                "对话展现性格", "行为体现内心", "细节描写", "对比手法", "成长轨迹"
            ],
            "环境描写": [
                "氛围营造", "感官描写", "象征手法", "对比烘托", "动态描写"
            ],
            "结尾技巧": [
                "悬念结尾", "情感高潮", "转折结尾", "呼应开头", "开放式结尾"
            ]
        }
        
        # 文风模板
        self.writing_styles = {
            "轻松愉快": {
                "特点": "语言幽默、节奏明快、对话生动",
                "技巧": ["幽默对话", "轻松氛围", "明快节奏", "生动描写"]
            },
            "严肃深刻": {
                "特点": "语言庄重、思想深刻、描写细腻",
                "技巧": ["深度思考", "细腻描写", "庄重语言", "哲学思辨"]
            },
            "热血激昂": {
                "特点": "情感强烈、节奏紧凑、气势磅礴",
                "技巧": ["情感渲染", "节奏紧凑", "气势描写", "激情对话"]
            },
            "温馨治愈": {
                "特点": "语言温暖、情感细腻、氛围温馨",
                "技巧": ["温暖描写", "细腻情感", "温馨氛围", "治愈元素"]
            }
        }
        
        self._log("增强版章节写作智能体初始化完成", "INFO")
    
    def write_chapter(self, storyline: Dict[str, Any], characters: Dict[str, Any], chapter_info: Dict[str, Any]) -> Dict[str, Any]:
        """写作增强版章节"""
        self._log(f"开始写作章节: {chapter_info.get('chapter_title', '未知章节')}", "INFO")
        
        # 构建增强的提示词
        prompt = self._build_chapter_prompt(storyline, characters, chapter_info)
        
        messages = [
            {
                "role": "system", 
                "content": "你是一个专业的小说作家，精通各种写作技巧和文学手法。你能够创作引人入胜、结构完整、文笔优美的章节内容。"
            },
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        # 增强和优化章节内容
        enhanced_chapter = self._enhance_chapter_content(result, storyline, characters, chapter_info)
        
        # 添加写作分析
        enhanced_chapter = self._add_writing_analysis(enhanced_chapter)
        
        # 添加改进建议
        enhanced_chapter = self._add_improvement_suggestions(enhanced_chapter)
        
        self._log("章节写作完成", "INFO")
        return enhanced_chapter
    
    def _build_chapter_prompt(self, storyline: Dict[str, Any], characters: Dict[str, Any], chapter_info: Dict[str, Any]) -> str:
        """构建章节写作提示词"""
        # 分析写作风格
        writing_style = self._analyze_writing_style(storyline)
        
        # 推荐写作技巧
        recommended_techniques = self._recommend_writing_techniques(chapter_info)
        
        # 确定章节结构
        chapter_structure = self._determine_chapter_structure(chapter_info)
        
        # 字数要求
        word_requirements = self._get_word_requirements(chapter_info)
        
        prompt = f"""
        请根据以下信息写作一个高质量的小说章节：
        
        故事线信息：{storyline.get('world_setting', {})}
        人物信息：{characters.get('basic_info', {})}
        章节信息：{chapter_info}
        
        写作风格：{writing_style}
        推荐技巧：{recommended_techniques}
        章节结构：{chapter_structure}
        字数要求：{word_requirements}
        
        写作要求：
        1. 保持人物性格一致性
        2. 推进故事情节发展
        3. 运用适当的写作技巧
        4. 控制章节节奏和字数
        5. 设置适当的悬念和伏笔
        6. 保持文风的一致性
        
        请返回JSON格式：
        {{
            "title": "章节标题",
            "content": "章节正文内容",
            "summary": "章节概要",
            "key_events": ["关键事件1", "关键事件2"],
            "character_development": "人物发展描述",
            "foreshadowing": ["伏笔1", "伏笔2"],
            "next_chapter_hint": "下章预告",
            "writing_techniques_used": ["使用的写作技巧"],
            "emotional_tone": "情感基调",
            "pacing": "节奏描述"
        }}
        """
        return prompt
    
    def _analyze_writing_style(self, storyline: Dict[str, Any]) -> str:
        """分析写作风格"""
        tone = storyline.get("tone", "")
        
        if "轻松" in tone or "愉快" in tone:
            return "轻松愉快"
        elif "严肃" in tone or "深刻" in tone:
            return "严肃深刻"
        elif "热血" in tone or "激昂" in tone:
            return "热血激昂"
        elif "温馨" in tone or "治愈" in tone:
            return "温馨治愈"
        else:
            return "轻松愉快"  # 默认风格
    
    def _recommend_writing_techniques(self, chapter_info: Dict[str, Any]) -> List[str]:
        """推荐写作技巧"""
        techniques = []
        
        # 根据章节类型推荐技巧
        chapter_type = chapter_info.get("chapter_type", "标准")
        
        if chapter_type == "对话":
            techniques.extend(["对话展现性格", "对话推进情节"])
        elif chapter_type == "动作":
            techniques.extend(["动作描写", "节奏控制"])
        elif chapter_type == "情感":
            techniques.extend(["情感渲染", "内心独白"])
        else:
            techniques.extend(["情节推进", "人物塑造"])
        
        return techniques
    
    def _determine_chapter_structure(self, chapter_info: Dict[str, Any]) -> str:
        """确定章节结构"""
        chapter_type = chapter_info.get("chapter_type", "标准")
        
        if chapter_type == "对话":
            return "对话为主"
        elif chapter_type == "动作":
            return "动作为主"
        else:
            return "标准结构"
    
    def _get_word_requirements(self, chapter_info: Dict[str, Any]) -> Dict[str, int]:
        """获取字数要求"""
        chapter_type = chapter_info.get("chapter_type", "标准")
        
        word_count_standards = {
            "短章节": {"min": 1500, "max": 2500, "ideal": 2000},
            "标准章节": {"min": 2500, "max": 4000, "ideal": 3000},
            "长章节": {"min": 4000, "max": 6000, "ideal": 5000}
        }
        
        if chapter_type == "短章节":
            return word_count_standards["短章节"]
        elif chapter_type == "长章节":
            return word_count_standards["长章节"]
        else:
            return word_count_standards["标准章节"]
    
    def _enhance_chapter_content(self, result: Dict[str, Any], storyline: Dict[str, Any], 
                                characters: Dict[str, Any], chapter_info: Dict[str, Any]) -> Dict[str, Any]:
        """增强章节内容"""
        enhanced = result.copy()
        
        # 确保基本结构完整
        if "title" not in enhanced:
            enhanced["title"] = chapter_info.get("chapter_title", "未命名章节")
        
        if "content" not in enhanced:
            enhanced["content"] = "章节内容生成失败，请检查配置。"
        
        # 添加章节元数据
        enhanced["chapter_metadata"] = {
            "created_at": datetime.now().isoformat(),
            "chapter_number": chapter_info.get("chapter_number", 1),
            "chapter_type": chapter_info.get("chapter_type", "标准"),
            "word_count": TextProcessor.count_words(enhanced.get("content", "")),
            "writing_style": self._analyze_writing_style(storyline),
            "structure_type": self._determine_chapter_structure(chapter_info)
        }
        
        return enhanced
    
    def _add_writing_analysis(self, chapter: Dict[str, Any]) -> Dict[str, Any]:
        """添加写作分析"""
        content = chapter.get("content", "")
        
        analysis = {
            "word_count": TextProcessor.count_words(content),
            "readability_score": TextProcessor.calculate_readability_score(content),
            "dialogue_ratio": self._calculate_dialogue_ratio(content),
            "emotional_intensity": self._assess_emotional_intensity(content),
            "pacing_analysis": self._analyze_pacing(content)
        }
        
        chapter["writing_analysis"] = analysis
        return chapter
    
    def _calculate_dialogue_ratio(self, content: str) -> float:
        """计算对话比例"""
        if not content:
            return 0.0
        
        # 简单的对话识别（引号内容）
        import re
        dialogue_pattern = r'"[^"]*"'
        dialogue_matches = re.findall(dialogue_pattern, content)
        dialogue_length = sum(len(match) for match in dialogue_matches)
        
        return (dialogue_length / len(content)) * 100 if content else 0.0
    
    def _assess_emotional_intensity(self, content: str) -> str:
        """评估情感强度"""
        if not content:
            return "未知"
        
        # 情感词汇识别
        emotional_words = {
            "高": ["愤怒", "狂喜", "绝望", "兴奋", "恐惧"],
            "中": ["高兴", "难过", "紧张", "担心", "期待"],
            "低": ["平静", "淡然", "轻松", "舒适", "满足"]
        }
        
        intensity_scores = {"高": 0, "中": 0, "低": 0}
        
        for intensity, words in emotional_words.items():
            for word in words:
                intensity_scores[intensity] += content.count(word)
        
        max_intensity = max(intensity_scores, key=intensity_scores.get)
        return max_intensity if intensity_scores[max_intensity] > 0 else "低"
    
    def _analyze_pacing(self, content: str) -> str:
        """分析节奏"""
        if not content:
            return "未知"
        
        # 基于标点符号分析节奏
        fast_punctuation = ["！", "？"]
        slow_punctuation = ["。", "，", "；"]
        
        fast_count = sum(content.count(p) for p in fast_punctuation)
        slow_count = sum(content.count(p) for p in slow_punctuation)
        
        if fast_count > slow_count * 0.3:
            return "快节奏"
        elif slow_count > fast_count * 2:
            return "慢节奏"
        else:
            return "中等节奏"
    
    def _add_improvement_suggestions(self, chapter: Dict[str, Any]) -> Dict[str, Any]:
        """添加改进建议"""
        suggestions = []
        analysis = chapter.get("writing_analysis", {})
        
        # 基于字数建议
        word_count = analysis.get("word_count", 0)
        if word_count < 2000:
            suggestions.append("建议增加内容，丰富情节发展")
        elif word_count > 5000:
            suggestions.append("建议精简内容，提高阅读体验")
        
        # 基于对话比例建议
        dialogue_ratio = analysis.get("dialogue_ratio", 0)
        if dialogue_ratio < 20:
            suggestions.append("建议增加对话，增强人物互动")
        elif dialogue_ratio > 60:
            suggestions.append("建议增加描写，丰富场景细节")
        
        # 基于可读性建议
        readability = analysis.get("readability_score", 0)
        if readability < 60:
            suggestions.append("建议简化句式，提高可读性")
        
        chapter["improvement_suggestions"] = suggestions
        return chapter
    
    def improve_chapter(self, chapter: Dict[str, Any], improvement_focus: str = "全面优化") -> Dict[str, Any]:
        """改进章节内容"""
        self._log(f"开始改进章节: {improvement_focus}", "INFO")
        
        # 分析当前章节问题
        current_analysis = chapter.get("writing_analysis", {})
        current_suggestions = chapter.get("improvement_suggestions", [])
        
        # 构建改进提示词
        prompt = self._build_improvement_prompt(chapter, improvement_focus, current_analysis, current_suggestions)
        
        messages = [
            {
                "role": "system", 
                "content": "你是一个专业的编辑和写作指导，擅长改进和优化小说内容。你能够识别问题并提供具体的改进方案。"
            },
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        # 应用改进
        improved_chapter = self._apply_improvements(chapter, result, improvement_focus)
        
        # 重新分析改进后的内容
        improved_chapter = self._add_writing_analysis(improved_chapter)
        improved_chapter = self._add_improvement_suggestions(improved_chapter)
        
        # 添加改进记录
        improved_chapter["improvement_history"] = improved_chapter.get("improvement_history", [])
        improved_chapter["improvement_history"].append({
            "timestamp": datetime.now().isoformat(),
            "focus": improvement_focus,
            "changes_made": result.get("changes_made", []),
            "improvement_score": result.get("improvement_score", 0)
        })
        
        self._log("章节改进完成", "INFO")
        return improved_chapter
    
    def _build_improvement_prompt(self, chapter: Dict[str, Any], focus: str, analysis: Dict[str, Any], suggestions: List[str]) -> str:
        """构建改进提示词"""
        prompt = f"""
        请根据以下信息改进章节内容：
        
        当前章节：{chapter.get('title', '未知章节')}
        章节内容：{chapter.get('content', '')[:500]}...
        改进重点：{focus}
        
        当前分析：
        - 字数：{analysis.get('word_count', 0)}
        - 可读性：{analysis.get('readability_score', 0)}
        - 对话比例：{analysis.get('dialogue_ratio', 0):.1f}%
        - 情感强度：{analysis.get('emotional_intensity', '未知')}
        - 节奏：{analysis.get('pacing_analysis', '未知')}
        
        改进建议：{suggestions}
        
        请返回JSON格式：
        {{
            "improved_content": "改进后的章节内容",
            "changes_made": ["具体改进项目"],
            "improvement_score": 改进得分(0-100),
            "explanation": "改进说明"
        }}
        """
        return prompt
    
    def _apply_improvements(self, original_chapter: Dict[str, Any], improvements: Dict[str, Any], focus: str) -> Dict[str, Any]:
        """应用改进"""
        improved = original_chapter.copy()
        
        # 应用改进后的内容
        if "improved_content" in improvements:
            improved["content"] = improvements["improved_content"]
        
        # 更新改进信息
        improved["last_improvement"] = {
            "timestamp": datetime.now().isoformat(),
            "focus": focus,
            "score": improvements.get("improvement_score", 0),
            "changes": improvements.get("changes_made", [])
        }
        
        return improved

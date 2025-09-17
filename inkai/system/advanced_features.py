# 高级功能模块
# 包含创意增强工具、知识库集成、智能分析、个性化推荐、性能优化

import json
import random
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import hashlib

from ..core.base_agent import EnhancedBaseAgent


class CreativeEnhancementTools(EnhancedBaseAgent):
    """创意增强工具集"""
    
    def __init__(self):
        super().__init__("创意增强工具")
        
        # 创意激发库
        self.creativity_triggers = {
            "情节转折": [
                "突然的发现", "意外的相遇", "隐藏的真相", "命运的转折",
                "背叛与救赎", "失而复得", "绝处逢生", "峰回路转"
            ],
            "情感冲突": [
                "爱与恨的交织", "忠诚与背叛", "理想与现实", "过去与未来",
                "自由与责任", "个人与集体", "理性与感性", "传统与创新"
            ],
            "环境变化": [
                "季节更替", "城市变迁", "科技发展", "社会变革",
                "自然灾害", "战争爆发", "和平降临", "文化碰撞"
            ],
            "人物成长": [
                "技能突破", "认知觉醒", "情感成熟", "价值观转变",
                "关系修复", "自我接纳", "目标重设", "使命发现"
            ]
        }
        
        self._log("创意增强工具初始化完成", "INFO")
    
    def generate_plot_twist(self, current_story: str, character_info: Dict[str, Any]) -> Dict[str, Any]:
        """生成情节转折"""
        self._log("生成情节转折", "INFO")
        
        # 分析当前故事状态
        story_analysis = self._analyze_story_state(current_story)
        
        # 选择合适的转折类型
        twist_type = self._select_twist_type(story_analysis, character_info)
        
        # 生成转折内容
        twist_content = self._generate_twist_content(twist_type, story_analysis, character_info)
        
        return {
            "twist_type": twist_type,
            "content": twist_content,
            "impact_analysis": self._analyze_twist_impact(twist_content, story_analysis),
            "implementation_suggestions": self._get_implementation_suggestions(twist_type)
        }
    
    def enhance_emotional_depth(self, content: str, target_emotion: str) -> Dict[str, Any]:
        """增强情感深度"""
        self._log(f"增强情感深度: {target_emotion}", "INFO")
        
        # 分析当前情感表达
        current_emotion = self._analyze_emotion(content)
        
        # 选择增强技巧
        enhancement_techniques = self._select_emotion_techniques(target_emotion, current_emotion)
        
        # 生成增强建议
        enhancement_suggestions = self._generate_emotion_enhancements(content, enhancement_techniques)
        
        return {
            "current_emotion": current_emotion,
            "target_emotion": target_emotion,
            "enhancement_techniques": enhancement_techniques,
            "suggestions": enhancement_suggestions,
            "enhanced_content": self._apply_enhancements(content, enhancement_suggestions)
        }
    
    def _analyze_story_state(self, story: str) -> Dict[str, Any]:
        """分析故事状态"""
        return {
            "length": len(story),
            "tension_level": self._calculate_tension_level(story),
            "character_count": len(re.findall(r'[A-Za-z\u4e00-\u9fff]+', story)),
            "dialogue_ratio": len(re.findall(r'"[^"]*"', story)) / max(len(story.split()), 1),
            "emotion_keywords": self._extract_emotion_keywords(story)
        }
    
    def _calculate_tension_level(self, story: str) -> float:
        """计算紧张程度"""
        tension_words = ["冲突", "危险", "紧张", "恐惧", "担心", "焦虑"]
        tension_count = sum(story.count(word) for word in tension_words)
        return min(1.0, tension_count / max(len(story.split()), 1) * 100)
    
    def _extract_emotion_keywords(self, story: str) -> List[str]:
        """提取情感关键词"""
        emotion_words = ["高兴", "悲伤", "愤怒", "恐惧", "惊讶", "厌恶", "期待"]
        found_emotions = []
        for emotion in emotion_words:
            if emotion in story:
                found_emotions.append(emotion)
        return found_emotions
    
    def _select_twist_type(self, story_analysis: Dict[str, Any], character_info: Dict[str, Any]) -> str:
        """选择转折类型"""
        tension = story_analysis["tension_level"]
        
        if tension < 0.3:
            return random.choice(["突然的发现", "意外的相遇"])
        elif tension < 0.6:
            return random.choice(["隐藏的真相", "命运的转折"])
        else:
            return random.choice(["背叛与救赎", "绝处逢生"])
    
    def _generate_twist_content(self, twist_type: str, story_analysis: Dict[str, Any], character_info: Dict[str, Any]) -> str:
        """生成转折内容"""
        prompt = f"""
        基于以下信息生成一个"{twist_type}"类型的情节转折：
        
        故事分析：{story_analysis}
        人物信息：{character_info}
        
        要求：
        1. 转折要合理且出人意料
        2. 符合人物性格和故事逻辑
        3. 能够推动情节发展
        4. 保持故事的连贯性
        
        请生成具体的情节转折描述。
        """
        
        messages = [
            {"role": "system", "content": "你是一个专业的故事创作专家，擅长设计巧妙的情节转折。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        return response
    
    def _analyze_twist_impact(self, twist_content: str, story_analysis: Dict[str, Any]) -> str:
        """分析转折影响"""
        return "这个转折将显著改变故事走向，增加读者的阅读兴趣。"
    
    def _get_implementation_suggestions(self, twist_type: str) -> List[str]:
        """获取实施建议"""
        suggestions = {
            "突然的发现": ["在关键时刻揭示", "通过细节暗示", "用对话引出"],
            "意外的相遇": ["创造偶然机会", "利用环境因素", "通过第三方介绍"],
            "隐藏的真相": ["逐步揭示", "通过回忆展现", "借助证据呈现"]
        }
        return suggestions.get(twist_type, ["根据情节需要灵活安排"])
    
    def _analyze_emotion(self, content: str) -> str:
        """分析当前情感"""
        emotions = self._extract_emotion_keywords(content)
        if emotions:
            return emotions[0]  # 返回第一个检测到的情感
        return "平静"
    
    def _select_emotion_techniques(self, target_emotion: str, current_emotion: str) -> List[str]:
        """选择情感增强技巧"""
        techniques = {
            "深度": ["细节描写", "内心独白", "环境烘托"],
            "激动": ["动作描写", "快节奏", "强烈对比"],
            "温暖": ["温馨场景", "细腻情感", "正面描写"]
        }
        return techniques.get(target_emotion, ["情感渲染", "氛围营造"])
    
    def _generate_emotion_enhancements(self, content: str, techniques: List[str]) -> List[str]:
        """生成情感增强建议"""
        suggestions = []
        for technique in techniques:
            if technique == "细节描写":
                suggestions.append("增加更多感官细节，让读者身临其境")
            elif technique == "内心独白":
                suggestions.append("添加人物内心想法，展现情感变化")
            elif technique == "环境烘托":
                suggestions.append("利用环境描写烘托情感氛围")
        return suggestions
    
    def _apply_enhancements(self, content: str, suggestions: List[str]) -> str:
        """应用增强建议"""
        # 这里可以实现具体的内容增强逻辑
        # 目前返回原内容加上增强说明
        enhanced = content + "\n\n[增强建议已应用]"
        return enhanced


class KnowledgeBaseIntegration(EnhancedBaseAgent):
    """知识库集成系统"""
    
    def __init__(self):
        super().__init__("知识库集成系统")
        
        # 知识库结构
        self.knowledge_bases = {
            "literary_theory": {
                "name": "文学理论库",
                "topics": ["叙事结构", "人物塑造", "主题表达", "语言技巧"],
                "sources": ["经典文学", "文学批评", "创作理论"]
            },
            "cultural_reference": {
                "name": "文化参考库", 
                "topics": ["历史事件", "文化传统", "社会现象", "时代背景"],
                "sources": ["历史资料", "文化研究", "社会观察"]
            },
            "technical_knowledge": {
                "name": "专业知识库",
                "topics": ["科学技术", "职业知识", "专业技能", "行业背景"],
                "sources": ["技术文档", "专业书籍", "行业报告"]
            }
        }
        
        # 知识检索缓存
        self.knowledge_cache = {}
        
        self._log("知识库集成系统初始化完成", "INFO")
    
    def search_knowledge(self, query: str, knowledge_type: str = "all") -> Dict[str, Any]:
        """搜索知识库"""
        self._log(f"搜索知识库: {query}", "INFO")
        
        # 检查缓存
        cache_key = hashlib.md5(f"{query}_{knowledge_type}".encode()).hexdigest()
        if cache_key in self.knowledge_cache:
            return self.knowledge_cache[cache_key]
        
        # 确定搜索范围
        search_bases = []
        if knowledge_type == "all":
            search_bases = list(self.knowledge_bases.keys())
        elif knowledge_type in self.knowledge_bases:
            search_bases = [knowledge_type]
        
        # 执行搜索
        results = {}
        for base_name in search_bases:
            base_results = self._search_single_base(query, base_name)
            if base_results:
                results[base_name] = base_results
        
        # 缓存结果
        self.knowledge_cache[cache_key] = results
        
        return results
    
    def get_writing_advice(self, content_type: str, specific_need: str) -> Dict[str, Any]:
        """获取写作建议"""
        self._log(f"获取写作建议: {content_type} - {specific_need}", "INFO")
        
        # 构建查询
        query = f"{content_type} {specific_need} 写作技巧"
        
        # 搜索相关知识
        knowledge_results = self.search_knowledge(query, "literary_theory")
        
        # 生成具体建议
        advice = self._generate_writing_advice(content_type, specific_need, knowledge_results)
        
        return {
            "content_type": content_type,
            "specific_need": specific_need,
            "knowledge_sources": knowledge_results,
            "advice": advice,
            "examples": self._get_advice_examples(content_type, specific_need)
        }
    
    def _search_single_base(self, query: str, base_name: str) -> Dict[str, Any]:
        """搜索单个知识库"""
        base_info = self.knowledge_bases[base_name]
        
        prompt = f"""
        在{base_info['name']}中搜索与"{query}"相关的信息：
        
        知识库主题：{base_info['topics']}
        信息来源：{base_info['sources']}
        
        请提供相关的知识点、理论、技巧或参考信息。
        """
        
        messages = [
            {"role": "system", "content": f"你是{base_info['name']}的专家，能够提供准确的知识信息。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        
        return {
            "base_name": base_name,
            "query": query,
            "results": response,
            "relevance_score": self._calculate_relevance(query, response)
        }
    
    def _calculate_relevance(self, query: str, response: str) -> float:
        """计算相关性得分"""
        query_words = set(query.split())
        response_words = set(response.split())
        
        if not query_words:
            return 0.0
        
        # 计算交集比例
        intersection = query_words.intersection(response_words)
        return len(intersection) / len(query_words)
    
    def _generate_writing_advice(self, content_type: str, specific_need: str, knowledge_results: Dict[str, Any]) -> List[str]:
        """生成写作建议"""
        advice = []
        
        # 基于内容类型生成通用建议
        if content_type == "人物描写":
            advice.extend([
                "通过细节描写展现人物性格",
                "使用对话体现人物特点",
                "结合环境描写烘托人物心境"
            ])
        elif content_type == "情节发展":
            advice.extend([
                "保持情节的逻辑性和连贯性",
                "合理设置冲突和转折点",
                "控制节奏，张弛有度"
            ])
        
        # 基于具体需求添加针对性建议
        if "情感" in specific_need:
            advice.append("运用感官描写增强情感表达")
        if "悬念" in specific_need:
            advice.append("适当保留信息，制造悬念")
        
        return advice
    
    def _get_advice_examples(self, content_type: str, specific_need: str) -> List[str]:
        """获取建议示例"""
        examples = {
            "人物描写": ["他的眼中闪过一丝不易察觉的失望", "她紧握双拳，指甲深深陷入掌心"],
            "情节发展": ["就在这时，门外传来了急促的脚步声", "一个意想不到的电话改变了一切"]
        }
        return examples.get(content_type, ["根据具体情况灵活运用"])


class AdvancedFeaturesManager:
    """高级功能管理器"""
    
    def __init__(self):
        self.creative_tools = CreativeEnhancementTools()
        self.knowledge_base = KnowledgeBaseIntegration()
        
        print("高级功能管理器初始化完成")
    
    def get_creative_suggestions(self, content: str, user_preferences: Dict[str, Any] = None) -> Dict[str, Any]:
        """获取创意建议"""
        suggestions = {
            "plot_twists": self.creative_tools.generate_plot_twist(content, user_preferences or {}),
            "emotion_enhancement": self.creative_tools.enhance_emotional_depth(content, "深度"),
            "writing_advice": self.knowledge_base.get_writing_advice("情节发展", "增强吸引力")
        }
        
        return suggestions
    
    def comprehensive_content_analysis(self, content: str) -> Dict[str, Any]:
        """综合内容分析"""
        analysis = {
            "knowledge_insights": self.knowledge_base.search_knowledge(content[:100]),
            "creative_suggestions": self.get_creative_suggestions(content)
        }
        
        return analysis

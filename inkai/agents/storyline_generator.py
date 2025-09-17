# 增强版故事线生成智能体
# 基于经典叙事理论的故事构建

import random
from datetime import datetime
from typing import Dict, List, Any, Optional

from ..core.base_agent import EnhancedBaseAgent


class EnhancedStorylineGeneratorAgent(EnhancedBaseAgent):
    """增强版故事线生成智能体 - 基于经典叙事理论的故事构建"""
    
    def __init__(self):
        super().__init__("增强故事线生成智能体")
        
        # 三幕剧结构模板
        self.three_act_structure = {
            "第一幕": {
                "占比": "25%",
                "功能": "建立世界、介绍人物、设置冲突",
                "关键要素": ["开场钩子", "人物介绍", "世界观建立", "冲突引入", "第一转折点"]
            },
            "第二幕": {
                "占比": "50%",
                "功能": "发展冲突、人物成长、情节推进",
                "关键要素": ["冲突升级", "人物考验", "次要情节", "中点转折", "危机时刻"]
            },
            "第三幕": {
                "占比": "25%",
                "功能": "高潮对决、冲突解决、故事收尾",
                "关键要素": ["最终对决", "冲突解决", "人物成长体现", "伏笔回收", "结局"]
            }
        }
        
        # 情节曲线模板
        self.plot_curves = {
            "英雄之旅": {
                "阶段": ["平凡世界", "冒险召唤", "拒绝召唤", "导师出现", "跨越门槛", "考验盟友敌人", "接近洞穴", "磨难", "奖赏", "回归之路", "复活", "回归"]
            },
            "三幕结构": {
                "阶段": ["建立", "对抗", "解决"]
            },
            "五幕结构": {
                "阶段": ["开端", "发展", "高潮", "回落", "结局"]
            }
        }
        
        # 冲突类型
        self.conflict_types = {
            "人与自我": "内心冲突、道德选择、自我认知",
            "人与人": "人际关系、竞争、背叛、误解",
            "人与社会": "社会制度、文化冲突、群体压力",
            "人与自然": "生存挑战、自然灾害、环境威胁",
            "人与命运": "宿命对抗、时间限制、不可抗力",
            "人与技术": "科技威胁、AI冲突、技术失控"
        }
        
        self._log("增强版故事线生成智能体初始化完成", "INFO")
    
    def generate_storyline(self, tags: Dict[str, List[str]], characters: Dict[str, Any], requirements: str) -> Dict[str, Any]:
        """生成增强版故事线"""
        self._log("开始生成故事线", "INFO")
        
        # 构建增强的提示词
        prompt = self._build_storyline_prompt(tags, characters, requirements)
        
        messages = [
            {
                "role": "system", 
                "content": "你是一个专业的故事设计师，精通叙事理论、情节构建和故事结构。你能够创造引人入胜、结构完整的故事线。"
            },
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        # 增强和验证故事线数据
        enhanced_storyline = self._enhance_storyline_data(result, tags, characters)
        
        # 添加结构分析
        enhanced_storyline = self._add_structure_analysis(enhanced_storyline)
        
        # 添加伏笔管理
        enhanced_storyline = self._add_foreshadowing_system(enhanced_storyline)
        
        # 添加节奏控制
        enhanced_storyline = self._add_pacing_control(enhanced_storyline)
        
        self._log("故事线生成完成", "INFO")
        return enhanced_storyline
    
    def _build_storyline_prompt(self, tags: Dict[str, List[str]], characters: Dict[str, Any], requirements: str) -> str:
        """构建故事线生成提示词"""
        # 分析故事类型
        story_type = self._analyze_story_type(tags)
        
        # 推荐冲突类型
        recommended_conflicts = self._recommend_conflicts(tags, characters)
        
        # 推荐情节结构
        recommended_structure = self._recommend_structure(tags)
        
        prompt = f"""
        请根据以下信息生成一个完整、引人入胜的故事线：
        
        标签信息：{tags}
        人物信息：{characters.get('basic_info', {})}
        用户需求：{requirements}
        
        故事类型分析：{story_type}
        推荐冲突类型：{recommended_conflicts}
        推荐结构：{recommended_structure}
        
        故事设计原则：
        1. 采用三幕剧结构，确保节奏合理
        2. 设置多层次冲突，增加故事张力
        3. 设计人物成长弧线，体现主题
        4. 埋下伏笔，增强故事连贯性
        5. 构建完整世界观，增强可信度
        6. 设置转折点，保持读者兴趣
        
        请返回JSON格式：
        {{
            "world_setting": {{
                "physical_world": "物理世界描述",
                "social_structure": "社会结构描述",
                "cultural_background": "文化背景描述",
                "special_rules": "特殊规则或设定"
            }},
            "main_conflict": {{
                "type": "冲突类型",
                "description": "冲突描述",
                "stakes": "冲突的赌注和后果",
                "resolution_approach": "解决冲突的方法"
            }},
            "three_act_structure": {{
                "act1": {{
                    "setup": "第一幕设定",
                    "key_events": ["关键事件1", "关键事件2"],
                    "turning_point": "第一转折点",
                    "character_introduction": "人物介绍"
                }},
                "act2": {{
                    "confrontation": "第二幕对抗",
                    "rising_action": ["上升行动1", "上升行动2"],
                    "midpoint_crisis": "中点危机",
                    "character_development": "人物发展"
                }},
                "act3": {{
                    "climax": "高潮对决",
                    "resolution": "冲突解决",
                    "denouement": "结局收尾",
                    "character_growth": "人物成长体现"
                }}
            }},
            "themes": ["主题1", "主题2"],
            "tone": "故事基调和氛围",
            "target_audience": "目标受众",
            "commercial_potential": "商业潜力评估"
        }}
        """
        return prompt
    
    def _analyze_story_type(self, tags: Dict[str, List[str]]) -> str:
        """分析故事类型"""
        type_tags = tags.get("recommended_tags", {}).get("类型标签", [])
        theme_tags = tags.get("recommended_tags", {}).get("主题标签", [])
        
        if "都市" in type_tags:
            if "系统" in theme_tags:
                return "都市系统流爽文"
            elif "商战" in type_tags:
                return "都市商战文"
            else:
                return "都市现实文"
        elif "玄幻" in type_tags or "修仙" in type_tags:
            return "玄幻修仙文"
        elif "历史" in type_tags:
            return "历史架空文"
        elif "科幻" in type_tags:
            return "科幻未来文"
        elif "悬疑" in type_tags:
            return "悬疑推理文"
        else:
            return "综合类型文"
    
    def _recommend_conflicts(self, tags: Dict[str, List[str]], characters: Dict[str, Any]) -> List[str]:
        """推荐冲突类型"""
        conflicts = []
        
        type_tags = tags.get("recommended_tags", {}).get("类型标签", [])
        theme_tags = tags.get("recommended_tags", {}).get("主题标签", [])
        
        # 基于类型推荐冲突
        if "都市" in type_tags:
            conflicts.extend(["人与自我", "人与人", "人与社会"])
        elif "玄幻" in type_tags:
            conflicts.extend(["人与自我", "人与命运", "人与自然"])
        elif "科幻" in type_tags:
            conflicts.extend(["人与技术", "人与社会", "人与自然"])
        
        # 基于主题推荐冲突
        if "成长" in theme_tags:
            conflicts.append("人与自我")
        if "权谋" in theme_tags:
            conflicts.extend(["人与人", "人与社会"])
        if "冒险" in theme_tags:
            conflicts.extend(["人与自然", "人与命运"])
        
        # 去重并返回
        return list(set(conflicts))
    
    def _recommend_structure(self, tags: Dict[str, List[str]]) -> str:
        """推荐故事结构"""
        style_tags = tags.get("recommended_tags", {}).get("风格标签", [])
        theme_tags = tags.get("recommended_tags", {}).get("主题标签", [])
        
        if "轻松愉快" in style_tags:
            return "三幕结构（适合轻松节奏）"
        elif "严肃深刻" in style_tags:
            return "五幕结构（适合深度探讨）"
        elif "冒险" in theme_tags:
            return "英雄之旅（适合冒险故事）"
        else:
            return "三幕结构（经典结构）"
    
    def _enhance_storyline_data(self, result: Dict[str, Any], tags: Dict[str, List[str]], characters: Dict[str, Any]) -> Dict[str, Any]:
        """增强故事线数据"""
        enhanced = result.copy()
        
        # 确保基本结构完整
        if "three_act_structure" not in enhanced:
            enhanced["three_act_structure"] = self._create_default_structure()
        
        # 添加故事元数据
        enhanced["story_metadata"] = {
            "created_at": datetime.now().isoformat(),
            "story_type": self._analyze_story_type(tags),
            "estimated_length": self._estimate_story_length(tags),
            "complexity_level": self._assess_complexity(tags, characters),
            "target_chapters": self._estimate_chapter_count(tags)
        }
        
        # 添加人物在故事中的作用
        enhanced["character_roles"] = self._assign_character_roles(characters, enhanced)
        
        return enhanced
    
    def _create_default_structure(self) -> Dict[str, Any]:
        """创建默认三幕结构"""
        return {
            "act1": {
                "setup": "故事开始，建立世界观和人物关系",
                "key_events": ["开场事件", "人物介绍", "冲突引入"],
                "turning_point": "第一转折点，故事正式开始"
            },
            "act2": {
                "confrontation": "冲突发展，人物面临挑战",
                "rising_action": ["冲突升级", "人物成长", "次要情节发展"],
                "midpoint_crisis": "中点危机，故事转折"
            },
            "act3": {
                "climax": "最终对决，冲突达到顶点",
                "resolution": "冲突解决，问题得到处理",
                "denouement": "故事收尾，人物命运确定"
            }
        }
    
    def _estimate_story_length(self, tags: Dict[str, List[str]]) -> str:
        """估算故事长度"""
        type_tags = tags.get("recommended_tags", {}).get("类型标签", [])
        
        if "都市" in type_tags:
            return "中篇（20-50万字）"
        elif "玄幻" in type_tags or "修仙" in type_tags:
            return "长篇（50-200万字）"
        elif "历史" in type_tags:
            return "长篇（50-100万字）"
        else:
            return "中篇（30-80万字）"
    
    def _assess_complexity(self, tags: Dict[str, List[str]], characters: Dict[str, Any]) -> str:
        """评估故事复杂度"""
        complexity_score = 0
        
        # 基于标签评估
        type_tags = tags.get("recommended_tags", {}).get("类型标签", [])
        if len(type_tags) > 2:
            complexity_score += 1
        
        if "权谋" in tags.get("recommended_tags", {}).get("主题标签", []):
            complexity_score += 2
        
        # 基于人物数量评估
        if isinstance(characters, dict) and len(characters) > 5:
            complexity_score += 1
        
        if complexity_score >= 3:
            return "高复杂度"
        elif complexity_score >= 1:
            return "中等复杂度"
        else:
            return "低复杂度"
    
    def _estimate_chapter_count(self, tags: Dict[str, List[str]]) -> int:
        """估算章节数量"""
        type_tags = tags.get("recommended_tags", {}).get("类型标签", [])
        
        if "都市" in type_tags:
            return random.randint(50, 150)
        elif "玄幻" in type_tags or "修仙" in type_tags:
            return random.randint(200, 500)
        elif "历史" in type_tags:
            return random.randint(100, 300)
        else:
            return random.randint(80, 200)
    
    def _assign_character_roles(self, characters: Dict[str, Any], storyline: Dict[str, Any]) -> Dict[str, str]:
        """分配人物角色"""
        roles = {}
        
        # 主角角色
        if "basic_info" in characters:
            main_char_name = characters["basic_info"].get("name", "主角")
            roles[main_char_name] = "主角 - 故事的核心人物"
        
        # 基于故事线分配其他角色
        conflict = storyline.get("main_conflict", {})
        if "人与自我" in conflict.get("type", ""):
            roles["内心声音"] = "内在冲突的体现"
        
        return roles
    
    def _add_structure_analysis(self, storyline: Dict[str, Any]) -> Dict[str, Any]:
        """添加结构分析"""
        storyline["structure_analysis"] = {
            "narrative_arc": {
                "exposition": "故事背景和人物介绍",
                "rising_action": "冲突发展和情节推进",
                "climax": "故事高潮和关键转折",
                "falling_action": "冲突解决过程",
                "resolution": "故事结局和人物命运"
            },
            "plot_points": {
                "inciting_incident": "引发事件",
                "first_plot_point": "第一情节点",
                "midpoint": "中点转折",
                "second_plot_point": "第二情节点",
                "climax": "故事高潮"
            }
        }
        
        return storyline
    
    def _add_foreshadowing_system(self, storyline: Dict[str, Any]) -> Dict[str, Any]:
        """添加伏笔管理系统"""
        storyline["foreshadowing_system"] = {
            "early_foreshadowing": {
                "act1_foreshadows": [
                    {
                        "type": "预言式",
                        "content": "暗示未来重要事件",
                        "placement": "第一幕早期",
                        "payoff": "第三幕高潮"
                    }
                ]
            },
            "foreshadowing_tracking": {
                "total_foreshadows": 0,
                "resolved_foreshadows": 0,
                "pending_foreshadows": 0
            }
        }
        
        return storyline
    
    def _add_pacing_control(self, storyline: Dict[str, Any]) -> Dict[str, Any]:
        """添加节奏控制"""
        storyline["pacing_control"] = {
            "act1_pacing": {
                "speed": "快",
                "description": "快速建立世界和人物，保持读者兴趣",
                "key_moments": ["开场钩子", "人物登场", "冲突引入"]
            },
            "act2_pacing": {
                "speed": "变化",
                "description": "快慢结合，有张有弛",
                "tension_points": ["冲突升级", "人物考验", "危机时刻"]
            },
            "act3_pacing": {
                "speed": "快",
                "description": "快速推进到高潮和结局",
                "climax_moments": ["最终对决", "冲突解决", "故事收尾"]
            }
        }
        
        return storyline
    
    def analyze_story_structure(self, storyline: Dict[str, Any]) -> Dict[str, Any]:
        """分析故事结构"""
        analysis = {
            "structure_score": 0,
            "strengths": [],
            "weaknesses": [],
            "suggestions": [],
            "detailed_analysis": {}
        }
        
        score = 100
        
        # 检查三幕结构完整性
        three_act = storyline.get("three_act_structure", {})
        if all(act in three_act for act in ["act1", "act2", "act3"]):
            analysis["strengths"].append("三幕结构完整")
            
            # 检查每幕的内容质量
            for act_name, act_content in three_act.items():
                if isinstance(act_content, dict):
                    if len(act_content) >= 2:
                        analysis["strengths"].append(f"{act_name}内容丰富")
                    else:
                        score -= 10
                        analysis["weaknesses"].append(f"{act_name}内容不足")
        else:
            score -= 30
            analysis["weaknesses"].append("三幕结构不完整")
        
        # 检查冲突设置
        main_conflict = storyline.get("main_conflict", {})
        if main_conflict.get("type") and main_conflict.get("description"):
            analysis["strengths"].append("主要冲突设置清晰")
        else:
            score -= 20
            analysis["weaknesses"].append("主要冲突设置不清晰")
        
        # 检查世界观构建
        world_setting = storyline.get("world_setting", {})
        if world_setting and len(world_setting) >= 2:
            analysis["strengths"].append("世界观构建完整")
        else:
            score -= 15
            analysis["weaknesses"].append("世界观构建不足")
        
        analysis["structure_score"] = max(0, score)
        
        # 生成改进建议
        if analysis["structure_score"] < 80:
            analysis["suggestions"].append("建议完善故事的基本结构")
        if analysis["structure_score"] < 60:
            analysis["suggestions"].append("建议重新设计冲突和人物关系")
        
        return analysis

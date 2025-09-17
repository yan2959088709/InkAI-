# 增强版人物创建智能体
# 基于心理学和文学理论的人物设计

import random
from datetime import datetime
from typing import Dict, List, Any, Optional

from ..core.base_agent import EnhancedBaseAgent


class EnhancedCharacterCreatorAgent(EnhancedBaseAgent):
    """增强版人物创建智能体 - 基于心理学和文学理论的人物设计"""
    
    def __init__(self):
        super().__init__("增强人物创建智能体")
        
        # Big Five人格模型
        self.big_five_traits = {
            "开放性": {
                "高": ["富有想象力", "好奇心强", "喜欢新体验", "创造性", "思维开放"],
                "低": ["传统保守", "实用主义", "谨慎", "循规蹈矩", "现实主义"]
            },
            "尽责性": {
                "高": ["有组织", "负责任", "自律", "目标导向", "勤奋"],
                "低": ["随性", "灵活", "自发", "适应性强", "不拘小节"]
            },
            "外向性": {
                "高": ["健谈", "活力充沛", "社交", "乐观", "主动"],
                "低": ["内向", "安静", "独立", "深思熟虑", "谨慎"]
            },
            "宜人性": {
                "高": ["合作", "信任他人", "慷慨", "同情心", "友善"],
                "低": ["竞争性", "怀疑", "直率", "独立", "批判性"]
            },
            "神经质": {
                "高": ["情绪敏感", "焦虑", "情绪波动", "紧张", "易受压力影响"],
                "低": ["情绪稳定", "平静", "自信", "放松", "抗压能力强"]
            }
        }
        
        # 职业特征库
        self.profession_traits = {
            "程序员": {
                "技能": ["编程", "逻辑思维", "问题解决", "系统设计"],
                "性格倾向": ["内向", "专注", "细致", "理性"],
                "常见动机": ["技术追求", "创新欲望", "完美主义"],
                "典型恐惧": ["技术落后", "项目失败", "沟通困难"]
            },
            "医生": {
                "技能": ["医学知识", "诊断能力", "决策能力", "沟通技巧"],
                "性格倾向": ["负责任", "细心", "冷静", "同情心"],
                "常见动机": ["救死扶伤", "知识追求", "社会认可"],
                "典型恐惧": ["误诊", "失去病人", "医疗事故"]
            },
            "教师": {
                "技能": ["教学能力", "沟通技巧", "知识传授", "课堂管理"],
                "性格倾向": ["耐心", "友善", "负责", "开放"],
                "常见动机": ["教育理想", "知识传播", "学生成长"],
                "典型恐惧": ["教学失败", "学生不理解", "知识过时"]
            },
            "企业家": {
                "技能": ["商业洞察", "领导能力", "风险评估", "资源整合"],
                "性格倾向": ["外向", "冒险", "自信", "进取"],
                "常见动机": ["成功欲望", "财富积累", "影响力"],
                "典型恐惧": ["失败", "破产", "失去控制"]
            }
        }
        
        # 角色原型
        self.character_archetypes = {
            "英雄": "勇敢、正义、有使命感，通常是故事的核心",
            "导师": "智慧、经验丰富，为主角提供指导",
            "盟友": "忠诚、支持主角，共同面对挑战",
            "守门人": "设置障碍，考验主角的决心和能力",
            "变形者": "多变、难以预测，增加故事复杂性",
            "阴影": "主角的对立面，代表内心黑暗或外在威胁",
            "小丑": "幽默、轻松，缓解紧张气氛",
            "无辜者": "纯真、需要保护，激发主角的保护欲"
        }
        
        self._log("增强版人物创建智能体初始化完成", "INFO")
    
    def create_character(self, tags: Dict[str, List[str]], requirements: str, character_type: str = "主角") -> Dict[str, Any]:
        """创建增强版人物（基于心理学和文学理论）"""
        self._log(f"开始创建{character_type}人物", "INFO")
        
        # 构建增强的提示词
        prompt = self._build_character_prompt(tags, requirements, character_type)
        
        messages = [
            {
                "role": "system", 
                "content": "你是一个专业的人物设计师，精通心理学、人格理论和文学创作。你能够创造深度立体、心理真实的人物形象。"
            },
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        # 增强和验证人物数据
        enhanced_character = self._enhance_character_data(result, tags, requirements)
        
        # 添加人物关系和弧线
        enhanced_character = self._add_character_relationships(enhanced_character)
        enhanced_character = self._design_character_arc(enhanced_character, tags)
        
        self._log(f"{character_type}人物创建完成", "INFO")
        return enhanced_character
    
    def _build_character_prompt(self, tags: Dict[str, List[str]], requirements: str, character_type: str) -> str:
        """构建人物创建提示词"""
        # 根据标签推荐职业
        recommended_profession = self._recommend_profession(tags)
        
        # 根据标签推荐人格特征
        recommended_traits = self._recommend_personality_traits(tags)
        
        prompt = f"""
        请根据以下信息创建一个立体、深度的{character_type}形象：
        
        标签信息：{tags}
        用户需求：{requirements}
        推荐职业：{recommended_profession}
        推荐性格特征：{recommended_traits}
        
        人格设计原则：
        1. 基于Big Five人格模型设计性格
        2. 职业特征要与性格相符
        3. 动机和恐惧要有深层心理依据
        4. 外貌描述要体现内在性格
        5. 技能设定要合理可信
        6. 为后续的成长弧线留下空间
        
        请返回JSON格式：
        {{
            "basic_info": {{
                "name": "姓名",
                "age": 年龄,
                "gender": "性别",
                "occupation": "职业",
                "background": "背景故事"
            }},
            "big_five_personality": {{
                "openness": 分数(1-5),
                "conscientiousness": 分数(1-5),
                "extraversion": 分数(1-5),
                "agreeableness": 分数(1-5),
                "neuroticism": 分数(1-5)
            }},
            "personality_description": "基于Big Five的详细性格描述",
            "appearance": {{
                "physical": "外貌特征",
                "style": "穿着风格",
                "distinctive_features": "独特特征"
            }},
            "psychology": {{
                "core_desire": "核心欲望",
                "deepest_fear": "最深恐惧",
                "motivation": "行为动机",
                "internal_conflict": "内在冲突",
                "emotional_wound": "情感创伤"
            }},
            "skills_and_abilities": {{
                "professional_skills": ["专业技能1", "专业技能2"],
                "personal_skills": ["个人技能1", "个人技能2"],
                "hidden_talents": ["隐藏天赋1", "隐藏天赋2"]
            }},
            "character_archetype": "角色原型（如英雄、导师等）",
            "speech_pattern": "说话方式和语言特点",
            "goals": {{
                "short_term": "短期目标",
                "long_term": "长期目标",
                "ultimate_goal": "终极目标"
            }}
        }}
        """
        return prompt
    
    def _recommend_profession(self, tags: Dict[str, List[str]]) -> str:
        """根据标签推荐职业"""
        type_tags = tags.get("recommended_tags", {}).get("类型标签", [])
        theme_tags = tags.get("recommended_tags", {}).get("主题标签", [])
        
        # 职业匹配规则
        if "都市" in type_tags:
            if "系统" in theme_tags or "逆袭" in theme_tags:
                return "程序员"
            elif "商战" in type_tags:
                return "企业家"
            else:
                return "白领"
        elif "医疗" in type_tags:
            return "医生"
        elif "校园" in type_tags:
            return "学生"
        elif "玄幻" in type_tags or "修仙" in type_tags:
            return "修行者"
        else:
            return "普通人"
    
    def _recommend_personality_traits(self, tags: Dict[str, List[str]]) -> Dict[str, str]:
        """根据标签推荐人格特征"""
        style_tags = tags.get("recommended_tags", {}).get("风格标签", [])
        theme_tags = tags.get("recommended_tags", {}).get("主题标签", [])
        
        traits = {
            "开放性": "中等",
            "尽责性": "中等", 
            "外向性": "中等",
            "宜人性": "中等",
            "神经质": "中等"
        }
        
        # 根据风格调整
        if "轻松愉快" in style_tags:
            traits["外向性"] = "高"
            traits["神经质"] = "低"
        elif "严肃深刻" in style_tags:
            traits["开放性"] = "高"
            traits["外向性"] = "低"
        
        # 根据主题调整
        if "成长" in theme_tags:
            traits["开放性"] = "高"
            traits["尽责性"] = "高"
        elif "冒险" in theme_tags:
            traits["开放性"] = "高"
            traits["外向性"] = "高"
        
        return traits
    
    def _enhance_character_data(self, result: Dict[str, Any], tags: Dict[str, List[str]], requirements: str) -> Dict[str, Any]:
        """增强和验证人物数据"""
        enhanced = result.copy()
        
        # 确保基本信息完整
        if "basic_info" not in enhanced:
            enhanced["basic_info"] = {
                "name": "未命名角色",
                "age": 25,
                "gender": "未指定",
                "occupation": "普通人",
                "background": "待完善"
            }
        
        # 添加职业特征
        occupation = enhanced["basic_info"].get("occupation", "普通人")
        if occupation in self.profession_traits:
            prof_traits = self.profession_traits[occupation]
            enhanced["profession_analysis"] = {
                "typical_skills": prof_traits["技能"],
                "personality_tendencies": prof_traits["性格倾向"],
                "common_motivations": prof_traits["常见动机"],
                "typical_fears": prof_traits["典型恐惧"]
            }
        
        # 验证Big Five人格
        if "big_five_personality" in enhanced:
            enhanced["personality_analysis"] = self._analyze_big_five(enhanced["big_five_personality"])
        
        # 添加创建时间戳
        enhanced["created_at"] = datetime.now().isoformat()
        enhanced["character_type"] = "主角"  # 默认类型
        
        return enhanced
    
    def _analyze_big_five(self, scores: Dict[str, float]) -> Dict[str, Any]:
        """分析Big Five人格得分"""
        analysis = {
            "personality_summary": [],
            "strengths": [],
            "potential_weaknesses": [],
            "behavioral_tendencies": []
        }
        
        trait_names = {
            "openness": "开放性",
            "conscientiousness": "尽责性",
            "extraversion": "外向性",
            "agreeableness": "宜人性",
            "neuroticism": "神经质"
        }
        
        for trait_en, score in scores.items():
            if trait_en in trait_names:
                trait_cn = trait_names[trait_en]
                if trait_cn in self.big_five_traits:
                    level = "高" if score >= 4 else "低" if score <= 2 else "中等"
                    
                    if level != "中等":
                        traits = self.big_five_traits[trait_cn][level]
                        analysis["personality_summary"].extend(traits[:2])  # 取前两个特征
                        
                        if trait_cn != "神经质" and level == "高":
                            analysis["strengths"].extend(traits[:1])
                        elif trait_cn == "神经质" and level == "高":
                            analysis["potential_weaknesses"].extend(traits[:1])
        
        return analysis
    
    def _add_character_relationships(self, character: Dict[str, Any]) -> Dict[str, Any]:
        """添加人物关系网络"""
        character["relationships"] = {
            "family": {
                "parents": "父母关系描述",
                "siblings": "兄弟姐妹关系",
                "other_family": "其他家庭成员"
            },
            "social": {
                "best_friend": "最好的朋友",
                "mentor": "导师或榜样",
                "rival": "竞争对手",
                "colleagues": "同事关系"
            },
            "romantic": {
                "current_status": "当前情感状态",
                "past_relationships": "过往情感经历",
                "ideal_partner": "理想伴侣类型"
            },
            "special": {
                "enemy": "敌人或对手",
                "protector": "保护对象",
                "mysterious_connection": "神秘联系人"
            }
        }
        
        # 基于性格生成关系特点
        if "big_five_personality" in character:
            extraversion = character["big_five_personality"].get("extraversion", 3)
            agreeableness = character["big_five_personality"].get("agreeableness", 3)
            
            if extraversion >= 4:
                character["relationships"]["social_tendencies"] = "社交活跃，朋友众多，善于建立人际关系"
            elif extraversion <= 2:
                character["relationships"]["social_tendencies"] = "较为内向，朋友不多但关系深厚，偏爱小圈子"
            
            if agreeableness >= 4:
                character["relationships"]["relationship_style"] = "合作友善，容易信任他人，关系和谐"
            elif agreeableness <= 2:
                character["relationships"]["relationship_style"] = "独立自主，对他人保持一定距离，关系复杂"
        
        return character
    
    def _design_character_arc(self, character: Dict[str, Any], tags: Dict[str, List[str]]) -> Dict[str, Any]:
        """设计角色成长弧线"""
        theme_tags = tags.get("recommended_tags", {}).get("主题标签", [])
        
        character["character_arc"] = {
            "starting_point": {
                "emotional_state": "故事开始时的情感状态",
                "skill_level": "初始能力水平",
                "worldview": "世界观和价值观",
                "relationships_status": "人际关系现状"
            },
            "growth_path": {
                "key_challenges": ["主要挑战1", "主要挑战2"],
                "learning_moments": ["重要领悟1", "重要领悟2"],
                "skill_development": "技能发展方向",
                "emotional_growth": "情感成长轨迹"
            },
            "transformation": {
                "internal_change": "内在转变",
                "external_change": "外在改变",
                "new_abilities": "获得的新能力",
                "resolved_conflicts": "解决的内在冲突"
            },
            "end_point": {
                "achieved_goals": "达成的目标",
                "new_understanding": "新的认知",
                "changed_relationships": "改变的人际关系",
                "future_potential": "未来发展潜力"
            }
        }
        
        # 根据主题标签调整弧线
        if "成长" in theme_tags:
            character["character_arc"]["arc_type"] = "成长弧线"
            character["character_arc"]["focus"] = "个人能力和心智的全面发展"
        elif "冒险" in theme_tags:
            character["character_arc"]["arc_type"] = "英雄之旅"
            character["character_arc"]["focus"] = "通过冒险获得力量和智慧"
        elif "爱情" in theme_tags:
            character["character_arc"]["arc_type"] = "情感弧线"
            character["character_arc"]["focus"] = "学会爱与被爱，情感成熟"
        
        return character
    
    def create_supporting_character(self, main_character: Dict[str, Any], relationship_type: str, tags: Dict[str, List[str]]) -> Dict[str, Any]:
        """创建配角"""
        self._log(f"创建配角: {relationship_type}", "INFO")
        
        # 基于主角设计配角
        prompt = f"""
        基于以下主角信息，创建一个{relationship_type}角色：
        
        主角信息：{main_character.get('basic_info', {})}
        主角性格：{main_character.get('personality_description', '')}
        故事标签：{tags}
        
        配角设计原则：
        1. 与主角形成互补或对比
        2. 有独立的动机和目标
        3. 能推动故事情节发展
        4. 具有明确的故事功能
        
        请返回与主角相同格式的JSON数据。
        """
        
        messages = [
            {"role": "system", "content": "你是专业的配角设计师，擅长创造与主角互补的立体角色。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        # 标记为配角
        result["character_type"] = "配角"
        result["relationship_to_main"] = relationship_type
        result["story_function"] = self._determine_story_function(relationship_type)
        
        return result
    
    def _determine_story_function(self, relationship_type: str) -> str:
        """确定角色的故事功能"""
        functions = {
            "导师": "提供指导和智慧，帮助主角成长",
            "朋友": "提供支持和陪伴，共同面对挑战",
            "敌人": "制造冲突和障碍，推动情节发展",
            "恋人": "提供情感支持，增加情感线索",
            "竞争对手": "激发主角潜力，提供成长动力",
            "家人": "提供背景和动机，影响主角决策"
        }
        return functions.get(relationship_type, "推动情节发展")
    
    def analyze_character_consistency(self, character: Dict[str, Any]) -> Dict[str, Any]:
        """分析人物一致性"""
        analysis = {
            "consistency_score": 0,
            "strengths": [],
            "issues": [],
            "suggestions": []
        }
        
        score = 100
        
        # 检查基本信息完整性
        basic_info = character.get("basic_info", {})
        required_fields = ["name", "age", "occupation"]
        missing_fields = [field for field in required_fields if not basic_info.get(field)]
        
        if missing_fields:
            score -= len(missing_fields) * 10
            analysis["issues"].append(f"缺少基本信息: {', '.join(missing_fields)}")
        else:
            analysis["strengths"].append("基本信息完整")
        
        # 检查性格一致性
        if "big_five_personality" in character and "personality_description" in character:
            analysis["strengths"].append("具有科学的性格评估")
        else:
            score -= 15
            analysis["issues"].append("缺少详细的性格分析")
        
        # 检查动机合理性
        psychology = character.get("psychology", {})
        if psychology.get("core_desire") and psychology.get("motivation"):
            analysis["strengths"].append("动机设定明确")
        else:
            score -= 10
            analysis["issues"].append("动机设定不够清晰")
        
        # 检查技能与职业匹配
        occupation = basic_info.get("occupation", "")
        skills = character.get("skills_and_abilities", {}).get("professional_skills", [])
        
        if occupation in self.profession_traits:
            expected_skills = self.profession_traits[occupation]["技能"]
            if any(skill in str(skills) for skill in expected_skills):
                analysis["strengths"].append("技能与职业匹配")
            else:
                score -= 10
                analysis["issues"].append("技能与职业不够匹配")
        
        analysis["consistency_score"] = max(0, score)
        
        # 生成改进建议
        if analysis["consistency_score"] < 80:
            analysis["suggestions"].append("建议完善人物的基本信息和背景")
        if analysis["consistency_score"] < 60:
            analysis["suggestions"].append("建议重新设计人物的动机和目标")
        if analysis["consistency_score"] < 40:
            analysis["suggestions"].append("建议重新构建人物的整体设定")
        
        return analysis

"""
人物形象创建智能体
负责根据标签和需求创建人物形象
"""
from base_agent import BaseAgent
from typing import Dict, List, Any
import config
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.type_safety import (
    safe_list_extend, safe_list_append, safe_dict_update, 
    ensure_field_type, validate_character_structure, 
    create_safe_defaults, log_type_mismatch
)
from utils.logger import get_logger

logger = get_logger("character_creator")


class CharacterCreatorAgent(BaseAgent):
    """人物形象创建智能体"""
    
    def __init__(self):
        super().__init__("人物形象创建智能体")
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理人物创建请求"""
        selected_tags = input_data.get("selected_tags", {})
        user_requirements = input_data.get("user_requirements", "")
        existing_characters = input_data.get("existing_characters", {})
        user_modifications = input_data.get("user_modifications", {})
        
        # 如果有现有人物数据和用户修改，则进行改进
        if existing_characters and user_modifications:
            return self._improve_existing_characters(existing_characters, user_modifications, selected_tags, user_requirements)
        
        # 否则创建新人物
        # 创建主要人物
        main_character = self._create_main_character(selected_tags, user_requirements)
        
        # 创建次要人物
        supporting_characters = self._create_supporting_characters(selected_tags, main_character)
        
        return {
            "main_character": main_character,
            "supporting_characters": supporting_characters,
            "character_relationships": self._define_relationships(main_character, supporting_characters)
        }
    
    def _create_main_character(self, tags: Dict[str, List[str]], requirements: str) -> Dict[str, Any]:
        """创建主要人物"""
        # 根据标签确定人物原型
        character_type = self._determine_character_type(tags)
        
        prompt = f"""
        你是一位专业的小说角色设计师，请根据以下信息创建一个立体化、有深度的小说主角：
        
        【故事背景分析】
        类型标签：{self._format_tags(tags)}
        用户创作需求：{requirements}
        推荐人物原型：{character_type}
        
        【角色设计要求】
        1. 人物立体度：角色必须具有多面性，避免脸谱化
        2. 内在冲突：角色内心要有合理的矛盾和挣扎
        3. 成长潜力：角色要有明确的成长弧线和变化空间
        4. 读者共鸣：角色要能让读者产生情感共鸣
        5. 故事驱动：角色要能推动故事发展，创造冲突和张力
        
        【详细设计要素】
        请创建包含以下维度的主角形象：
        
        1. 基础信息（姓名、年龄、性别、职业）
           - 姓名要有寓意，符合角色特质
           - 年龄要与故事背景和角色发展匹配
           - 职业要能体现角色性格和推动情节
        
        2. 性格特质（基于五维人格模型）
           - 外向性：社交倾向和能量来源
           - 宜人性：合作倾向和信任度
           - 尽责性：自律性和目标导向
           - 神经质：情绪稳定性和压力反应
           - 开放性：创新性和经验接受度
           - 每个维度都要有具体的行为表现
        
        3. 外貌特征（服务于角色塑造）
           - 标志性装扮：体现性格和身份
           - 身体特征：与性格形成呼应
           - 特殊印记：增加记忆点和故事性
        
        4. 动机与背景（驱动角色行为）
           - 核心欲望：角色的终极目标
           - 主要恐惧：角色的心理弱点
           - 重要经历：塑造性格的关键事件
           - 行为动机：驱动当前行动的原因
        
        5. 技能特长（推动情节发展）
           - 核心技能：与故事主线相关
           - 辅助技能：增加角色丰富度
           - 隐藏技能：为后续情节埋下伏笔
        
        6. 人际关系（构建故事网络）
           - 家庭关系：影响角色价值观
           - 朋友关系：提供支持和冲突
           - 敌对关系：创造故事张力
        
        【输出要求】
        请严格按照以下JSON格式输出，确保数据完整且符合要求：
        
        {{
            "basic_info": {{
                "name": "角色姓名（要有寓意，符合角色特质）",
                "age": 年龄数字,
                "gender": "性别",
                "occupation": "职业（要能推动情节发展）",
                "education": "教育背景",
                "social_status": "社会地位"
            }},
            "personality": {{
                "extraversion": 外向性分数(1-10),
                "agreeableness": 宜人性分数(1-10),
                "conscientiousness": 尽责性分数(1-10),
                "neuroticism": 神经质分数(1-10),
                "openness": 开放性分数(1-10),
                "description": "详细性格描述（至少200字）",
                "strengths": ["性格优势1", "性格优势2", "性格优势3"],
                "weaknesses": ["性格弱点1", "性格弱点2"],
                "quirks": ["独特习惯1", "独特习惯2"]
            }},
            "appearance": {{
                "height": "身高描述",
                "build": "体型描述",
                "distinctive_features": ["标志性特征1", "标志性特征2"],
                "clothing_style": "着装风格描述",
                "voice": "声音特征",
                "body_language": "肢体语言特点"
            }},
            "background": {{
                "core_desire": "核心欲望（驱动角色行动的根本动力）",
                "fear": "主要恐惧（角色的心理弱点）",
                "past_experience": "重要过往经历（塑造性格的关键事件）",
                "motivation": "当前行为动机",
                "values": ["核心价值观1", "核心价值观2"],
                "trauma": "心理创伤（如果有）",
                "achievements": ["重要成就1", "重要成就2"]
            }},
            "skills": {{
                "core_skills": ["核心技能1", "核心技能2"],
                "auxiliary_skills": ["辅助技能1", "辅助技能2"],
                "hidden_skills": ["隐藏技能1"],
                "skill_levels": {{
                    "技能名称": "熟练程度（初级/中级/高级/专家级）"
                }}
            }},
            "relationships": {{
                "family": {{
                    "parents": "父母关系描述",
                    "siblings": "兄弟姐妹关系",
                    "extended_family": "其他家庭成员"
                }},
                "friends": {{
                    "close_friends": ["挚友1", "挚友2"],
                    "acquaintances": ["熟人1", "熟人2"]
                }},
                "enemies": {{
                    "rivals": ["竞争对手1"],
                    "antagonists": ["敌对者1"]
                }},
                "romantic": "感情状况描述"
            }},
            "character_arc": {{
                "starting_point": "角色起始状态",
                "growth_direction": "成长方向",
                "potential_conflicts": ["潜在冲突1", "潜在冲突2"],
                "transformation_opportunities": ["转变机会1", "转变机会2"]
            }},
            "story_function": {{
                "role_in_plot": "在故事中的作用",
                "conflict_generator": "如何产生冲突",
                "theme_representative": "代表的故事主题",
                "reader_connection": "与读者的情感连接点"
            }}
        }}
        
        【质量要求】
        1. 所有文本内容必须具体、生动，避免空洞描述
        2. 性格分数要合理分布，体现角色的复杂性
        3. 背景故事要有逻辑性，与性格特征一致
        4. 技能设置要服务于故事发展
        5. 人际关系要真实可信，有发展潜力
        """
        
        messages = [
            {"role": "system", "content": """你是一位世界级的小说人物设计师，拥有丰富的文学创作经验和心理学背景。你擅长：

1. 创建立体化角色：设计具有多面性、内在冲突和成长潜力的角色
2. 心理学应用：运用人格心理学理论塑造真实可信的角色
3. 故事驱动设计：确保角色能够推动情节发展，创造戏剧张力
4. 读者共鸣：设计能让读者产生情感连接的角色
5. 细节丰富：为角色添加生动的细节和独特特征

你的设计原则：
- 避免脸谱化和刻板印象
- 注重角色的内在逻辑和一致性
- 平衡角色的优点和缺点
- 为角色设计清晰的成长弧线
- 确保角色服务于整体故事

请用专业、细致的态度完成角色设计任务。"""},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        # 【关键兜底】检查并尝试从 'content' 中恢复数据
        if result.get('parse_error', False):
            logger.error("⚠️ JSON解析失败，尝试从 'content' 字段恢复...")
            # 尝试从 'content' 中提取纯JSON字符串并重新解析
            raw_content = result.get('content', '')
            # 移除可能存在的 ```json ``` 标记
            if raw_content.startswith('```json'):
                start = raw_content.find('{')
                end = raw_content.rfind('}') + 1
                if start != -1 and end != 0:
                    clean_json_str = raw_content[start:end]
                    # 再次尝试解析
                    second_attempt = self.parse_json_response(clean_json_str)
                    if not second_attempt.get('parse_error', False):
                        logger.info("✅ 从 'content' 中成功恢复结构化数据")
                        result = second_attempt
                    else:
                        logger.error("❌ 二次解析仍然失败，返回空结构")
                        return self._get_empty_character_structure()
        
        # 验证和补充人物信息
        return self._validate_character(result, character_type)
    
    def _create_supporting_characters(self, tags: Dict[str, List[str]], main_character: Dict[str, Any]) -> List[Dict[str, Any]]:
        """创建次要人物"""
        try:
            # 根据故事类型确定需要的次要人物
            character_roles = self._determine_supporting_roles(tags)
            
            # 确保character_roles是列表
            if not isinstance(character_roles, list):
                character_roles = []
                self.log("character_roles不是列表类型，已重置为空列表")
            
            supporting_characters = []
            for role in character_roles:
                if isinstance(role, str):
                    character = self._create_single_supporting_character(role, main_character, tags)
                    if isinstance(character, dict):
                        # 使用安全的添加方法
                        supporting_characters = safe_list_append(
                            supporting_characters, 
                            character, 
                            "supporting_characters"
                        )
            
            return supporting_characters
            
        except Exception as e:
            self.log(f"创建次要人物时出错: {e}")
            return []
    
    def _create_single_supporting_character(self, role: str, main_character: Dict[str, Any], tags: Dict[str, List[str]]) -> Dict[str, Any]:
        """创建单个次要人物"""
        prompt = f"""
        为主角创建{role}角色：
        
        主角信息：
        {self._format_character_info(main_character)}
        
        故事标签：
        {self._format_tags(tags)}
        
        请创建这个{role}角色，包括基础信息、性格、外貌、背景和与主角的关系。
        
        返回JSON格式（简化版）：
        {{
            "role": "{role}",
            "basic_info": {{
                "name": "姓名",
                "age": 年龄,
                "gender": "性别",
                "occupation": "职业"
            }},
            "personality": "性格描述",
            "appearance": "外貌描述",
            "background": "背景故事",
            "relationship_with_main": "与主角的关系"
        }}
        """
        
        messages = [
            {"role": "system", "content": "你是一个专业的小说人物设计师，擅长创建与主角形成良好互动的配角。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        return result
    
    def _determine_character_type(self, tags: Dict[str, List[str]]) -> str:
        """根据标签确定人物类型"""
        type_tags = tags.get("类型标签", [])
        
        # 根据类型标签匹配人物原型
        if "悬疑" in type_tags:
            return "侦探"
        elif "校园" in type_tags or "青春" in type_tags:
            return "学生"
        elif "医疗" in type_tags:
            return "医生"
        else:
            return "普通人"
    
    def _determine_supporting_roles(self, tags: Dict[str, List[str]]) -> List[str]:
        """确定需要的次要人物角色"""
        type_tags = tags.get("类型标签", [])
        
        if "悬疑" in type_tags:
            return ["助手", "反派", "受害者"]
        elif "言情" in type_tags:
            return ["恋人", "情敌", "朋友"]
        elif "校园" in type_tags:
            return ["同学", "老师", "朋友"]
        else:
            return ["朋友", "导师", "对手"]
    
    def _define_relationships(self, main_character: Dict[str, Any], supporting_characters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """定义人物关系"""
        try:
            # 确保supporting_characters是列表
            if not isinstance(supporting_characters, list):
                supporting_characters = []
                self.log("supporting_characters不是列表类型，已重置为空列表")
            
            relationships = {
                "main_character": main_character.get("basic_info", {}).get("name", "主角"),
                "relationships": []
            }
            
            for char in supporting_characters:
                if isinstance(char, dict):
                    relationship_item = {
                        "character": char.get("basic_info", {}).get("name", "未知"),
                        "role": char.get("role", "未知"),
                        "relationship_type": char.get("relationship_with_main", "未知")
                    }
                    # 使用安全的添加方法
                    relationships["relationships"] = safe_list_append(
                        relationships["relationships"], 
                        relationship_item, 
                        "relationships"
                    )
            
            return relationships
            
        except Exception as e:
            self.log(f"定义角色关系时出错: {e}")
            return {
                "main_character": "主角",
                "relationships": []
            }
    
    def _format_tags(self, tags: Dict[str, List[str]]) -> str:
        """格式化标签信息"""
        if not tags:
            return "无标签信息"
        
        formatted = ""
        for category, tag_list in tags.items():
            if tag_list and isinstance(tag_list, list):
                formatted += f"{category}: {', '.join(tag_list)}\n"
            else:
                formatted += f"{category}: 无标签\n"
        return formatted
    
    def _format_character_info(self, character: Dict[str, Any]) -> str:
        """格式化人物信息"""
        basic_info = character.get("basic_info", {})
        return f"姓名: {basic_info.get('name', '未知')}, 年龄: {basic_info.get('age', '未知')}, 职业: {basic_info.get('occupation', '未知')}"
    
    def _get_empty_character_structure(self) -> Dict[str, Any]:
        """返回空的角色结构，用于解析完全失败的情况"""
        return {
            "basic_info": {
                "name": "解析失败",
                "age": 0,
                "gender": "未知",
                "occupation": "未知"
            },
            "personality": {},
            "appearance": {},
            "background": {},
            "skills": {},
            "relationships": {}
        }
    
    def _validate_character(self, character: Dict[str, Any], character_type: str) -> Dict[str, Any]:
        """验证和补充人物信息"""
        try:
            # 使用类型安全工具验证和修复角色结构
            character = validate_character_structure(character)
            
            # 补充原型特征（使用类型安全的扩展方法）
            if character_type in config.CHARACTER_ARCHETYPES:
                archetype = config.CHARACTER_ARCHETYPES[character_type]
                archetype_traits = archetype.get("traits", [])
                
                # 使用安全的扩展方法
                character["skills"] = safe_list_extend(
                    character.get("skills", []), 
                    archetype_traits, 
                    "skills"
                )
            
            return character
            
        except Exception as e:
            self.log(f"验证角色数据时出错: {e}")
            # 返回安全的默认结构
            return create_safe_defaults("character_creator")["main_character"]
    
    def _improve_existing_characters(self, existing_characters: Dict[str, Any], 
                                   user_modifications: Dict[str, Any], 
                                   selected_tags: Dict[str, List[str]], 
                                   user_requirements: str) -> Dict[str, Any]:
        """改进现有人物数据"""
        try:
            # 获取现有数据
            main_character = existing_characters.get("main_character", {})
            supporting_characters = existing_characters.get("supporting_characters", [])
            character_relationships = existing_characters.get("character_relationships", {})
            
            # 构建改进提示
            prompt = f"""
            请基于用户的修改，对现有人物形象进行完善和补充：
            
            故事标签：
            {self._format_tags(selected_tags)}
            
            用户需求：
            {user_requirements}
            
            现有人物设定：
            {self._format_existing_characters(existing_characters)}
            
            用户修改内容：
            {self._format_user_modifications(user_modifications)}
            
            改进要求：
            1. 保持用户修改的内容不变
            2. 根据用户修改补充和完善相关的人物信息
            3. 确保人物设定的一致性和合理性
            4. 补充缺失的人物信息（如性格、外貌、背景等）
            5. 优化人物关系的描述
            6. 保持与故事标签和用户需求的一致性
            
            请返回完善后的JSON格式人物设定：
            {{
                "main_character": {{
                    "basic_info": {{
                        "name": "姓名",
                        "age": 年龄,
                        "gender": "性别",
                        "occupation": "职业"
                    }},
                    "personality": {{
                        "extraversion": 外向性分数(1-10),
                        "agreeableness": 宜人性分数(1-10),
                        "conscientiousness": 尽责性分数(1-10),
                        "neuroticism": 神经质分数(1-10),
                        "openness": 开放性分数(1-10),
                        "description": "完善后的性格描述"
                    }},
                    "appearance": {{
                        "height": "身高",
                        "build": "体型",
                        "distinctive_features": ["标志性特征"],
                        "clothing_style": "着装风格"
                    }},
                    "background": {{
                        "core_desire": "核心欲望",
                        "fear": "主要恐惧",
                        "past_experience": "重要过往经历",
                        "motivation": "行为动机"
                    }},
                    "skills": ["技能1", "技能2"],
                    "relationships": {{
                        "family": "家庭关系",
                        "friends": "朋友关系",
                        "enemies": "敌对关系"
                    }},
                    "personality_traits": ["性格特点1", "性格特点2"],
                    "background_story": "详细的背景故事"
                }},
                "supporting_characters": [
                    {{
                        "role": "角色定位",
                        "basic_info": {{
                            "name": "姓名",
                            "age": 年龄,
                            "gender": "性别",
                            "occupation": "职业"
                        }},
                        "personality": "性格描述",
                        "appearance": "外貌描述",
                        "background": "背景故事",
                        "relationship_with_main": "与主角的关系"
                    }}
                ],
                "character_relationships": {{
                    "main_character": "主角姓名",
                    "relationships": [
                        {{
                            "character": "角色姓名",
                            "role": "角色定位",
                            "relationship_type": "关系类型"
                        }}
                    ]
                }},
                "improvement_summary": "改进要点总结"
            }}
            """
            
            messages = [
                {"role": "system", "content": "你是一个专业的人物设定编辑，擅长根据用户修改完善人物形象，保持设定的一致性和合理性。"},
                {"role": "user", "content": prompt}
            ]
            
            response = self.call_llm(messages)
            result = self.parse_json_response(response)
            
            # 验证和补充结果
            return self._validate_improved_characters(result, existing_characters)
            
        except Exception as e:
            self.log(f"改进人物形象失败: {e}")
            return existing_characters
    
    def _format_existing_characters(self, characters: Dict[str, Any]) -> str:
        """格式化现有人物设定"""
        formatted = ""
        
        main_character = characters.get("main_character", {})
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
        
        supporting_characters = characters.get("supporting_characters", [])
        if isinstance(supporting_characters, dict):
            # 处理对象格式的配角
            supporting_characters = list(supporting_characters.values())
        
        for char in supporting_characters:
            basic_info = char.get("basic_info", {})
            formatted += f"配角：{basic_info.get('name', '未知')} ({char.get('role', '未知角色')})\n"
            formatted += f"  性格：{char.get('personality', '未知')}\n"
            formatted += f"  与主角关系：{char.get('relationship_with_main', '未知')}\n\n"
        
        return formatted
    
    def _format_user_modifications(self, modifications: Dict[str, Any]) -> str:
        """格式化用户修改内容"""
        if not modifications:
            return "无用户修改"
        
        formatted = ""
        for field_path, value in modifications.items():
            formatted += f"{field_path}: {value}\n"
        
        return formatted
    
    def _validate_improved_characters(self, result: Dict[str, Any], original_characters: Dict[str, Any]) -> Dict[str, Any]:
        """验证改进后的人物设定"""
        try:
            # 使用类型安全工具确保字段存在且类型正确
            result = ensure_field_type(result, "main_character", dict, original_characters.get("main_character", {}))
            result = ensure_field_type(result, "supporting_characters", list, original_characters.get("supporting_characters", []))
            result = ensure_field_type(result, "character_relationships", dict, original_characters.get("character_relationships", {}))
            
            # 验证主角数据结构
            main_char = result["main_character"]
            if isinstance(main_char, dict):
                main_char = validate_character_structure(main_char)
                result["main_character"] = main_char
            
            return result
            
        except Exception as e:
            self.log(f"验证改进后角色数据时出错: {e}")
            # 返回安全的默认结构
            return create_safe_defaults("character_creator")

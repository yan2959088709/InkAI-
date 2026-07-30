"""
增强角色分析智能体
负责分析章节内容中的角色变化，提取情感、能力、心理和社交状态变化
"""

from base_agent import BaseAgent
from typing import Dict, List, Any, Optional
import config
import sys
import os
from utils.logger import get_logger
logger = get_logger("enhanced_character_analyzer")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.type_safety import (

    safe_list_append, safe_dict_update, safe_int, 
    log_type_mismatch
)


class EnhancedCharacterAnalyzer(BaseAgent):
    """增强角色分析智能体"""
    
    def __init__(self):
        super().__init__("增强角色分析智能体")
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析章节中的角色状态变化"""
        chapter_content = input_data.get("chapter_content", {})
        current_character_states = input_data.get("current_character_states", {})
        chapter_number = input_data.get("chapter_number", 1)
        
        if not chapter_content:
            return {"error": "缺少章节内容"}
        
        # 分析角色变化
        character_changes = self._analyze_character_changes(
            chapter_content, current_character_states, chapter_number
        )
        
        return {
            "success": True,
            "status": "success",
            "character_changes": character_changes,
            "analysis_summary": self._generate_analysis_summary(character_changes)
        }
    
    def _analyze_character_changes(self, chapter_content: Dict[str, Any], 
                                 current_states: Dict[str, Any], 
                                 chapter_number: int) -> Dict[str, Any]:
        """分析角色在本章中的变化"""
        try:
            content = chapter_content.get("content", "")
            title = chapter_content.get("title", f"第{chapter_number}章")
            existing_char_dev = chapter_content.get("character_development", {})
            
            # 构建角色分析prompt
            prompt = f"""你是一名专业的角色心理分析师，请深入分析以下章节中主要角色的状态变化。

## 章节信息
标题：{title}
章节号：第{chapter_number}章

## 当前角色状态
{self._format_current_states(current_states)}

## 章节内容
{content[:3000]}{'...' if len(content) > 3000 else ''}

## 已有角色发展信息
{existing_char_dev if existing_char_dev else '无'}

请从以下四个维度分析每个主要角色的变化：

### 1. 情感状态分析
- 主要情感（如：愤怒、喜悦、恐惧、悲伤、坚定、困惑等）
- 情感强度（1-10级，10为最强烈）
- 情感触发因素
- 情感变化趋势

### 2. 能力状态分析  
- 战斗力/实力变化
- 技能掌握程度变化
- 新能力获得
- 能力突破事件

### 3. 心理状态分析
- 信念强度变化（1-100）
- 心理创伤程度（0-100）
- 心理恢复进度（0-100）
- 核心信念变化

### 4. 社交状态分析
- 声望/名声变化
- 影响力变化
- 与其他角色关系变化
- 社交地位变化

请返回JSON格式：
{{
    "角色名1": {{
        "emotional_changes": {{
            "primary_emotion": "主要情感",
            "intensity": 情感强度数值,
            "triggers": ["触发因素1", "触发因素2"],
            "description": "情感变化描述"
        }},
        "ability_changes": {{
            "combat_level": 战斗力等级,
            "skills": {{
                "技能名": 掌握程度
            }},
            "breakthroughs": ["突破事件1", "突破事件2"],
            "description": "能力变化描述"
        }},
        "psychological_changes": {{
            "belief_strength": 信念强度,
            "trauma_level": 创伤程度,
            "recovery_progress": 恢复进度,
            "core_beliefs": ["核心信念1", "核心信念2"],
            "description": "心理变化描述"
        }},
        "social_changes": {{
            "reputation": 声望值,
            "influence_level": 影响力等级,
            "relationships": {{
                "其他角色名": {{
                    "relationship_type": "关系类型",
                    "strength": 关系强度,
                    "change": "关系变化描述"
                }}
            }},
            "description": "社交变化描述"
        }},
        "overall_development": "角色整体发展总结",
        "significance": "本章对该角色的重要意义"
    }}
}}

注意：
1. 只分析在本章中有明显变化或重要表现的角色
2. 数值变化要基于具体的情节事件
3. 如果某个维度没有明显变化，可以省略该字段
4. 重点关注角色的内在变化，不只是外在行为"""
            
            # 调用LLM分析
            response = self.call_llm([{"role": "user", "content": prompt}])
            result = self.parse_json_response(response)
            
            if "error" in result:
                logger.error(f"角色分析失败: {result['error']}")
                return self._create_fallback_analysis(chapter_content, current_states)
            
            # 验证和完善分析结果
            validated_result = self._validate_character_analysis(result, chapter_content)
            
            return validated_result
            
        except Exception as e:
            logger.info(f"分析角色变化时出错: {e}")
            return self._create_fallback_analysis(chapter_content, current_states)
    
    def _format_current_states(self, current_states: Dict[str, Any]) -> str:
        """格式化当前角色状态"""
        if not current_states:
            return "无当前角色状态信息"
        
        formatted_states = []
        for char_name, state_data in current_states.items():
            char_summary = f"【{char_name}】"
            
            # 情感状态
            emotional = state_data.get("emotional_profile", {})
            if emotional:
                char_summary += f"\n  情感: {emotional.get('current_emotion', 'unknown')}({emotional.get('current_intensity', 5)}/10)"
            
            # 能力状态
            ability = state_data.get("ability_profile", {})
            if ability:
                char_summary += f"\n  能力: 战斗力{ability.get('combat_level', 1)}级"
                skills = ability.get("skills", {})
                if skills:
                    skill_summary = ", ".join([f"{k}:{v}" for k, v in list(skills.items())[:3]])
                    char_summary += f", 技能({skill_summary})"
            
            # 心理状态
            psychological = state_data.get("psychological_profile", {})
            if psychological:
                char_summary += f"\n  心理: 信念{psychological.get('belief_strength', 50)}/100"
            
            formatted_states.append(char_summary)
        
        return "\n\n".join(formatted_states)
    
    def _validate_character_analysis(self, analysis_result: Dict[str, Any], 
                                   chapter_content: Dict[str, Any]) -> Dict[str, Any]:
        """验证和完善角色分析结果"""
        validated_result = {}
        
        for char_name, changes in analysis_result.items():
            if not isinstance(changes, dict):
                continue
            
            validated_changes = {}
            
            # 验证情感变化
            if "emotional_changes" in changes:
                emotional = changes["emotional_changes"]
                if isinstance(emotional, dict):
                    validated_changes["emotional_changes"] = {
                        "primary_emotion": emotional.get("primary_emotion", "neutral"),
                        "intensity": max(1, min(10, emotional.get("intensity", 5))),
                        "triggers": emotional.get("triggers", []),
                        "description": emotional.get("description", "情感状态变化")
                    }
            
            # 验证能力变化
            if "ability_changes" in changes:
                ability = changes["ability_changes"]
                if isinstance(ability, dict):
                    # 安全地处理combat_level，确保是数字
                    combat_level = ability.get("combat_level", 1)
                    if isinstance(combat_level, str):
                        try:
                            combat_level = int(combat_level)
                        except ValueError:
                            combat_level = 1
                    
                    validated_changes["ability_changes"] = {
                        "combat_level": max(1, combat_level),
                        "skills": ability.get("skills", {}),
                        "breakthroughs": ability.get("breakthroughs", []),
                        "description": ability.get("description", "能力状态变化")
                    }
            
            # 验证心理变化
            if "psychological_changes" in changes:
                psychological = changes["psychological_changes"]
                if isinstance(psychological, dict):
                    # 安全地处理数值字段
                    def safe_int(value, default, min_val=0, max_val=100):
                        if isinstance(value, str):
                            try:
                                return max(min_val, min(max_val, int(value)))
                            except ValueError:
                                return default
                        elif isinstance(value, (int, float)):
                            return max(min_val, min(max_val, int(value)))
                        else:
                            return default
                    
                    validated_changes["psychological_changes"] = {
                        "belief_strength": safe_int(psychological.get("belief_strength"), 50),
                        "trauma_level": safe_int(psychological.get("trauma_level"), 0),
                        "recovery_progress": safe_int(psychological.get("recovery_progress"), 100),
                        "core_beliefs": psychological.get("core_beliefs", []),
                        "description": psychological.get("description", "心理状态变化")
                    }
            
            # 验证社交变化
            if "social_changes" in changes:
                social = changes["social_changes"]
                if isinstance(social, dict):
                    # 使用相同的安全处理函数
                    def safe_int(value, default, min_val=0, max_val=100):
                        if isinstance(value, str):
                            try:
                                return max(min_val, min(max_val, int(value)))
                            except ValueError:
                                return default
                        elif isinstance(value, (int, float)):
                            return max(min_val, min(max_val, int(value)))
                        else:
                            return default
                    
                    validated_changes["social_changes"] = {
                        "reputation": safe_int(social.get("reputation"), 50),
                        "influence_level": safe_int(social.get("influence_level"), 1, 1, 10),
                        "relationships": social.get("relationships", {}),
                        "description": social.get("description", "社交状态变化")
                    }
            
            # 添加整体信息
            validated_changes["overall_development"] = changes.get("overall_development", f"{char_name}在本章的发展")
            validated_changes["significance"] = changes.get("significance", "角色发展的重要节点")
            
            if validated_changes:
                validated_result[char_name] = validated_changes
        
        return validated_result
    
    def _create_fallback_analysis(self, chapter_content: Dict[str, Any], 
                                current_states: Dict[str, Any]) -> Dict[str, Any]:
        """创建备用分析结果"""
        fallback_result = {}
        
        # 从章节内容中提取角色发展信息
        char_development = chapter_content.get("character_development", {})
        
        if isinstance(char_development, dict):
            for char_name, development in char_development.items():
                # 使用安全的字典更新方法
                fallback_result = safe_dict_update(fallback_result, {
                    char_name: {
                        "emotional_changes": {
                            "primary_emotion": "neutral",
                            "intensity": 5,
                            "triggers": [],
                            "description": development if isinstance(development, str) else "角色发展"
                        },
                        "overall_development": development if isinstance(development, str) else f"{char_name}的发展",
                        "significance": "角色发展的重要环节"
                    }
                }, "fallback_result")
        elif isinstance(char_development, str) and char_development:
            # 如果character_development是字符串，尝试提取主角信息
            fallback_result["主角"] = {
                "emotional_changes": {
                    "primary_emotion": "neutral",
                    "intensity": 5,
                    "triggers": [],
                    "description": char_development
                },
                "overall_development": char_development,
                "significance": "主角发展的重要环节"
            }
        
        return fallback_result
    
    def _generate_analysis_summary(self, character_changes: Dict[str, Any]) -> str:
        """生成分析摘要"""
        if not character_changes:
            return "本章无明显角色变化"
        
        summary_parts = []
        
        for char_name, changes in character_changes.items():
            char_summary = f"{char_name}: "
            
            change_aspects = []
            if "emotional_changes" in changes:
                emotion = changes["emotional_changes"].get("primary_emotion", "")
                if emotion:
                    change_aspects.append(f"情感变化({emotion})")
            
            if "ability_changes" in changes:
                if changes["ability_changes"].get("breakthroughs"):
                    change_aspects.append("能力突破")
            
            if "psychological_changes" in changes:
                change_aspects.append("心理发展")
            
            if "social_changes" in changes:
                change_aspects.append("社交变化")
            
            if change_aspects:
                char_summary += ", ".join(change_aspects)
            else:
                char_summary += "整体发展"
            
            summary_parts.append(char_summary)
        
        return "; ".join(summary_parts)

"""
增强版故事线生成器
严格按照中长篇小说创作标准
"""

from typing import Dict, List, Any
from utils.logger import get_logger

logger = get_logger("enhanced_storyline")


class EnhancedStorylineGenerator:
    """增强版故事线生成器"""
    
    # 章节类型
    CHAPTER_TYPES = {
        0: "strong_push",  # 强推进章
        1: "buffer_setup",  # 缓冲铺垫章
        2: "upgrade_turn"   # 升级转折章
    }
    
    # 冲突类型
    CONFLICT_TYPES = {
        "external": "外部强冲突 - 生死对抗、正邪对决",
        "internal": "内部冲突 - 内心挣扎、两难选择",
        "interpersonal": "人际冲突 - 信任危机、理念不合",
        "suspense": "悬念冲突 - 线索断裂、真相反转"
    }
    
    def get_chapter_type(self, chapter_number: int) -> str:
        """根据章节号确定章节类型"""
        return self.CHAPTER_TYPES[chapter_number % 3]
    
    def generate_storyline_prompt(self, chapter_number: int, 
                                 knowledge_base: Dict,
                                 previous_chapters: List[Dict]) -> str:
        """
        生成符合标准的故事线prompt
        
        Args:
            chapter_number: 章节号
            knowledge_base: 知识库
            previous_chapters: 前几章内容
        
        Returns:
            完整的prompt
        """
        chapter_type = self.get_chapter_type(chapter_number)
        
        # 获取上一章结尾
        last_chapter_ending = ""
        if previous_chapters:
            last_content = previous_chapters[-1].get("content", "")
            last_chapter_ending = last_content[-500:] if last_content else ""
        
        # 获取已埋伏笔
        active_foreshadowing = self._get_active_foreshadowing(knowledge_base)
        
        # 构建基础prompt
        prompt = f"""
请为小说生成第{chapter_number}章的故事线。

【章节类型】：{self._get_chapter_type_description(chapter_type)}

【上一章结尾内容】（必须从这里开始续写，禁止重复）：
{last_chapter_ending}

【当前活跃伏笔】：
{self._format_foreshadowing(active_foreshadowing)}

【写作规则】（严格遵守）：
{self._get_writing_rules(chapter_type)}

【双层故事线要求】：
{self._get_dual_storyline_rules(chapter_number)}

【本章必须包含】：
1. 明确的核心冲突（主角目标 + 阻碍力量）
2. 完整的情绪曲线（紧张→期待→高潮→钩子）
3. 有效的人物弧光推进
4. 伏笔的埋设或回收

请返回JSON格式：
{{
    "chapter_type": "{chapter_type}",
    "chapter_title": "章节标题",
    "main_conflict": {{
        "protagonist_goal": "主角本章目标",
        "obstacle": "阻碍力量",
        "stakes": "失败的代价",
        "conflict_type": "external/internal/interpersonal/suspense"
    }},
    "scene_setting": {{
        "time": "时间",
        "location": "地点",
        "atmosphere": "氛围"
    }},
    "plot_points": [
        "开篇承接点（承接上一章结尾）",
        "冲突展开点",
        "障碍/转折点",
        "高潮点",
        "结尾钩子点"
    ],
    "emotional_curve": {{
        "opening": "开篇情绪（承接上文）",
        "rising": "上升情绪",
        "climax": "高潮情绪",
        "hook": "钩子情绪"
    }},
    "foreshadowing": {{
        "new_foreshadowing": ["新埋伏笔（如有）"],
        "recycled_foreshadowing": ["本章回收的伏笔（如有）"]
    }},
    "dual_storyline": {{
        "line_type": "明线/暗线/交汇",
        "connection_point": "与另一条线的关联点"
    }},
    "character_development": {{
        "main_character_change": "主角本章的成长/变化",
        "key_decision": "主角的关键选择"
    }},
    "chapter_ending": "结尾钩子描述（必须留下悬念）",
    "next_chapter_hint": "下章预告"
}}
"""
        return prompt
    
    def _get_chapter_type_description(self, chapter_type: str) -> str:
        """获取章节类型描述"""
        descriptions = {
            "strong_push": "强推进章 - 核心主线推进，主角直面障碍，完成关键行动",
            "buffer_setup": "缓冲铺垫章 - 人物塑造、伏笔铺垫、双线穿插",
            "upgrade_turn": "升级转折章 - 收束铺垫，矛盾升级，为下阶段铺垫"
        }
        return descriptions.get(chapter_type, "")
    
    def _get_writing_rules(self, chapter_type: str) -> str:
        """获取写作规则"""
        base_rules = """
1. 【禁止重复】不要重复上一章已写过的内容
2. 【开篇承接】前300字必须承接上一章结尾
3. 【明确目标】开篇必须明确主角本章核心目标
4. 【冲突铁则】本章必须有明确冲突（目标+阻碍）
5. 【情绪曲线】必须有完整的起承转合
6. 【结尾钩子】必须留下悬念/危机/疑问
"""
        
        type_rules = {
            "strong_push": """
7. 【强推进】本章必须有核心主线的重大推进
8. 【外部冲突】以生死对抗、正邪对决为主
9. 【爽点】必须有明确的高光时刻/爽点
""",
            "buffer_setup": """
7. 【人物弧光】本章重点推进人物成长
8. 【内部冲突】以内心挣扎、两难选择为主
9. 【伏笔铺垫】为后续剧情埋下伏笔
""",
            "upgrade_turn": """
7. 【矛盾升级】核心矛盾必须升级
8. 【双线交汇】明暗线必须有一次交叉
9. 【危机感】结尾必须让读者感到更大的危机
"""
        }
        
        return base_rules + type_rules.get(chapter_type, "")
    
    def _get_dual_storyline_rules(self, chapter_number: int) -> str:
        """获取双层故事线规则"""
        return f"""
本章属于第{chapter_number}章，请按照以下规则处理双层故事线：

1. 明线（古玩鉴定冒险）：
   - 主角利用透视异能进行鉴定/冒险
   - 遭遇古玩界的黑暗势力
   - 获取关键线索/证据

2. 暗线（家族秘密和阴谋）：
   - 十二年前妹妹受伤的真相
   - 双玉扳指的秘密
   - 顾明渊的真实身份和目的

3. 咬合规则：
   - 明线的每一个事件，都是暗线真相的一块拼图
   - 暗线的每一个伏笔，都会影响明线的发展
   - 每3章必须有一次明暗线的交叉点
"""
    
    def _get_active_foreshadowing(self, knowledge_base: Dict) -> List[Dict]:
        """获取当前活跃伏笔"""
        # 从知识库中提取伏笔
        foreshadowing = []
        
        # 从chapters中提取
        chapters = knowledge_base.get("chapters", [])
        for chapter in chapters[-5:]:  # 最近5章
            chapter_foreshadowing = chapter.get("foreshadowing", [])
            for f in chapter_foreshadowing:
                if isinstance(f, str):
                    foreshadowing.append({"content": f, "status": "active"})
                elif isinstance(f, dict):
                    foreshadowing.append(f)
        
        return foreshadowing
    
    def _format_foreshadowing(self, foreshadowing: List[Dict]) -> str:
        """格式化伏笔"""
        if not foreshadowing:
            return "暂无活跃伏笔"
        
        formatted = ""
        for i, f in enumerate(foreshadowing[:5], 1):
            content = f.get("content", str(f))
            formatted += f"{i}. {content}\n"
        
        return formatted


def get_enhanced_storyline_prompt(chapter_number: int, 
                                 knowledge_base: Dict,
                                 previous_chapters: List[Dict]) -> str:
    """获取增强版故事线prompt的便捷函数"""
    generator = EnhancedStorylineGenerator()
    return generator.generate_storyline_prompt(chapter_number, knowledge_base, previous_chapters)

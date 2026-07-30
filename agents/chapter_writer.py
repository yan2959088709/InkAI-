"""
章节写作智能体
负责生成具体的章节内容
"""

from base_agent import BaseAgent
from typing import Dict, List, Any
import config


class ChapterWriterAgent(BaseAgent):
    """章节写作智能体"""
    
    def __init__(self):
        super().__init__("章节写作智能体")
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理章节写作请求"""
        chapter_info = input_data.get("chapter_info", {})
        characters = input_data.get("characters", {})
        storyline = input_data.get("storyline", {})
        tags = input_data.get("tags", {})
        user_requirements = input_data.get("user_requirements", "")
        
        # 生成章节内容
        chapter_content = self._write_chapter(chapter_info, characters, storyline, tags, user_requirements)
        
        return {
            "chapter_content": chapter_content,
            "word_count": len(chapter_content.get("content", "")),
            "writing_quality": self._assess_writing_quality(chapter_content)
        }
    
    def _write_chapter(self, chapter_info: Dict[str, Any], characters: Dict[str, Any], 
                      storyline: Dict[str, Any], tags: Dict[str, List[str]], user_requirements: str) -> Dict[str, Any]:
        """写作章节内容"""
        main_character = characters.get("main_character", {})
        supporting_characters = characters.get("supporting_characters", [])
        
        prompt = f"""
        请根据以下信息写作小说章节：
        
        用户创作需求：
        {user_requirements}
        
        章节信息：
        {self._format_chapter_info(chapter_info)}
        
        主角信息：
        {self._format_character_info(main_character)}
        
        配角信息：
        {self._format_supporting_characters(supporting_characters)}
        
        故事线：
        {self._format_storyline_info(storyline)}
        
        故事标签：
        {self._format_tags(tags)}
        
        写作要求：
        1. 保持与故事标签一致的风格
        2. 体现人物性格特点
        3. 推进故事情节发展
        4. 设置适当的伏笔和悬念
        5. 语言生动，描写细腻
        6. 小说正文字数必须大于3000字且在3000-5000字之间
        7. 小说的第一章是开篇，小说情节跟内容需要足够吸引读者
        8. 用你最大的输出能力进行输出

        
        请返回JSON格式：
        {{
            "title": "章节标题",
            "content": "章节正文内容",
            "summary": "章节概要",
            "key_events": ["关键事件1", "关键事件2"],
            "character_development": "人物发展",
            "foreshadowing": ["伏笔1", "伏笔2"],
            "next_chapter_hint": "下章预告"
        }}
        """
        
        messages = [
            {"role": "system", "content": """你是一个专业的小说作家，擅长创作引人入胜的章节内容。

【重要约束】
1. 你必须严格遵循用户给定的角色设定
2. 主角名称、性格、职业、背景等信息必须在正文中体现
3. 故事背景、地点必须与用户需求一致
4. 绝对不能擅自创建或引入用户需求中没有的主角，但是配角可以任意创建
5. 如果用户指定了主角，必须以该主角的视角展开故事
6. 返回的JSON中，"title"和"content"字段必须与给定设定完全一致"""},
            {"role": "user", "content": prompt}
        ]
        
        # 章节写作需要更多token空间，使用最大限制
        response = self.call_llm(messages, max_tokens=config.CHAPTER_MAX_TOKENS)
        result = self.parse_json_response(response)
        
        return self._validate_chapter_content(result)
    
    
    def _assess_writing_quality(self, chapter_content: Dict[str, Any]) -> Dict[str, Any]:
        """评估写作质量"""
        content = chapter_content.get("content", "")
        
        # 简单的质量评估指标
        word_count = len(content)
        sentence_count = content.count('。') + content.count('！') + content.count('？')
        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
        
        # 检查是否有对话
        has_dialogue = '"' in content or '"' in content or '「' in content
        
        # 检查是否有环境描写
        has_description = any(word in content for word in ['的', '地', '得', '着', '了', '过'])
        
        quality_score = 0
        if 2000 <= word_count <= 3000:
            quality_score += 30
        elif 1500 <= word_count <= 4000:
            quality_score += 20
        
        if 10 <= avg_sentence_length <= 30:
            quality_score += 20
        elif 5 <= avg_sentence_length <= 50:
            quality_score += 10
        
        if has_dialogue:
            quality_score += 25
        
        if has_description:
            quality_score += 25
        
        return {
            "overall_score": min(quality_score, 100),
            "word_count": word_count,
            "sentence_count": sentence_count,
            "avg_sentence_length": round(avg_sentence_length, 2),
            "has_dialogue": has_dialogue,
            "has_description": has_description
        }
    
    def _format_chapter_info(self, chapter_info: Dict[str, Any]) -> str:
        """格式化章节信息"""
        return f"""
        章节标题: {chapter_info.get('chapter_title', '未知')}
        场景设定: {chapter_info.get('scene_setting', {})}
        情节要点: {chapter_info.get('plot_points', [])}
        章节结尾: {chapter_info.get('chapter_ending', '未知')}
        """
    
    def _format_character_info(self, character: Dict[str, Any]) -> str:
        """格式化人物信息"""
        if not character:
            return "无人物信息"
        
        basic_info = character.get("basic_info", {})
        personality = character.get("personality", {})
        background = character.get("background", {})
        
        return f"""
        姓名: {basic_info.get('name', '未知')}
        年龄: {basic_info.get('age', '未知')}
        职业: {basic_info.get('occupation', '未知')}
        性格: {personality.get('description', '未知')}
        核心欲望: {background.get('core_desire', '未知')}
        主要恐惧: {background.get('fear', '未知')}
        """
    
    def _format_supporting_characters(self, characters: List[Dict[str, Any]]) -> str:
        """格式化配角信息"""
        if not characters:
            return "无配角信息"
        
        formatted = ""
        for char in characters:
            basic_info = char.get("basic_info", {})
            formatted += f"- {basic_info.get('name', '未知')} ({char.get('role', '未知角色')}): {char.get('personality', '未知性格')}\n"
        
        return formatted
    
    def _format_storyline_info(self, storyline: Dict[str, Any]) -> str:
        """格式化故事线信息"""
        return f"""
        世界观: {storyline.get('world_setting', '未知')}
        主角目标: {storyline.get('main_goal', '未知')}
        核心冲突: {storyline.get('conflict', '未知')}
        故事基调: {storyline.get('tone', '未知')}
        """
    
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
    
    def _validate_chapter_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """验证章节内容"""
        required_fields = ["title", "content", "summary"]
        
        for field in required_fields:
            if field not in content:
                if field == "content":
                    content[field] = "内容待生成"
                elif field == "title":
                    content[field] = "章节标题"
                else:
                    content[field] = "待补充"
        
        # 确保其他字段存在
        optional_fields = ["key_events", "character_development", "foreshadowing", "next_chapter_hint"]
        for field in optional_fields:
            if field not in content:
                if field == "key_events" or field == "foreshadowing":
                    content[field] = []
                else:
                    content[field] = "待补充"
        
        # 确保包含字数统计
        if 'word_count' not in content:
            chapter_content = content.get('content', '')
            if chapter_content:
                # 计算实际字数（去除空白字符）
                clean_content = chapter_content.replace(' ', '').replace('\n', '').replace('\r', '').replace('\t', '').replace('\u3000', '')
                content['word_count'] = len(clean_content)
            else:
                content['word_count'] = 0
        
        # 确保包含创建时间
        if 'created_at' not in content:
            from datetime import datetime
            content['created_at'] = datetime.now().isoformat()
        
        return content

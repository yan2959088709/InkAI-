"""
续写章节写作智能体
负责基于知识库生成续写章节内容
"""

from base_agent import BaseAgent
from typing import Dict, List, Any, Optional
import config


class ContinuationChapterWriter(BaseAgent):
    """续写章节写作智能体"""
    
    # 章节类型定义
    CHAPTER_TYPES = {
        0: {
            "name": "strong_push",
            "display_name": "强推进章",
            "description": "核心主线推进，主角直面障碍，完成关键行动",
            "conflict_preference": "external",
            "focus": "plot_progression"
        },
        1: {
            "name": "buffer_setup", 
            "display_name": "缓冲铺垫章",
            "description": "人物塑造、伏笔铺垫、双线穿插",
            "conflict_preference": "internal",
            "focus": "character_development"
        },
        2: {
            "name": "upgrade_turn",
            "display_name": "升级转折章",
            "description": "收束铺垫，矛盾升级，为下阶段铺垫",
            "conflict_preference": "mixed",
            "focus": "conflict_escalation"
        }
    }
    
    # 双线交汇间隔
    INTERSECTION_INTERVAL = 3
    
    def __init__(self):
        super().__init__("续写章节写作智能体")
    
    def _get_chapter_type(self, chapter_number: int) -> Dict[str, Any]:
        """根据章节号获取章节类型"""
        type_index = chapter_number % 3
        chapter_type = self.CHAPTER_TYPES[type_index].copy()
        chapter_type["chapter_number"] = chapter_number
        chapter_type["type_index"] = type_index
        return chapter_type
    
    def _get_rhythm_guidance(self, chapter_number: int) -> str:
        """获取节奏指导"""
        chapter_type = self._get_chapter_type(chapter_number)
        
        guidance = f"""
【本章类型】：{chapter_type['display_name']}
【类型说明】：{chapter_type['description']}

{self._get_type_specific_guidance(chapter_type)}
{self._get_dual_storyline_guidance(chapter_number)}
"""
        return guidance
    
    def _get_dual_storyline_guidance(self, chapter_number: int) -> str:
        """获取双线咬合指导"""
        if chapter_number % self.INTERSECTION_INTERVAL == 0:
            return """
【双线交汇要求】：
本章必须包含明暗线的交汇点！

明线（古玩鉴定冒险）：
- 主角利用透视异能进行鉴定/冒险
- 遭遇古玩界的黑暗势力
- 获取关键线索/证据

暗线（家族秘密和阴谋）：
- 十二年前妹妹受伤的真相
- 双玉扳指的秘密
- 顾明渊的真实身份和目的

咬合规则：
1. 明线的每一个事件，都是暗线真相的一块拼图
2. 暗线的每一个伏笔，都会影响明线的发展
3. 交汇点要让读者产生"原来如此"的爽感
"""
        return ""
    
    def _get_type_specific_guidance(self, chapter_type: Dict) -> str:
        """获取类型特定的写作指导"""
        type_name = chapter_type["name"]
        
        if type_name == "strong_push":
            return """
【强推进章写作要求】：
1. 冲突类型：以外部强冲突为主（生死对抗、正邪对决）
2. 核心任务：推进主线剧情，完成关键行动
3. 情绪落点：必须有明确的爽点/高光时刻
4. 结尾要求：强钩子，让读者期待下一章
"""
        elif type_name == "buffer_setup":
            return """
【缓冲铺垫章写作要求】：
1. 冲突类型：以内部冲突/人际冲突为主
2. 核心任务：人物成长、伏笔铺垫、双线穿插
3. 情绪落点：人物弧光的关键节点/悬念升级
4. 结尾要求：埋下新的伏笔或揭示新的疑点
"""
        elif type_name == "upgrade_turn":
            return """
【升级转折章写作要求】：
1. 冲突类型：多类型冲突叠加
2. 核心任务：矛盾升级，为下阶段铺垫
3. 情绪落点：危机感升级，读者感到更大威胁
4. 结尾要求：颠覆性反转或危机升级
"""
        return ""
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理续写章节写作请求"""
        storyline = input_data.get("storyline", {})
        knowledge_base = input_data.get("knowledge_base", {})
        user_requirements = input_data.get("user_requirements", "")
        
        if not storyline or not knowledge_base:
            return {"error": "缺少必要的故事线和知识库数据"}
        
        # 生成续写章节内容
        chapter_content = self._write_continuation_chapter(storyline, knowledge_base, user_requirements)
        
        return {
            "success": True,
            "status": "success",
            "chapter_content": chapter_content,
            "word_count": len(chapter_content.get("content", "")),
            "writing_quality": self._assess_writing_quality(chapter_content)
        }
    
    def _write_continuation_chapter(self, storyline: Dict[str, Any], 
                                  knowledge_base: Dict[str, Any], 
                                  user_requirements: str) -> Dict[str, Any]:
        """写作续写章节内容"""
        try:
            # 获取基本信息
            novel_info = knowledge_base.get("novel_info", {})
            character_profiles = knowledge_base.get("character_profiles", {})
            world_setting = knowledge_base.get("world_setting", "")
            story_tone = knowledge_base.get("story_tone", "")
            tags = knowledge_base.get("tags", {})
            last_chapter = knowledge_base.get("last_chapter_summary", {})
            
            # [FIX] 获取上一章实际结尾内容
            last_chapter_ending = last_chapter.get("content_ending", "")
            last_chapter_title = last_chapter.get("title", "")
            last_chapter_number = last_chapter.get("chapter_number", 0)
            
            # [NEW] 获取节奏指导
            chapter_number = storyline.get('chapter_number', 1)
            rhythm_guidance = self._get_rhythm_guidance(chapter_number)
            
            # [FIX] 构建改进的提示词
            prompt = f"""
请续写小说《{novel_info.get('title', '未知标题')}》的第{chapter_number}章。

{rhythm_guidance}

【上一章结尾内容】（这是第{last_chapter_number}章《{last_chapter_title}》的最后部分，请从这里开始续写）：
{last_chapter_ending}

【本章故事线】：
{self._format_storyline(storyline)}

【人物档案】：
{self._format_character_profiles(character_profiles)}

【世界观】：{world_setting}
【故事基调】：{story_tone}
【标签】：{self._format_tags(tags)}

【写作要求】：
1. 直接从上一章结尾处开始，不要重复上一章的内容
2. 情节自然衔接，保持故事连贯性
3. 【重要】字数必须在3000-5000字之间，这是硬性要求，请务必写够3000字
4. 保持人物性格一致
5. 推进本章故事线
6. 设置适当的悬念和伏笔
7. 语言生动，描写细腻
8. 可以通过增加对话、环境描写、心理活动来扩展内容

请务必写够3000字以上的章节正文内容，不需要JSON格式。
"""
            
            messages = [
                {"role": "system", "content": """你是一个专业的小说作家，擅长续写创作。

【重要约束】
1. 你必须严格遵循给定的角色设定，主角名称、性格、职业必须在正文中体现
2. 绝对不能擅自创建或引入用户需求中没有的角色
3. 必须以给定的主角视角展开故事
4. 地点、背景必须与之前章节保持一致
5. 你的每章作品都必须写够3000字以上，这是硬性要求
6. 请直接输出小说正文内容"""},
                {"role": "user", "content": prompt}
            ]
            
            # 续写章节写作需要更多token空间，使用最大限制
            response = self.call_llm(messages, max_tokens=config.CHAPTER_MAX_TOKENS)
            
            # [FIX] 直接使用响应内容，不再要求JSON格式
            # 构建返回结果
            validated_result = {
                "title": storyline.get("chapter_title", f"第{storyline.get('chapter_number', 1)}章"),
                "content": response,
                "summary": "",
                "key_events": storyline.get("key_events", []),
                "character_development": "",
                "foreshadowing": storyline.get("foreshadowing", []),
                "next_chapter_hint": "",
                "consistency_notes": ""
            }
            
            # 计算字数
            content = validated_result.get("content", "")
            if content:
                clean_content = content.replace(' ', '').replace('\n', '').replace('\r', '').replace('\t', '').replace('\u3000', '')
                validated_result['word_count'] = len(clean_content)
            
            self.log(f"章节内容生成完成，内容长度: {len(content)}")
            return validated_result
            
        except Exception as e:
            import traceback
            self.log(f"续写章节失败: {e}")
            self.log(f"详细错误: {traceback.format_exc()}")
            return self._create_default_chapter(storyline)
    
    def _validate_chapter_content(self, content: Dict[str, Any], storyline: Dict[str, Any]) -> Dict[str, Any]:
        """验证章节内容"""
        # 只补充真正缺失的字段，不覆盖已有的有效内容
        required_fields = {
            "title": storyline.get("chapter_title", f"第{storyline.get('chapter_number', 1)}章"),
            "content": "内容待生成",
            "summary": "章节概要待生成",
            "key_events": [],
            "character_development": "人物发展待描述",
            "foreshadowing": [],
            "next_chapter_hint": "下章预告待生成",
            "consistency_notes": "一致性说明待补充"
        }
        
        # 只补充真正缺失的字段
        for field, default_value in required_fields.items():
            if field not in content:
                content[field] = default_value
            elif not content[field]:  # 字段存在但为空
                content[field] = default_value
            elif isinstance(content[field], str) and content[field].strip() in ["", "待补充", "概要待补充", "未知"]:
                content[field] = default_value
        
        # 特别处理数组字段 - 只处理真正为空的数组
        if not content.get("key_events") or len(content["key_events"]) == 0:
            content["key_events"] = ["关键事件待提取"]
        
        if not content.get("foreshadowing") or len(content["foreshadowing"]) == 0:
            content["foreshadowing"] = ["伏笔设置待分析"]
        
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
    
    
    
    
    
    def _create_default_chapter(self, storyline: Dict[str, Any]) -> Dict[str, Any]:
        """创建默认章节"""
        return {
            "title": storyline.get("chapter_title", f"第{storyline.get('chapter_number', 1)}章"),
            "content": "章节内容生成失败，请检查输入数据。",
            "summary": "概要待补充",
            "key_events": storyline.get("key_events", []),
            "character_development": "待补充",
            "foreshadowing": storyline.get("foreshadowing", []),
            "next_chapter_hint": "待补充",
            "consistency_notes": "内容生成失败"
        }
    
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
        
        # 检查是否有动作描写
        has_action = any(word in content for word in ['走', '跑', '看', '听', '说', '想', '做'])
        
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
            quality_score += 20
        
        if has_description:
            quality_score += 15
        
        if has_action:
            quality_score += 15
        
        return {
            "overall_score": min(quality_score, 100),
            "word_count": word_count,
            "sentence_count": sentence_count,
            "avg_sentence_length": round(avg_sentence_length, 2),
            "has_dialogue": has_dialogue,
            "has_description": has_description,
            "has_action": has_action
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
    
    def _format_last_chapter(self, last_chapter: Dict[str, Any]) -> str:
        """格式化上一章信息"""
        if not last_chapter:
            return "无上一章信息"
        
        formatted = f"第{last_chapter.get('chapter_number', 0)}章：{last_chapter.get('title', '未知标题')}\n"
        formatted += f"概要：{last_chapter.get('summary', '无概要')}\n"
        
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
    
    def _format_storyline(self, storyline: Dict[str, Any]) -> str:
        """格式化故事线"""
        formatted = f"章节标题：{storyline.get('chapter_title', '未知')}\n"
        
        scene_setting = storyline.get("scene_setting", {})
        if scene_setting:
            formatted += f"场景设定：\n"
            formatted += f"  时间：{scene_setting.get('time', '待设定')}\n"
            formatted += f"  地点：{scene_setting.get('location', '待设定')}\n"
            formatted += f"  氛围：{scene_setting.get('atmosphere', '待设定')}\n"
            formatted += f"  天气：{scene_setting.get('weather', '待设定')}\n"
        
        plot_points = storyline.get("plot_points", [])
        if plot_points:
            formatted += f"情节要点：\n"
            for i, point in enumerate(plot_points, 1):
                formatted += f"  {i}. {point}\n"
        
        key_events = storyline.get("key_events", [])
        if key_events:
            formatted += f"关键事件：{', '.join(key_events)}\n"
        
        conflicts = storyline.get("conflicts", [])
        if conflicts:
            formatted += f"冲突：\n"
            for conflict in conflicts:
                if isinstance(conflict, dict):
                    formatted += f"  - {conflict.get('description', '未知冲突')}\n"
                else:
                    formatted += f"  - {conflict}\n"
        
        foreshadowing = storyline.get("foreshadowing", [])
        if foreshadowing:
            formatted += f"伏笔：{', '.join(foreshadowing)}\n"
        
        chapter_ending = storyline.get("chapter_ending", "")
        if chapter_ending:
            formatted += f"章节结尾：{chapter_ending}\n"
        
        writing_notes = storyline.get("writing_notes", "")
        if writing_notes:
            formatted += f"写作注意事项：{writing_notes}\n"
        
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
    
    def process_long_context(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        [OPTIMIZED] 长上下文模式处理续写章节写作请求
        
        与传统模式的区别：
        1. 直接使用原文片段（而非JSON结构化数据）
        2. 包含风格锚点（第1章开头）
        3. 包含最近N章完整原文
        4. 使用自然语言描述角色状态和伏笔
        """
        long_context = input_data.get("long_context", {})
        storyline = input_data.get("storyline", {})
        user_requirements = input_data.get("user_requirements", "")
        
        if not long_context:
            # 降级到传统模式
            self.log("长上下文数据不可用，降级到传统模式")
            return self.process(input_data)
        
        # 生成续写章节内容
        chapter_content = self._write_chapter_long_context(long_context, storyline, user_requirements)
        
        return {
            "success": True,
            "status": "success",
            "chapter_content": chapter_content,
            "word_count": len(chapter_content.get("content", "")),
            "writing_quality": self._assess_writing_quality(chapter_content)
        }
    
    def _write_chapter_long_context(self, long_context: Dict[str, Any],
                                    storyline: Dict[str, Any],
                                    user_requirements: str) -> Dict[str, Any]:
        """使用长上下文模式写作续写章节"""
        try:
            # 提取长上下文数据
            book_summary = long_context.get("book_summary", "")
            style_anchor = long_context.get("style_anchor", "")
            recent_chapters_text = long_context.get("recent_chapters_text", "")
            character_status = long_context.get("character_status_natural", "")
            foreshadowing = long_context.get("active_foreshadowing_natural", "")
            narrative_phase = long_context.get("narrative_phase", {})
            current_chapter = long_context.get("current_chapter", 1)

            # 获取章节类型指导（简化版，不强制）
            chapter_type = self._get_chapter_type(current_chapter)

            # 构建提示词
            prompt = f"""
请续写小说的第{current_chapter}章。

=== 全书概要 ===
{book_summary}

=== 风格锚点（第1章开头，请保持一致的文风）===
{style_anchor}

=== 最近章节原文（请从最后一章结尾处自然衔接）===
{recent_chapters_text}

=== 角色当前状态 ===
{character_status}

=== 活跃伏笔 ===
{foreshadowing}

=== 当前叙事阶段 ===
阶段：{narrative_phase.get('phase', 'unknown')}
任务：{narrative_phase.get('mission', '推进故事发展')}

=== 本章类型参考 ===
类型：{chapter_type['display_name']} - {chapter_type['description']}

=== 写作要求 ===
1. 【最重要】直接从上一章结尾处自然衔接，不要重复上文内容
2. 【重要】保持与风格锚点一致的文风和语气
3. 【重要】字数必须在3000-5000字之间
4. 人物性格和行为必须与角色状态描述一致
5. 可以适当推进或呼应活跃伏笔
6. 情节发展要符合当前叙事阶段
7. 结尾设置悬念钩子，吸引读者继续阅读
8. 通过对话、环境描写、心理活动等丰富内容

请直接输出小说正文内容，不要输出任何解释或说明。
"""

            messages = [
                {"role": "system", "content": """你是一个专业的小说作家，擅长长篇小说续写。

【重要约束】
1. 你必须严格遵循给定的角色设定，主角名称、性格、职业必须在正文中体现
2. 绝对不能擅自创建或引入用户需求中没有的角色
3. 必须以给定的主角视角展开故事
4. 地点、背景必须与之前章节保持一致
5. 人物性格和行为必须与角色状态描述一致
6. 你的每章作品都必须写够3000字以上
7. 请直接输出小说正文内容"""},
                {"role": "user", "content": prompt}
            ]

            # 使用最大token限制
            response = self.call_llm(messages, max_tokens=config.CHAPTER_MAX_TOKENS)

            # 构建返回结果
            result = {
                "title": storyline.get("chapter_title", f"第{current_chapter}章"),
                "content": response,
                "summary": "",
                "key_events": storyline.get("key_events", []),
                "character_development": "",
                "foreshadowing": storyline.get("foreshadowing", []),
                "next_chapter_hint": "",
                "consistency_notes": ""
            }

            # 计算字数
            content = result.get("content", "")
            if content:
                clean_content = content.replace(' ', '').replace('\n', '').replace('\r', '').replace('\t', '').replace('\u3000', '')
                result['word_count'] = len(clean_content)

            self.log(f"长上下文模式章节生成完成，内容长度: {len(content)}")
            return result

        except Exception as e:
            import traceback
            self.log(f"长上下文模式章节生成失败: {e}")
            self.log(f"详细错误: {traceback.format_exc()}")
            return self._create_default_chapter(storyline)

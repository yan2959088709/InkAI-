"""
章节质量分析器
按照中长篇小说创作标准分析章节质量
"""

import re
from typing import Dict, List, Any, Optional
from utils.logger import get_logger

logger = get_logger("chapter_quality_analyzer")


class ChapterQualityAnalyzer:
    """章节质量分析器"""
    
    def __init__(self):
        self.quality_standards = {
            "word_count": {"min": 2500, "max": 5000, "ideal": 3000},
            "opening_words": 300,  # 开篇承接字数
            "conflict_ratio": 0.3,  # 冲突内容占比
            "dialogue_ratio": 0.2,  # 对话占比
        }
    
    def analyze_chapter(self, content: str, chapter_number: int, 
                       previous_chapter: Optional[Dict] = None) -> Dict[str, Any]:
        """
        分析章节质量
        
        Args:
            content: 章节内容
            chapter_number: 章节号
            previous_chapter: 上一章内容（用于检查承接）
        
        Returns:
            质量分析结果
        """
        analysis = {
            "chapter_number": chapter_number,
            "word_count": len(content),
            "structure": self._analyze_structure(content),
            "conflict": self._analyze_conflict(content),
            "pacing": self._analyze_pacing(content),
            "continuity": self._analyze_continuity(content, previous_chapter),
            "quality_score": 0,
            "issues": [],
            "suggestions": []
        }
        
        # 计算质量分数
        analysis["quality_score"] = self._calculate_score(analysis)
        
        # 生成问题和建议
        analysis["issues"] = self._identify_issues(analysis)
        analysis["suggestions"] = self._generate_suggestions(analysis)
        
        return analysis
    
    def _analyze_structure(self, content: str) -> Dict[str, Any]:
        """分析章节结构（黄金结构）"""
        word_count = len(content)
        
        # 按字数划分结构区域
        opening_end = int(word_count * 0.15)  # 前15%
        conflict_start = opening_end
        conflict_end = int(word_count * 0.65)  # 15%-65%
        climax_start = conflict_end
        climax_end = int(word_count * 0.85)  # 65%-85%
        hook_start = climax_end  # 85%-100%
        
        opening = content[:opening_end]
        conflict = content[conflict_start:conflict_end]
        climax = content[climax_start:climax_end]
        hook = content[hook_start:]
        
        return {
            "opening": {
                "content": opening,
                "word_count": len(opening),
                "has_continuation": self._check_continuation(opening),
                "has_goal": self._check_goal(opening)
            },
            "conflict": {
                "content": conflict,
                "word_count": len(conflict),
                "has_action": self._check_action(conflict),
                "has_progression": self._check_progression(conflict)
            },
            "climax": {
                "content": climax,
                "word_count": len(climax),
                "has_turning_point": self._check_turning_point(climax)
            },
            "hook": {
                "content": hook,
                "word_count": len(hook),
                "has_cliffhanger": self._check_cliffhanger(hook)
            }
        }
    
    def _analyze_conflict(self, content: str) -> Dict[str, Any]:
        """分析冲突类型和强度"""
        # 检查外部冲突关键词
        external_keywords = ["战斗", "打斗", "对抗", "追杀", "逃跑", "生死", "危机"]
        external_count = sum(1 for kw in external_keywords if kw in content)
        
        # 检查内部冲突关键词
        internal_keywords = ["挣扎", "纠结", "选择", "矛盾", "恐惧", "犹豫", "痛苦"]
        internal_count = sum(1 for kw in internal_keywords if kw in content)
        
        # 检查人际冲突关键词
        interpersonal_keywords = ["争吵", "对峙", "背叛", "信任", "误会", "分歧", "冲突"]
        interpersonal_count = sum(1 for kw in interpersonal_keywords if kw in content)
        
        # 检查悬念冲突关键词
        suspense_keywords = ["神秘", "谜团", "线索", "疑点", "反转", "真相", "秘密"]
        suspense_count = sum(1 for kw in suspense_keywords if kw in content)
        
        # 确定主要冲突类型
        conflict_types = {
            "external": external_count,
            "internal": internal_count,
            "interpersonal": interpersonal_count,
            "suspense": suspense_count
        }
        
        primary_conflict = max(conflict_types, key=conflict_types.get)
        
        return {
            "types": conflict_types,
            "primary_conflict": primary_conflict,
            "has_conflict": any(v > 0 for v in conflict_types.values()),
            "conflict_intensity": sum(conflict_types.values())
        }
    
    def _analyze_pacing(self, content: str) -> Dict[str, Any]:
        """分析节奏"""
        # 检查对话
        dialogue_markers = ['"', '"', '「', '」', '：', ':']
        dialogue_count = sum(content.count(m) for m in dialogue_markers)
        
        # 检查动作描写
        action_verbs = ["走", "跑", "看", "听", "说", "想", "做", "拿", "放", "打"]
        action_count = sum(content.count(v) for v in action_verbs)
        
        # 检查环境描写
        env_keywords = ["天", "地", "风", "雨", "光", "影", "声音", "气味"]
        env_count = sum(content.count(kw) for kw in env_keywords)
        
        # 检查心理描写
        psych_keywords = ["心里", "想到", "感觉", "觉得", "明白", "意识到"]
        psych_count = sum(content.count(kw) for kw in psych_keywords)
        
        return {
            "dialogue_count": dialogue_count,
            "action_count": action_count,
            "environment_count": env_count,
            "psychology_count": psych_count,
            "is_balanced": self._check_pacing_balance(dialogue_count, action_count, env_count, psych_count)
        }
    
    def _analyze_continuity(self, content: str, previous_chapter: Optional[Dict]) -> Dict[str, Any]:
        """分析与上一章的连贯性"""
        if not previous_chapter:
            return {"has_continuation": False, "issues": []}
        
        issues = []
        
        # 检查是否有重复内容
        prev_content = previous_chapter.get("content", "")
        if prev_content:
            # 取前200字比较
            prev_start = prev_content[:200]
            curr_start = content[:200]
            
            # 简单相似度检查
            similarity = self._calculate_similarity(prev_start, curr_start)
            if similarity > 0.5:
                issues.append(f"开篇与上一章相似度过高: {similarity:.2f}")
        
        # 检查时间线连续性
        # TODO: 更复杂的时间线检查
        
        return {
            "has_continuation": len(issues) == 0,
            "issues": issues
        }
    
    def _check_continuation(self, opening: str) -> bool:
        """检查开篇是否有承接"""
        continuation_markers = ["上一章", "之前", "刚才", "接着", "继续", "然后", "随后"]
        return any(marker in opening for marker in continuation_markers)
    
    def _check_goal(self, opening: str) -> bool:
        """检查开篇是否有目标"""
        goal_markers = ["要", "必须", "想要", "需要", "决定", "打算", "目标"]
        return any(marker in opening for marker in goal_markers)
    
    def _check_action(self, conflict: str) -> bool:
        """检查冲突区域是否有行动"""
        action_verbs = ["走", "跑", "看", "听", "说", "做", "拿", "打", "冲"]
        return any(verb in conflict for verb in action_verbs)
    
    def _check_progression(self, conflict: str) -> bool:
        """检查冲突是否有推进"""
        progression_markers = ["但是", "然而", "突然", "结果", "发现", "意识到"]
        return any(marker in conflict for marker in progression_markers)
    
    def _check_turning_point(self, climax: str) -> bool:
        """检查高潮是否有转折"""
        turning_markers = ["转折", "反转", "真相", "发现", "突然", "原来", "竟然"]
        return any(marker in climax for marker in turning_markers)
    
    def _check_cliffhanger(self, hook: str) -> bool:
        """检查结尾是否有钩子"""
        cliffhanger_markers = ["突然", "但是", "然而", "却发现", "下一章", "接着"]
        return any(marker in hook for marker in cliffhanger_markers)
    
    def _check_pacing_balance(self, dialogue, action, env, psych) -> bool:
        """检查节奏是否平衡"""
        total = dialogue + action + env + psych
        if total == 0:
            return False
        
        # 各部分占比在合理范围内
        ratios = [dialogue/total, action/total, env/total, psych/total]
        return all(0.1 <= r <= 0.5 for r in ratios)
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1)
        words2 = set(text2)
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_score(self, analysis: Dict) -> int:
        """计算质量分数"""
        score = 0
        
        # 字数分数
        word_count = analysis["word_count"]
        if 2500 <= word_count <= 5000:
            score += 20
        elif 2000 <= word_count < 2500 or 5000 < word_count <= 6000:
            score += 10
        
        # 结构分数
        structure = analysis["structure"]
        if structure["opening"]["has_continuation"]:
            score += 10
        if structure["opening"]["has_goal"]:
            score += 10
        if structure["conflict"]["has_action"]:
            score += 10
        if structure["conflict"]["has_progression"]:
            score += 10
        if structure["climax"]["has_turning_point"]:
            score += 15
        if structure["hook"]["has_cliffhanger"]:
            score += 15
        
        # 冲突分数
        conflict = analysis["conflict"]
        if conflict["has_conflict"]:
            score += 10
        
        return min(score, 100)
    
    def _identify_issues(self, analysis: Dict) -> List[str]:
        """识别问题"""
        issues = []
        
        # 字数问题
        word_count = analysis["word_count"]
        if word_count < 2500:
            issues.append(f"字数不足: {word_count} < 2500")
        elif word_count > 5000:
            issues.append(f"字数过多: {word_count} > 5000")
        
        # 结构问题
        structure = analysis["structure"]
        if not structure["opening"]["has_continuation"]:
            issues.append("开篇缺少承接上一章的内容")
        if not structure["opening"]["has_goal"]:
            issues.append("开篇缺少主角目标")
        if not structure["hook"]["has_cliffhanger"]:
            issues.append("结尾缺少钩子")
        
        # 冲突问题
        conflict = analysis["conflict"]
        if not conflict["has_conflict"]:
            issues.append("章节缺少冲突")
        
        # 连贯性问题
        continuity = analysis["continuity"]
        issues.extend(continuity.get("issues", []))
        
        return issues
    
    def _generate_suggestions(self, analysis: Dict) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        # 根据问题生成建议
        issues = analysis["issues"]
        
        if "字数不足" in str(issues):
            suggestions.append("增加冲突描写或人物心理刻画")
        
        if "缺少承接" in str(issues):
            suggestions.append("在开篇添加对上一章结尾的承接")
        
        if "缺少钩子" in str(issues):
            suggestions.append("在结尾添加悬念或转折，吸引读者继续阅读")
        
        if "缺少冲突" in str(issues):
            suggestions.append("增加主角目标与阻碍之间的对抗")
        
        return suggestions


def analyze_chapter_quality(content: str, chapter_number: int, 
                          previous_chapter: Optional[Dict] = None) -> Dict[str, Any]:
    """分析章节质量的便捷函数"""
    analyzer = ChapterQualityAnalyzer()
    return analyzer.analyze_chapter(content, chapter_number, previous_chapter)

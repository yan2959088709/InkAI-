"""
质量熔断器
检测内容重复和质量问题，强制改进或终止流程
防止低质量内容通过系统
"""

from typing import Dict, List, Any, Optional, Tuple
import re
import json
from datetime import datetime
import difflib
from utils.logger import get_logger

logger = get_logger("quality_circuit_breaker")


class QualityCircuitBreaker:
    """质量熔断器"""
    
    def __init__(self, data_manager=None):
        self.data_manager = data_manager
        self.max_retry_attempts = 3
        self.similarity_threshold = 0.7  # 相似度阈值
        self.quality_threshold = 50  # 质量分数阈值
        self.repetition_patterns = {}  # 缓存重复模式
        
    def check_and_enforce(self, novel_id: str, chapter_number: int, 
                         content: Dict[str, Any], content_type: str = "storyline") -> Tuple[bool, Dict[str, Any]]:
        """
        检查内容质量并强制改进
        
        Args:
            novel_id: 小说ID
            chapter_number: 章节号
            content: 待检查内容
            content_type: 内容类型 ("storyline" 或 "chapter")
            
        Returns:
            (is_acceptable, processed_content)
        """
        try:
            # 多维度质量检查
            quality_issues = []
            
            # 1. 重复性检测
            repetition_score, repetition_issues = self._detect_repetition(
                novel_id, chapter_number, content, content_type
            )
            if repetition_score > self.similarity_threshold:
                quality_issues.extend(repetition_issues)
            
            # 2. 内容质量检测
            quality_score, quality_issues_found = self._assess_content_quality(content, content_type)
            if quality_score < self.quality_threshold:
                quality_issues.extend(quality_issues_found)
            
            # 3. 结构完整性检测
            structure_issues = self._check_structure_integrity(content, content_type)
            quality_issues.extend(structure_issues)
            
            # 4. 逻辑一致性检测
            consistency_issues = self._check_logical_consistency(
                novel_id, chapter_number, content
            )
            quality_issues.extend(consistency_issues)
            
            # 如果有质量问题，尝试自动修复
            if quality_issues:
                logger.info(f"检测到质量问题: {quality_issues}")
                fixed_content = self._auto_fix_content(content, quality_issues, content_type)
                
                # 再次检查修复后的内容
                if self._is_content_acceptable(novel_id, chapter_number, fixed_content, content_type):
                    return True, fixed_content
                else:
                    return False, {
                        "error": "内容质量不达标且自动修复失败",
                        "issues": quality_issues,
                        "original_content": content
                    }
            
            return True, content
            
        except Exception as e:
            logger.error(f"质量检查失败: {e}")
            return False, {"error": f"质量检查异常: {e}"}
    
    def _detect_repetition(self, novel_id: str, chapter_number: int, 
                          content: Dict[str, Any], content_type: str) -> Tuple[float, List[str]]:
        """检测内容重复"""
        try:
            # 获取历史内容
            historical_content = self._get_historical_content(novel_id, chapter_number, content_type)
            if not historical_content:
                return 0.0, []
            
            issues = []
            max_similarity = 0.0
            
            # 检查标题重复（如果是故事线）
            if content_type == "storyline" and "chapter_title" in content:
                title_similarity = self._check_title_repetition(
                    content["chapter_title"], historical_content
                )
                if title_similarity > 0.8:
                    issues.append(f"标题重复度过高: {title_similarity:.2f}")
                    max_similarity = max(max_similarity, title_similarity)
            
            # 检查内容重复
            if content_type == "storyline":
                content_text = self._extract_storyline_text(content)
            else:
                content_text = content.get("content", "")
            
            if content_text:
                for historical_item in historical_content[-10:]:  # 检查最近10章
                    if content_type == "storyline":
                        historical_text = self._extract_storyline_text(historical_item)
                    else:
                        historical_text = historical_item.get("content", "")
                    
                    if historical_text:
                        similarity = self._calculate_text_similarity(content_text, historical_text)
                        if similarity > 0.6:
                            issues.append(f"与第{historical_item.get('chapter_number', '?')}章内容重复: {similarity:.2f}")
                            max_similarity = max(max_similarity, similarity)
            
            # 检查特定模式重复
            pattern_similarity = self._check_pattern_repetition(novel_id, content_text)
            if pattern_similarity > 0.7:
                issues.append(f"重复使用固定模式: {pattern_similarity:.2f}")
                max_similarity = max(max_similarity, pattern_similarity)
            
            return max_similarity, issues
            
        except Exception as e:
            logger.error(f"重复检测失败: {e}")
            return 0.0, []
    
    def _assess_content_quality(self, content: Dict[str, Any], 
                              content_type: str) -> Tuple[int, List[str]]:
        """评估内容质量"""
        issues = []
        base_score = 100
        
        try:
            if content_type == "storyline":
                # 故事线质量检查
                required_fields = ["chapter_title", "plot_points", "key_events"]
                for field in required_fields:
                    if field not in content or not content[field]:
                        issues.append(f"缺少必要字段: {field}")
                        base_score -= 20
                
                # 检查情节点数量
                plot_points = content.get("plot_points", [])
                if len(plot_points) < 3:
                    issues.append("情节点过少，缺乏丰富性")
                    base_score -= 15
                
                # 检查关键事件
                key_events = content.get("key_events", [])
                if len(key_events) < 2:
                    issues.append("关键事件过少")
                    base_score -= 10
                    
            else:
                # 章节内容质量检查
                content_text = content.get("content", "")
                if len(content_text) < 1000:
                    issues.append("内容过短")
                    base_score -= 30
                elif len(content_text) < 2000:
                    issues.append("内容偏短")
                    base_score -= 15
                
                # 检查内容多样性
                if self._is_content_monotonous(content_text):
                    issues.append("内容单调，缺乏变化")
                    base_score -= 20
            
            return max(0, base_score), issues
            
        except Exception as e:
            logger.error(f"质量评估失败: {e}")
            return 0, [f"质量评估异常: {e}"]
    
    def _check_structure_integrity(self, content: Dict[str, Any], 
                                 content_type: str) -> List[str]:
        """检查结构完整性"""
        issues = []
        
        try:
            if content_type == "storyline":
                # 故事线结构检查
                if "chapter_ending" not in content:
                    issues.append("缺少章节结尾")
                if "next_chapter_hint" not in content:
                    issues.append("缺少下章预告")
                
                # 检查伏笔设置
                foreshadowing = content.get("foreshadowing", [])
                if not foreshadowing:
                    issues.append("未设置伏笔，可能影响后续发展")
                    
            else:
                # 章节结构检查
                content_text = content.get("content", "")
                if not self._has_proper_structure(content_text):
                    issues.append("章节结构不完整")
                
                # 检查必要元素
                if "summary" not in content:
                    issues.append("缺少章节摘要")
            
            return issues
            
        except Exception as e:
            logger.error(f"结构检查失败: {e}")
            return [f"结构检查异常: {e}"]
    
    def _check_logical_consistency(self, novel_id: str, chapter_number: int, 
                                 content: Dict[str, Any]) -> List[str]:
        """检查逻辑一致性"""
        issues = []
        
        try:
            # 这里可以添加更复杂的逻辑一致性检查
            # 暂时进行简单检查
            
            # 检查角色行为一致性
            if "character_development" in content:
                char_dev = content["character_development"]
                if isinstance(char_dev, str) and "矛盾" in char_dev:
                    issues.append("检测到角色行为矛盾")
            
            return issues
            
        except Exception as e:
            logger.error(f"一致性检查失败: {e}")
            return []
    
    def _auto_fix_content(self, content: Dict[str, Any], issues: List[str], 
                         content_type: str) -> Dict[str, Any]:
        """自动修复内容"""
        fixed_content = content.copy()
        
        try:
            for issue in issues:
                if "标题重复" in issue:
                    # 修复标题重复
                    if "chapter_title" in fixed_content:
                        original_title = fixed_content["chapter_title"]
                        fixed_content["chapter_title"] = self._generate_alternative_title(original_title)
                
                elif "情节点过少" in issue:
                    # 增加情节点
                    plot_points = fixed_content.get("plot_points", [])
                    if len(plot_points) < 3:
                        plot_points.extend(self._generate_additional_plot_points())
                        fixed_content["plot_points"] = plot_points
                
                elif "关键事件过少" in issue:
                    # 增加关键事件
                    key_events = fixed_content.get("key_events", [])
                    if len(key_events) < 2:
                        key_events.extend(self._generate_additional_key_events())
                        fixed_content["key_events"] = key_events
                
                elif "内容过短" in issue:
                    # 标记需要扩展内容
                    fixed_content["_needs_expansion"] = True
                
                elif "缺少伏笔" in issue:
                    # 添加伏笔
                    if "foreshadowing" not in fixed_content:
                        fixed_content["foreshadowing"] = self._generate_basic_foreshadowing()
            
            return fixed_content
            
        except Exception as e:
            logger.error(f"自动修复失败: {e}")
            return content
    
    def _is_content_acceptable(self, novel_id: str, chapter_number: int, 
                             content: Dict[str, Any], content_type: str) -> bool:
        """判断内容是否可接受"""
        try:
            # 重新进行快速检查
            repetition_score, _ = self._detect_repetition(novel_id, chapter_number, content, content_type)
            quality_score, _ = self._assess_content_quality(content, content_type)
            
            return repetition_score <= self.similarity_threshold and quality_score >= self.quality_threshold
            
        except Exception as e:
            logger.error(f"可接受性检查失败: {e}")
            return False
    
    def _get_historical_content(self, novel_id: str, chapter_number: int, 
                              content_type: str) -> List[Dict]:
        """获取历史内容"""
        try:
            if not self.data_manager:
                return []
            
            historical_content = []
            
            if content_type == "storyline":
                # 获取历史故事线
                for i in range(max(1, chapter_number - 15), chapter_number):
                    storyline_file = f"next_chapter_storyline_{i:03d}.json"
                    storyline_data = self.data_manager.load_novel_data(novel_id, storyline_file)
                    if storyline_data:
                        storyline_data["chapter_number"] = i
                        historical_content.append(storyline_data)
            else:
                # 获取历史章节
                chapters = self.data_manager.get_novel_chapters(novel_id)
                for chapter in chapters:
                    if chapter.get("chapter_number", 0) < chapter_number:
                        historical_content.append(chapter)
            
            return historical_content
            
        except Exception as e:
            logger.error(f"获取历史内容失败: {e}")
            return []
    
    def _check_title_repetition(self, title: str, historical_content: List[Dict]) -> float:
        """检查标题重复"""
        max_similarity = 0.0
        
        for historical_item in historical_content[-10:]:  # 检查最近10章
            historical_title = historical_item.get("chapter_title", "")
            if historical_title:
                similarity = self._calculate_text_similarity(title, historical_title)
                max_similarity = max(max_similarity, similarity)
        
        return max_similarity
    
    def _extract_storyline_text(self, storyline: Dict) -> str:
        """提取故事线文本"""
        text_parts = []
        
        # 提取主要文本字段
        for field in ["chapter_title", "scene_setting", "chapter_ending"]:
            if field in storyline and storyline[field]:
                if isinstance(storyline[field], str):
                    text_parts.append(storyline[field])
                elif isinstance(storyline[field], dict):
                    text_parts.append(str(storyline[field]))
        
        # 提取列表字段
        for field in ["plot_points", "key_events", "conflicts"]:
            if field in storyline and storyline[field]:
                if isinstance(storyline[field], list):
                    text_parts.extend([str(item) for item in storyline[field]])
        
        return " ".join(text_parts)
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        if not text1 or not text2:
            return 0.0
        
        # 使用SequenceMatcher计算相似度
        matcher = difflib.SequenceMatcher(None, text1, text2)
        return matcher.ratio()
    
    def _check_pattern_repetition(self, novel_id: str, content_text: str) -> float:
        """检查模式重复"""
        # 简单的模式检查，实际可以更复杂
        common_patterns = [
            "药尘", "透明之花", "紫色纹路", "系统提示", 
            "修为提升", "突破境界", "感受到", "意识到"
        ]
        
        pattern_count = 0
        total_patterns = len(common_patterns)
        
        for pattern in common_patterns:
            if pattern in content_text:
                pattern_count += content_text.count(pattern)
        
        # 计算模式密度
        if len(content_text) > 0:
            pattern_density = pattern_count / len(content_text) * 1000  # 每千字的模式数
            return min(1.0, pattern_density / 10)  # 标准化到0-1
        
        return 0.0
    
    def _is_content_monotonous(self, content_text: str) -> bool:
        """判断内容是否单调"""
        # 简单的单调性检测
        sentences = content_text.split('。')
        if len(sentences) < 5:
            return False
        
        # 检查句子长度变化
        lengths = [len(s) for s in sentences if s.strip()]
        if len(set(lengths)) < len(lengths) * 0.3:  # 长度变化少于30%
            return True
        
        return False
    
    def _has_proper_structure(self, content_text: str) -> bool:
        """检查是否有合适的结构"""
        # 简单的结构检查：是否有对话、描述、动作的混合
        has_dialogue = '"' in content_text or '"' in content_text
        has_description = len(content_text) > 500
        has_paragraphs = content_text.count('\n') > 3
        
        return has_dialogue and has_description and has_paragraphs
    
    def _generate_alternative_title(self, original_title: str) -> str:
        """生成替代标题"""
        # 简单的标题变化策略
        alternatives = [
            f"{original_title}（续）",
            f"新的{original_title}",
            f"{original_title}之后",
            f"再次{original_title}",
            f"{original_title}的延续"
        ]
        
        import random
        return random.choice(alternatives)
    
    def _generate_additional_plot_points(self) -> List[str]:
        """生成额外情节点"""
        return [
            "角色内心冲突加剧",
            "出现新的挑战或障碍",
            "重要信息的揭示"
        ]
    
    def _generate_additional_key_events(self) -> List[str]:
        """生成额外关键事件"""
        return [
            "角色做出重要决定",
            "情节出现转折点"
        ]
    
    def _generate_basic_foreshadowing(self) -> List[str]:
        """生成基础伏笔"""
        return [
            "暗示未来的发展方向",
            "为后续情节埋下伏笔"
        ]

# 数据验证工具类
# 提供小说数据、章节数据的验证功能

from typing import Dict, List, Any
from .text_processor import TextProcessor
from .config import CREATIVE_CONFIG

class DataValidator:
    """数据验证工具类（增强版）"""
    
    @staticmethod
    def validate_novel_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """验证小说数据"""
        errors = []
        warnings = []
        
        # 检查必要字段
        required_fields = ['title', 'characters', 'storyline']
        for field in required_fields:
            if field not in data:
                errors.append(f"缺少必要字段: {field}")
        
        # 检查标题
        if 'title' in data and not data['title']:
            errors.append("标题不能为空")
        
        # 检查人物信息
        if 'characters' in data:
            chars = data['characters']
            if not chars.get('basic_info', {}).get('name'):
                warnings.append("主角姓名未设置")
        
        # 检查故事线
        if 'storyline' in data:
            storyline = data['storyline']
            if not storyline.get('world_setting'):
                warnings.append("世界观设定未完善")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "score": max(0, 100 - len(errors) * 20 - len(warnings) * 5)
        }
    
    @staticmethod
    def validate_chapter_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """验证章节数据"""
        errors = []
        warnings = []
        
        # 检查必要字段
        if not data.get('title'):
            errors.append("章节标题不能为空")
        if not data.get('content'):
            errors.append("章节内容不能为空")
        
        # 检查字数
        content = data.get('content', '')
        word_count = TextProcessor.count_words(content)
        
        if word_count < CREATIVE_CONFIG['min_chapter_length']:
            warnings.append(f"章节字数过少: {word_count}字")
        elif word_count > CREATIVE_CONFIG['max_chapter_length']:
            warnings.append(f"章节字数过多: {word_count}字")
        
        # 检查可读性
        readability_score = TextProcessor.calculate_readability_score(content)
        if readability_score < 60:
            warnings.append(f"文本可读性较低: {readability_score}分")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "word_count": word_count,
            "readability_score": readability_score,
            "score": max(0, 100 - len(errors) * 30 - len(warnings) * 10)
        }

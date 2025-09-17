# 文本处理工具类
# 提供文本统计、关键词提取、文本清理等功能

import re
from typing import List, Tuple

# 可选：中文处理库
try:
    import jieba
    import jieba.analyse
    HAS_JIEBA = True
except ImportError:
    HAS_JIEBA = False

class TextProcessor:
    """文本处理工具类（增强版）"""
    
    @staticmethod
    def count_words(text: str) -> int:
        """统计字数"""
        if not text:
            return 0
        return len(text.replace(' ', '').replace('\n', ''))
    
    @staticmethod
    def extract_keywords(text: str, top_k: int = 10) -> List[str]:
        """提取关键词"""
        if not HAS_JIEBA:
            # 简单的中文关键词提取
            words = re.findall(r'[\u4e00-\u9fff]+', text)
            word_count = {}
            for word in words:
                if len(word) >= 2:
                    word_count[word] = word_count.get(word, 0) + 1
            return [word for word, _ in sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:top_k]]
        else:
            # 使用jieba进行关键词提取
            keywords = jieba.analyse.extract_tags(text, topK=top_k)
            return keywords
    
    @staticmethod
    def clean_text(text: str) -> str:
        """清理文本"""
        if not text:
            return ""
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        # 移除特殊字符
        text = re.sub(r'[^\w\s\u4e00-\u9fff，。！？；：""''（）【】]', '', text)
        return text.strip()
    
    @staticmethod
    def format_chapter_content(content: str, title: str = "") -> str:
        """格式化章节内容"""
        if not content:
            return ""
        formatted = ""
        if title:
            formatted += f"{title}\n"
            formatted += "=" * len(title) + "\n"
        # 分段处理
        paragraphs = content.split('\n')
        for para in paragraphs:
            para = para.strip()
            if para:
                formatted += para + "\n"
        return formatted
    
    @staticmethod
    def calculate_readability_score(text: str) -> float:
        """计算文本可读性得分"""
        if not text:
            return 0.0
        
        # 简单的可读性计算
        sentences = text.count('。') + text.count('！') + text.count('？')
        words = len(text.replace(' ', '').replace('\n', ''))
        
        if sentences == 0:
            return 0.0
        
        avg_words_per_sentence = words / sentences
        
        # 基于平均句长的可读性得分（0-100）
        if avg_words_per_sentence <= 10:
            return 90
        elif avg_words_per_sentence <= 20:
            return 80
        elif avg_words_per_sentence <= 30:
            return 70
        else:
            return 60

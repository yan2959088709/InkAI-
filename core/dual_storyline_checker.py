"""
双线咬合检查器
确保明暗线有强咬合

改进：
- 改为"检查交汇点"而非"强制交汇"
- 有自然交汇点则强化，无则铺垫
- 咬合强度随剧情阶段变化
"""

from typing import Dict, List, Any, Optional
from utils.logger import get_logger

logger = get_logger("dual_storyline_checker")


class DualStorylineChecker:
    """双线咬合检查器"""
    
    # 双线类型定义
    STORYLINE_TYPES = {
        "bright": {
            "name": "明线",
            "description": "表层事件（如主角查连环凶案）",
            "keywords": ["鉴定", "冒险", "行动", "调查", "对抗"]
        },
        "dark": {
            "name": "暗线", 
            "description": "核心真相/人物执念（如主角童年创伤的真相）",
            "keywords": ["真相", "秘密", "回忆", "执念", "阴谋"]
        }
    }
    
    # 咬合强度配置
    LINK_STRENGTH = {
        "weak": {
            "name": "弱咬合",
            "description": "开端阶段，暗线仅铺垫",
            "require_intersection": False
        },
        "medium": {
            "name": "中咬合",
            "description": "中段阶段，双线交叉",
            "require_intersection": False  # 改为检查而非强制
        },
        "strong": {
            "name": "强咬合",
            "description": "结尾阶段，双线汇合",
            "require_intersection": True
        }
    }
    
    def __init__(self, check_interval: int = 3):
        self.check_interval = check_interval  # 检查间隔（而非强制间隔）
    
    def check_intersection_point(self, chapter_number: int, 
                                total_chapters: int,
                                chapter_content: str = "") -> Dict[str, Any]:
        """
        检查双线交汇点（非强制）
        
        改进：检查是否有自然交汇点，而非强制要求
        """
        # 计算咬合强度
        link_strength = self._get_link_strength(chapter_number, total_chapters)
        
        # 检查是否到了检查点
        should_check = chapter_number % self.check_interval == 0
        
        # 分析内容中的双线元素
        bright_elements = []
        dark_elements = []
        
        if chapter_content:
            for keyword in self.STORYLINE_TYPES["bright"]["keywords"]:
                if keyword in chapter_content:
                    bright_elements.append(keyword)
            
            for keyword in self.STORYLINE_TYPES["dark"]["keywords"]:
                if keyword in chapter_content:
                    dark_elements.append(keyword)
        
        # 检查是否有自然交汇点
        has_natural_intersection = len(bright_elements) > 0 and len(dark_elements) > 0
        
        # 生成指导
        guidance = self._generate_guidance(
            chapter_number, 
            link_strength, 
            should_check, 
            has_natural_intersection,
            bright_elements,
            dark_elements
        )
        
        return {
            "chapter_number": chapter_number,
            "should_check": should_check,
            "link_strength": link_strength,
            "has_natural_intersection": has_natural_intersection,
            "bright_elements": bright_elements,
            "dark_elements": dark_elements,
            "guidance": guidance
        }
    
    def _get_link_strength(self, chapter_number: int, total_chapters: int) -> str:
        """获取咬合强度（根据剧情阶段）"""
        if total_chapters <= 0:
            return "medium"
        
        ratio = chapter_number / total_chapters
        
        if ratio <= 0.25:
            return "weak"  # 开端：弱咬合
        elif ratio <= 0.75:
            return "medium"  # 中段：中咬合
        else:
            return "strong"  # 结尾：强咬合
    
    def _generate_guidance(self, chapter_number: int, link_strength: str,
                          should_check: bool, has_natural_intersection: bool,
                          bright_elements: List[str], 
                          dark_elements: List[str]) -> str:
        """生成指导"""
        strength_config = self.LINK_STRENGTH[link_strength]
        
        guidance = f"""
【双线咬合信息】：
- 咬合强度：{strength_config['name']}（{strength_config['description']}）
- 是否检查点：{'是' if should_check else '否'}
- 明线元素：{', '.join(bright_elements[:3]) if bright_elements else '无'}
- 暗线元素：{', '.join(dark_elements[:3]) if dark_elements else '无'}
"""
        
        if has_natural_intersection:
            guidance += """
【自然交汇检测】：
检测到明暗线元素同时存在，建议强化交汇效果！

交汇方式：
1. 明线事件直接关联暗线真相
2. 暗线伏笔影响明线发展
3. 让读者产生"原来如此"的爽感
"""
        elif should_check:
            if link_strength == "strong":
                guidance += """
【强咬合要求】：
本章是检查点且处于结尾阶段，必须有双线交汇！

交汇方式：
1. 明线的突破直接揭示暗线真相
2. 暗线的伏笔成为明线的关键
3. 双线汇合推向大高潮
"""
            else:
                guidance += """
【咬合建议】：
本章是检查点，但非强制交汇。

建议：
1. 如果有自然交汇点，强化它
2. 如果没有，可以继续铺垫暗线
3. 不要强行插入，保持剧情自然
"""
        else:
            guidance += """
【当前建议】：
本章不是检查点，保持当前剧情发展即可。

建议：
1. 专注于当前章节的核心冲突
2. 暗线可以暂时不提，等合适时机
3. 不要为了咬合而咬合
"""
        
        return guidance
    
    def analyze_intersection_quality(self, content: str) -> Dict[str, Any]:
        """分析交汇质量"""
        paragraphs = content.split('\n\n')
        
        intersection_points = []
        
        for para in paragraphs:
            has_bright = any(kw in para for kw in self.STORYLINE_TYPES["bright"]["keywords"])
            has_dark = any(kw in para for kw in self.STORYLINE_TYPES["dark"]["keywords"])
            
            if has_bright and has_dark:
                intersection_points.append({
                    "content": para[:100] + "..." if len(para) > 100 else para,
                    "bright_keywords": [kw for kw in self.STORYLINE_TYPES["bright"]["keywords"] if kw in para],
                    "dark_keywords": [kw for kw in self.STORYLINE_TYPES["dark"]["keywords"] if kw in para]
                })
        
        return {
            "has_intersection": len(intersection_points) > 0,
            "intersection_count": len(intersection_points),
            "intersection_points": intersection_points,
            "quality_score": min(100, len(intersection_points) * 30)  # 每个交汇点30分
        }
    
    # 保持向后兼容
    def check_intersection_required(self, chapter_number: int) -> bool:
        """检查本章是否需要双线交汇（向后兼容）"""
        return chapter_number % self.check_interval == 0
    
    def analyze_storyline_content(self, content: str, chapter_number: int,
                                 total_chapters: int = 40) -> Dict[str, Any]:
        """
        分析章节内容中的双线咬合情况（向后兼容）
        """
        result = self.check_intersection_point(chapter_number, total_chapters, content)
        
        # 转换为旧格式
        return {
            "chapter_number": chapter_number,
            "bright_line_elements": result["bright_elements"],
            "dark_line_elements": result["dark_elements"],
            "intersection_points": [],
            "is_intersection_required": result["should_check"],
            "has_intersection": result["has_natural_intersection"],
            "quality_score": 100 if result["has_natural_intersection"] else 50
        }
    
    def get_intersection_guidance(self, chapter_number: int) -> str:
        """获取双线交汇指导（向后兼容）"""
        result = self.check_intersection_point(chapter_number, 40, "")
        return result["guidance"]


def check_dual_storyline_intersection(content: str, chapter_number: int,
                                      total_chapters: int = 40) -> Dict[str, Any]:
    """检查双线交汇的便捷函数"""
    checker = DualStorylineChecker()
    return checker.check_intersection_point(chapter_number, total_chapters, content)


def get_intersection_guidance(chapter_number: int) -> str:
    """获取双线交汇指导的便捷函数"""
    checker = DualStorylineChecker()
    return checker.get_intersection_guidance(chapter_number)

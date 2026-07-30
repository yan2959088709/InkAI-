"""
伏笔强制回收器
到回收节点时，强制回收伏笔，杜绝烂尾

功能：
1. 检测到期伏笔
2. 强制插入回收剧情
3. 拒绝生成新内容直到伏笔回收
"""

from typing import Dict, List, Any, Optional
from utils.logger import get_logger

logger = get_logger("foreshadowing_recycler")


class ForeshadowingRecycler:
    """伏笔强制回收器"""
    
    # 伏笔回收期限
    RECYCLE_DEADLINES = {
        "short": 3,   # 短伏笔3章内回收
        "medium": 20, # 中伏笔20章内回收
        "long": 999   # 长伏笔全书回收
    }
    
    def __init__(self):
        pass
    
    def check_overdue_foreshadowing(self, novel_id: str, chapter_number: int,
                                    chapters: List[Dict]) -> List[Dict]:
        """
        检查到期未回收的伏笔
        
        Args:
            novel_id: 小说ID
            chapter_number: 当前章节号
            chapters: 所有章节
        
        Returns:
            到期未回收的伏笔列表
        """
        overdue = []
        
        # 收集所有伏笔及其埋设章节
        all_foreshadowing = {}
        
        for ch in chapters:
            ch_num = ch.get("chapter_number", 0)
            foreshadowing = ch.get("foreshadowing", [])
            
            for fs in foreshadowing:
                if isinstance(fs, str):
                    # 简单伏笔（字符串）
                    if fs not in all_foreshadowing:
                        all_foreshadowing[fs] = {
                            "content": fs,
                            "planted_chapter": ch_num,
                            "type": self._classify_foreshadowing(fs),
                            "status": "active"
                        }
                elif isinstance(fs, dict):
                    # 结构化伏笔
                    fs_content = fs.get("content", "")
                    if fs_content and fs_content not in all_foreshadowing:
                        all_foreshadowing[fs_content] = {
                            "content": fs_content,
                            "planted_chapter": fs.get("planted_chapter", ch_num),
                            "type": fs.get("type", "medium"),
                            "status": fs.get("status", "active")
                        }
        
        # 检查哪些伏笔到期了
        for fs_content, fs_info in all_foreshadowing.items():
            if fs_info["status"] != "active":
                continue
            
            planted = fs_info["planted_chapter"]
            elapsed = chapter_number - planted
            fs_type = fs_info["type"]
            deadline = self.RECYCLE_DEADLINES.get(fs_type, 20)
            
            # 检查是否已回收
            is_recycled = self._check_if_recycled(fs_content, chapters, planted)
            
            if not is_recycled and elapsed >= deadline:
                overdue.append({
                    "content": fs_content,
                    "planted_chapter": planted,
                    "current_chapter": chapter_number,
                    "elapsed_chapters": elapsed,
                    "type": fs_type,
                    "deadline": deadline,
                    "urgency": "high" if elapsed > deadline else "medium"
                })
        
        # 按紧急程度排序
        overdue.sort(key=lambda x: (-1 if x["urgency"] == "high" else 0, -x["elapsed_chapters"]))
        
        return overdue
    
    def _classify_foreshadowing(self, content: str) -> str:
        """分类伏笔类型"""
        # 简单分类逻辑
        short_keywords = ["钥匙", "信件", "照片", "小物件"]
        long_keywords = ["真相", "秘密", "命运", "预言", "诅咒"]
        
        for kw in short_keywords:
            if kw in content:
                return "short"
        
        for kw in long_keywords:
            if kw in content:
                return "long"
        
        return "medium"
    
    def _check_if_recycled(self, foreshadowing: str, chapters: List[Dict],
                          planted_chapter: int) -> bool:
        """检查伏笔是否已回收"""
        # 在后续章节中查找是否提到这个伏笔的解决
        recycle_keywords = ["回收", "揭晓", "解开", "真相", "原来", "终于明白"]
        
        for ch in chapters:
            ch_num = ch.get("chapter_number", 0)
            if ch_num <= planted_chapter:
                continue
            
            content = ch.get("content", "")
            
            # 检查是否包含伏笔内容和回收关键词
            if foreshadowing in content:
                for kw in recycle_keywords:
                    if kw in content:
                        return True
        
        return False
    
    def generate_recycle_guidance(self, overdue_foreshadowing: List[Dict]) -> str:
        """生成回收指导"""
        if not overdue_foreshadowing:
            return ""
        
        guidance = """
【伏笔强制回收要求】：
本章必须回收以下到期伏笔，拒绝生成新内容直到伏笔回收！

到期伏笔：
"""
        
        for i, fs in enumerate(overdue_foreshadowing, 1):
            urgency = "紧急" if fs["urgency"] == "high" else "需回收"
            guidance += f"""
{i}. 【{urgency}】{fs['content']}
   - 埋设章节：第{fs['planted_chapter']}章
   - 已过：{fs['elapsed_chapters']}章
   - 回收期限：{fs['type']}伏笔，{fs['deadline']}章内
"""
        
        guidance += """
【回收方式】：
1. 在本章情节中自然揭示伏笔真相
2. 通过角色对话或行动解开谜团
3. 伏笔回收后才能推进新剧情
"""
        
        return guidance
    
    def should_force_recycle(self, overdue_foreshadowing: List[Dict]) -> bool:
        """检查是否需要强制回收"""
        if not overdue_foreshadowing:
            return False
        
        # 有紧急伏笔必须回收
        for fs in overdue_foreshadowing:
            if fs["urgency"] == "high":
                return True
        
        # 有多个到期伏笔也必须回收
        if len(overdue_foreshadowing) >= 2:
            return True
        
        return False


def check_overdue_foreshadowing(novel_id: str, chapter_number: int,
                               chapters: List[Dict]) -> List[Dict]:
    """检查到期伏笔的便捷函数"""
    recycler = ForeshadowingRecycler()
    return recycler.check_overdue_foreshadowing(novel_id, chapter_number, chapters)


def get_recycle_guidance(overdue_foreshadowing: List[Dict]) -> str:
    """获取回收指导的便捷函数"""
    recycler = ForeshadowingRecycler()
    return recycler.generate_recycle_guidance(overdue_foreshadowing)

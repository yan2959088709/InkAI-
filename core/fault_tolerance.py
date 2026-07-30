"""
容错机制增强
解决批量续写中断的问题

功能：
1. 自动重试（最多3次）
2. 断点增量生成
3. 降级策略（过渡章节）
"""

from typing import Dict, Any, Optional, Callable
import time
from utils.logger import get_logger

logger = get_logger("fault_tolerance")


class FaultToleranceManager:
    """容错管理器"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        "max_retries": 3,  # 最大重试次数
        "retry_delay": 5,  # 重试延迟（秒）
        "enable_fallback": True,  # 启用降级策略
        "fallback_chapter_type": "buffer"  # 降级章节类型
    }
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = self.DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)
        
        # 失败记录
        self.failed_chapters = {}
    
    def execute_with_retry(self, func: Callable, chapter_number: int,
                          *args, **kwargs) -> Dict[str, Any]:
        """
        带重试的执行
        
        Args:
            func: 要执行的函数
            chapter_number: 章节号
            *args, **kwargs: 函数参数
        
        Returns:
            执行结果
        """
        max_retries = self.config["max_retries"]
        retry_delay = self.config["retry_delay"]
        
        for attempt in range(max_retries):
            try:
                result = func(*args, **kwargs)
                
                if result and not result.get("error"):
                    # 成功
                    if chapter_number in self.failed_chapters:
                        del self.failed_chapters[chapter_number]
                    return result
                else:
                    error = result.get("error", "未知错误") if result else "返回空"
                    logger.warning(f"第{chapter_number}章尝试{attempt + 1}失败: {error}")
                    
            except Exception as e:
                logger.error(f"第{chapter_number}章尝试{attempt + 1}异常: {e}")
            
            # 等待后重试
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        
        # 所有重试失败
        logger.error(f"第{chapter_number}章重试{max_retries}次均失败")
        
        # 记录失败
        self.failed_chapters[chapter_number] = {
            "chapter_number": chapter_number,
            "attempts": max_retries,
            "timestamp": time.time()
        }
        
        # 返回降级结果
        if self.config["enable_fallback"]:
            return self._create_fallback_chapter(chapter_number)
        
        return {"error": f"第{chapter_number}章生成失败，已重试{max_retries}次"}
    
    def _create_fallback_chapter(self, chapter_number: int) -> Dict[str, Any]:
        """
        创建降级章节（过渡章节）
        
        优化：更轻量，最短篇幅，最小冲突，只承上启下
        """
        logger.info(f"为第{chapter_number}章创建降级过渡章节")
        
        # 3套轻量模板，保证不水、不崩、不影响主线
        templates = [
            {
                "name": "时间过渡",
                "content": f"""第{chapter_number}章

夜幕降临，古玩街逐渐安静下来。

林澈站在窗前，望着远处的灯火。今天的经历让他思绪万千，但他知道，明天还有更多的事情等待着他。

"该休息了。"他轻声说道。

（过渡章节）"""
            },
            {
                "name": "场景切换",
                "content": f"""第{chapter_number}章

清晨的阳光透过窗帘，新的一天开始了。

林澈整理好行装，准备出发。今天的计划已经安排妥当，他只需要按部就班地执行。

一切都在朝着预期的方向发展。

（过渡章节）"""
            },
            {
                "name": "内心独白",
                "content": f"""第{chapter_number}章

林澈独自坐在房间里，回顾着最近发生的事情。

很多事情超出了他的预料，但他并没有退缩。相反，这些挑战让他更加坚定了自己的信念。

"继续前进吧。"他对自己说。

（过渡章节）"""
            }
        ]
        
        # 随机选择模板
        import random
        template = random.choice(templates)
        
        content = template["content"]
        
        return {
            "success": True,
            "chapter_content": {
                "title": f"第{chapter_number}章",
                "content": content,
                "is_fallback": True,  # 标记为降级章节
                "fallback_type": template["name"],
                "word_count": len(content)
            },
            "is_fallback": True
        }
    
    def get_failed_chapters(self) -> Dict[int, Dict]:
        """获取失败章节列表"""
        return self.failed_chapters.copy()
    
    def clear_failed_chapters(self):
        """清除失败记录"""
        self.failed_chapters.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_failed": len(self.failed_chapters),
            "failed_chapters": list(self.failed_chapters.keys()),
            "config": self.config
        }


class IncrementalGenerator:
    """增量生成器 - 支持断点续写"""
    
    def __init__(self, data_manager=None):
        self.data_manager = data_manager
    
    def get_remaining_chapters(self, novel_id: str, 
                              target_chapters: int) -> int:
        """获取剩余需要生成的章节数"""
        if not self.data_manager:
            return target_chapters
        
        existing_chapters = self.data_manager.get_chapters(novel_id)
        current_count = len(existing_chapters)
        
        remaining = target_chapters - current_count
        return max(0, remaining)
    
    def get_start_chapter(self, novel_id: str) -> int:
        """获取起始章节号"""
        if not self.data_manager:
            return 1
        
        existing_chapters = self.data_manager.get_chapters(novel_id)
        
        if existing_chapters:
            last_chapter = max(ch.get("chapter_number", 0) for ch in existing_chapters)
            return last_chapter + 1
        else:
            return 1
    
    def should_skip_chapter(self, novel_id: str, chapter_number: int) -> bool:
        """检查是否应该跳过某章（已存在）"""
        if not self.data_manager:
            return False
        
        existing_chapters = self.data_manager.get_chapters(novel_id)
        
        for ch in existing_chapters:
            if ch.get("chapter_number") == chapter_number:
                return True
        
        return False


def execute_with_retry(func: Callable, chapter_number: int,
                      *args, **kwargs) -> Dict[str, Any]:
    """带重试执行的便捷函数"""
    manager = FaultToleranceManager()
    return manager.execute_with_retry(func, chapter_number, *args, **kwargs)

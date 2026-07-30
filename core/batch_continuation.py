"""
批量续写功能
支持批量生成多章，用于上千章小说的快速创作

功能：
1. 批量续写指定数量的章节
2. 自动进度保存
3. 断点续写
4. 进度追踪
5. 容错机制（自动重试、降级章节）
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import json
import time
from utils.logger import get_logger

logger = get_logger("batch_continuation")


class BatchContinuationManager:
    """批量续写管理器"""
    
    def __init__(self, workflow=None, data_manager=None, enable_fault_tolerance: bool = True):
        self.workflow = workflow
        self.data_manager = data_manager
        self.progress_file = "batch_progress.json"
        self.enable_fault_tolerance = enable_fault_tolerance
        self.fault_manager = None  # 延迟初始化
    
    def _get_fault_manager(self):
        """获取容错管理器"""
        if self.fault_manager is None and self.enable_fault_tolerance:
            from core.fault_tolerance import FaultToleranceManager
            self.fault_manager = FaultToleranceManager()
        return self.fault_manager
        
    def batch_continue(self, novel_id: str, num_chapters: int,
                      start_chapter: int = None,
                      chapters_per_volume: int = 40,
                      progress_callback: Callable = None) -> Dict[str, Any]:
        """
        批量续写章节
        
        Args:
            novel_id: 小说ID
            num_chapters: 要续写的章节数
            start_chapter: 起始章节号（默认从当前最后一章+1开始）
            chapters_per_volume: 每卷章节数
            progress_callback: 进度回调函数
        
        Returns:
            批量续写结果
        """
        from inkai_workflow_optimized import InkAIWorkflowOptimized
        from workflow_context import WorkflowContext
        from core.volume_manager import VolumeManager
        
        # 初始化工作流
        if self.workflow is None:
            self.workflow = InkAIWorkflowOptimized()
        
        if self.data_manager is None:
            from data_manager import DataManager
            self.data_manager = DataManager()
        
        volume_manager = VolumeManager(self.data_manager)
        
        # 获取起始章节
        if start_chapter is None:
            chapters = self.data_manager.get_chapters(novel_id)
            start_chapter = len(chapters) + 1
        
        end_chapter = start_chapter + num_chapters - 1
        
        logger.info(f"开始批量续写: 第{start_chapter}章到第{end_chapter}章 (共{num_chapters}章)")
        
        # 记录开始时间
        start_time = time.time()
        
        # 结果统计
        result = {
            "novel_id": novel_id,
            "start_chapter": start_chapter,
            "end_chapter": end_chapter,
            "total_chapters": num_chapters,
            "completed_chapters": 0,
            "failed_chapters": 0,
            "failed_chapter_list": [],
            "success_chapters": [],
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "elapsed_seconds": 0,
            "average_time_per_chapter": 0
        }
        
        # 逐章续写
        for chapter_num in range(start_chapter, end_chapter + 1):
            chapter_start_time = time.time()
            
            # 使用容错机制续写单章
            chapter_success = self._write_single_chapter_with_retry(
                novel_id, chapter_num, chapters_per_volume, volume_manager, result
            )
            
            if chapter_success:
                result["completed_chapters"] += 1
                result["success_chapters"].append(chapter_num)
                
                chapter_elapsed = time.time() - chapter_start_time
                logger.info(f"第{chapter_num}章完成 (耗时: {chapter_elapsed:.0f}秒)")
            else:
                result["failed_chapters"] += 1
                result["failed_chapter_list"].append(chapter_num)
            
            # 进度回调
            if progress_callback:
                progress_callback({
                    "chapter_number": chapter_num,
                    "completed": result["completed_chapters"],
                    "total": num_chapters,
                    "progress": result["completed_chapters"] / num_chapters
                })
            
            # 保存进度
            self._save_progress(novel_id, chapter_num, result)
            
            # 检查是否是卷结尾
            volume_info = volume_manager.get_volume_info(novel_id, chapter_num, chapters_per_volume)
            if volume_info["is_volume_end"]:
                self._generate_volume_summary(novel_id, volume_info["volume_number"], chapters_per_volume)
        
        # 计算统计
        end_time = time.time()
        result["end_time"] = datetime.now().isoformat()
        result["elapsed_seconds"] = end_time - start_time
        
        if result["completed_chapters"] > 0:
            result["average_time_per_chapter"] = result["elapsed_seconds"] / result["completed_chapters"]
        
        logger.info(f"\n{'='*50}")
        logger.info(f"批量续写完成!")
        logger.info(f"完成: {result['completed_chapters']}/{num_chapters}章")
        logger.info(f"失败: {result['failed_chapters']}章")
        logger.info(f"总耗时: {result['elapsed_seconds']:.0f}秒")
        logger.info(f"平均每章: {result['average_time_per_chapter']:.0f}秒")
        logger.info(f"{'='*50}")
        
        return result
    
    def _write_single_chapter_with_retry(self, novel_id: str, chapter_num: int,
                                        chapters_per_volume: int, volume_manager,
                                        result: Dict) -> bool:
        """
        使用容错机制续写单章
        
        Returns:
            是否成功
        """
        from workflow_context import WorkflowContext
        
        fault_manager = self._get_fault_manager()
        
        def write_chapter():
            """续写单章的核心逻辑"""
            logger.info(f"\n{'='*50}")
            logger.info(f"正在写第{chapter_num}章...")
            logger.info(f"{'='*50}")
            
            # 获取卷信息
            volume_info = volume_manager.get_volume_info(novel_id, chapter_num, chapters_per_volume)
            logger.info(f"第{volume_info['volume_number']}卷, 卷内第{volume_info['chapter_in_volume']}章")
            
            # 加载上下文
            self.workflow.context = WorkflowContext(novel_id)
            self.workflow.context.load_context(novel_id)
            
            storyline = self.data_manager.load_novel_data(novel_id, "storyline")
            characters = self.data_manager.load_novel_data(novel_id, "characters")
            tags = self.data_manager.load_novel_data(novel_id, "tags")
            chapters = self.data_manager.get_chapters(novel_id)
            
            self.workflow.context.set_storyline(storyline)
            self.workflow.context.set_characters(characters)
            self.workflow.context.set_tags(tags)
            self.workflow.context.is_continuation = True
            
            self.workflow.context.continuation_data = {
                "knowledge_base": {
                    "character_profiles": characters or {},
                    "plot_lines": storyline or {},
                    "chapters": chapters,
                    "tags": tags or {}
                },
                "status": "initialized"
            }
            
            # 生成故事线
            storyline_result = self.workflow.generate_continuation_storyline(novel_id)
            
            if not storyline_result or storyline_result.get("error"):
                return {"error": f"故事线生成失败: {storyline_result.get('error', '未知')}"}
            
            # 写作章节
            chapter_result = self.workflow.write_continuation_chapter(novel_id)
            
            if not chapter_result or chapter_result.get("error"):
                return {"error": f"章节写作失败: {chapter_result.get('error', '未知')}"}
            
            # 保存章节
            save_result = self.workflow.save_continuation_chapter(novel_id)
            
            if not save_result or not save_result.get("success"):
                return {"error": f"章节保存失败"}
            
            return {"success": True}
        
        # 使用容错机制执行
        if fault_manager:
            chapter_result = fault_manager.execute_with_retry(write_chapter, chapter_num)
            
            if chapter_result.get("success"):
                if chapter_result.get("is_fallback"):
                    logger.warning(f"第{chapter_num}章使用降级章节")
                return True
            else:
                return False
        else:
            # 无容错机制，直接执行
            try:
                chapter_result = write_chapter()
                return chapter_result.get("success", False)
            except Exception as e:
                logger.error(f"第{chapter_num}章异常: {e}")
                return False
    
    def _save_progress(self, novel_id: str, chapter_number: int, result: Dict):
        """保存进度"""
        try:
            progress = {
                "novel_id": novel_id,
                "last_chapter": chapter_number,
                "result": result,
                "updated_at": datetime.now().isoformat()
            }
            
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"保存进度失败: {e}")
    
    def load_progress(self, novel_id: str) -> Optional[Dict[str, Any]]:
        """加载进度"""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    progress = json.load(f)
                    if progress.get("novel_id") == novel_id:
                        return progress
            return None
        except Exception as e:
            logger.error(f"加载进度失败: {e}")
            return None
    
    def _generate_volume_summary(self, novel_id: str, volume_number: int,
                                chapters_per_volume: int) -> bool:
        """生成卷摘要"""
        try:
            from core.volume_manager import VolumeManager
            
            volume_manager = VolumeManager(self.data_manager)
            
            # 获取卷内所有章节
            chapters = self.data_manager.get_chapters(novel_id)
            volume_start = (volume_number - 1) * chapters_per_volume + 1
            volume_end = volume_number * chapters_per_volume
            
            volume_chapters = [
                ch for ch in chapters 
                if volume_start <= ch.get("chapter_number", 0) <= volume_end
            ]
            
            if not volume_chapters:
                return False
            
            # 构建卷摘要
            summary = {
                "volume_number": volume_number,
                "chapters_count": len(volume_chapters),
                "chapter_range": f"第{volume_start}-{volume_end}章",
                "titles": [ch.get("title", "") for ch in volume_chapters],
                "key_events": [],
                "main_plot": "",
                "character_developments": [],
                "foreshadowing": [],
                "next_volume_hook": ""
            }
            
            # 提取关键事件
            for ch in volume_chapters:
                key_events = ch.get("key_events", [])
                summary["key_events"].extend(key_events[:2])  # 每章取前2个事件
            
            # 保存
            volume_manager.save_volume_summary(novel_id, volume_number, summary)
            logger.info(f"第{volume_number}卷摘要已生成")
            
            return True
            
        except Exception as e:
            logger.error(f"生成卷摘要失败: {e}")
            return False
    
    def resume_batch(self, novel_id: str, remaining_chapters: int,
                    chapters_per_volume: int = 40,
                    progress_callback: Callable = None) -> Dict[str, Any]:
        """
        断点续写
        
        Args:
            novel_id: 小说ID
            remaining_chapters: 剩余要写的章节数
            chapters_per_volume: 每卷章节数
            progress_callback: 进度回调
        
        Returns:
            续写结果
        """
        # 加载进度
        progress = self.load_progress(novel_id)
        
        if progress:
            last_chapter = progress.get("last_chapter", 0)
            start_chapter = last_chapter + 1
            logger.info(f"从第{start_chapter}章继续续写")
        else:
            chapters = self.data_manager.get_chapters(novel_id)
            start_chapter = len(chapters) + 1
            logger.info(f"未找到进度，从第{start_chapter}章开始")
        
        return self.batch_continue(
            novel_id, 
            remaining_chapters,
            start_chapter,
            chapters_per_volume,
            progress_callback
        )


def batch_continue_novel(novel_id: str, num_chapters: int,
                        start_chapter: int = None) -> Dict[str, Any]:
    """批量续写的便捷函数"""
    manager = BatchContinuationManager()
    return manager.batch_continue(novel_id, num_chapters, start_chapter)

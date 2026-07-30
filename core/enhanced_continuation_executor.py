"""
增强版续写执行器
集成新的综合小说生成系统
"""

import os
import sys
import json
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comprehensive_novel_generation_system import ComprehensiveNovelGenerationSystem
from data_manager import DataManager
import config
from utils.logger import get_logger
logger = get_logger("enhanced_continuation_executor")


@dataclass
class EnhancedContinuationProgress:
    """增强版续写进度信息"""
    novel_id: str
    novel_title: str
    mode: str  # 'fixed', 'continuous', 'infinite'
    total_chapters: int
    completed_chapters: int
    current_chapter: int
    current_step: str
    status: str  # 'running', 'completed', 'failed', 'paused'
    start_time: str
    last_update: str
    error_message: str = ""
    chapter_details: List[Dict[str, Any]] = None
    quality_scores: List[float] = None
    memory_usage: float = 0.0
    performance_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.chapter_details is None:
            self.chapter_details = []
        if self.quality_scores is None:
            self.quality_scores = []
        if self.performance_metrics is None:
            self.performance_metrics = {}


class EnhancedContinuationExecutor:
    """增强版续写执行器"""
    
    def __init__(self):
        logger.info("🚀 初始化增强版续写执行器...")
        
        # 初始化组件
        self.data_manager = DataManager()
        self.comprehensive_system = ComprehensiveNovelGenerationSystem(self.data_manager)
        
        # 执行状态
        self.running_tasks: Dict[str, EnhancedContinuationProgress] = {}
        self.lock = threading.Lock()
        
        # 状态目录
        self.status_dir = "data/continuation_status"
        os.makedirs(self.status_dir, exist_ok=True)
        
        # 恢复中断的任务
        self._restore_interrupted_tasks()
        
        logger.info("✅ 增强版续写执行器初始化完成")
    
    def start_continuation(self, novel_id: str, novel_title: str, 
                          requirements: str, mode: str = "fixed", 
                          total_chapters: int = 1, continuous_mode: str = "auto") -> Dict[str, Any]:
        """开始续写"""
        
        with self.lock:
            # 检查是否已有任务在运行
            if novel_id in self.running_tasks:
                return {
                    "success": False, 
                    "error": "该小说已有续写任务在运行中"
                }
        
        try:
            logger.info(f"📚 开始续写小说: {novel_id}, 标题: {novel_title}")
            
            # 初始化小说
            if not self.comprehensive_system.initialize_novel(novel_id):
                return {
                    "success": False,
                    "error": "小说初始化失败"
                }
            
            # 获取当前章节数
            chapters = self.data_manager.get_novel_chapters(novel_id)
            current_chapter = len(chapters) + 1
            
            # 创建进度对象
            progress = EnhancedContinuationProgress(
                novel_id=novel_id,
                novel_title=novel_title,
                mode=mode,
                total_chapters=total_chapters,
                completed_chapters=0,
                current_chapter=current_chapter,
                current_step="initialization",
                status="running",
                start_time=datetime.now().isoformat(),
                last_update=datetime.now().isoformat()
            )
            
            # 保存进度
            self._save_progress(progress)
            
            # 添加到运行任务
            with self.lock:
                self.running_tasks[novel_id] = progress
            
            # 启动续写线程
            thread = threading.Thread(
                target=self._execute_continuation,
                args=(progress, requirements, continuous_mode),
                daemon=True
            )
            thread.start()
            
            # 转换为字典格式的进度信息
            progress_dict = asdict(progress)
            
            return {
                "success": True,
                "message": "续写任务已启动",
                "novel_id": novel_id,
                "current_chapter": current_chapter,
                "task_id": novel_id,  # 使用 novel_id 作为 task_id
                "progress": progress_dict  # 添加进度信息
            }
            
        except Exception as e:
            logger.error(f"❌ 启动续写失败: {e}")
            return {
                "success": False,
                "error": f"启动续写失败: {str(e)}"
            }
    
    def _execute_continuation(self, progress: EnhancedContinuationProgress, 
                            requirements: str, continuous_mode: str):
        """执行续写流程"""
        
        try:
            logger.info(f"🔄 开始执行续写流程，模式: {continuous_mode}")
            
            while progress.status == "running":
                # 检查是否被停止
                with self.lock:
                    if progress.novel_id not in self.running_tasks:
                        logger.info(f"🛑 任务已被停止: {progress.novel_id}")
                        progress.status = "stopped"
                        progress.current_step = "stopped"
                        break
                
                # 更新当前步骤
                progress.current_step = f"generating_chapter_{progress.current_chapter}"
                progress.last_update = datetime.now().isoformat()
                self._update_progress(progress)
                
                logger.info(f"✍️ 开始生成第{progress.current_chapter}章...")
                
                # 生成章节
                chapter_result = self.comprehensive_system.generate_chapter(
                    progress.novel_id,
                    progress.current_chapter,
                    requirements
                )
                
                if chapter_result.get("success"):
                    # 章节生成成功
                    chapter_content = chapter_result.get("chapter_content", {})
                    quality_score = chapter_result.get("quality_score", 0)
                    
                    logger.info(f"✅ 第{progress.current_chapter}章生成成功，质量分数: {quality_score}")
                    
                    # 保存章节
                    success = self._save_chapter(progress.novel_id, progress.current_chapter, chapter_content)
                    
                    if success:
                        # 更新进度
                        progress.completed_chapters += 1
                        progress.quality_scores.append(quality_score)
                        
                        # 记录章节详情
                        chapter_detail = {
                            "chapter_number": progress.current_chapter,
                            "completed_at": datetime.now().isoformat(),
                            "status": "completed",
                            "quality_score": quality_score,
                            "word_count": len(str(chapter_content.get("content", "")).split())
                        }
                        progress.chapter_details.append(chapter_detail)
                        
                        # 更新内存使用情况
                        system_status = self.comprehensive_system.get_system_status()
                        memory_report = system_status.get("memory_report", {})
                        memory_status = memory_report.get("memory_status", {})
                        progress.memory_usage = memory_status.get("current_memory_percent", 0)
                        
                        # 更新性能指标
                        progress.performance_metrics = chapter_result.get("performance", {})
                        
                        # 检查是否需要继续
                        if self._should_continue(progress, continuous_mode):
                            progress.current_chapter += 1
                        else:
                            progress.status = "completed"
                            progress.current_step = "completed"
                            logger.info(f"🎉 续写完成，共生成{progress.completed_chapters}章")
                            break
                    else:
                        # 保存失败
                        progress.status = "failed"
                        progress.error_message = "章节保存失败"
                        break
                else:
                    # 章节生成失败
                    error_msg = chapter_result.get("error", "未知错误")
                    logger.error(f"❌ 第{progress.current_chapter}章生成失败: {error_msg}")
                    
                    progress.status = "failed"
                    progress.error_message = f"第{progress.current_chapter}章生成失败: {error_msg}"
                    break
                
                # 短暂休息
                time.sleep(1)
            
            # 更新最终进度
            progress.last_update = datetime.now().isoformat()
            self._update_progress(progress)
            
            # 从运行任务中移除
            with self.lock:
                if progress.novel_id in self.running_tasks:
                    del self.running_tasks[progress.novel_id]
            
        except Exception as e:
            logger.error(f"❌ 续写执行异常: {e}")
            progress.status = "failed"
            progress.error_message = f"续写执行异常: {str(e)}"
            progress.last_update = datetime.now().isoformat()
            self._update_progress(progress)
            
            # 从运行任务中移除
            with self.lock:
                if progress.novel_id in self.running_tasks:
                    del self.running_tasks[progress.novel_id]
    
    def _should_continue(self, progress: EnhancedContinuationProgress, continuous_mode: str) -> bool:
        """判断是否应该继续"""
        
        if continuous_mode == "infinite":
            # 无限模式，检查是否有自然结束条件
            # 这里可以添加更多的结束条件判断
            return progress.completed_chapters < 100  # 限制最大章节数
        
        elif continuous_mode == "auto":
            # 自动模式，检查故事发展
            if progress.completed_chapters >= progress.total_chapters:
                return False
            
            # 检查最近章节的质量趋势
            if len(progress.quality_scores) >= 3:
                recent_scores = progress.quality_scores[-3:]
                if all(score < 60 for score in recent_scores):
                    logger.info("⚠️ 检测到质量持续下降，自动停止续写")
                    return False
            
            return True
        
        elif continuous_mode == "manual":
            # 手动模式，需要用户确认
            # 这里可以添加用户交互逻辑
            return progress.completed_chapters < progress.total_chapters
        
        else:
            # 固定模式
            return progress.completed_chapters < progress.total_chapters
    
    def _save_chapter(self, novel_id: str, chapter_number: int, content: Dict[str, Any]) -> bool:
        """保存章节"""
        try:
            # 保存JSON文件
            json_file = f"data/novels/{novel_id}/chapter_{chapter_number:03d}.json"
            os.makedirs(os.path.dirname(json_file), exist_ok=True)
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            
            # 保存TXT文件
            txt_file = f"data/novels/{novel_id}/chapters/chapter_{chapter_number:03d}.txt"
            os.makedirs(os.path.dirname(txt_file), exist_ok=True)
            
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(content.get("content", ""))
            
            # 更新元数据
            self._update_metadata(novel_id, chapter_number)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存章节失败: {e}")
            return False
    
    def _update_metadata(self, novel_id: str, chapter_number: int):
        """更新元数据"""
        try:
            metadata_file = f"data/novels/{novel_id}/metadata.json"
            
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            else:
                metadata = {
                    "novel_id": novel_id,
                    "title": "未知标题",
                    "author": "AI作者",
                    "created_at": datetime.now().isoformat(),
                    "chapters": []
                }
            
            # 更新章节数
            metadata["current_chapter"] = chapter_number
            metadata["last_update"] = datetime.now().isoformat()
            
            # 添加章节信息
            chapter_info = {
                "chapter_number": chapter_number,
                "created_at": datetime.now().isoformat()
            }
            
            if "chapters" not in metadata:
                metadata["chapters"] = []
            
            metadata["chapters"].append(chapter_info)
            
            # 保存元数据
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"⚠️ 更新元数据失败: {e}")
    
    def get_progress(self, novel_id: str) -> Optional[Dict[str, Any]]:
        """获取进度"""
        with self.lock:
            if novel_id in self.running_tasks:
                progress = self.running_tasks[novel_id]
                return asdict(progress)
        
        # 从文件系统获取
        progress_file = os.path.join(self.status_dir, f"{novel_id}_progress.json")
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                pass
        
        return None
    
    def stop_continuation(self, novel_id: str) -> bool:
        """停止续写"""
        try:
            with self.lock:
                if novel_id in self.running_tasks:
                    progress = self.running_tasks[novel_id]
                    progress.status = "stopped"
                    progress.current_step = "stopped"
                    progress.last_update = datetime.now().isoformat()
                    self._update_progress(progress)
                    
                    # 从运行任务中移除
                    del self.running_tasks[novel_id]
                    logger.info(f"✅ 已停止续写任务: {novel_id}")
                    return True
                else:
                    logger.info(f"⚠️ 未找到运行中的任务: {novel_id}")
                    return False
        except Exception as e:
            logger.error(f"❌ 停止续写异常: {e}")
            return False
    
    def has_running_tasks(self) -> bool:
        """检查是否有正在运行的任务"""
        try:
            # 检查内存中的任务
            with self.lock:
                if self.running_tasks:
                    return True
            
            # 检查文件系统中的任务状态
            if os.path.exists(self.status_dir):
                for filename in os.listdir(self.status_dir):
                    if filename.endswith('.json'):
                        progress_file = os.path.join(self.status_dir, filename)
                        try:
                            with open(progress_file, 'r', encoding='utf-8') as f:
                                progress_data = json.load(f)
                                if progress_data.get('status') == 'running':
                                    return True
                        except Exception as e:
                            continue
            
            return False
        except Exception as e:
            logger.debug(f"检查运行任务时出错: {e}")
            return False
    
    def _save_progress(self, progress: EnhancedContinuationProgress):
        """保存进度"""
        try:
            progress_file = os.path.join(self.status_dir, f"{progress.novel_id}_progress.json")
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(progress), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存进度失败: {e}")
    
    def _update_progress(self, progress: EnhancedContinuationProgress):
        """更新进度"""
        progress.last_update = datetime.now().isoformat()
        
        # 立即保存到文件系统
        self._save_progress(progress)
        
        # 同时更新内存中的任务状态
        with self.lock:
            self.running_tasks[progress.novel_id] = progress
        
        logger.info(f"📊 进度已更新: {progress.current_step} - {progress.status}")
    
    def _restore_interrupted_tasks(self):
        """恢复中断的任务"""
        try:
            logger.debug("🔍 检查是否有中断的任务需要恢复...")
            
            if not os.path.exists(self.status_dir):
                return
            
            restored_count = 0
            for filename in os.listdir(self.status_dir):
                if filename.endswith('.json'):
                    progress_file = os.path.join(self.status_dir, filename)
                    try:
                        with open(progress_file, 'r', encoding='utf-8') as f:
                            progress_data = json.load(f)
                        
                        if progress_data.get('status') == 'running':
                            novel_id = progress_data.get('novel_id')
                            if novel_id:
                                logger.info(f"🔄 发现中断的任务: {novel_id}")
                                
                                # 标记为失败状态，因为任务已经中断
                                progress_data['status'] = 'failed'
                                progress_data['error_message'] = '任务因服务器重启而中断'
                                progress_data['last_update'] = datetime.now().isoformat()
                                
                                # 保存修复后的状态
                                with open(progress_file, 'w', encoding='utf-8') as f:
                                    json.dump(progress_data, f, ensure_ascii=False, indent=2)
                                
                                restored_count += 1
                                logger.info(f"✅ 已修复中断任务状态: {novel_id}")
                                
                    except Exception as e:
                        logger.info(f"⚠️ 处理任务文件 {filename} 时出错: {e}")
                        continue
            
            if restored_count > 0:
                logger.info(f"🎯 总共修复了 {restored_count} 个中断的任务")
            else:
                logger.info("✅ 没有发现需要恢复的中断任务")
                
        except Exception as e:
            logger.info(f"❌ 恢复中断任务时出错: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            # 获取综合系统状态
            comprehensive_status = self.comprehensive_system.get_system_status()
            
            # 获取执行器状态
            executor_status = {
                "running_tasks_count": len(self.running_tasks),
                "running_tasks": list(self.running_tasks.keys()),
                "executor_type": "enhanced"
            }
            
            return {
                "executor_status": executor_status,
                "comprehensive_system_status": comprehensive_status,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "error": f"获取系统状态失败: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def shutdown(self):
        """关闭执行器"""
        try:
            logger.info("🛑 正在关闭增强版续写执行器...")
            
            # 停止所有运行的任务
            with self.lock:
                for novel_id, progress in self.running_tasks.items():
                    progress.status = "paused"
                    progress.current_step = "shutdown"
                    progress.last_update = datetime.now().isoformat()
                    self._save_progress(progress)
                
                self.running_tasks.clear()
            
            # 关闭综合系统
            self.comprehensive_system.shutdown()
            
            logger.info("✅ 增强版续写执行器已关闭")
            
        except Exception as e:
            logger.error(f"❌ 关闭执行器异常: {e}")

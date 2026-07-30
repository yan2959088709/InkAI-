"""
运行时保证系统
负责保证系统运行时间，提供超时处理和降级机制
"""

import time
import threading
import signal
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
import concurrent.futures
from utils.logger import get_logger

logger = get_logger("runtime_guarantee_system")


class RuntimeGuaranteeSystem:
    """运行时保证系统"""
    
    def __init__(self, default_timeout: float = 30.0):
        self.default_timeout = default_timeout
        self.active_tasks = {}
        self.task_lock = threading.Lock()
        self.timeout_handlers = {}
        self.cleanup_timer = None
        self._start_cleanup_timer()
    
    def execute_with_timeout(self, func: Callable, args: tuple = (), 
                           kwargs: dict = None, timeout: float = None) -> Dict[str, Any]:
        """在超时限制内执行函数"""
        try:
            if timeout is None:
                timeout = self.default_timeout
            
            if kwargs is None:
                kwargs = {}
            
            # 创建任务ID
            task_id = f"task_{int(time.time() * 1000)}"
            
            # 记录任务开始
            with self.task_lock:
                self.active_tasks[task_id] = {
                    "start_time": time.time(),
                    "timeout": timeout,
                    "status": "running"
                }
            
            # 使用线程池执行任务
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                
                try:
                    # 等待任务完成或超时
                    result = future.result(timeout=timeout)
                    
                    # 任务成功完成
                    with self.task_lock:
                        if task_id in self.active_tasks:
                            self.active_tasks[task_id]["status"] = "completed"
                            self.active_tasks[task_id]["end_time"] = time.time()
                    
                    return {
                        "status": "success",
                        "result": result,
                        "execution_time": time.time() - self.active_tasks[task_id]["start_time"],
                        "task_id": task_id
                    }
                    
                except concurrent.futures.TimeoutError:
                    # 任务超时
                    with self.task_lock:
                        if task_id in self.active_tasks:
                            self.active_tasks[task_id]["status"] = "timeout"
                            self.active_tasks[task_id]["end_time"] = time.time()
                    
                    return {
                        "status": "timeout",
                        "error": f"任务执行超时 ({timeout}秒)",
                        "execution_time": timeout,
                        "task_id": task_id
                    }
                    
                except Exception as e:
                    # 任务执行出错
                    with self.task_lock:
                        if task_id in self.active_tasks:
                            self.active_tasks[task_id]["status"] = "error"
                            self.active_tasks[task_id]["end_time"] = time.time()
                            self.active_tasks[task_id]["error"] = str(e)
                    
                    return {
                        "status": "error",
                        "error": str(e),
                        "execution_time": time.time() - self.active_tasks[task_id]["start_time"],
                        "task_id": task_id
                    }
                    
        except Exception as e:
            return {
                "status": "error",
                "error": f"运行时保证系统出错: {str(e)}",
                "task_id": task_id if 'task_id' in locals() else "unknown"
            }
    
    def execute_llm_with_timeout(self, llm_client, messages: List[Dict[str, str]], 
                               timeout: float = None) -> Dict[str, Any]:
        """在超时限制内执行LLM调用"""
        try:
            if timeout is None:
                timeout = self.default_timeout
            
            def llm_call():
                return llm_client.call_llm(messages)
            
            result = self.execute_with_timeout(llm_call, timeout=timeout)
            
            if result["status"] == "timeout":
                # 返回降级响应
                result["fallback_response"] = self._generate_fallback_response(messages)
                result["status"] = "timeout_with_fallback"
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"LLM调用超时处理失败: {str(e)}"
            }
    
    def execute_assessment_with_timeout(self, assessor, input_data: Dict[str, Any], 
                                      timeout: float = None) -> Dict[str, Any]:
        """在超时限制内执行评估"""
        try:
            if timeout is None:
                timeout = self.default_timeout
            
            def assessment_call():
                return assessor.process(input_data)
            
            result = self.execute_with_timeout(assessment_call, timeout=timeout)
            
            if result["status"] == "timeout":
                # 返回降级评估结果
                result["fallback_assessment"] = self._generate_fallback_assessment(input_data)
                result["status"] = "timeout_with_fallback"
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"评估超时处理失败: {str(e)}"
            }
    
    def execute_improvement_with_timeout(self, improver, input_data: Dict[str, Any], 
                                       timeout: float = None) -> Dict[str, Any]:
        """在超时限制内执行改进"""
        try:
            if timeout is None:
                timeout = self.default_timeout
            
            def improvement_call():
                return improver.process(input_data)
            
            result = self.execute_with_timeout(improvement_call, timeout=timeout)
            
            if result["status"] == "timeout":
                # 返回降级改进结果
                result["fallback_improvement"] = self._generate_fallback_improvement(input_data)
                result["status"] = "timeout_with_fallback"
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"改进超时处理失败: {str(e)}"
            }
    
    def _generate_fallback_response(self, messages: List[Dict[str, str]]) -> str:
        """生成降级响应"""
        try:
            # 基于消息内容生成简单的降级响应
            if not messages:
                return "抱歉，系统暂时无法处理您的请求。"
            
            last_message = messages[-1].get("content", "")
            if "评估" in last_message:
                return "评估功能暂时不可用，请稍后重试。"
            elif "改进" in last_message:
                return "改进功能暂时不可用，请稍后重试。"
            elif "续写" in last_message:
                return "续写功能暂时不可用，请稍后重试。"
            else:
                return "系统暂时无法处理您的请求，请稍后重试。"
                
        except Exception:
            return "系统暂时无法处理您的请求，请稍后重试。"
    
    def _generate_fallback_assessment(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成降级评估结果"""
        try:
            return {
                "is_high_quality": True,
                "overall_score": 75,
                "dimensions": {
                    "general_quality": 75
                },
                "suggestions": ["系统暂时无法进行详细评估，请稍后重试"],
                "fallback": True
            }
        except Exception:
            return {
                "is_high_quality": True,
                "overall_score": 75,
                "dimensions": {},
                "suggestions": ["评估功能暂时不可用"],
                "fallback": True
            }
    
    def _generate_fallback_improvement(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成降级改进结果"""
        try:
            continuation_content = input_data.get("continuation_content", {})
            return {
                "status": "success",
                "improved_content": continuation_content,
                "improvement_notes": "改进功能暂时不可用，保持原内容",
                "fallback": True
            }
        except Exception:
            return {
                "status": "error",
                "error": "改进功能暂时不可用",
                "fallback": True
            }
    
    def get_active_tasks(self) -> Dict[str, Any]:
        """获取活跃任务"""
        with self.task_lock:
            return self.active_tasks.copy()
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        with self.task_lock:
            return self.active_tasks.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        try:
            with self.task_lock:
                if task_id in self.active_tasks:
                    self.active_tasks[task_id]["status"] = "cancelled"
                    self.active_tasks[task_id]["end_time"] = time.time()
                    return True
            return False
        except Exception:
            return False
    
    def cleanup_completed_tasks(self):
        """清理已完成的任务"""
        try:
            with self.task_lock:
                current_time = time.time()
                tasks_to_remove = []
                
                for task_id, task_info in self.active_tasks.items():
                    if task_info["status"] in ["completed", "timeout", "error", "cancelled"]:
                        # 保留最近1小时的任务记录
                        if current_time - task_info.get("end_time", current_time) > 3600:
                            tasks_to_remove.append(task_id)
                
                for task_id in tasks_to_remove:
                    del self.active_tasks[task_id]
                    
        except Exception as e:
            logger.error(f"清理已完成任务失败: {e}")
    
    def get_runtime_stats(self) -> Dict[str, Any]:
        """获取运行时统计"""
        try:
            with self.task_lock:
                total_tasks = len(self.active_tasks)
                running_tasks = sum(1 for task in self.active_tasks.values() 
                                  if task["status"] == "running")
                completed_tasks = sum(1 for task in self.active_tasks.values() 
                                    if task["status"] == "completed")
                timeout_tasks = sum(1 for task in self.active_tasks.values() 
                                  if task["status"] == "timeout")
                error_tasks = sum(1 for task in self.active_tasks.values() 
                                if task["status"] == "error")
                
                return {
                    "total_tasks": total_tasks,
                    "running_tasks": running_tasks,
                    "completed_tasks": completed_tasks,
                    "timeout_tasks": timeout_tasks,
                    "error_tasks": error_tasks,
                    "success_rate": completed_tasks / total_tasks if total_tasks > 0 else 0,
                    "timeout_rate": timeout_tasks / total_tasks if total_tasks > 0 else 0,
                    "error_rate": error_tasks / total_tasks if total_tasks > 0 else 0
                }
                
        except Exception as e:
            logger.error(f"获取运行时统计失败: {e}")
            return {}
    
    def set_timeout_handler(self, task_type: str, handler: Callable):
        """设置超时处理器"""
        self.timeout_handlers[task_type] = handler
    
    def _start_cleanup_timer(self):
        """启动清理定时器"""
        try:
            import threading
            
            def cleanup_worker():
                while True:
                    time.sleep(300)  # 每5分钟清理一次
                    self.cleanup_completed_tasks()
            
            self.cleanup_timer = threading.Thread(target=cleanup_worker, daemon=True)
            self.cleanup_timer.start()
        except Exception as e:
            logger.error(f"启动清理定时器失败: {e}")
    
    def __del__(self):
        """析构函数"""
        try:
            self.cleanup_completed_tasks()
        except Exception as e:
            logger.error(f"清理任务失败: {e}")

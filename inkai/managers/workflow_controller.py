# 优化版工作流程控制器
# 包含智能工作流程编排、任务调度监控、错误处理重试、进度跟踪报告

import json
import asyncio
import threading
import time
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta
from enum import Enum
import uuid

from ..core.base_agent import EnhancedBaseAgent


class WorkflowStatus(Enum):
    """工作流程状态枚举"""
    PENDING = "pending"      # 等待中
    RUNNING = "running"      # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 已取消
    PAUSED = "paused"        # 已暂停


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class EnhancedWorkflowController(EnhancedBaseAgent):
    """优化版工作流程控制器 - 智能工作流程编排和管理系统"""
    
    def __init__(self):
        super().__init__("增强工作流程控制器")
        
        # 工作流程状态管理
        self.active_workflows = {}
        self.workflow_history = []
        self.task_queue = []
        self.running_tasks = {}
        
        # 智能体注册表
        self.registered_agents = {}
        self.agent_capabilities = {}
        
        # 工作流程模板
        self.workflow_templates = {
            "novel_creation": {
                "name": "小说创作流程",
                "description": "完整的小说创作工作流程",
                "steps": [
                    {"id": "tag_selection", "agent": "tag_selector", "priority": TaskPriority.HIGH},
                    {"id": "character_creation", "agent": "character_creator", "priority": TaskPriority.HIGH},
                    {"id": "storyline_generation", "agent": "storyline_generator", "priority": TaskPriority.HIGH},
                    {"id": "chapter_writing", "agent": "chapter_writer", "priority": TaskPriority.NORMAL},
                    {"id": "quality_assessment", "agent": "quality_assessor", "priority": TaskPriority.NORMAL}
                ],
                "dependencies": {
                    "character_creation": ["tag_selection"],
                    "storyline_generation": ["tag_selection", "character_creation"],
                    "chapter_writing": ["storyline_generation"],
                    "quality_assessment": ["chapter_writing"]
                }
            },
            "novel_continuation": {
                "name": "小说续写流程",
                "description": "基于现有内容的续写流程",
                "steps": [
                    {"id": "continuation_analysis", "agent": "continuation_analyzer", "priority": TaskPriority.HIGH},
                    {"id": "continuation_writing", "agent": "continuation_writer", "priority": TaskPriority.HIGH},
                    {"id": "quality_check", "agent": "quality_assessor", "priority": TaskPriority.NORMAL}
                ],
                "dependencies": {
                    "continuation_writing": ["continuation_analysis"],
                    "quality_check": ["continuation_writing"]
                }
            }
        }
        
        # 错误处理和重试配置
        self.retry_config = {
            "max_retries": 3,
            "retry_delay": 2,  # 秒
            "exponential_backoff": True,
            "retry_conditions": ["timeout", "api_error", "parsing_error"]
        }
        
        # 性能监控
        self.performance_metrics = {
            "total_workflows": 0,
            "successful_workflows": 0,
            "failed_workflows": 0,
            "average_execution_time": 0,
            "agent_usage_stats": {}
        }
        
        # 启动任务调度器
        self.scheduler_running = True
        self.scheduler_thread = threading.Thread(target=self._task_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        self._log("优化版工作流程控制器初始化完成", "INFO")
    
    def register_agent(self, agent_name: str, agent_instance: Any, capabilities: List[str]):
        """注册智能体"""
        self._log(f"注册智能体: {agent_name}", "INFO")
        
        self.registered_agents[agent_name] = agent_instance
        self.agent_capabilities[agent_name] = capabilities
        
        # 更新性能统计
        if agent_name not in self.performance_metrics["agent_usage_stats"]:
            self.performance_metrics["agent_usage_stats"][agent_name] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "average_response_time": 0
            }
    
    def create_workflow(self, template_name: str, project_id: str, parameters: Dict[str, Any] = None) -> str:
        """创建工作流程"""
        self._log(f"创建工作流程: {template_name}", "INFO")
        
        if template_name not in self.workflow_templates:
            self._log(f"工作流程模板不存在: {template_name}", "ERROR")
            return ""
        
        workflow_id = str(uuid.uuid4())
        template = self.workflow_templates[template_name]
        
        # 创建工作流程实例
        workflow = {
            "id": workflow_id,
            "template_name": template_name,
            "name": template["name"],
            "description": template["description"],
            "project_id": project_id,
            "status": WorkflowStatus.PENDING,
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "parameters": parameters or {},
            "steps": template["steps"].copy(),
            "dependencies": template["dependencies"].copy(),
            "current_step": None,
            "completed_steps": [],
            "failed_steps": [],
            "results": {},
            "error_log": [],
            "progress": 0,
            "estimated_completion": None
        }
        
        # 添加到活跃工作流程
        self.active_workflows[workflow_id] = workflow
        
        # 更新统计
        self.performance_metrics["total_workflows"] += 1
        
        self._log(f"工作流程创建完成: {workflow_id}", "INFO")
        return workflow_id
    
    def start_workflow(self, workflow_id: str) -> bool:
        """启动工作流程"""
        self._log(f"启动工作流程: {workflow_id}", "INFO")
        
        if workflow_id not in self.active_workflows:
            self._log(f"工作流程不存在: {workflow_id}", "ERROR")
            return False
        
        workflow = self.active_workflows[workflow_id]
        
        if workflow["status"] != WorkflowStatus.PENDING:
            self._log(f"工作流程状态不允许启动: {workflow['status']}", "ERROR")
            return False
        
        # 更新状态
        workflow["status"] = WorkflowStatus.RUNNING
        workflow["started_at"] = datetime.now().isoformat()
        
        # 开始执行第一个任务
        self._execute_next_step(workflow_id)
        
        return True
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流程状态"""
        if workflow_id not in self.active_workflows:
            # 检查历史记录
            for workflow in self.workflow_history:
                if workflow["id"] == workflow_id:
                    return {
                        "id": workflow_id,
                        "name": workflow["name"],
                        "status": workflow["status"].value,
                        "progress": 100 if workflow["status"] == WorkflowStatus.COMPLETED else workflow.get("progress", 0),
                        "current_step": workflow.get("current_step"),
                        "completed_steps": len(workflow.get("completed_steps", [])),
                        "total_steps": len(workflow.get("steps", [])),
                        "created_at": workflow.get("created_at"),
                        "started_at": workflow.get("started_at"),
                        "completed_at": workflow.get("completed_at")
                    }
            return None
        
        workflow = self.active_workflows[workflow_id]
        
        return {
            "id": workflow_id,
            "name": workflow["name"],
            "status": workflow["status"].value,
            "progress": workflow["progress"],
            "current_step": workflow["current_step"],
            "completed_steps": len(workflow["completed_steps"]),
            "total_steps": len(workflow["steps"]),
            "created_at": workflow["created_at"],
            "started_at": workflow["started_at"],
            "estimated_completion": workflow["estimated_completion"]
        }
    
    def get_workflow_results(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流程结果"""
        # 先检查活跃工作流程
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
            return {
                "workflow_id": workflow_id,
                "status": workflow["status"].value,
                "results": workflow["results"],
                "progress": workflow["progress"]
            }
        
        # 再检查历史记录
        for workflow in self.workflow_history:
            if workflow["id"] == workflow_id:
                return {
                    "workflow_id": workflow_id,
                    "status": workflow["status"].value,
                    "results": workflow["results"],
                    "progress": 100 if workflow["status"] == WorkflowStatus.COMPLETED else workflow["progress"]
                }
        
        return None
    
    def _execute_next_step(self, workflow_id: str):
        """执行下一个步骤"""
        if workflow_id not in self.active_workflows:
            return
        
        workflow = self.active_workflows[workflow_id]
        
        # 找到下一个可执行的步骤
        next_step = self._find_next_executable_step(workflow)
        
        if not next_step:
            # 没有更多步骤，工作流程完成
            self._complete_workflow(workflow_id)
            return
        
        # 更新当前步骤
        workflow["current_step"] = next_step["id"]
        
        # 创建任务
        task = {
            "workflow_id": workflow_id,
            "step_id": next_step["id"],
            "agent_name": next_step["agent"],
            "priority": next_step["priority"],
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "retry_count": 0,
            "parameters": workflow["parameters"]
        }
        
        # 添加到任务队列
        self.task_queue.append(task)
        
        self._log(f"添加任务到队列: {next_step['id']}", "INFO")
    
    def _find_next_executable_step(self, workflow: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """找到下一个可执行的步骤"""
        dependencies = workflow["dependencies"]
        completed_steps = workflow["completed_steps"]
        
        for step in workflow["steps"]:
            step_id = step["id"]
            
            # 跳过已完成的步骤
            if step_id in completed_steps:
                continue
            
            # 跳过失败的步骤
            if step_id in workflow["failed_steps"]:
                continue
            
            # 检查依赖关系
            if step_id in dependencies:
                required_steps = dependencies[step_id]
                if not all(req_step in completed_steps for req_step in required_steps):
                    continue
            
            return step
        
        return None
    
    def _task_scheduler(self):
        """任务调度器"""
        while self.scheduler_running:
            try:
                # 按优先级排序任务队列
                self.task_queue.sort(key=lambda x: x["priority"].value, reverse=True)
                
                # 执行任务
                for task in self.task_queue[:]:
                    if task["status"] == "pending":
                        self._execute_task(task)
                        break
                
                time.sleep(1)  # 1秒检查一次
                
            except Exception as e:
                self._log(f"任务调度器错误: {e}", "ERROR")
                time.sleep(5)
    
    def _execute_task(self, task: Dict[str, Any]):
        """执行任务"""
        workflow_id = task["workflow_id"]
        step_id = task["step_id"]
        agent_name = task["agent_name"]
        
        self._log(f"执行任务: {step_id} (智能体: {agent_name})", "INFO")
        
        # 检查智能体是否注册
        if agent_name not in self.registered_agents:
            self._log(f"智能体未注册: {agent_name}", "ERROR")
            self._handle_task_failure(task, "智能体未注册")
            return
        
        # 更新任务状态
        task["status"] = "running"
        task["started_at"] = datetime.now().isoformat()
        self.running_tasks[workflow_id] = task
        
        try:
            # 获取智能体实例
            agent = self.registered_agents[agent_name]
            
            # 准备参数
            parameters = self._prepare_task_parameters(workflow_id, step_id, task["parameters"])
            
            # 执行智能体任务
            result = self._call_agent_method(agent, step_id, parameters)
            
            # 处理成功结果
            self._handle_task_success(task, result)
            
        except Exception as e:
            self._log(f"任务执行失败: {e}", "ERROR")
            self._handle_task_failure(task, str(e))
    
    def _prepare_task_parameters(self, workflow_id: str, step_id: str, base_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """准备任务参数"""
        workflow = self.active_workflows[workflow_id]
        parameters = base_parameters.copy()
        
        # 添加工作流程上下文
        parameters["workflow_id"] = workflow_id
        parameters["project_id"] = workflow["project_id"]
        
        # 添加前面步骤的结果
        for completed_step in workflow["completed_steps"]:
            if completed_step in workflow["results"]:
                parameters[f"{completed_step}_result"] = workflow["results"][completed_step]
        
        return parameters
    
    def _call_agent_method(self, agent: Any, step_id: str, parameters: Dict[str, Any]) -> Any:
        """调用智能体方法"""
        # 根据步骤ID确定要调用的方法
        method_mapping = {
            "tag_selection": "recommend_tags",
            "character_creation": "create_character",
            "storyline_generation": "generate_storyline",
            "chapter_writing": "write_chapter",
            "quality_assessment": "assess_content_quality",
            "continuation_analysis": "analyze_for_continuation",
            "continuation_writing": "write_continuation",
            "quality_check": "assess_content_quality"
        }
        
        method_name = method_mapping.get(step_id, "process")
        
        if hasattr(agent, method_name):
            method = getattr(agent, method_name)
            # 根据方法名调用不同参数
            if method_name == "recommend_tags":
                return method(parameters.get("user_requirements", ""))
            elif method_name == "create_character":
                tags = parameters.get("tag_selection_result", {})
                requirements = parameters.get("user_requirements", "")
                return method(tags, requirements)
            elif method_name == "generate_storyline":
                tags = parameters.get("tag_selection_result", {})
                characters = parameters.get("character_creation_result", {})
                requirements = parameters.get("user_requirements", "")
                return method(tags, characters, requirements)
            elif method_name == "write_chapter":
                storyline = parameters.get("storyline_generation_result", {})
                characters = parameters.get("character_creation_result", {})
                chapter_info = {"chapter_number": 1, "chapter_title": "第一章"}
                return method(storyline, characters, chapter_info)
            elif method_name == "assess_content_quality":
                # 获取最新生成的内容
                if "chapter_writing_result" in parameters:
                    content = parameters["chapter_writing_result"].get("content", "")
                    return method(content, "章节")
                elif "continuation_writing_result" in parameters:
                    content = parameters["continuation_writing_result"].get("content", {}).get("content", "")
                    return method(content, "续写章节")
                return method("", "未知")
            elif method_name == "analyze_for_continuation":
                # 需要加载现有小说数据
                return method({}, parameters.get("continuation_requirements", ""))
            elif method_name == "write_continuation":
                novel_data = {}  # 需要从数据管理器加载
                analysis_result = parameters.get("continuation_analysis_result", {})
                requirements = parameters.get("continuation_requirements", "")
                return method(novel_data, analysis_result, requirements)
            else:
                return method(**parameters)
        else:
            raise AttributeError(f"智能体没有方法: {method_name}")
    
    def _handle_task_success(self, task: Dict[str, Any], result: Any):
        """处理任务成功"""
        workflow_id = task["workflow_id"]
        step_id = task["step_id"]
        
        # 更新工作流程
        workflow = self.active_workflows[workflow_id]
        workflow["completed_steps"].append(step_id)
        workflow["results"][step_id] = result
        
        # 计算进度
        total_steps = len(workflow["steps"])
        completed_steps = len(workflow["completed_steps"])
        workflow["progress"] = (completed_steps / total_steps) * 100
        
        # 从队列中移除任务
        if task in self.task_queue:
            self.task_queue.remove(task)
        if workflow_id in self.running_tasks:
            del self.running_tasks[workflow_id]
        
        self._log(f"任务完成: {step_id}", "INFO")
        
        # 执行下一个步骤
        self._execute_next_step(workflow_id)
    
    def _handle_task_failure(self, task: Dict[str, Any], error_message: str):
        """处理任务失败"""
        workflow_id = task["workflow_id"]
        step_id = task["step_id"]
        
        # 检查是否需要重试
        if task["retry_count"] < self.retry_config["max_retries"]:
            task["retry_count"] += 1
            task["status"] = "pending"
            task["last_error"] = error_message
            
            self._log(f"任务失败，准备重试: {step_id}", "WARNING")
            
        else:
            # 重试次数用完，标记为失败
            workflow = self.active_workflows[workflow_id]
            workflow["failed_steps"].append(step_id)
            workflow["error_log"].append({
                "step_id": step_id,
                "error": error_message,
                "timestamp": datetime.now().isoformat()
            })
            
            # 从队列中移除任务
            if task in self.task_queue:
                self.task_queue.remove(task)
            if workflow_id in self.running_tasks:
                del self.running_tasks[workflow_id]
            
            self._log(f"任务最终失败: {step_id}", "ERROR")
            
            # 检查是否所有步骤都完成或失败
            if len(workflow["completed_steps"]) + len(workflow["failed_steps"]) >= len(workflow["steps"]):
                self._complete_workflow(workflow_id, success=False)
    
    def _complete_workflow(self, workflow_id: str, success: bool = True):
        """完成工作流程"""
        workflow = self.active_workflows[workflow_id]
        
        if success:
            workflow["status"] = WorkflowStatus.COMPLETED
            self.performance_metrics["successful_workflows"] += 1
            self._log(f"工作流程完成: {workflow_id}", "INFO")
        else:
            workflow["status"] = WorkflowStatus.FAILED
            self.performance_metrics["failed_workflows"] += 1
            self._log(f"工作流程失败: {workflow_id}", "ERROR")
        
        workflow["completed_at"] = datetime.now().isoformat()
        
        # 移动到历史记录
        self._move_to_history(workflow_id)
    
    def _move_to_history(self, workflow_id: str):
        """移动到历史记录"""
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
            self.workflow_history.append(workflow)
            del self.active_workflows[workflow_id]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return self.performance_metrics.copy()
    
    def shutdown(self):
        """关闭工作流程控制器"""
        self.scheduler_running = False
        if self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        self._log("工作流程控制器已关闭", "INFO")

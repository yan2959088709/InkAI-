"""
优化的智能体交互系统
实现智能体间的协调和数据传递优化
"""

import json
import os
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from abc import ABC, abstractmethod
import threading
import queue
import time
from utils.logger import get_logger
logger = get_logger("optimized_agent_interaction_system")


class AgentInteractionFlow:
    """智能体交互流程定义"""
    
    def __init__(self, flow_id: str, name: str, description: str = ""):
        self.flow_id = flow_id
        self.name = name
        self.description = description
        self.steps: List[Dict[str, Any]] = []
        self.input_schema: Dict[str, Any] = {}
        self.output_schema: Dict[str, Any] = {}
        self.error_handlers: Dict[str, Callable] = {}
    
    def add_step(self, step: Dict[str, Any]) -> 'AgentInteractionFlow':
        """添加流程步骤"""
        self.steps.append(step)
        return self
    
    def set_input_schema(self, schema: Dict[str, Any]) -> 'AgentInteractionFlow':
        """设置输入模式"""
        self.input_schema = schema
        return self
    
    def set_output_schema(self, schema: Dict[str, Any]) -> 'AgentInteractionFlow':
        """设置输出模式"""
        self.output_schema = schema
        return self
    
    def add_error_handler(self, error_type: str, handler: Callable) -> 'AgentInteractionFlow':
        """添加错误处理器"""
        self.error_handlers[error_type] = handler
        return self


class AgentDataValidator:
    """智能体数据验证器"""
    
    def __init__(self):
        self.validation_rules = {}
    
    def validate_input(self, agent_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证输入数据"""
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "cleaned_data": input_data.copy()
        }
        
        # 获取验证规则
        rules = self.validation_rules.get(agent_name, {})
        
        # 验证必需字段
        required_fields = rules.get("required_fields", [])
        for field in required_fields:
            if field not in input_data or not input_data[field]:
                validation_result["is_valid"] = False
                validation_result["errors"].append(f"缺少必需字段: {field}")
        
        # 验证字段类型
        field_types = rules.get("field_types", {})
        for field, expected_type in field_types.items():
            if field in input_data:
                if not isinstance(input_data[field], expected_type):
                    validation_result["is_valid"] = False
                    validation_result["errors"].append(
                        f"字段 {field} 类型错误，期望 {expected_type.__name__}，实际 {type(input_data[field]).__name__}"
                    )
        
        # 验证字段值
        field_validators = rules.get("field_validators", {})
        for field, validator in field_validators.items():
            if field in input_data:
                try:
                    if not validator(input_data[field]):
                        validation_result["is_valid"] = False
                        validation_result["errors"].append(f"字段 {field} 验证失败")
                except Exception as e:
                    validation_result["is_valid"] = False
                    validation_result["errors"].append(f"字段 {field} 验证异常: {str(e)}")
        
        # 数据清理
        if validation_result["is_valid"]:
            validation_result["cleaned_data"] = self._clean_data(input_data, rules)
        
        return validation_result
    
    def _clean_data(self, data: Dict[str, Any], rules: Dict[str, Any]) -> Dict[str, Any]:
        """清理数据"""
        cleaned_data = data.copy()
        
        # 应用数据转换器
        transformers = rules.get("transformers", {})
        for field, transformer in transformers.items():
            if field in cleaned_data:
                try:
                    cleaned_data[field] = transformer(cleaned_data[field])
                except Exception as e:
                    logger.error(f"数据转换失败 {field}: {e}")
        
        return cleaned_data
    
    def register_validation_rules(self, agent_name: str, rules: Dict[str, Any]):
        """注册验证规则"""
        self.validation_rules[agent_name] = rules


class AgentDataTransformer:
    """智能体数据转换器"""
    
    def __init__(self):
        self.transformers = {}
    
    def register_transformer(self, from_agent: str, to_agent: str, transformer: Callable):
        """注册数据转换器"""
        key = f"{from_agent}->{to_agent}"
        self.transformers[key] = transformer
    
    def transform_data(self, from_agent: str, to_agent: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """转换数据"""
        key = f"{from_agent}->{to_agent}"
        
        if key in self.transformers:
            try:
                return self.transformers[key](data)
            except Exception as e:
                logger.error(f"数据转换失败 {key}: {e}")
                return data
        
        # 默认转换：直接传递
        return data


class AgentExecutionContext:
    """智能体执行上下文"""
    
    def __init__(self, context_id: str):
        self.context_id = context_id
        self.created_at = datetime.now().isoformat()
        self.data: Dict[str, Any] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self.error_history: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, Any] = {}
        self.lock = threading.Lock()
    
    def set_data(self, key: str, value: Any):
        """设置数据"""
        with self.lock:
            self.data[key] = value
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """获取数据"""
        with self.lock:
            return self.data.get(key, default)
    
    def update_data(self, updates: Dict[str, Any]):
        """更新数据"""
        with self.lock:
            self.data.update(updates)
    
    def record_execution(self, agent_name: str, start_time: float, end_time: float, 
                        input_data: Dict[str, Any], output_data: Dict[str, Any], 
                        success: bool, error: str = None):
        """记录执行历史"""
        with self.lock:
            execution_record = {
                "timestamp": datetime.now().isoformat(),
                "agent_name": agent_name,
                "start_time": start_time,
                "end_time": end_time,
                "duration": end_time - start_time,
                "input_data": input_data,
                "output_data": output_data,
                "success": success,
                "error": error
            }
            self.execution_history.append(execution_record)
    
    def record_error(self, agent_name: str, error_type: str, error_message: str, context: Dict[str, Any] = None):
        """记录错误"""
        with self.lock:
            error_record = {
                "timestamp": datetime.now().isoformat(),
                "agent_name": agent_name,
                "error_type": error_type,
                "error_message": error_message,
                "context": context or {}
            }
            self.error_history.append(error_record)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        with self.lock:
            if not self.execution_history:
                return {}
            
            total_executions = len(self.execution_history)
            successful_executions = sum(1 for record in self.execution_history if record["success"])
            failed_executions = total_executions - successful_executions
            
            total_duration = sum(record["duration"] for record in self.execution_history)
            avg_duration = total_duration / total_executions if total_executions > 0 else 0
            
            return {
                "total_executions": total_executions,
                "successful_executions": successful_executions,
                "failed_executions": failed_executions,
                "success_rate": successful_executions / total_executions if total_executions > 0 else 0,
                "total_duration": total_duration,
                "average_duration": avg_duration,
                "error_count": len(self.error_history)
            }


class OptimizedAgentInteractionSystem:
    """优化的智能体交互系统"""
    
    def __init__(self):
        self.flows: Dict[str, AgentInteractionFlow] = {}
        self.agents: Dict[str, Any] = {}
        self.data_validator = AgentDataValidator()
        self.data_transformer = AgentDataTransformer()
        self.execution_contexts: Dict[str, AgentExecutionContext] = {}
        self.performance_monitor = AgentPerformanceMonitor()
        
        # 初始化默认流程
        self._initialize_default_flows()
        
        # 初始化验证规则
        self._initialize_validation_rules()
        
        # 初始化数据转换器
        self._initialize_data_transformers()
    
    def _initialize_default_flows(self):
        """初始化默认流程"""
        
        # 章节生成流程
        chapter_generation_flow = AgentInteractionFlow(
            "chapter_generation",
            "章节生成流程",
            "完整的章节生成流程，包括上下文管理、故事线生成、内容生成和质量评估"
        )
        
        chapter_generation_flow.add_step({
            "step_id": "context_preparation",
            "agent_name": "context_manager",
            "input_fields": ["novel_id", "chapter_number", "previous_chapters"],
            "output_fields": ["compressed_context", "memory_usage", "relevant_entities"],
            "next_steps": ["storyline_generation"],
            "timeout": 30,
            "retry_count": 3
        })
        
        chapter_generation_flow.add_step({
            "step_id": "storyline_generation",
            "agent_name": "storyline_manager",
            "input_fields": ["compressed_context", "upper_constraints", "progress"],
            "output_fields": ["chapter_storyline", "deviation_score", "consistency_score"],
            "next_steps": ["knowledge_update"],
            "timeout": 60,
            "retry_count": 3
        })
        
        chapter_generation_flow.add_step({
            "step_id": "knowledge_update",
            "agent_name": "knowledge_graph",
            "input_fields": ["chapter_storyline", "current_knowledge"],
            "output_fields": ["updated_knowledge", "consistency_check", "new_entities"],
            "next_steps": ["content_generation"],
            "timeout": 45,
            "retry_count": 2
        })
        
        chapter_generation_flow.add_step({
            "step_id": "content_generation",
            "agent_name": "content_generator",
            "input_fields": ["chapter_storyline", "updated_knowledge", "context"],
            "output_fields": ["chapter_content", "generation_metadata", "word_count"],
            "next_steps": ["quality_assessment"],
            "timeout": 120,
            "retry_count": 3
        })
        
        chapter_generation_flow.add_step({
            "step_id": "quality_assessment",
            "agent_name": "quality_assessor",
            "input_fields": ["chapter_content", "storyline", "knowledge"],
            "output_fields": ["quality_score", "improvement_suggestions", "consistency_issues"],
            "next_steps": ["content_improvement"] if "quality_score < 70" else None,
            "timeout": 60,
            "retry_count": 2
        })
        
        chapter_generation_flow.add_step({
            "step_id": "content_improvement",
            "agent_name": "content_improver",
            "input_fields": ["chapter_content", "improvement_suggestions", "quality_issues"],
            "output_fields": ["improved_content", "improvement_metadata"],
            "next_steps": ["final_validation"],
            "timeout": 90,
            "retry_count": 2
        })
        
        chapter_generation_flow.add_step({
            "step_id": "final_validation",
            "agent_name": "final_validator",
            "input_fields": ["improved_content", "original_storyline", "quality_score"],
            "output_fields": ["final_content", "validation_result", "final_quality_score"],
            "next_steps": None,
            "timeout": 30,
            "retry_count": 1
        })
        
        self.flows["chapter_generation"] = chapter_generation_flow
        
        # 故事线生成流程
        storyline_generation_flow = AgentInteractionFlow(
            "storyline_generation",
            "故事线生成流程",
            "双层故事线生成流程"
        )
        
        storyline_generation_flow.add_step({
            "step_id": "upper_constraint_analysis",
            "agent_name": "novel_storyline",
            "input_fields": ["novel_id", "chapter_number"],
            "output_fields": ["upper_constraints", "phase_info", "progress"],
            "next_steps": ["chapter_storyline_generation"],
            "timeout": 30,
            "retry_count": 2
        })
        
        storyline_generation_flow.add_step({
            "step_id": "chapter_storyline_generation",
            "agent_name": "chapter_storyline",
            "input_fields": ["upper_constraints", "phase_info", "previous_chapters"],
            "output_fields": ["chapter_storyline", "deviation_score", "consistency_score"],
            "next_steps": ["constraint_validation"],
            "timeout": 60,
            "retry_count": 3
        })
        
        storyline_generation_flow.add_step({
            "step_id": "constraint_validation",
            "agent_name": "constraint_validator",
            "input_fields": ["chapter_storyline", "upper_constraints"],
            "output_fields": ["validation_result", "adjusted_storyline"],
            "next_steps": None,
            "timeout": 30,
            "retry_count": 2
        })
        
        self.flows["storyline_generation"] = storyline_generation_flow
    
    def _initialize_validation_rules(self):
        """初始化验证规则"""
        
        # 上下文管理器验证规则
        self.data_validator.register_validation_rules("context_manager", {
            "required_fields": ["novel_id", "chapter_number"],
            "field_types": {
                "novel_id": str,
                "chapter_number": int,
                "previous_chapters": list
            },
            "field_validators": {
                "chapter_number": lambda x: x > 0,
                "novel_id": lambda x: len(x) > 0
            }
        })
        
        # 故事线管理器验证规则
        self.data_validator.register_validation_rules("storyline_manager", {
            "required_fields": ["compressed_context", "upper_constraints"],
            "field_types": {
                "compressed_context": dict,
                "upper_constraints": dict,
                "progress": dict
            }
        })
        
        # 知识图谱验证规则
        self.data_validator.register_validation_rules("knowledge_graph", {
            "required_fields": ["chapter_storyline"],
            "field_types": {
                "chapter_storyline": dict,
                "current_knowledge": dict
            }
        })
        
        # 内容生成器验证规则
        self.data_validator.register_validation_rules("content_generator", {
            "required_fields": ["chapter_storyline", "context"],
            "field_types": {
                "chapter_storyline": dict,
                "context": dict,
                "updated_knowledge": dict
            }
        })
        
        # 质量评估器验证规则
        self.data_validator.register_validation_rules("quality_assessor", {
            "required_fields": ["chapter_content"],
            "field_types": {
                "chapter_content": dict,
                "storyline": dict,
                "knowledge": dict
            }
        })
    
    def _initialize_data_transformers(self):
        """初始化数据转换器"""
        
        # 上下文管理器 -> 故事线管理器
        self.data_transformer.register_transformer(
            "context_manager", "storyline_manager",
            lambda data: {
                "compressed_context": data.get("compressed_context", {}),
                "upper_constraints": data.get("upper_constraints", {}),
                "progress": data.get("progress", {}),
                "relevant_entities": data.get("relevant_entities", []),
                "memory_usage": data.get("memory_usage", 0)
            }
        )
        
        # 故事线管理器 -> 知识图谱
        self.data_transformer.register_transformer(
            "storyline_manager", "knowledge_graph",
            lambda data: {
                "chapter_storyline": data.get("chapter_storyline", {}),
                "current_knowledge": data.get("current_knowledge", {}),
                "deviation_score": data.get("deviation_score", 0.0),
                "consistency_score": data.get("consistency_score", 0.0)
            }
        )
        
        # 知识图谱 -> 内容生成器
        self.data_transformer.register_transformer(
            "knowledge_graph", "content_generator",
            lambda data: {
                "chapter_storyline": data.get("chapter_storyline", {}),
                "updated_knowledge": data.get("updated_knowledge", {}),
                "context": data.get("updated_knowledge", {}),  # 使用updated_knowledge作为context
                "new_entities": data.get("new_entities", [])
            }
        )
        
        # 内容生成器 -> 质量评估器
        self.data_transformer.register_transformer(
            "content_generator", "quality_assessor",
            lambda data: {
                "chapter_content": data.get("chapter_content", {}),
                "storyline": data.get("chapter_storyline", {}),
                "knowledge": data.get("updated_knowledge", {}),
                "generation_metadata": data.get("generation_metadata", {})
            }
        )
    
    def register_agent(self, agent_name: str, agent_instance: Any):
        """注册智能体"""
        self.agents[agent_name] = agent_instance
    
    def register_flow(self, flow: AgentInteractionFlow):
        """注册流程"""
        self.flows[flow.flow_id] = flow
    
    def execute_flow(self, flow_id: str, initial_data: Dict[str, Any], 
                    context_id: str = None) -> Dict[str, Any]:
        """执行智能体交互流程"""
        
        if flow_id not in self.flows:
            return {"error": f"未找到流程: {flow_id}"}
        
        # 创建执行上下文
        if not context_id:
            context_id = f"{flow_id}_{int(time.time())}"
        
        context = AgentExecutionContext(context_id)
        self.execution_contexts[context_id] = context
        
        # 初始化上下文数据
        context.update_data(initial_data)
        
        flow = self.flows[flow_id]
        current_step = 0
        
        try:
            # 执行流程步骤
            while current_step < len(flow.steps):
                step = flow.steps[current_step]
                step_id = step["step_id"]
                agent_name = step["agent_name"]
                
                logger.info(f"🔄 执行步骤 {current_step + 1}/{len(flow.steps)}: {step_id} (智能体: {agent_name})")
                
                # 准备输入数据
                input_data = self._prepare_step_input(step, context)
                
                # 如果有前一个智能体，使用数据转换器
                if current_step > 0:
                    previous_step = flow.steps[current_step - 1]
                    previous_agent = previous_step["agent_name"]
                    
                    # 使用数据转换器转换数据
                    input_data = self.data_transformer.transform_data(previous_agent, agent_name, input_data)
                
                # 验证输入数据
                validation_result = self.data_validator.validate_input(agent_name, input_data)
                if not validation_result["is_valid"]:
                    error_msg = f"输入验证失败: {validation_result['errors']}"
                    logger.debug(f"🔍 调试信息 - 智能体: {agent_name}")
                    logger.info(f"🔍 输入数据: {input_data}")
                    logger.error(f"🔍 验证错误: {validation_result['errors']}")
                    context.record_error(agent_name, "validation_error", error_msg, input_data)
                    return {"error": error_msg}
                
                # 执行智能体
                execution_result = self._execute_agent_step(
                    agent_name, validation_result["cleaned_data"], 
                    step, context
                )
                
                if not execution_result["success"]:
                    # 处理执行失败
                    error_msg = execution_result.get("error", "未知错误")
                    context.record_error(agent_name, "execution_error", error_msg, input_data)
                    
                    # 检查是否有错误处理器
                    if agent_name in flow.error_handlers:
                        recovery_result = flow.error_handlers[agent_name](context, error_msg)
                        if not recovery_result:
                            return {"error": f"智能体执行失败且恢复失败: {error_msg}"}
                    else:
                        return {"error": f"智能体执行失败: {error_msg}"}
                
                # 更新上下文数据
                context.update_data(execution_result["output_data"])
                
                # 检查下一步
                next_steps = step.get("next_steps")
                if next_steps is None:
                    break
                elif isinstance(next_steps, list):
                    # 多分支选择（简化实现，选择第一个）
                    current_step += 1
                else:
                    # 条件分支
                    current_step = self._evaluate_condition(next_steps, context)
            
            # 返回最终结果
            final_result = {
                "success": True,
                "context_id": context_id,
                "final_data": context.data,
                "execution_summary": context.get_performance_summary(),
                "flow_id": flow_id
            }
            
            return final_result
            
        except Exception as e:
            error_msg = f"流程执行异常: {str(e)}"
            context.record_error("system", "flow_execution_error", error_msg)
            return {"error": error_msg}
    
    def _prepare_step_input(self, step: Dict[str, Any], context: AgentExecutionContext) -> Dict[str, Any]:
        """准备步骤输入数据"""
        input_fields = step.get("input_fields", [])
        input_data = {}
        
        for field in input_fields:
            value = context.get_data(field)
            if value is not None:
                input_data[field] = value
        
        return input_data
    
    def _execute_agent_step(self, agent_name: str, input_data: Dict[str, Any], 
                           step: Dict[str, Any], context: AgentExecutionContext) -> Dict[str, Any]:
        """执行智能体步骤"""
        
        if agent_name not in self.agents:
            return {
                "success": False,
                "error": f"未找到智能体: {agent_name}"
            }
        
        agent = self.agents[agent_name]
        start_time = time.time()
        
        try:
            # 设置超时
            timeout = step.get("timeout", 60)
            
            # 执行智能体
            if hasattr(agent, 'process'):
                result = agent.process(input_data)
            else:
                return {
                    "success": False,
                    "error": f"智能体 {agent_name} 没有 process 方法"
                }
            
            end_time = time.time()
            
            # 记录执行历史
            context.record_execution(
                agent_name, start_time, end_time, 
                input_data, result, True
            )
            
            # 检查结果格式
            if not isinstance(result, dict):
                return {
                    "success": False,
                    "error": f"智能体 {agent_name} 返回结果格式错误"
                }
            
            # 检查是否有错误
            if "error" in result:
                return {
                    "success": False,
                    "error": result["error"]
                }
            
            return {
                "success": True,
                "output_data": result,
                "execution_time": end_time - start_time
            }
            
        except Exception as e:
            end_time = time.time()
            error_msg = f"智能体执行异常: {str(e)}"
            
            # 记录执行历史
            context.record_execution(
                agent_name, start_time, end_time, 
                input_data, {}, False, error_msg
            )
            
            return {
                "success": False,
                "error": error_msg
            }
    
    def _evaluate_condition(self, condition: str, context: AgentExecutionContext) -> int:
        """评估条件（简化实现）"""
        # 这里应该实现更复杂的条件评估逻辑
        # 目前简化处理
        return 0
    
    def get_execution_context(self, context_id: str) -> Optional[AgentExecutionContext]:
        """获取执行上下文"""
        return self.execution_contexts.get(context_id)
    
    def get_flow_status(self, context_id: str) -> Dict[str, Any]:
        """获取流程状态"""
        context = self.get_execution_context(context_id)
        if not context:
            return {"error": "未找到执行上下文"}
        
        return {
            "context_id": context_id,
            "status": "running" if len(context.execution_history) < 10 else "completed",
            "progress": len(context.execution_history),
            "performance": context.get_performance_summary(),
            "errors": len(context.error_history)
        }


class AgentPerformanceMonitor:
    """智能体性能监控器"""
    
    def __init__(self):
        self.performance_data = {}
        self.lock = threading.Lock()
    
    def record_performance(self, agent_name: str, execution_time: float, 
                          success: bool, memory_usage: float = 0):
        """记录性能数据"""
        with self.lock:
            if agent_name not in self.performance_data:
                self.performance_data[agent_name] = {
                    "total_executions": 0,
                    "successful_executions": 0,
                    "failed_executions": 0,
                    "total_time": 0.0,
                    "average_time": 0.0,
                    "max_time": 0.0,
                    "min_time": float('inf'),
                    "total_memory": 0.0,
                    "average_memory": 0.0
                }
            
            data = self.performance_data[agent_name]
            data["total_executions"] += 1
            data["total_time"] += execution_time
            data["total_memory"] += memory_usage
            
            if success:
                data["successful_executions"] += 1
            else:
                data["failed_executions"] += 1
            
            data["average_time"] = data["total_time"] / data["total_executions"]
            data["average_memory"] = data["total_memory"] / data["total_executions"]
            data["max_time"] = max(data["max_time"], execution_time)
            data["min_time"] = min(data["min_time"], execution_time)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        with self.lock:
            return {
                "agents": self.performance_data.copy(),
                "summary": self._generate_summary()
            }
    
    def _generate_summary(self) -> Dict[str, Any]:
        """生成摘要"""
        if not self.performance_data:
            return {}
        
        total_executions = sum(data["total_executions"] for data in self.performance_data.values())
        total_successful = sum(data["successful_executions"] for data in self.performance_data.values())
        total_failed = sum(data["failed_executions"] for data in self.performance_data.values())
        total_time = sum(data["total_time"] for data in self.performance_data.values())
        
        return {
            "total_agents": len(self.performance_data),
            "total_executions": total_executions,
            "total_successful": total_successful,
            "total_failed": total_failed,
            "overall_success_rate": total_successful / total_executions if total_executions > 0 else 0,
            "total_execution_time": total_time,
            "average_execution_time": total_time / total_executions if total_executions > 0 else 0
        }

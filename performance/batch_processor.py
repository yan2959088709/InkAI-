"""
批量处理优化器
负责优化批量LLM调用，提升系统性能
"""

import json
import time
import threading
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from utils.logger import get_logger
logger = get_logger("batch_processor")


class BatchProcessor:
    """批量处理优化器"""
    
    def __init__(self, batch_size: int = 5, batch_timeout: float = 2.0):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_requests = []
        self.batch_lock = threading.Lock()
        self.last_batch_time = time.time()
    
    def add_llm_request(self, request: Dict[str, Any]) -> str:
        """添加LLM请求到批量队列"""
        try:
            request_id = f"req_{int(time.time() * 1000)}_{len(self.pending_requests)}"
            request["request_id"] = request_id
            request["timestamp"] = time.time()
            
            with self.batch_lock:
                self.pending_requests.append(request)
                
                # 检查是否需要立即处理批量请求
                if (len(self.pending_requests) >= self.batch_size or 
                    time.time() - self.last_batch_time >= self.batch_timeout):
                    return self._process_batch()
                else:
                    return request_id
                    
        except Exception as e:
            logger.error(f"添加LLM请求失败: {e}")
            return ""
    
    def _process_batch(self) -> str:
        """处理批量请求"""
        try:
            if not self.pending_requests:
                return ""
            
            with self.batch_lock:
                batch_requests = self.pending_requests.copy()
                self.pending_requests.clear()
                self.last_batch_time = time.time()
            
            # 执行批量处理
            batch_result = self._execute_batch_requests(batch_requests)
            
            # 通知所有请求完成
            for request in batch_requests:
                request_id = request.get("request_id", "")
                if request_id in batch_result:
                    # 这里可以添加回调机制通知请求完成
                    pass
            
            return batch_result.get("batch_id", "")
            
        except Exception as e:
            logger.error(f"处理批量请求失败: {e}")
            return ""
    
    def _execute_batch_requests(self, requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行批量请求"""
        try:
            batch_id = f"batch_{int(time.time() * 1000)}"
            
            # 构建批量请求
            batch_request = self._build_batch_request(requests)
            
            # 执行批量LLM调用
            batch_response = self._call_batch_llm(batch_request)
            
            # 解析批量响应
            individual_responses = self._parse_batch_response(batch_response, requests)
            
            return {
                "batch_id": batch_id,
                "total_requests": len(requests),
                "responses": individual_responses,
                "execution_time": time.time() - requests[0].get("timestamp", time.time())
            }
            
        except Exception as e:
            logger.error(f"执行批量请求失败: {e}")
            return {"error": str(e)}
    
    def _build_batch_request(self, requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构建批量请求"""
        try:
            batch_request = {
                "batch_id": f"batch_{int(time.time() * 1000)}",
                "requests": []
            }
            
            for request in requests:
                batch_request["requests"].append({
                    "request_id": request.get("request_id", ""),
                    "messages": request.get("messages", []),
                    "model": request.get("model", "glm-4.5-flash"),
                    "temperature": request.get("temperature", 0.7),
                    "max_tokens": request.get("max_tokens", 2000)
                })
            
            return batch_request
            
        except Exception as e:
            logger.error(f"构建批量请求失败: {e}")
            return {}
    
    def _call_batch_llm(self, batch_request: Dict[str, Any]) -> Dict[str, Any]:
        """调用批量LLM"""
        try:
            # 这里应该调用实际的批量LLM API
            # 目前返回模拟响应，实际使用时需要替换为真实的LLM调用
            responses = []
            for req in batch_request.get("requests", []):
                try:
                    # 模拟LLM调用
                    response = f"批量响应_{req.get('request_id', '')}"
                    responses.append({
                        "request_id": req.get("request_id", ""),
                        "response": response,
                        "status": "success"
                    })
                except Exception as e:
                    responses.append({
                        "request_id": req.get("request_id", ""),
                        "response": "",
                        "status": "error",
                        "error": str(e)
                    })
            
            return {
                "batch_id": batch_request.get("batch_id", ""),
                "responses": responses
            }
            
        except Exception as e:
            logger.error(f"调用批量LLM失败: {e}")
            return {"error": str(e)}
    
    def _parse_batch_response(self, batch_response: Dict[str, Any], 
                            original_requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """解析批量响应"""
        try:
            individual_responses = {}
            
            for response in batch_response.get("responses", []):
                request_id = response.get("request_id", "")
                individual_responses[request_id] = {
                    "response": response.get("response", ""),
                    "status": response.get("status", "success"),
                    "request_id": request_id
                }
            
            return individual_responses
            
        except Exception as e:
            logger.error(f"解析批量响应失败: {e}")
            return {}
    
    def get_pending_requests_count(self) -> int:
        """获取待处理请求数量"""
        with self.batch_lock:
            return len(self.pending_requests)
    
    def force_process_batch(self) -> str:
        """强制处理当前批量请求"""
        return self._process_batch()
    
    def get_batch_stats(self) -> Dict[str, Any]:
        """获取批量处理统计信息"""
        with self.batch_lock:
            return {
                "pending_requests": len(self.pending_requests),
                "batch_size": self.batch_size,
                "batch_timeout": self.batch_timeout,
                "last_batch_time": self.last_batch_time,
                "time_since_last_batch": time.time() - self.last_batch_time
            }


class LLMRequestBatcher:
    """LLM请求批处理器"""
    
    def __init__(self, batch_processor: BatchProcessor):
        self.batch_processor = batch_processor
        self.request_callbacks = {}
    
    def submit_request(self, messages: List[Dict[str, str]], 
                      callback: Optional[callable] = None,
                      **kwargs) -> str:
        """提交LLM请求"""
        try:
            request = {
                "messages": messages,
                "callback": callback,
                **kwargs
            }
            
            request_id = self.batch_processor.add_llm_request(request)
            
            if callback:
                self.request_callbacks[request_id] = callback
            
            return request_id
            
        except Exception as e:
            logger.error(f"提交LLM请求失败: {e}")
            return ""
    
    def get_response(self, request_id: str) -> Optional[Dict[str, Any]]:
        """获取请求响应"""
        try:
            # 这里应该实现响应获取机制
            # 目前返回模拟响应
            return {
                "request_id": request_id,
                "response": f"响应_{request_id}",
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"获取响应失败: {e}")
            return None
    
    def wait_for_response(self, request_id: str, timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        """等待响应"""
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                response = self.get_response(request_id)
                if response:
                    return response
                time.sleep(0.1)
            
            return None
            
        except Exception as e:
            logger.error(f"等待响应失败: {e}")
            return None
    
    def submit_batch_requests(self, requests: List[Dict[str, Any]]) -> List[str]:
        """提交批量请求"""
        try:
            request_ids = []
            for request in requests:
                request_id = self.submit_request(
                    request.get("messages", []),
                    request.get("callback"),
                    **request.get("kwargs", {})
                )
                request_ids.append(request_id)
            
            return request_ids
            
        except Exception as e:
            logger.error(f"提交批量请求失败: {e}")
            return []
    
    def get_batch_responses(self, request_ids: List[str]) -> Dict[str, Any]:
        """获取批量响应"""
        try:
            responses = {}
            for request_id in request_ids:
                response = self.get_response(request_id)
                if response:
                    responses[request_id] = response
            
            return responses
            
        except Exception as e:
            logger.error(f"获取批量响应失败: {e}")
            return {}
    
    def wait_for_batch_responses(self, request_ids: List[str], 
                               timeout: float = 30.0) -> Dict[str, Any]:
        """等待批量响应"""
        try:
            start_time = time.time()
            responses = {}
            
            while time.time() - start_time < timeout:
                for request_id in request_ids:
                    if request_id not in responses:
                        response = self.get_response(request_id)
                        if response:
                            responses[request_id] = response
                
                if len(responses) == len(request_ids):
                    break
                
                time.sleep(0.1)
            
            return responses
            
        except Exception as e:
            logger.error(f"等待批量响应失败: {e}")
            return {}

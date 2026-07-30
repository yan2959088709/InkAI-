"""
性能监控器
负责监控系统性能，提供实时性能数据
"""

import time
import psutil
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import os
from utils.logger import get_logger
logger = get_logger("performance_monitor")


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, monitoring_interval: float = 1.0):
        self.monitoring_interval = monitoring_interval
        self.monitoring_active = False
        self.monitoring_thread = None
        self.performance_data = []
        self.performance_lock = threading.Lock()
        self.start_time = time.time()
        
        # 性能指标
        self.current_metrics = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "memory_available": 0.0,
            "disk_usage": 0.0,
            "network_io": {"bytes_sent": 0, "bytes_recv": 0},
            "active_threads": 0,
            "timestamp": time.time()
        }
        
        # 任务性能统计
        self.task_stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "average_execution_time": 0.0,
            "total_execution_time": 0.0
        }
        
        # LLM调用统计
        self.llm_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "average_response_time": 0.0,
            "total_response_time": 0.0,
            "total_tokens_used": 0
        }
    
    def start_monitoring(self):
        """开始性能监控"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
            logger.info("性能监控已启动")
    
    def stop_monitoring(self):
        """停止性能监控"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join()
        logger.info("性能监控已停止")
    
    def _monitoring_loop(self):
        """监控循环"""
        while self.monitoring_active:
            try:
                # 收集性能数据
                metrics = self._collect_system_metrics()
                
                # 更新当前指标
                with self.performance_lock:
                    self.current_metrics.update(metrics)
                    self.performance_data.append(metrics.copy())
                    
                    # 保持最近1000条记录
                    if len(self.performance_data) > 1000:
                        self.performance_data = self.performance_data[-1000:]
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.info(f"性能监控循环出错: {e}")
                time.sleep(self.monitoring_interval)
    
    def _collect_system_metrics(self) -> Dict[str, Any]:
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_usage = psutil.cpu_percent(interval=0.1)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            memory_available = memory.available / (1024**3)  # GB
            
            # 磁盘使用情况 - 使用当前目录而不是根目录
            try:
                disk = psutil.disk_usage('.')
                disk_usage = (disk.used / disk.total) * 100
            except Exception as e:
                disk_usage = 0
            
            # 网络IO
            try:
                network = psutil.net_io_counters()
                network_io = {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv
                }
            except Exception as e:
                network_io = {"bytes_sent": 0, "bytes_recv": 0}
            
            # 活跃线程数
            active_threads = threading.active_count()
            
            return {
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "memory_available": memory_available,
                "disk_usage": disk_usage,
                "network_io": network_io,
                "active_threads": active_threads,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
            # 返回默认值而不是空字典
            return {
                "cpu_usage": 0,
                "memory_usage": 0,
                "memory_available": 0,
                "disk_usage": 0,
                "network_io": {"bytes_sent": 0, "bytes_recv": 0},
                "active_threads": 1,
                "timestamp": time.time()
            }
    
    def record_task_execution(self, task_type: str, execution_time: float, 
                            success: bool = True):
        """记录任务执行"""
        try:
            with self.performance_lock:
                self.task_stats["total_tasks"] += 1
                self.task_stats["total_execution_time"] += execution_time
                
                if success:
                    self.task_stats["completed_tasks"] += 1
                else:
                    self.task_stats["failed_tasks"] += 1
                
                # 更新平均执行时间
                if self.task_stats["total_tasks"] > 0:
                    self.task_stats["average_execution_time"] = (
                        self.task_stats["total_execution_time"] / 
                        self.task_stats["total_tasks"]
                    )
                
        except Exception as e:
            logger.error(f"记录任务执行失败: {e}")
    
    def record_llm_call(self, response_time: float, success: bool = True, 
                       tokens_used: int = 0):
        """记录LLM调用"""
        try:
            with self.performance_lock:
                self.llm_stats["total_calls"] += 1
                self.llm_stats["total_response_time"] += response_time
                self.llm_stats["total_tokens_used"] += tokens_used
                
                if success:
                    self.llm_stats["successful_calls"] += 1
                else:
                    self.llm_stats["failed_calls"] += 1
                
                # 更新平均响应时间
                if self.llm_stats["total_calls"] > 0:
                    self.llm_stats["average_response_time"] = (
                        self.llm_stats["total_response_time"] / 
                        self.llm_stats["total_calls"]
                    )
                
        except Exception as e:
            logger.error(f"记录LLM调用失败: {e}")
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """获取当前指标"""
        with self.performance_lock:
            return self.current_metrics.copy()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        try:
            with self.performance_lock:
                # 计算运行时间
                uptime = time.time() - self.start_time
                
                # 计算平均指标
                if self.performance_data:
                    avg_cpu = sum(m.get("cpu_usage", 0) for m in self.performance_data) / len(self.performance_data)
                    avg_memory = sum(m.get("memory_usage", 0) for m in self.performance_data) / len(self.performance_data)
                    avg_threads = sum(m.get("active_threads", 0) for m in self.performance_data) / len(self.performance_data)
                else:
                    avg_cpu = avg_memory = avg_threads = 0
                
                return {
                    "uptime": uptime,
                    "current_metrics": self.current_metrics.copy(),
                    "average_metrics": {
                        "cpu_usage": avg_cpu,
                        "memory_usage": avg_memory,
                        "active_threads": avg_threads
                    },
                    "task_stats": self.task_stats.copy(),
                    "llm_stats": self.llm_stats.copy(),
                    "monitoring_active": self.monitoring_active
                }
                
        except Exception as e:
            logger.error(f"获取性能摘要失败: {e}")
            return {}
    
    def get_performance_history(self, duration_minutes: int = 60) -> List[Dict[str, Any]]:
        """获取性能历史数据"""
        try:
            with self.performance_lock:
                cutoff_time = time.time() - (duration_minutes * 60)
                return [
                    data for data in self.performance_data 
                    if data.get("timestamp", 0) >= cutoff_time
                ]
                
        except Exception as e:
            logger.error(f"获取性能历史数据失败: {e}")
            return []
    
    def get_performance_alerts(self) -> List[Dict[str, Any]]:
        """获取性能告警"""
        try:
            alerts = []
            current = self.get_current_metrics()
            
            # CPU使用率告警
            if current.get("cpu_usage", 0) > 80:
                alerts.append({
                    "type": "cpu_usage",
                    "level": "warning",
                    "message": f"CPU使用率过高: {current.get('cpu_usage', 0):.1f}%",
                    "timestamp": time.time()
                })
            
            # 内存使用率告警
            if current.get("memory_usage", 0) > 85:
                alerts.append({
                    "type": "memory_usage",
                    "level": "warning",
                    "message": f"内存使用率过高: {current.get('memory_usage', 0):.1f}%",
                    "timestamp": time.time()
                })
            
            # 磁盘使用率告警
            if current.get("disk_usage", 0) > 90:
                alerts.append({
                    "type": "disk_usage",
                    "level": "critical",
                    "message": f"磁盘使用率过高: {current.get('disk_usage', 0):.1f}%",
                    "timestamp": time.time()
                })
            
            # 任务失败率告警
            if self.task_stats["total_tasks"] > 0:
                failure_rate = self.task_stats["failed_tasks"] / self.task_stats["total_tasks"]
                if failure_rate > 0.1:  # 失败率超过10%
                    alerts.append({
                        "type": "task_failure_rate",
                        "level": "warning",
                        "message": f"任务失败率过高: {failure_rate:.1%}",
                        "timestamp": time.time()
                    })
            
            # LLM调用失败率告警
            if self.llm_stats["total_calls"] > 0:
                llm_failure_rate = self.llm_stats["failed_calls"] / self.llm_stats["total_calls"]
                if llm_failure_rate > 0.05:  # 失败率超过5%
                    alerts.append({
                        "type": "llm_failure_rate",
                        "level": "warning",
                        "message": f"LLM调用失败率过高: {llm_failure_rate:.1%}",
                        "timestamp": time.time()
                    })
            
            return alerts
            
        except Exception as e:
            logger.error(f"获取性能告警失败: {e}")
            return []
    
    def export_performance_data(self, file_path: str):
        """导出性能数据"""
        try:
            with self.performance_lock:
                data = {
                    "export_time": datetime.now().isoformat(),
                    "performance_summary": self.get_performance_summary(),
                    "performance_history": self.performance_data,
                    "task_stats": self.task_stats,
                    "llm_stats": self.llm_stats
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"性能数据已导出到: {file_path}")
                
        except Exception as e:
            logger.error(f"导出性能数据失败: {e}")
    
    def reset_stats(self):
        """重置统计信息"""
        try:
            with self.performance_lock:
                self.task_stats = {
                    "total_tasks": 0,
                    "completed_tasks": 0,
                    "failed_tasks": 0,
                    "average_execution_time": 0.0,
                    "total_execution_time": 0.0
                }
                
                self.llm_stats = {
                    "total_calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "average_response_time": 0.0,
                    "total_response_time": 0.0,
                    "total_tokens_used": 0
                }
                
                self.performance_data.clear()
                self.start_time = time.time()
                
        except Exception as e:
            logger.error(f"重置统计信息失败: {e}")
    
    def __del__(self):
        """析构函数"""
        self.stop_monitoring()

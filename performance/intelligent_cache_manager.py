"""
智能缓存管理器
负责管理各种缓存，提升系统性能
"""

import json
import os
import time
import hashlib
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import threading
from utils.logger import get_logger

logger = get_logger("intelligent_cache_manager")


class IntelligentCacheManager:
    """智能缓存管理器"""
    
    def __init__(self, cache_dir: str = "cache", max_cache_size: int = 1000):
        self.cache_dir = cache_dir
        self.max_cache_size = max_cache_size
        self.memory_cache = {}
        self.cache_lock = threading.Lock()
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_requests": 0
        }
        
        # 确保缓存目录存在
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"创建缓存目录失败: {e}")
            # 使用临时目录作为备选
            import tempfile
            self.cache_dir = tempfile.mkdtemp()
            logger.info(f"使用临时缓存目录: {self.cache_dir}")
    
    def get_cache_key(self, data: Dict[str, Any]) -> str:
        """生成缓存键"""
        try:
            # 将数据转换为字符串并生成哈希
            data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
            return hashlib.md5(data_str.encode('utf-8')).hexdigest()
        except Exception as e:
            return f"cache_key_{int(time.time())}"
    
    def get_assessment_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取评估缓存"""
        try:
            with self.cache_lock:
                self.cache_stats["total_requests"] += 1
                
                # 先检查内存缓存
                if cache_key in self.memory_cache:
                    cache_data = self.memory_cache[cache_key]
                    if self._is_cache_valid(cache_data):
                        self.cache_stats["hits"] += 1
                        return cache_data.get("data")
                
                # 检查文件缓存
                file_path = os.path.join(self.cache_dir, f"assessment_{cache_key}.json")
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                        if self._is_cache_valid(cache_data):
                            # 更新内存缓存
                            self.memory_cache[cache_key] = cache_data
                            self.cache_stats["hits"] += 1
                            return cache_data.get("data")
                
                self.cache_stats["misses"] += 1
                return None
                
        except Exception as e:
            logger.error(f"获取评估缓存失败: {e}")
            return None
    
    def set_assessment_cache(self, cache_key: str, data: Dict[str, Any], 
                           ttl: int = 3600) -> bool:
        """设置评估缓存"""
        try:
            with self.cache_lock:
                cache_data = {
                    "data": data,
                    "timestamp": time.time(),
                    "ttl": ttl,
                    "type": "assessment"
                }
                
                # 更新内存缓存
                self.memory_cache[cache_key] = cache_data
                
                # 保存到文件缓存
                file_path = os.path.join(self.cache_dir, f"assessment_{cache_key}.json")
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
                # 检查缓存大小限制
                self._enforce_cache_size_limit()
                
                return True
                
        except Exception as e:
            logger.error(f"设置评估缓存失败: {e}")
            return False
    
    def get_improvement_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取改进缓存"""
        try:
            with self.cache_lock:
                self.cache_stats["total_requests"] += 1
                
                # 先检查内存缓存
                if cache_key in self.memory_cache:
                    cache_data = self.memory_cache[cache_key]
                    if self._is_cache_valid(cache_data):
                        self.cache_stats["hits"] += 1
                        return cache_data.get("data")
                
                # 检查文件缓存
                file_path = os.path.join(self.cache_dir, f"improvement_{cache_key}.json")
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                        if self._is_cache_valid(cache_data):
                            # 更新内存缓存
                            self.memory_cache[cache_key] = cache_data
                            self.cache_stats["hits"] += 1
                            return cache_data.get("data")
                
                self.cache_stats["misses"] += 1
                return None
                
        except Exception as e:
            logger.error(f"获取改进缓存失败: {e}")
            return None
    
    def set_improvement_cache(self, cache_key: str, data: Dict[str, Any], 
                            ttl: int = 3600) -> bool:
        """设置改进缓存"""
        try:
            with self.cache_lock:
                cache_data = {
                    "data": data,
                    "timestamp": time.time(),
                    "ttl": ttl,
                    "type": "improvement"
                }
                
                # 更新内存缓存
                self.memory_cache[cache_key] = cache_data
                
                # 保存到文件缓存
                file_path = os.path.join(self.cache_dir, f"improvement_{cache_key}.json")
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
                # 检查缓存大小限制
                self._enforce_cache_size_limit()
                
                return True
                
        except Exception as e:
            logger.error(f"设置改进缓存失败: {e}")
            return False
    
    def get_context_cache(self, novel_id: str, chapter_number: int) -> Optional[Dict[str, Any]]:
        """获取上下文缓存"""
        try:
            cache_key = f"context_{novel_id}_{chapter_number}"
            with self.cache_lock:
                self.cache_stats["total_requests"] += 1
                
                # 先检查内存缓存
                if cache_key in self.memory_cache:
                    cache_data = self.memory_cache[cache_key]
                    if self._is_cache_valid(cache_data):
                        self.cache_stats["hits"] += 1
                        return cache_data.get("data")
                
                # 检查文件缓存
                file_path = os.path.join(self.cache_dir, f"context_{cache_key}.json")
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                        if self._is_cache_valid(cache_data):
                            # 更新内存缓存
                            self.memory_cache[cache_key] = cache_data
                            self.cache_stats["hits"] += 1
                            return cache_data.get("data")
                
                self.cache_stats["misses"] += 1
                return None
                
        except Exception as e:
            logger.error(f"获取上下文缓存失败: {e}")
            return None
    
    def set_context_cache(self, novel_id: str, chapter_number: int, 
                         data: Dict[str, Any], ttl: int = 1800) -> bool:
        """设置上下文缓存"""
        try:
            cache_key = f"context_{novel_id}_{chapter_number}"
            with self.cache_lock:
                cache_data = {
                    "data": data,
                    "timestamp": time.time(),
                    "ttl": ttl,
                    "type": "context"
                }
                
                # 更新内存缓存
                self.memory_cache[cache_key] = cache_data
                
                # 保存到文件缓存
                file_path = os.path.join(self.cache_dir, f"context_{cache_key}.json")
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
                return True
                
        except Exception as e:
            logger.error(f"设置上下文缓存失败: {e}")
            return False
    
    def get_llm_response_cache(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """获取LLM响应缓存"""
        try:
            cache_key = self.get_cache_key({"messages": messages})
            with self.cache_lock:
                self.cache_stats["total_requests"] += 1
                
                # 先检查内存缓存
                if cache_key in self.memory_cache:
                    cache_data = self.memory_cache[cache_key]
                    if self._is_cache_valid(cache_data):
                        self.cache_stats["hits"] += 1
                        return cache_data.get("data")
                
                # 检查文件缓存
                file_path = os.path.join(self.cache_dir, f"llm_{cache_key}.json")
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                        if self._is_cache_valid(cache_data):
                            # 更新内存缓存
                            self.memory_cache[cache_key] = cache_data
                            self.cache_stats["hits"] += 1
                            return cache_data.get("data")
                
                self.cache_stats["misses"] += 1
                return None
                
        except Exception as e:
            logger.error(f"获取LLM响应缓存失败: {e}")
            return None
    
    def set_llm_response_cache(self, messages: List[Dict[str, str]], 
                             response: str, ttl: int = 7200) -> bool:
        """设置LLM响应缓存"""
        try:
            cache_key = self.get_cache_key({"messages": messages})
            with self.cache_lock:
                cache_data = {
                    "data": response,
                    "timestamp": time.time(),
                    "ttl": ttl,
                    "type": "llm_response"
                }
                
                # 更新内存缓存
                self.memory_cache[cache_key] = cache_data
                
                # 保存到文件缓存
                file_path = os.path.join(self.cache_dir, f"llm_{cache_key}.json")
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
                return True
                
        except Exception as e:
            logger.error(f"设置LLM响应缓存失败: {e}")
            return False
    
    def _is_cache_valid(self, cache_data: Dict[str, Any]) -> bool:
        """检查缓存是否有效"""
        try:
            timestamp = cache_data.get("timestamp", 0)
            ttl = cache_data.get("ttl", 3600)
            return time.time() - timestamp < ttl
        except Exception:
            return False
    
    def _enforce_cache_size_limit(self):
        """强制执行缓存大小限制"""
        try:
            if len(self.memory_cache) > self.max_cache_size:
                # 按时间戳排序，删除最旧的缓存
                sorted_items = sorted(
                    self.memory_cache.items(),
                    key=lambda x: x[1].get("timestamp", 0)
                )
                
                # 删除最旧的缓存项
                items_to_remove = len(self.memory_cache) - self.max_cache_size
                for i in range(items_to_remove):
                    key, _ = sorted_items[i]
                    del self.memory_cache[key]
                    self.cache_stats["evictions"] += 1
                    
        except Exception as e:
            logger.error(f"执行缓存大小限制失败: {e}")
    
    def clear_cache(self, cache_type: str = None):
        """清理缓存"""
        try:
            with self.cache_lock:
                if cache_type:
                    # 清理特定类型的缓存
                    keys_to_remove = []
                    for key, cache_data in self.memory_cache.items():
                        if cache_data.get("type") == cache_type:
                            keys_to_remove.append(key)
                    
                    for key in keys_to_remove:
                        del self.memory_cache[key]
                else:
                    # 清理所有缓存
                    self.memory_cache.clear()
                
                # 清理文件缓存
                if os.path.exists(self.cache_dir):
                    for filename in os.listdir(self.cache_dir):
                        if cache_type:
                            if filename.startswith(f"{cache_type}_"):
                                os.remove(os.path.join(self.cache_dir, filename))
                        else:
                            os.remove(os.path.join(self.cache_dir, filename))
                            
        except Exception as e:
            logger.error(f"清理缓存失败: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.cache_lock:
            hit_rate = 0
            if self.cache_stats["total_requests"] > 0:
                hit_rate = self.cache_stats["hits"] / self.cache_stats["total_requests"]
            
            return {
                "total_requests": self.cache_stats["total_requests"],
                "hits": self.cache_stats["hits"],
                "misses": self.cache_stats["misses"],
                "evictions": self.cache_stats["evictions"],
                "hit_rate": hit_rate,
                "memory_cache_size": len(self.memory_cache),
                "max_cache_size": self.max_cache_size
            }
    
    def cleanup_expired_cache(self):
        """清理过期缓存"""
        try:
            with self.cache_lock:
                keys_to_remove = []
                for key, cache_data in self.memory_cache.items():
                    if not self._is_cache_valid(cache_data):
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self.memory_cache[key]
                    
        except Exception as e:
            logger.error(f"清理过期缓存失败: {e}")

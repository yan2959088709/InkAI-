"""
智能内存管理系统
实现内存优化和智能缓存管理
"""

import json
import os
import gc
import psutil
import threading
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import OrderedDict
import hashlib
from utils.logger import get_logger
logger = get_logger("intelligent_memory_manager")


class MemoryUsageMonitor:
    """内存使用监控器"""
    
    def __init__(self):
        self.monitoring = False
        self.monitor_thread = None
        self.memory_history = []
        self.peak_memory = 0
        self.current_memory = 0
        self.lock = threading.Lock()
    
    def start_monitoring(self, interval: float = 5.0):
        """开始监控"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
    
    def _monitor_loop(self, interval: float):
        """监控循环"""
        while self.monitoring:
            try:
                # 获取内存使用情况
                memory_info = psutil.virtual_memory()
                process = psutil.Process()
                process_memory = process.memory_info()
                
                memory_data = {
                    "timestamp": datetime.now().isoformat(),
                    "system_memory_percent": memory_info.percent,
                    "system_memory_available": memory_info.available,
                    "process_memory_rss": process_memory.rss,
                    "process_memory_vms": process_memory.vms,
                    "process_memory_percent": process.memory_percent()
                }
                
                with self.lock:
                    self.current_memory = memory_info.percent
                    self.peak_memory = max(self.peak_memory, memory_info.percent)
                    self.memory_history.append(memory_data)
                    
                    # 只保留最近100条记录
                    if len(self.memory_history) > 100:
                        self.memory_history.pop(0)
                
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"内存监控异常: {e}")
                time.sleep(interval)
    
    def get_memory_status(self) -> Dict[str, Any]:
        """获取内存状态"""
        with self.lock:
            return {
                "current_memory_percent": self.current_memory,
                "peak_memory_percent": self.peak_memory,
                "memory_history_count": len(self.memory_history),
                "is_high_memory_usage": self.current_memory > 80,
                "memory_trend": self._calculate_memory_trend()
            }
    
    def _calculate_memory_trend(self) -> str:
        """计算内存趋势"""
        if len(self.memory_history) < 10:
            return "unknown"
        
        recent_data = self.memory_history[-10:]
        memory_values = [data["system_memory_percent"] for data in recent_data]
        
        # 简单趋势计算
        first_half_avg = sum(memory_values[:5]) / 5
        second_half_avg = sum(memory_values[5:]) / 5
        
        if second_half_avg > first_half_avg + 5:
            return "increasing"
        elif second_half_avg < first_half_avg - 5:
            return "decreasing"
        else:
            return "stable"


class IntelligentCache:
    """智能缓存系统"""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 512):
        self.max_size = max_size
        self.max_memory_mb = max_memory_mb
        self.cache = OrderedDict()
        self.access_times = {}
        self.access_counts = {}
        self.memory_usage = 0
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存项"""
        with self.lock:
            if key in self.cache:
                # 更新访问时间和计数
                self.access_times[key] = time.time()
                self.access_counts[key] = self.access_counts.get(key, 0) + 1
                
                # 移动到末尾（LRU）
                value = self.cache.pop(key)
                self.cache[key] = value
                
                return value
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """设置缓存项"""
        with self.lock:
            try:
                # 检查内存限制
                if self._should_evict():
                    self._evict_items()
                
                # 设置缓存项
                self.cache[key] = value
                self.access_times[key] = time.time()
                self.access_counts[key] = 1
                
                # 更新内存使用量
                self._update_memory_usage()
                
                return True
                
            except Exception as e:
                logger.error(f"设置缓存失败: {e}")
                return False
    
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                if key in self.access_times:
                    del self.access_times[key]
                if key in self.access_counts:
                    del self.access_counts[key]
                self._update_memory_usage()
                return True
            return False
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
            self.access_counts.clear()
            self.memory_usage = 0
    
    def _should_evict(self) -> bool:
        """判断是否需要清理"""
        # 检查大小限制
        if len(self.cache) >= self.max_size:
            return True
        
        # 检查内存限制
        memory_mb = self.memory_usage / (1024 * 1024)
        if memory_mb >= self.max_memory_mb:
            return True
        
        return False
    
    def _evict_items(self):
        """清理缓存项"""
        # 计算清理数量
        evict_count = max(1, len(self.cache) // 10)  # 清理10%
        
        # 按访问频率和最近访问时间计算分数
        scores = {}
        current_time = time.time()
        
        for key in self.cache:
            access_time = self.access_times.get(key, current_time)
            access_count = self.access_counts.get(key, 1)
            
            # 分数 = 访问次数 / (当前时间 - 访问时间 + 1)
            # 分数越低，越应该被清理
            scores[key] = access_count / (current_time - access_time + 1)
        
        # 按分数排序，清理分数最低的项
        sorted_keys = sorted(scores.keys(), key=lambda k: scores[k])
        
        for i in range(min(evict_count, len(sorted_keys))):
            key = sorted_keys[i]
            self.delete(key)
    
    def _update_memory_usage(self):
        """更新内存使用量"""
        try:
            total_size = 0
            for key, value in self.cache.items():
                # 估算对象大小
                if isinstance(value, str):
                    total_size += len(value.encode('utf-8'))
                elif isinstance(value, (dict, list)):
                    total_size += len(str(value).encode('utf-8'))
                else:
                    total_size += 100  # 默认估算
            
            self.memory_usage = total_size
        except Exception as e:
            pass
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self.lock:
            return {
                "cache_size": len(self.cache),
                "max_size": self.max_size,
                "memory_usage_mb": self.memory_usage / (1024 * 1024),
                "max_memory_mb": self.max_memory_mb,
                "hit_rate": self._calculate_hit_rate(),
                "access_counts": dict(self.access_counts)
            }
    
    def _calculate_hit_rate(self) -> float:
        """计算命中率"""
        total_access = sum(self.access_counts.values())
        if total_access == 0:
            return 0.0
        
        # 简化计算：当前缓存项数 / 总访问次数
        return len(self.cache) / total_access


class ContextCompressor:
    """上下文压缩器"""
    
    def __init__(self):
        self.compression_ratios = {
            "high": 0.1,    # 压缩到10%
            "medium": 0.3,  # 压缩到30%
            "low": 0.6      # 压缩到60%
        }
    
    def compress_context(self, context: Dict[str, Any], 
                        compression_level: str = "medium") -> Dict[str, Any]:
        """压缩上下文"""
        
        ratio = self.compression_ratios.get(compression_level, 0.3)
        
        compressed_context = {}
        
        for key, value in context.items():
            if isinstance(value, str):
                # 压缩文本
                compressed_context[key] = self._compress_text(value, ratio)
            elif isinstance(value, list):
                # 压缩列表
                compressed_context[key] = self._compress_list(value, ratio)
            elif isinstance(value, dict):
                # 压缩字典
                compressed_context[key] = self._compress_dict(value, ratio)
            else:
                # 保持原值
                compressed_context[key] = value
        
        return compressed_context
    
    def _compress_text(self, text: str, ratio: float) -> str:
        """压缩文本"""
        if len(text) <= 100:  # 短文本不压缩
            return text
        
        # 保留开头和结尾
        keep_length = int(len(text) * ratio)
        if keep_length < 50:
            keep_length = 50
        
        start_length = keep_length // 2
        end_length = keep_length - start_length
        
        if len(text) <= keep_length:
            return text
        
        return text[:start_length] + "...[压缩]" + text[-end_length:]
    
    def _compress_list(self, items: List[Any], ratio: float) -> List[Any]:
        """压缩列表"""
        if len(items) <= 5:  # 短列表不压缩
            return items
        
        keep_count = max(1, int(len(items) * ratio))
        
        # 保留前几个和后几个
        if keep_count >= len(items):
            return items
        
        start_count = keep_count // 2
        end_count = keep_count - start_count
        
        result = items[:start_count]
        if end_count > 0:
            result.extend(items[-end_count:])
        
        return result
    
    def _compress_dict(self, data: Dict[str, Any], ratio: float) -> Dict[str, Any]:
        """压缩字典"""
        if len(data) <= 10:  # 小字典不压缩
            return data
        
        keep_count = max(1, int(len(data) * ratio))
        
        # 按重要性排序（简化实现）
        important_keys = list(data.keys())[:keep_count]
        
        return {key: data[key] for key in important_keys}


class DataArchiver:
    """数据归档器"""
    
    def __init__(self, archive_dir: str = "archive"):
        self.archive_dir = archive_dir
        os.makedirs(archive_dir, exist_ok=True)
    
    def archive_old_data(self, novel_id: str, cutoff_chapter: int) -> bool:
        """归档旧数据"""
        try:
            novel_dir = f"data/novels/{novel_id}"
            archive_file = os.path.join(self.archive_dir, f"{novel_id}_chapters_{cutoff_chapter}.json")
            
            archived_data = {
                "novel_id": novel_id,
                "cutoff_chapter": cutoff_chapter,
                "archived_at": datetime.now().isoformat(),
                "chapters": {}
            }
            
            # 归档旧章节
            for chapter_num in range(1, cutoff_chapter):
                chapter_file = os.path.join(novel_dir, f"chapter_{chapter_num:03d}.json")
                if os.path.exists(chapter_file):
                    with open(chapter_file, 'r', encoding='utf-8') as f:
                        chapter_data = json.load(f)
                    
                    # 压缩章节数据
                    compressed_data = self._compress_chapter_data(chapter_data)
                    archived_data["chapters"][chapter_num] = compressed_data
            
            # 保存归档文件
            with open(archive_file, 'w', encoding='utf-8') as f:
                json.dump(archived_data, f, ensure_ascii=False, indent=2)
            
            # 删除原始文件
            for chapter_num in range(1, cutoff_chapter):
                chapter_file = os.path.join(novel_dir, f"chapter_{chapter_num:03d}.json")
                if os.path.exists(chapter_file):
                    os.remove(chapter_file)
            
            return True
            
        except Exception as e:
            logger.error(f"归档数据失败: {e}")
            return False
    
    def _compress_chapter_data(self, chapter_data: Dict[str, Any]) -> Dict[str, Any]:
        """压缩章节数据"""
        compressed = {
            "title": chapter_data.get("title", ""),
            "chapter_number": chapter_data.get("chapter_number", 0),
            "word_count": chapter_data.get("word_count", 0),
            "summary": chapter_data.get("summary", ""),
            "key_events": chapter_data.get("key_events", []),
            "foreshadowing": chapter_data.get("foreshadowing", [])
        }
        
        # 压缩内容
        content = chapter_data.get("content", "")
        if len(content) > 500:
            compressed["content"] = content[:200] + "...[压缩]" + content[-200:]
        else:
            compressed["content"] = content
        
        return compressed
    
    def restore_archived_data(self, novel_id: str, archive_file: str) -> bool:
        """恢复归档数据"""
        try:
            archive_path = os.path.join(self.archive_dir, archive_file)
            if not os.path.exists(archive_path):
                return False
            
            with open(archive_path, 'r', encoding='utf-8') as f:
                archived_data = json.load(f)
            
            novel_dir = f"data/novels/{novel_id}"
            os.makedirs(novel_dir, exist_ok=True)
            
            # 恢复章节数据
            for chapter_num, chapter_data in archived_data["chapters"].items():
                chapter_file = os.path.join(novel_dir, f"chapter_{int(chapter_num):03d}.json")
                with open(chapter_file, 'w', encoding='utf-8') as f:
                    json.dump(chapter_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"恢复归档数据失败: {e}")
            return False


class IntelligentMemoryManager:
    """智能内存管理器"""
    
    def __init__(self, data_manager=None):
        self.data_manager = data_manager
        
        # 内存监控
        self.memory_monitor = MemoryUsageMonitor()
        
        # 智能缓存
        self.context_cache = IntelligentCache(max_size=500, max_memory_mb=256)
        self.storyline_cache = IntelligentCache(max_size=200, max_memory_mb=128)
        self.knowledge_cache = IntelligentCache(max_size=100, max_memory_mb=64)
        
        # 上下文压缩器
        self.context_compressor = ContextCompressor()
        
        # 数据归档器
        self.data_archiver = DataArchiver()
        
        # 配置
        self.max_memory_percent = 80
        self.cleanup_threshold = 70
        self.archive_threshold = 50
        
        # 统计信息
        self.cleanup_count = 0
        self.archive_count = 0
        self.compression_count = 0
        
        # 启动监控
        self.memory_monitor.start_monitoring()
    
    def get_context_with_compression(self, novel_id: str, chapter: int, 
                                   max_context_size: int = 8000) -> Dict[str, Any]:
        """获取压缩的上下文"""
        
        cache_key = f"context_{novel_id}_{chapter}"
        
        # 尝试从缓存获取
        cached_context = self.context_cache.get(cache_key)
        if cached_context:
            return cached_context
        
        # 生成上下文
        context = self._generate_context(novel_id, chapter)
        
        # 检查上下文大小
        context_size = self._estimate_context_size(context)
        
        if context_size > max_context_size:
            # 需要压缩
            compression_level = self._determine_compression_level(context_size, max_context_size)
            context = self.context_compressor.compress_context(context, compression_level)
            self.compression_count += 1
        
        # 缓存结果
        self.context_cache.set(cache_key, context)
        
        return context
    
    def _generate_context(self, novel_id: str, chapter: int) -> Dict[str, Any]:
        """生成上下文（简化实现）"""
        context = {
            "novel_id": novel_id,
            "current_chapter": chapter,
            "previous_chapters": [],
            "character_info": {},
            "world_setting": {},
            "story_progress": {}
        }
        
        # 加载最近章节
        recent_chapters = []
        for i in range(max(1, chapter - 5), chapter):
            chapter_data = self._load_chapter_data(novel_id, i)
            if chapter_data:
                recent_chapters.append(chapter_data)
        
        context["previous_chapters"] = recent_chapters
        
        return context
    
    def _load_chapter_data(self, novel_id: str, chapter: int) -> Optional[Dict[str, Any]]:
        """加载章节数据"""
        try:
            if self.data_manager:
                chapters = self.data_manager.get_novel_chapters(novel_id)
                if chapters and chapter <= len(chapters):
                    return chapters[chapter - 1]
            return None
        except Exception as e:
            return None
    
    def _estimate_context_size(self, context: Dict[str, Any]) -> int:
        """估算上下文大小"""
        return len(str(context).encode('utf-8'))
    
    def _determine_compression_level(self, current_size: int, target_size: int) -> str:
        """确定压缩级别"""
        ratio = target_size / current_size
        
        if ratio < 0.2:
            return "high"
        elif ratio < 0.5:
            return "medium"
        else:
            return "low"
    
    def check_and_cleanup(self) -> bool:
        """检查并清理内存"""
        memory_status = self.memory_monitor.get_memory_status()
        
        if memory_status["current_memory_percent"] > self.max_memory_percent:
            # 内存使用过高，需要清理
            self._perform_cleanup()
            return True
        elif memory_status["current_memory_percent"] > self.cleanup_threshold:
            # 内存使用较高，预防性清理
            self._perform_light_cleanup()
            return True
        
        return False
    
    def _perform_cleanup(self):
        """执行完整清理"""
        logger.info("🧹 执行内存清理...")
        
        # 清理缓存
        self.context_cache.clear()
        self.storyline_cache.clear()
        self.knowledge_cache.clear()
        
        # 强制垃圾回收
        gc.collect()
        
        # 归档旧数据
        self._archive_old_data()
        
        self.cleanup_count += 1
        logger.info(f"✅ 内存清理完成，已清理 {self.cleanup_count} 次")
    
    def _perform_light_cleanup(self):
        """执行轻度清理"""
        logger.info("🧹 执行轻度内存清理...")
        
        # 清理部分缓存
        self.context_cache._evict_items()
        self.storyline_cache._evict_items()
        
        # 垃圾回收
        gc.collect()
        
        logger.info("✅ 轻度内存清理完成")
    
    def _archive_old_data(self):
        """归档旧数据"""
        try:
            # 这里需要根据实际需求实现归档逻辑
            # 例如归档超过20章的旧数据
            pass
        except Exception as e:
            logger.error(f"归档旧数据失败: {e}")
    
    def get_memory_report(self) -> Dict[str, Any]:
        """获取内存报告"""
        memory_status = self.memory_monitor.get_memory_status()
        
        return {
            "memory_status": memory_status,
            "cache_stats": {
                "context_cache": self.context_cache.get_stats(),
                "storyline_cache": self.storyline_cache.get_stats(),
                "knowledge_cache": self.knowledge_cache.get_stats()
            },
            "cleanup_stats": {
                "cleanup_count": self.cleanup_count,
                "archive_count": self.archive_count,
                "compression_count": self.compression_count
            },
            "recommendations": self._generate_recommendations(memory_status)
        }
    
    def _generate_recommendations(self, memory_status: Dict[str, Any]) -> List[str]:
        """生成建议"""
        recommendations = []
        
        if memory_status["current_memory_percent"] > 90:
            recommendations.append("内存使用过高，建议立即清理")
        elif memory_status["current_memory_percent"] > 80:
            recommendations.append("内存使用较高，建议进行清理")
        
        if memory_status["memory_trend"] == "increasing":
            recommendations.append("内存使用呈上升趋势，建议检查内存泄漏")
        
        cache_stats = self.context_cache.get_stats()
        if cache_stats["hit_rate"] < 0.3:
            recommendations.append("缓存命中率较低，建议优化缓存策略")
        
        return recommendations
    
    def cleanup_old_data(self, novel_id: str, current_chapter: int):
        """清理旧数据"""
        try:
            # 归档超过20章的旧数据
            if current_chapter > 20:
                cutoff_chapter = current_chapter - 20
                success = self.data_archiver.archive_old_data(novel_id, cutoff_chapter)
                if success:
                    self.archive_count += 1
                    logger.info(f"✅ 已归档小说 {novel_id} 第1-{cutoff_chapter}章的数据")
            
            # 清理相关缓存
            self._clear_novel_cache(novel_id)
            
        except Exception as e:
            logger.error(f"清理旧数据失败: {e}")
    
    def _clear_novel_cache(self, novel_id: str):
        """清理小说相关缓存"""
        # 清理上下文缓存
        keys_to_remove = []
        for key in self.context_cache.cache.keys():
            if key.startswith(f"context_{novel_id}_"):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            self.context_cache.delete(key)
        
        # 清理故事线缓存
        keys_to_remove = []
        for key in self.storyline_cache.cache.keys():
            if key.startswith(f"storyline_{novel_id}_"):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            self.storyline_cache.delete(key)
    
    def shutdown(self):
        """关闭内存管理器"""
        self.memory_monitor.stop_monitoring()
        self._perform_cleanup()
        logger.info("🛑 智能内存管理器已关闭")

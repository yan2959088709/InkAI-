"""
API速率限制器
控制对智普AI API的并发调用，避免超出限制
"""

import time
import threading
from typing import Optional
from datetime import datetime, timedelta
from utils.logger import get_logger

logger = get_logger("api_rate_limiter")


class APIRateLimiter:
    """API速率限制器"""
    
    def __init__(self, max_concurrent: int = 2, min_interval: float = 1.0):
        """
        初始化速率限制器
        
        Args:
            max_concurrent: 最大并发数
            min_interval: 最小调用间隔（秒）
        """
        self.max_concurrent = max_concurrent
        self.min_interval = min_interval
        
        # 并发控制
        self.semaphore = threading.Semaphore(max_concurrent)
        self.lock = threading.Lock()
        
        # 调用间隔控制
        self.last_call_time = None
        
        # 统计信息
        self.total_calls = 0
        self.blocked_calls = 0
        
    def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        获取API调用许可
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            是否成功获取许可
        """
        # 尝试获取并发许可
        if not self.semaphore.acquire(timeout=timeout):
            self.blocked_calls += 1
            return False
        
        # 控制调用间隔
        with self.lock:
            current_time = time.time()
            
            if self.last_call_time is not None:
                elapsed = current_time - self.last_call_time
                if elapsed < self.min_interval:
                    sleep_time = self.min_interval - elapsed
                    logger.info(f"🕒 API调用间隔控制，等待 {sleep_time:.1f} 秒...")
                    time.sleep(sleep_time)
            
            self.last_call_time = time.time()
            self.total_calls += 1
        
        return True
    
    def release(self):
        """释放API调用许可"""
        self.semaphore.release()
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_calls": self.total_calls,
            "blocked_calls": self.blocked_calls,
            "current_concurrent": self.max_concurrent - self.semaphore._value,
            "max_concurrent": self.max_concurrent,
            "min_interval": self.min_interval
        }


class APICallContext:
    """API调用上下文管理器"""
    
    def __init__(self, rate_limiter: APIRateLimiter, timeout: Optional[float] = 30.0):
        self.rate_limiter = rate_limiter
        self.timeout = timeout
        self.acquired = False
    
    def __enter__(self):
        self.acquired = self.rate_limiter.acquire(self.timeout)
        if not self.acquired:
            raise Exception("无法获取API调用许可，请稍后重试")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.acquired:
            self.rate_limiter.release()


# 全局速率限制器实例
_global_rate_limiter = None


def get_global_rate_limiter() -> APIRateLimiter:
    """获取全局速率限制器"""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = APIRateLimiter(
            max_concurrent=3,  # 最大并发数设为3（qwen-long支持更高并发）
            min_interval=0.3   # 最小间隔0.3秒
        )
    return _global_rate_limiter


def api_call_with_rate_limit(func, *args, **kwargs):
    """
    带速率限制的API调用
    
    Args:
        func: 要调用的函数
        *args: 函数参数
        **kwargs: 函数关键字参数
        
    Returns:
        函数执行结果
    """
    rate_limiter = get_global_rate_limiter()
    
    with APICallContext(rate_limiter):
        return func(*args, **kwargs)


if __name__ == "__main__":
    # 测试速率限制器
    import concurrent.futures
    from utils.logger import get_logger
    logger = get_logger("api_rate_limiter")
    
    def test_api_call(call_id):
        """模拟API调用"""
        rate_limiter = get_global_rate_limiter()
        
        with APICallContext(rate_limiter):
            logger.info(f"API调用 {call_id} 开始")
            time.sleep(0.1)  # 模拟API调用耗时
            logger.info(f"API调用 {call_id} 完成")
            return f"结果 {call_id}"
    
    logger.info("🧪 测试API速率限制器...")
    
    # 并发测试
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(test_api_call, i) for i in range(10)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    # 显示统计信息
    stats = get_global_rate_limiter().get_stats()
    logger.info(f"📊 统计信息: {stats}")
    logger.info("✅ 测试完成")

"""
InkAI 统一日志模块
提供统一的日志记录功能，替代所有print语句
"""

import logging
import sys
import os
from datetime import datetime
from typing import Optional


class InkAILogger:
    """InkAI 日志管理器"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not InkAILogger._initialized:
            self._setup_logging()
            InkAILogger._initialized = True
    
    def _setup_logging(self):
        """设置日志配置"""
        # 创建日志目录
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # 生成日志文件名
        log_file = os.path.join(log_dir, f"inkai_{datetime.now().strftime('%Y%m%d')}.log")
        
        # 配置根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        
        # 文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        
        # 添加处理器
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
    
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """获取指定名称的日志器"""
        return logging.getLogger(name)


def get_logger(name: str) -> logging.Logger:
    """获取日志器的便捷函数"""
    # 确保日志系统已初始化
    InkAILogger()
    return logging.getLogger(name)


# 便捷的日志函数
def debug(msg: str, logger_name: str = "inkai"):
    """记录调试信息"""
    get_logger(logger_name).debug(msg)


def info(msg: str, logger_name: str = "inkai"):
    """记录信息"""
    get_logger(logger_name).info(msg)


def warning(msg: str, logger_name: str = "inkai"):
    """记录警告"""
    get_logger(logger_name).warning(msg)


def error(msg: str, logger_name: str = "inkai"):
    """记录错误"""
    get_logger(logger_name).error(msg)


def critical(msg: str, logger_name: str = "inkai"):
    """记录严重错误"""
    get_logger(logger_name).critical(msg)


# 用于替换print的格式化函数
def log_info(msg: str, logger_name: str = "inkai"):
    """格式化信息日志（用于替换print）"""
    get_logger(logger_name).info(msg)


def log_error(msg: str, logger_name: str = "inkai"):
    """格式化错误日志（用于替换print）"""
    get_logger(logger_name).error(msg)


def log_warning(msg: str, logger_name: str = "inkai"):
    """格式化警告日志（用于替换print）"""
    get_logger(logger_name).warning(msg)


# 模块级别的日志器
logger = get_logger("inkai")

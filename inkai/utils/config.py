# 配置文件
# 包含API配置、系统配置、创作配置等

import os
from typing import Dict, Any

# ==================== API配置 ====================
API_CONFIGS = {
    "zhipuai": {
        "api_key": os.getenv("ZHIPUAI_API_KEY", "请在此处填写您的智谱AI_API密钥"),  # 👈 请替换为您的真实API密钥
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "model": "glm-4.5-flash",
        "temperature": 0.6,
        "max_tokens": 4000
    },
    "openai": {
        "api_key": os.getenv("OPENAI_API_KEY", "your_openai_api_key_here"), 
        "base_url": "https://api.openai.com/v1/",
        "model": "gpt-3.5-turbo",
        "temperature": 0.6,
        "max_tokens": 4000
    }
}

# 选择使用的API提供商
CURRENT_API = os.getenv("INKAI_API_PROVIDER", "zhipuai")  # 可选：zhipuai, openai
API_CONFIG = API_CONFIGS[CURRENT_API]

# ==================== 系统配置 ====================
SYSTEM_CONFIG = {
    "data_dir": os.getenv("INKAI_DATA_DIR", "novel_data"),
    "backup_dir": os.getenv("INKAI_BACKUP_DIR", "backups"), 
    "log_dir": os.getenv("INKAI_LOG_DIR", "logs"),
    "max_retries": int(os.getenv("INKAI_MAX_RETRIES", "3")),
    "timeout": int(os.getenv("INKAI_TIMEOUT", "30")),
    "auto_save": os.getenv("INKAI_AUTO_SAVE", "True").lower() == "true",
    "quality_threshold": int(os.getenv("INKAI_QUALITY_THRESHOLD", "70")),
    "max_chapters_per_novel": int(os.getenv("INKAI_MAX_CHAPTERS", "1000")),
    "cache_size_limit": int(os.getenv("INKAI_CACHE_SIZE", "100")),  # 缓存大小限制
    "log_level": os.getenv("INKAI_LOG_LEVEL", "INFO")  # 日志级别
}

# ==================== 创作配置 ====================
CREATIVE_CONFIG = {
    "default_chapter_length": int(os.getenv("INKAI_DEFAULT_CHAPTER_LENGTH", "2500")),
    "min_chapter_length": int(os.getenv("INKAI_MIN_CHAPTER_LENGTH", "1500")),
    "max_chapter_length": int(os.getenv("INKAI_MAX_CHAPTER_LENGTH", "4000")),
    "enable_quality_check": os.getenv("INKAI_ENABLE_QUALITY_CHECK", "True").lower() == "true",
    "enable_auto_improvement": os.getenv("INKAI_ENABLE_AUTO_IMPROVEMENT", "True").lower() == "true",
    "story_structure": os.getenv("INKAI_STORY_STRUCTURE", "三幕剧"),
    "writing_style": os.getenv("INKAI_WRITING_STYLE", "网络小说")
}

def get_config(config_name: str) -> Dict[str, Any]:
    """获取配置"""
    configs = {
        "api": API_CONFIG,
        "system": SYSTEM_CONFIG, 
        "creative": CREATIVE_CONFIG
    }
    return configs.get(config_name, {})

def update_config(config_name: str, updates: Dict[str, Any]) -> bool:
    """更新配置"""
    try:
        if config_name == "api":
            API_CONFIG.update(updates)
        elif config_name == "system":
            SYSTEM_CONFIG.update(updates)
        elif config_name == "creative":
            CREATIVE_CONFIG.update(updates)
        else:
            return False
        return True
    except Exception:
        return False

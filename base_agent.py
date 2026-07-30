"""
基础智能体类，提供通用的LLM调用功能
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from openai import OpenAI
import json
import config
from core.api_rate_limiter import api_call_with_rate_limit
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.type_safety import log_type_mismatch
from utils.json_fixer import JsonFixer
from utils.logger import get_logger

logger = get_logger("base_agent")


class BaseAgent(ABC):
    """基础智能体抽象类"""
    
    def __init__(self, name: str):
        self.name = name
        self.client = OpenAI(
            api_key=config.API_KEY,
            base_url=config.BASE_URL
        )
        self.model = config.MODEL_NAME
        self.temperature = config.TEMPERATURE
    
    def call_llm(self, messages: List[Dict[str, str]], temperature: Optional[float] = None, max_tokens: Optional[int] = None, max_retries: int = 3) -> str:
        """调用大语言模型"""
        for attempt in range(max_retries):
            try:
                if max_tokens is None:
                    max_tokens = config.MAX_TOKENS  # 使用配置文件中的值

                # 使用速率限制器调用API
                response = api_call_with_rate_limit(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=messages,
                    temperature=temperature or self.temperature,
                    max_tokens=max_tokens
                )

                # [BUG FIX] 检查finish_reason，判断是否被截断
                finish_reason = response.choices[0].finish_reason if hasattr(response.choices[0], 'finish_reason') else None
                if finish_reason == "length":
                    self.log(f"⚠️ [WARN] LLM输出被max_tokens截断，可能内容不完整 (max_tokens={max_tokens})")

                # [Issue #2] 缓存命中诊断：DeepSeek=prompt_cache_hit_tokens / OpenAI=prompt_tokens_details.cached_tokens
                try:
                    usage = getattr(response, 'usage', None)
                    if usage:
                        prompt_tokens = getattr(usage, 'prompt_tokens', 0) or 0
                        cache_hit = getattr(usage, 'prompt_cache_hit_tokens', None)
                        if cache_hit is None:
                            details = getattr(usage, 'prompt_tokens_details', None)
                            if details:
                                cache_hit = getattr(details, 'cached_tokens', None)
                        cache_hit = cache_hit or 0
                        if prompt_tokens > 0:
                            hit_rate = cache_hit / prompt_tokens * 100
                            self.log(f"[cache] prompt={prompt_tokens} cache_hit={cache_hit} ({hit_rate:.1f}%) provider={getattr(config, 'PROVIDER', '?')}")
                except Exception:
                    pass

                return response.choices[0].message.content
            except Exception as e:
                error_msg = f"LLM调用失败 (尝试 {attempt + 1}/{max_retries}): {e}"
                self.log(error_msg)
                
                if attempt == max_retries - 1:
                    # 最后一次尝试失败，返回错误信息
                    return f"LLM调用失败: {str(e)}"
                
                # 等待一段时间后重试
                import time
                time.sleep(2 ** attempt)  # 指数退避
        
        return "LLM调用失败: 超过最大重试次数"
    
    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """解析JSON响应，确保返回结构化数据"""
        return JsonFixer.parse_json_response(response, verbose=False)
    
    def _fix_json_format(self, json_str: str) -> str:
        """修复常见的JSON格式问题 - 使用统一的JsonFixer"""
        return JsonFixer.fix_json_format(json_str, verbose=False)
    
    def _fix_missing_delimiters_simple(self, json_str: str) -> str:
        """简单的缺失定界符修复 - 使用统一的JsonFixer"""
        return JsonFixer._fix_missing_delimiters_simple(json_str)
    
    
    def _smart_fix_json_by_error(self, json_str: str, error: json.JSONDecodeError) -> str:
        """根据JSON解析错误信息智能修复 - 使用统一的JsonFixer"""
        return JsonFixer._smart_fix_json_by_error(json_str, error, verbose=False)
    
    def _escape_control_char(self, char: str) -> str:
        """将控制字符转义为JSON可接受的格式 - 使用统一的JsonFixer"""
        return JsonFixer._escape_control_char(char)
    
    def _fix_control_chars_in_strings(self, json_str: str) -> str:
        """只在字符串值内转义控制字符，不影响JSON结构 - 使用统一的JsonFixer"""
        return JsonFixer._fix_control_chars_in_strings(json_str)
    
    def _escape_inner_quotes_in_strings(self, json_str: str) -> str:
        """使用状态机转义JSON字符串内部的未转义双引号 - 使用统一的JsonFixer"""
        return JsonFixer._escape_inner_quotes_in_strings(json_str)
    
    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理输入数据，返回处理结果"""
        pass
    
    def log(self, message: str):
        """记录日志"""
        logger.info(f"[{self.name}] {message}")
    
    def validate_input(self, input_data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
        """验证输入数据"""
        missing_fields = []
        for field in required_fields:
            if field not in input_data or not input_data[field]:
                missing_fields.append(field)
        
        if missing_fields:
            return {
                "is_valid": False,
                "error": f"缺少必要字段: {', '.join(missing_fields)}"
            }
        
        return {"is_valid": True}
    
    def handle_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """统一错误处理"""
        error_msg = f"{context}: {str(error)}" if context else str(error)
        self.log(f"错误: {error_msg}")
        
        return {
            "error": error_msg,
            "error_type": type(error).__name__,
            "context": context
        }

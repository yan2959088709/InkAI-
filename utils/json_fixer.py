"""
JSON修复工具类
提供统一的JSON格式修复功能，供BaseAgent和DataManager使用
"""
import json
import re
from typing import Optional
from utils.logger import get_logger
logger = get_logger("json_fixer")


class JsonFixer:
    """JSON修复工具类"""
    
    @staticmethod
    def fix_json_format(json_str: str, verbose: bool = False) -> str:
        """修复常见的JSON格式问题"""
        
        # 第一步：去除首尾空白字符
        json_str = json_str.strip()
        if verbose:
            logger.info(f"[JSON修复] 已去除首尾空白字符")
        
        # 定义修复模式（按优先级顺序）
        fix_patterns = [
            # 1. 替换中文引号
            (lambda s: s.replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'").replace('\u2019', "'"), 
             "替换中文引号"),
            
            # 2. 处理字符串值中的控制字符
            (JsonFixer._fix_control_chars_in_strings, "修复字符串值中的控制字符"),
            
            # 3. 移除对象和数组末尾的多余逗号
            (lambda s: re.sub(r',(\s*[}\]])', r'\1', s), "移除多余逗号"),
            
            # 4. 转义字符串内部的未转义引号
            (JsonFixer._escape_inner_quotes_in_strings, "转义字符串内部的未转义引号"),
            
            # 5. 修复数组中的未转义引号
            (lambda s: re.sub(r'(\[\s*")(.*?)("(?=\s*[,\]]))', 
                             lambda m: m.group(1) + m.group(2).replace('"', '\\"') + m.group(3), s), 
             "修复数组中的未转义引号"),
            
            # 6. 修复缺失的定界符
            (JsonFixer._fix_missing_delimiters_simple, "修复缺失的定界符"),
        ]
        
        # 逐层尝试修复
        for fix_func, fix_name in fix_patterns:
            old_str = json_str
            json_str = fix_func(json_str)
            if verbose and old_str != json_str:
                logger.info(f"[JSON修复] {fix_name} 已应用")
            
            # 尝试解析，看当前修复是否已解决问题
            try:
                json.loads(json_str)
                if verbose:
                    logger.info(f"[JSON修复] {fix_name} 修复成功，JSON有效!")
                return json_str
            except json.JSONDecodeError:
                pass  # 继续下一个修复
        
        # 所有常规修复都失败后，尝试智能修复
        try:
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError as e:
            if verbose:
                logger.info(f"[JSON修复] 尝试智能修复最后的结构问题")
            json_str = JsonFixer._smart_fix_json_by_error(json_str, e, verbose)
            
            try:
                json.loads(json_str)
                if verbose:
                    logger.info("[JSON修复] 智能修复成功，JSON有效!")
                return json_str
            except json.JSONDecodeError:
                if verbose:
                    logger.info("[JSON修复] 智能修复未能产生有效JSON")
        
        return json_str
    
    @staticmethod
    def _fix_missing_delimiters_simple(json_str: str) -> str:
        """简单的缺失定界符修复"""
        stripped = json_str.rstrip()
        if stripped.endswith((',', ':')):
            json_str = stripped.rstrip(',').rstrip(':') + '}'
        return json_str
    
    @staticmethod
    def _smart_fix_json_by_error(json_str: str, error: json.JSONDecodeError, verbose: bool = False) -> str:
        """根据JSON解析错误信息智能修复"""
        error_msg = str(error)
        
        # 获取错误位置
        error_pos = getattr(error, 'pos', None)
        
        # 通用delimiter修复
        delimiter_pattern = r"Expecting '(.+?)' delimiter"
        delimiter_match = re.search(delimiter_pattern, error_msg)
        if delimiter_match:
            missing_char = delimiter_match.group(1)
            
            if error_pos is not None and error_pos <= len(json_str):
                if verbose:
                    logger.error(f"[JSON修复] 在位置 {error_pos} 插入缺失的 '{missing_char}'")
                return json_str[:error_pos] + missing_char + json_str[error_pos:]
        
        # 处理特殊情况
        special_fixes = {
            "Unterminated string": '"',
        }
        
        for pattern, fix_char in special_fixes.items():
            if pattern in error_msg and error_pos is not None and error_pos <= len(json_str):
                if verbose:
                    logger.info(f"[JSON修复] 特殊修复: {pattern}")
                return json_str[:error_pos] + fix_char + json_str[error_pos:]
        
        # 控制字符处理
        if "Invalid control character" in error_msg and error_pos is not None and error_pos < len(json_str):
            char_to_escape = json_str[error_pos]
            escaped_char = JsonFixer._escape_control_char(char_to_escape)
            if escaped_char:
                if verbose:
                    logger.info(f"[JSON修复] 转义控制字符 {repr(char_to_escape)} -> {escaped_char}")
                return json_str[:error_pos] + escaped_char + json_str[error_pos + 1:]
        
        return json_str
    
    @staticmethod
    def _escape_control_char(char: str) -> Optional[str]:
        """将控制字符转义为JSON可接受的格式"""
        escape_map = {
            '\n': '\\n',
            '\r': '\\r',
            '\t': '\\t',
            '\b': '\\b',
            '\f': '\\f',
        }
        return escape_map.get(char, None)
    
    @staticmethod
    def _fix_control_chars_in_strings(json_str: str) -> str:
        """只在字符串值内转义控制字符，不影响JSON结构"""
        
        def fix_string_content(match):
            quote_start = match.group(1)
            content = match.group(2)
            quote_end = match.group(3)
            
            # 只转义字符串内容中的控制字符
            fixed_content = (content.replace('\n', '\\n')
                                   .replace('\r', '\\r')
                                   .replace('\t', '\\t')
                                   .replace('\b', '\\b')
                                   .replace('\f', '\\f'))
            
            return quote_start + fixed_content + quote_end
        
        # 匹配键值对中的字符串值
        json_str = re.sub(r'("[^"]*"\s*:\s*")(.*?)(")', fix_string_content, json_str, flags=re.DOTALL)
        
        # 匹配数组中的字符串值
        json_str = re.sub(r'(\[\s*")(.*?)(")', fix_string_content, json_str, flags=re.DOTALL)
        
        return json_str
    
    @staticmethod
    def _escape_inner_quotes_in_strings(json_str: str) -> str:
        """使用状态机转义JSON字符串内部的未转义双引号"""
        result = []
        in_string = False
        escape_next = False
        
        for i, char in enumerate(json_str):
            if escape_next:
                result.append(char)
                escape_next = False
                continue
            
            if char == '\\':
                result.append(char)
                escape_next = True
                continue
            
            if char == '"':
                if not in_string:
                    in_string = True
                    result.append(char)
                else:
                    # 检查下一个字符，判断这个引号是否是字符串的结束
                    next_chars = json_str[i+1:].lstrip()
                    if next_chars and next_chars[0] in [':', ',', '}', ']']:
                        in_string = False
                        result.append(char)
                    else:
                        # 字符串内部的引号，需要转义
                        result.append('\\"')
            else:
                result.append(char)
        
        return ''.join(result)
    
    @staticmethod
    def parse_json_response(response: str, verbose: bool = False) -> dict:
        """解析JSON响应，确保返回结构化数据"""
        try:
            # 尝试直接解析
            result = json.loads(response)
            if not isinstance(result, dict):
                return {"parse_error": True, "content": response, "error": "结果不是字典类型"}
            return result
        except json.JSONDecodeError:
            pass
        
        # 尝试处理markdown格式的JSON
        try:
            if '```json' in response:
                start_marker = '```json'
                end_marker = '```'
                start = response.find(start_marker)
                if start != -1:
                    start += len(start_marker)
                    end = response.find(end_marker, start)
                    if end != -1:
                        json_str = response[start:end].strip()
                        json_str = JsonFixer.fix_json_format(json_str, verbose)
                        result = json.loads(json_str)
                        if not isinstance(result, dict):
                            return {"parse_error": True, "content": response, "error": "结果不是字典类型"}
                        return result
        except json.JSONDecodeError:
            pass
        
        # 尝试提取JSON部分
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = response[start:end]
                json_str = JsonFixer.fix_json_format(json_str, verbose)
                result = json.loads(json_str)
                if not isinstance(result, dict):
                    return {"parse_error": True, "content": response, "error": "结果不是字典类型"}
                return result
        except json.JSONDecodeError:
            pass
        
        # 如果响应看起来像markdown，尝试提取文本部分
        if '```' in response:
            lines = response.split('\n')
            text_content = []
            in_code_block = False
            for line in lines:
                if line.strip().startswith('```'):
                    in_code_block = not in_code_block
                    continue
                if not in_code_block and line.strip():
                    text_content.append(line)
            
            if text_content:
                return {"content": '\n'.join(text_content)}
        
        # 最后尝试，返回原始文本但添加错误标记
        return {"content": response, "parse_error": True}

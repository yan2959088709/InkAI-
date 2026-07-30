"""
类型安全工具模块
提供统一的类型检查、转换和验证功能
"""

from typing import Dict, List, Any, Union, Optional, Type
import logging

logger = logging.getLogger(__name__)


class TypeSafetyError(Exception):
    """类型安全相关错误"""
    pass


def safe_list_extend(target_list: Any, source_list: Any, field_name: str = "field") -> List[Any]:
    """
    安全地扩展列表，处理类型不匹配的情况
    
    Args:
        target_list: 目标列表（可能不是列表）
        source_list: 源列表（可能不是列表）
        field_name: 字段名称（用于错误日志）
    
    Returns:
        List[Any]: 扩展后的列表
    """
    try:
        # 确保target_list是列表
        if not isinstance(target_list, list):
            if isinstance(target_list, dict):
                # 如果是字典，转换为列表
                target_list = [target_list]
                logger.warning(f"{field_name}是字典类型，已转换为列表")
            elif isinstance(target_list, str):
                # 如果是字符串，转换为列表
                target_list = [target_list]
                logger.warning(f"{field_name}是字符串类型，已转换为列表")
            else:
                # 其他类型，创建空列表
                target_list = []
                logger.warning(f"{field_name}类型为{type(target_list)}，已重置为空列表")
        
        # 确保source_list是列表
        if not isinstance(source_list, list):
            if isinstance(source_list, dict):
                # 如果是字典，提取值
                source_list = list(source_list.values())
                logger.warning(f"{field_name}的源数据是字典类型，已提取值")
            elif isinstance(source_list, str):
                # 如果是字符串，转换为列表
                source_list = [source_list]
                logger.warning(f"{field_name}的源数据是字符串类型，已转换为列表")
            else:
                # 其他类型，创建空列表
                source_list = []
                logger.warning(f"{field_name}的源数据类型为{type(source_list)}，已重置为空列表")
        
        # 执行扩展操作
        target_list.extend(source_list)
        return target_list
        
    except Exception as e:
        logger.error(f"扩展{field_name}时出错: {e}")
        # 返回安全的默认值
        return list(source_list) if isinstance(source_list, list) else []


def safe_list_append(target_list: Any, item: Any, field_name: str = "field") -> List[Any]:
    """
    安全地向列表添加元素
    
    Args:
        target_list: 目标列表（可能不是列表）
        item: 要添加的元素
        field_name: 字段名称（用于错误日志）
    
    Returns:
        List[Any]: 添加元素后的列表
    """
    try:
        # 确保target_list是列表
        if not isinstance(target_list, list):
            if isinstance(target_list, dict):
                # 如果是字典，转换为列表
                target_list = [target_list]
                logger.warning(f"{field_name}是字典类型，已转换为列表")
            elif isinstance(target_list, str):
                # 如果是字符串，转换为列表
                target_list = [target_list]
                logger.warning(f"{field_name}是字符串类型，已转换为列表")
            else:
                # 其他类型，创建空列表
                target_list = []
                logger.warning(f"{field_name}类型为{type(target_list)}，已重置为空列表")
        
        # 添加元素
        target_list.append(item)
        return target_list
        
    except Exception as e:
        logger.error(f"向{field_name}添加元素时出错: {e}")
        # 返回安全的默认值
        return [item] if item is not None else []


def safe_dict_update(target_dict: Any, source_dict: Any, field_name: str = "field") -> Dict[str, Any]:
    """
    安全地更新字典
    
    Args:
        target_dict: 目标字典（可能不是字典）
        source_dict: 源字典（可能不是字典）
        field_name: 字段名称（用于错误日志）
    
    Returns:
        Dict[str, Any]: 更新后的字典
    """
    try:
        # 确保target_dict是字典
        if not isinstance(target_dict, dict):
            if isinstance(target_dict, list):
                # 如果是列表，转换为字典
                target_dict = {"data": target_dict}
                logger.warning(f"{field_name}是列表类型，已转换为字典")
            elif isinstance(target_dict, str):
                # 如果是字符串，转换为字典
                target_dict = {"value": target_dict}
                logger.warning(f"{field_name}是字符串类型，已转换为字典")
            else:
                # 其他类型，创建空字典
                target_dict = {}
                logger.warning(f"{field_name}类型为{type(target_dict)}，已重置为空字典")
        
        # 确保source_dict是字典
        if not isinstance(source_dict, dict):
            logger.warning(f"{field_name}的源数据类型为{type(source_dict)}，跳过更新")
            return target_dict
        
        # 执行更新操作
        target_dict.update(source_dict)
        return target_dict
        
    except Exception as e:
        logger.error(f"更新{field_name}时出错: {e}")
        # 返回安全的默认值
        return target_dict if isinstance(target_dict, dict) else {}


def ensure_field_type(data: Dict[str, Any], field_name: str, expected_type: Type, default_value: Any = None) -> Any:
    """
    确保字段具有正确的类型
    
    Args:
        data: 数据字典
        field_name: 字段名称
        expected_type: 期望的类型
        default_value: 默认值
    
    Returns:
        Any: 类型正确的字段值
    """
    try:
        field_value = data.get(field_name, default_value)
        
        # 如果字段不存在，使用默认值
        if field_value is None:
            data[field_name] = default_value
            return default_value
        
        # 如果类型已经正确，直接返回
        if isinstance(field_value, expected_type):
            return field_value
        
        # 类型转换
        if expected_type == list:
            if isinstance(field_value, dict):
                # 字典转列表（提取值）
                converted = list(field_value.values())
            elif isinstance(field_value, str):
                # 字符串转列表
                converted = [field_value]
            else:
                # 其他类型转列表
                converted = [field_value] if field_value is not None else []
            
            data[field_name] = converted
            logger.warning(f"{field_name}类型从{type(field_value)}转换为列表")
            return converted
            
        elif expected_type == dict:
            if isinstance(field_value, list):
                # 列表转字典（使用索引作为键）
                converted = {str(i): item for i, item in enumerate(field_value)}
            elif isinstance(field_value, str):
                # 字符串转字典
                converted = {"value": field_value}
            else:
                # 其他类型转字典
                converted = {"data": field_value} if field_value is not None else {}
            
            data[field_name] = converted
            logger.warning(f"{field_name}类型从{type(field_value)}转换为字典")
            return converted
            
        elif expected_type == str:
            converted = str(field_value)
            data[field_name] = converted
            logger.warning(f"{field_name}类型从{type(field_value)}转换为字符串")
            return converted
            
        else:
            # 其他类型，尝试直接转换
            converted = expected_type(field_value)
            data[field_name] = converted
            logger.warning(f"{field_name}类型从{type(field_value)}转换为{expected_type}")
            return converted
            
    except Exception as e:
        logger.error(f"转换{field_name}类型时出错: {e}")
        # 使用默认值
        data[field_name] = default_value
        return default_value


def validate_character_structure(character: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证和修复角色数据结构
    
    Args:
        character: 角色数据
    
    Returns:
        Dict[str, Any]: 修复后的角色数据
    """
    if not isinstance(character, dict):
        logger.error("角色数据不是字典类型")
        return {}
    
    # 确保必要字段存在且类型正确，但保留原始数据
    # 只有当字段完全不存在时才使用默认值
    if "basic_info" not in character:
        character["basic_info"] = {}
    elif not isinstance(character["basic_info"], dict):
        logger.warning("basic_info不是字典类型，保留原始数据")
    
    if "personality" not in character:
        character["personality"] = {}
    elif not isinstance(character["personality"], dict):
        logger.warning("personality不是字典类型，保留原始数据")
    
    if "appearance" not in character:
        character["appearance"] = {}
    elif not isinstance(character["appearance"], dict):
        logger.warning("appearance不是字典类型，保留原始数据")
    
    if "background" not in character:
        character["background"] = {}
    elif not isinstance(character["background"], dict):
        logger.warning("background不是字典类型，保留原始数据")
    
    if "skills" not in character:
        character["skills"] = []
    elif not isinstance(character["skills"], list):
        logger.warning("skills不是列表类型，保留原始数据")
    
    if "relationships" not in character:
        character["relationships"] = {}
    elif not isinstance(character["relationships"], dict):
        logger.warning("relationships不是字典类型，保留原始数据")
    
    return character


def validate_storyline_structure(storyline: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证和修复故事线数据结构
    
    Args:
        storyline: 故事线数据
    
    Returns:
        Dict[str, Any]: 修复后的故事线数据
    """
    if not isinstance(storyline, dict):
        logger.error("故事线数据不是字典类型")
        return {}
    
    # 确保必要字段存在且类型正确
    storyline = ensure_field_type(storyline, "plot_points", list, [])
    storyline = ensure_field_type(storyline, "character_interactions", list, [])
    storyline = ensure_field_type(storyline, "key_events", list, [])
    storyline = ensure_field_type(storyline, "conflicts", list, [])
    storyline = ensure_field_type(storyline, "foreshadowing", list, [])
    
    return storyline


def safe_join_list(items: Any, separator: str = ", ", field_name: str = "field") -> str:
    """
    安全地连接列表元素
    
    Args:
        items: 要连接的元素（可能是各种类型）
        separator: 分隔符
        field_name: 字段名称（用于错误日志）
    
    Returns:
        str: 连接后的字符串
    """
    try:
        if not isinstance(items, (list, tuple)):
            if isinstance(items, dict):
                # 如果是字典，连接值
                items = list(items.values())
            elif isinstance(items, str):
                # 如果是字符串，直接返回
                return items
            else:
                # 其他类型，转换为字符串
                return str(items)
        
        # 过滤None值并转换为字符串
        filtered_items = [str(item) for item in items if item is not None]
        return separator.join(filtered_items)
        
    except Exception as e:
        logger.error(f"连接{field_name}时出错: {e}")
        return str(items) if items is not None else ""


def safe_int(value: Any, default: int = 0, min_val: Optional[int] = None, max_val: Optional[int] = None) -> int:
    """
    安全地转换为整数
    
    Args:
        value: 要转换的值
        default: 默认值
        min_val: 最小值
        max_val: 最大值
    
    Returns:
        int: 转换后的整数
    """
    try:
        if value is None:
            return default
        
        if isinstance(value, (int, float)):
            result = int(value)
        elif isinstance(value, str):
            # 尝试提取数字
            import re
            numbers = re.findall(r'-?\d+', value)
            if numbers:
                result = int(numbers[0])
            else:
                return default
        else:
            return default
        
        # 应用范围限制
        if min_val is not None:
            result = max(min_val, result)
        if max_val is not None:
            result = min(max_val, result)
        
        return result
        
    except Exception as e:
        logger.error(f"转换整数时出错: {e}")
        return default


def log_type_mismatch(field_name: str, expected_type: Type, actual_type: Type, value: Any = None):
    """
    记录类型不匹配的详细信息
    
    Args:
        field_name: 字段名称
        expected_type: 期望类型
        actual_type: 实际类型
        value: 字段值（可选）
    """
    logger.warning(
        f"类型不匹配 - 字段: {field_name}, "
        f"期望: {expected_type.__name__}, "
        f"实际: {actual_type.__name__}"
    )
    if value is not None:
        logger.debug(f"字段值: {value}")


def create_safe_defaults(agent_type: str) -> Dict[str, Any]:
    """
    为不同智能体类型创建安全的默认数据结构
    
    Args:
        agent_type: 智能体类型
    
    Returns:
        Dict[str, Any]: 默认数据结构
    """
    defaults = {
        "character_creator": {
            "main_character": {
                "basic_info": {},
                "personality": {},
                "appearance": {},
                "background": {},
                "skills": [],
                "relationships": {}
            },
            "supporting_characters": [],
            "character_relationships": {}
        },
        "storyline_generator": {
            "plot_points": [],
            "character_interactions": [],
            "key_events": [],
            "conflicts": [],
            "foreshadowing": []
        },
        "chapter_writer": {
            "chapter_content": "",
            "chapter_title": "",
            "key_events": [],
            "character_development": {}
        }
    }
    
    return defaults.get(agent_type, {})

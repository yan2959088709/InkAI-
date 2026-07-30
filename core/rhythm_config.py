"""
节奏规则配置化
支持不同类型小说的节奏配置

解决专家提出的问题：
- 避免"一套规则适配所有类型"的僵化问题
- 让节奏控制更灵活
"""

from typing import Dict, Any
from utils.logger import get_logger

logger = get_logger("rhythm_config")


class RhythmConfig:
    """节奏配置管理器"""
    
    # 不同类型小说的节奏配置
    NOVEL_TYPE_CONFIGS = {
        "爽文": {
            "name": "爽文",
            "cycle_chapters": 2,  # 2章循环
            "volume_chapters": 50,  # 每卷50章
            "double_line_link": 2,  # 每2章双线交汇
            "conflict_intensity": "high",  # 高强度冲突
            "cliffhanger_required": True,  # 必须有钩子
            "pacing": "fast"  # 快节奏
        },
        "悬疑": {
            "name": "悬疑",
            "cycle_chapters": 4,  # 4章循环
            "volume_chapters": 30,  # 每卷30章
            "double_line_link": 4,  # 每4章双线交汇
            "conflict_intensity": "medium",  # 中等强度
            "cliffhanger_required": True,  # 必须有钩子
            "pacing": "slow"  # 慢节奏铺垫
        },
        "都市": {
            "name": "都市",
            "cycle_chapters": 3,  # 3章循环
            "volume_chapters": 40,  # 每卷40章
            "double_line_link": 3,  # 每3章双线交汇
            "conflict_intensity": "medium",  # 中等强度
            "cliffhanger_required": True,
            "pacing": "medium"  # 中等节奏
        },
        "言情": {
            "name": "言情",
            "cycle_chapters": 2,  # 2章循环
            "volume_chapters": 35,  # 每卷35章
            "double_line_link": 2,
            "conflict_intensity": "low",  # 低强度（情感冲突为主）
            "cliffhanger_required": False,  # 可以没有钩子
            "pacing": "slow"  # 慢节奏
        },
        "玄幻": {
            "name": "玄幻",
            "cycle_chapters": 2,  # 2章循环
            "volume_chapters": 60,  # 每卷60章
            "double_line_link": 2,
            "conflict_intensity": "high",  # 高强度
            "cliffhanger_required": True,
            "pacing": "fast"  # 快节奏
        },
        "历史": {
            "name": "历史",
            "cycle_chapters": 4,  # 4章循环
            "volume_chapters": 40,
            "double_line_link": 4,
            "conflict_intensity": "medium",
            "cliffhanger_required": False,
            "pacing": "slow"  # 慢节奏
        }
    }
    
    # 节奏循环定义（可配置）
    RHYTHM_CYCLES = {
        2: {  # 2章循环
            1: {"name": "缓冲章", "focus": "情感/铺垫"},
            2: {"name": "高潮章", "focus": "推进/爽点"}
        },
        3: {  # 3章循环
            1: {"name": "缓冲铺垫章", "focus": "人物/伏笔"},
            2: {"name": "升级转折章", "focus": "矛盾升级"},
            3: {"name": "强推进章", "focus": "主线推进"}
        },
        4: {  # 4章循环
            1: {"name": "铺垫章", "focus": "氛围/伏笔"},
            2: {"name": "发展章", "focus": "情节发展"},
            3: {"name": "冲突章", "focus": "矛盾激化"},
            4: {"name": "高潮章", "focus": "高潮/收束"}
        }
    }
    
    def __init__(self, novel_type: str = "都市"):
        self.novel_type = novel_type
        self.config = self._load_config(novel_type)
    
    def _load_config(self, novel_type: str) -> Dict[str, Any]:
        """加载配置"""
        if novel_type in self.NOVEL_TYPE_CONFIGS:
            return self.NOVEL_TYPE_CONFIGS[novel_type].copy()
        else:
            logger.warning(f"未知小说类型: {novel_type}，使用默认配置")
            return self.NOVEL_TYPE_CONFIGS["都市"].copy()
    
    def get_rhythm_for_chapter(self, chapter_number: int) -> Dict[str, Any]:
        """获取章节的节奏配置"""
        cycle_chapters = self.config["cycle_chapters"]
        
        # 计算循环位置
        cycle_position = ((chapter_number - 1) % cycle_chapters) + 1
        
        # 获取循环定义
        cycle_def = self.RHYTHM_CYCLES.get(cycle_chapters, self.RHYTHM_CYCLES[3])
        rhythm = cycle_def.get(cycle_position, cycle_def[1]).copy()
        
        # 添加配置信息
        rhythm["chapter_number"] = chapter_number
        rhythm["cycle_position"] = cycle_position
        rhythm["cycle_total"] = cycle_chapters
        rhythm["pacing"] = self.config["pacing"]
        rhythm["conflict_intensity"] = self.config["conflict_intensity"]
        
        return rhythm
    
    def should_link_double_lines(self, chapter_number: int) -> bool:
        """检查是否应该双线交汇"""
        link_interval = self.config["double_line_link"]
        
        # 修改：改为"检查交汇点"而非"强制交汇"
        # 每N章检查一次，有自然交汇点则强化，无则铺垫
        return chapter_number % link_interval == 0
    
    def get_link_strength(self, chapter_number: int, total_chapters: int) -> str:
        """获取咬合强度（根据剧情阶段）"""
        ratio = chapter_number / total_chapters
        
        if ratio <= 0.25:
            return "weak"  # 开端：弱咬合
        elif ratio <= 0.75:
            return "medium"  # 中段：中咬合
        else:
            return "strong"  # 结尾：强咬合
    
    def get_volume_chapters(self) -> int:
        """获取每卷章节数"""
        return self.config["volume_chapters"]
    
    def get_config_summary(self) -> str:
        """获取配置摘要"""
        return f"""
【小说类型】：{self.config['name']}
【节奏循环】：{self.config['cycle_chapters']}章循环
【每卷章数】：{self.config['volume_chapters']}章
【双线交汇】：每{self.config['double_line_link']}章检查
【冲突强度】：{self.config['conflict_intensity']}
【节奏速度】：{self.config['pacing']}
"""
    
    @classmethod
    def get_available_types(cls) -> list:
        """获取可用的小说类型"""
        return list(cls.NOVEL_TYPE_CONFIGS.keys())
    
    @classmethod
    def create_custom_config(cls, name: str, **kwargs) -> Dict[str, Any]:
        """创建自定义配置"""
        default = cls.NOVEL_TYPE_CONFIGS["都市"].copy()
        default.update(kwargs)
        default["name"] = name
        return default


def get_rhythm_config(novel_type: str = "都市") -> RhythmConfig:
    """获取节奏配置的便捷函数"""
    return RhythmConfig(novel_type)

"""
小说篇幅规划器
支持短篇、中篇、长篇、超长篇的规划

功能：
1. 篇幅类型选择
2. 软性分卷规划
3. 超卷处理策略
4. 明暗线规划
"""

from typing import Dict, List, Any, Tuple
from utils.logger import get_logger

logger = get_logger("novel_planner")


class NovelPlanner:
    """小说规划器"""
    
    # 篇幅类型配置
    LENGTH_CONFIGS = {
        "短篇": {
            "name": "短篇小说",
            "chapters_range": (1, 15),
            "volumes": 1,
            "chapters_per_volume": 15,
            "focus": "单点爆破",
            "description": "完整小故事，节奏紧凑"
        },
        "中篇": {
            "name": "中篇小说",
            "chapters_range": (16, 100),
            "volumes_range": (2, 3),
            "chapters_per_volume": 40,
            "focus": "完整闭环",
            "description": "完整故事线，有始有终"
        },
        "长篇": {
            "name": "长篇小说",
            "chapters_range": (101, 400),
            "volumes_range": (3, 10),
            "chapters_per_volume": 40,
            "focus": "长线结构",
            "description": "多卷结构，长线推进"
        },
        "超长篇": {
            "name": "超长篇小说",
            "chapters_range": (401, 1000),
            "volumes_range": (10, 25),
            "chapters_per_volume": 40,
            "focus": "千章连载",
            "description": "超长连载，系统主打"
        }
    }
    
    # 超卷处理策略
    OVERFLOW_STRATEGIES = {
        "accelerate": {
            "name": "加速节奏",
            "actions": [
                "减少缓冲章节比例",
                "增加强推进章节",
                "压缩过渡内容"
            ]
        },
        "merge_dark_lines": {
            "name": "合并暗线",
            "actions": [
                "提前引入下一卷暗线",
                "增加暗线交汇频率"
            ]
        },
        "add_conflict": {
            "name": "引入新冲突",
            "actions": [
                "升级反派威胁",
                "增加支线危机"
            ]
        }
    }
    
    def __init__(self):
        pass
    
    def get_length_config(self, novel_type: str) -> Dict[str, Any]:
        """获取篇幅配置"""
        return self.LENGTH_CONFIGS.get(novel_type, self.LENGTH_CONFIGS["超长篇"])
    
    def plan_novel(self, novel_type: str, estimated_chapters: int = None) -> Dict[str, Any]:
        """
        规划小说
        
        Args:
            novel_type: 篇幅类型（短篇/中篇/长篇/超长篇）
            estimated_chapters: 预估章节数（可选）
        
        Returns:
            规划结果
        """
        config = self.get_length_config(novel_type)
        
        # 确定预估章节数
        if estimated_chapters is None:
            # 使用范围中位数
            min_ch, max_ch = config["chapters_range"]
            estimated_chapters = (min_ch + max_ch) // 2
        
        # 确保在范围内
        min_ch, max_ch = config["chapters_range"]
        estimated_chapters = max(min_ch, min(max_ch, estimated_chapters))
        
        # 计算分卷
        chapters_per_volume = config["chapters_per_volume"]
        expected_volumes = max(1, estimated_chapters // chapters_per_volume)
        
        # 生成规划
        plan = {
            "novel_type": novel_type,
            "config": config,
            "estimated_chapters": estimated_chapters,
            "chapters_per_volume": chapters_per_volume,
            "expected_volumes": expected_volumes,
            "is_soft_plan": True,  # 软性规划，不卡死
            "overflow_strategy": "accelerate",  # 默认超卷策略
            "volume_plans": self._generate_volume_plans(expected_volumes, chapters_per_volume)
        }
        
        return plan
    
    def _generate_volume_plans(self, num_volumes: int, 
                               chapters_per_volume: int) -> List[Dict]:
        """生成每卷规划"""
        volume_plans = []
        
        for vol in range(1, num_volumes + 1):
            start_chapter = (vol - 1) * chapters_per_volume + 1
            end_chapter = vol * chapters_per_volume
            
            # 确定卷阶段
            if vol <= num_volumes * 0.25:
                phase = "开端"
            elif vol <= num_volumes * 0.75:
                phase = "中段"
            else:
                phase = "结尾"
            
            volume_plans.append({
                "volume_number": vol,
                "chapter_range": (start_chapter, end_chapter),
                "phase": phase,
                "chapters_count": chapters_per_volume
            })
        
        return volume_plans
    
    def plan_dual_storyline(self, novel_type: str, 
                           novel_theme: str = None) -> Dict[str, Any]:
        """
        规划明暗线
        
        Args:
            novel_type: 篇幅类型
            novel_theme: 小说主题（可选）
        
        Returns:
            明暗线规划
        """
        config = self.get_length_config(novel_type)
        expected_volumes = config.get("volumes", config.get("volumes_range", (10, 25))[1])
        
        # 生成暗线规划
        dark_lines = self._generate_dark_lines(expected_volumes, novel_theme)
        
        return {
            "bright_line": {
                "description": "主线剧情（贯穿全书）",
                "consistency": "全程保持"
            },
            "dark_lines": dark_lines,
            "intersection_rules": {
                "frequency": "每卷2-3次",
                "mandatory_at_volume_end": True,
                "binding": "暗线 = 本卷伏笔 + 核心配角动机"
            },
            "overflow_handling": {
                "strategy": "accelerate",
                "actions": [
                    "增加暗线交汇频率",
                    "提前引入下一卷暗线"
                ]
            }
        }
    
    def _generate_dark_lines(self, num_volumes: int, 
                            novel_theme: str = None) -> List[Dict]:
        """生成每卷暗线"""
        dark_lines = []
        
        # 根据主题生成暗线
        if novel_theme and "异能" in novel_theme:
            themes = [
                "身世之谜初现",
                "异能来源揭秘",
                "组织阴谋浮出",
                "终极敌人现身",
                "真相大白"
            ]
        elif novel_theme and "悬疑" in novel_theme:
            themes = [
                "案件背后秘密",
                "真凶身份线索",
                "深层阴谋揭露",
                "最终对决",
                "真相闭环"
            ]
        else:
            # 默认暗线主题
            themes = [
                "身世之谜",
                "核心秘密",
                "阴谋浮出",
                "终极对决",
                "真相大白"
            ]
        
        # 为每卷生成暗线
        for vol in range(1, num_volumes + 1):
            # 循环使用主题
            theme_idx = (vol - 1) % len(themes)
            
            dark_lines.append({
                "volume_number": vol,
                "theme": themes[theme_idx],
                "trigger_count": 2 if vol % 2 == 0 else 3,  # 交替2-3次
                "must_intersect_at_end": True,
                "foreshadowing_examples": [
                    f"第{vol}卷伏笔1",
                    f"第{vol}卷伏笔2"
                ]
            })
        
        return dark_lines
    
    def check_overflow(self, current_chapter: int, 
                      expected_total: int) -> Dict[str, Any]:
        """
        检查是否超卷
        
        Args:
            current_chapter: 当前章节号
            expected_total: 预估总章数
        
        Returns:
            超卷检查结果
        """
        overflow_ratio = current_chapter / expected_total if expected_total > 0 else 0
        
        result = {
            "current_chapter": current_chapter,
            "expected_total": expected_total,
            "overflow_ratio": overflow_ratio,
            "is_overflow": overflow_ratio > 1.0,
            "overflow_chapters": max(0, current_chapter - expected_total),
            "recommendation": ""
        }
        
        if overflow_ratio > 1.2:
            result["recommendation"] = "严重超卷，建议加速节奏或结束本卷"
            result["strategy"] = "accelerate"
        elif overflow_ratio > 1.0:
            result["recommendation"] = "轻微超卷，可以适当加速节奏"
            result["strategy"] = "mild_accelerate"
        elif overflow_ratio > 0.9:
            result["recommendation"] = "接近预估，准备本卷收尾"
            result["strategy"] = "prepare_ending"
        else:
            result["recommendation"] = "正常进度"
            result["strategy"] = "normal"
        
        return result
    
    def get_planning_summary(self, plan: Dict[str, Any]) -> str:
        """获取规划摘要"""
        novel_type = plan.get("novel_type", "未知")
        estimated = plan.get("estimated_chapters", 0)
        volumes = plan.get("expected_volumes", 0)
        chapters_per_vol = plan.get("chapters_per_volume", 40)
        
        return f"""
【小说规划】：
- 篇幅类型：{novel_type}
- 预估章数：{estimated}章
- 预估卷数：{volumes}卷
- 每卷章数：{chapters_per_vol}章（软性参考）
- 超卷策略：加速节奏，不跳脱

【明暗线规划】：
- 明线：主线剧情贯穿全书
- 暗线：每卷独立暗线主题
- 触发：每卷提示2-3次
- 交汇：卷末必交汇
"""


def plan_novel(novel_type: str, estimated_chapters: int = None) -> Dict[str, Any]:
    """规划小说的便捷函数"""
    planner = NovelPlanner()
    return planner.plan_novel(novel_type, estimated_chapters)


def plan_dual_storyline(novel_type: str, novel_theme: str = None) -> Dict[str, Any]:
    """规划明暗线的便捷函数"""
    planner = NovelPlanner()
    return planner.plan_dual_storyline(novel_type, novel_theme)

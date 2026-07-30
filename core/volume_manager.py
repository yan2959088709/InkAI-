"""
分卷管理系统
支持上千章小说的分卷管理

1000章 = 25卷 × 40章

每卷：
- 独立的剧情阶段
- 卷级摘要
- 卷间衔接处理
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import os
from utils.logger import get_logger

logger = get_logger("volume_manager")


class VolumeManager:
    """分卷管理器"""
    
    # 默认每卷章节数
    DEFAULT_CHAPTERS_PER_VOLUME = 40
    
    def __init__(self, data_manager=None):
        self.data_manager = data_manager
        
    def get_volume_info(self, novel_id: str, chapter_number: int, 
                       chapters_per_volume: int = None) -> Dict[str, Any]:
        """
        获取章节所在的卷信息
        
        Args:
            novel_id: 小说ID
            chapter_number: 章节号
            chapters_per_volume: 每卷章节数
        
        Returns:
            卷信息
        """
        if chapters_per_volume is None:
            chapters_per_volume = self.DEFAULT_CHAPTERS_PER_VOLUME
        
        # 计算卷号（从1开始）
        volume_number = ((chapter_number - 1) // chapters_per_volume) + 1
        
        # 计算卷内章节号
        chapter_in_volume = ((chapter_number - 1) % chapters_per_volume) + 1
        
        # 计算卷的起始和结束章节
        volume_start = (volume_number - 1) * chapters_per_volume + 1
        volume_end = volume_number * chapters_per_volume
        
        # 计算卷内进度
        volume_progress = chapter_in_volume / chapters_per_volume
        
        # 确定卷内阶段
        volume_phase = self._get_volume_phase(chapter_in_volume, chapters_per_volume)
        
        return {
            "novel_id": novel_id,
            "chapter_number": chapter_number,
            "volume_number": volume_number,
            "chapter_in_volume": chapter_in_volume,
            "chapters_per_volume": chapters_per_volume,
            "volume_start": volume_start,
            "volume_end": volume_end,
            "volume_progress": volume_progress,
            "volume_phase": volume_phase,
            "is_volume_start": chapter_in_volume == 1,
            "is_volume_end": chapter_in_volume == chapters_per_volume,
            "is_volume_middle": chapter_in_volume == chapters_per_volume // 2
        }
    
    def _get_volume_phase(self, chapter_in_volume: int, chapters_per_volume: int) -> str:
        """获取卷内阶段"""
        ratio = chapter_in_volume / chapters_per_volume
        
        if ratio <= 0.25:
            return "volume_beginning"  # 卷开端
        elif ratio <= 0.75:
            return "volume_middle"  # 卷中段
        else:
            return "volume_ending"  # 卷结尾
    
    def get_volume_summary_path(self, novel_id: str, volume_number: int) -> str:
        """获取卷摘要文件路径"""
        if self.data_manager:
            base_dir = self.data_manager.novels_dir
        else:
            base_dir = "data/novels"
        
        return os.path.join(base_dir, novel_id, f"volume_{volume_number:03d}_summary.json")
    
    def save_volume_summary(self, novel_id: str, volume_number: int, 
                           summary_data: Dict[str, Any]) -> bool:
        """保存卷摘要"""
        try:
            file_path = self.get_volume_summary_path(novel_id, volume_number)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 添加元数据
            summary_data["novel_id"] = novel_id
            summary_data["volume_number"] = volume_number
            summary_data["updated_at"] = datetime.now().isoformat()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"卷{volume_number}摘要已保存: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存卷摘要失败: {e}")
            return False
    
    def load_volume_summary(self, novel_id: str, volume_number: int) -> Optional[Dict[str, Any]]:
        """加载卷摘要"""
        try:
            file_path = self.get_volume_summary_path(novel_id, volume_number)
            
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            return None
            
        except Exception as e:
            logger.error(f"加载卷摘要失败: {e}")
            return None
    
    def get_all_volume_summaries(self, novel_id: str) -> List[Dict[str, Any]]:
        """获取所有卷摘要"""
        summaries = []
        
        if self.data_manager:
            base_dir = self.data_manager.novels_dir
        else:
            base_dir = "data/novels"
        
        novel_dir = os.path.join(base_dir, novel_id)
        
        if os.path.exists(novel_dir):
            for filename in os.listdir(novel_dir):
                if filename.startswith("volume_") and filename.endswith("_summary.json"):
                    try:
                        with open(os.path.join(novel_dir, filename), 'r', encoding='utf-8') as f:
                            summary = json.load(f)
                            summaries.append(summary)
                    except:
                        pass
        
        # 按卷号排序
        summaries.sort(key=lambda x: x.get("volume_number", 0))
        return summaries
    
    def get_cross_volume_context(self, novel_id: str, current_chapter: int,
                                chapters_per_volume: int = None) -> Dict[str, Any]:
        """
        获取跨卷上下文（用于长篇小说的连贯性）
        
        Args:
            novel_id: 小说ID
            current_chapter: 当前章节号
            chapters_per_volume: 每卷章节数
        
        Returns:
            跨卷上下文信息
        """
        volume_info = self.get_volume_info(novel_id, current_chapter, chapters_per_volume)
        current_volume = volume_info["volume_number"]
        
        context = {
            "current_volume": current_volume,
            "volume_info": volume_info,
            "previous_volume_summary": None,
            "all_volume_summaries": []
        }
        
        # 获取上一卷摘要（如果是新卷开始）
        if volume_info["is_volume_start"] and current_volume > 1:
            prev_summary = self.load_volume_summary(novel_id, current_volume - 1)
            context["previous_volume_summary"] = prev_summary
        
        # 获取所有卷摘要
        context["all_volume_summaries"] = self.get_all_volume_summaries(novel_id)
        
        return context
    
    def get_volume_guidance(self, novel_id: str, chapter_number: int,
                           chapters_per_volume: int = None) -> str:
        """获取分卷写作指导"""
        volume_info = self.get_volume_info(novel_id, chapter_number, chapters_per_volume)
        
        guidance = f"""
【分卷信息】：
- 当前卷：第{volume_info['volume_number']}卷
- 卷内章节：第{volume_info['chapter_in_volume']}章/{volume_info['chapters_per_volume']}章
- 卷进度：{volume_info['volume_progress']*100:.0f}%
- 卷阶段：{self._get_phase_name(volume_info['volume_phase'])}
"""
        
        # 添加卷阶段特定指导
        phase = volume_info['volume_phase']
        if phase == "volume_beginning":
            guidance += """
【卷开端写作要求】：
1. 承接上卷结尾，建立新卷的基调
2. 引入本卷的核心冲突/目标
3. 为本卷的高潮做铺垫
"""
        elif phase == "volume_middle":
            guidance += """
【卷中段写作要求】：
1. 推进本卷的核心冲突
2. 深化人物关系和发展
3. 埋设本卷高潮的伏笔
"""
        elif phase == "volume_ending":
            guidance += """
【卷结尾写作要求】：
1. 收束本卷的核心冲突
2. 完成阶段性目标
3. 为下一卷留下钩子
4. 本卷必须有一个大高潮
"""
        
        # 如果是新卷开始，添加跨卷指导
        if volume_info['is_volume_start'] and volume_info['volume_number'] > 1:
            guidance += """
【跨卷衔接要求】：
1. 简要回顾上卷结尾
2. 建立时间/空间的连续性
3. 引入新的冲突或升级旧冲突
"""
        
        return guidance
    
    def _get_phase_name(self, phase: str) -> str:
        """获取阶段名称"""
        names = {
            "volume_beginning": "卷开端（25%）",
            "volume_middle": "卷中段（50%）",
            "volume_ending": "卷结尾（25%）"
        }
        return names.get(phase, phase)


def get_volume_info(novel_id: str, chapter_number: int, 
                   chapters_per_volume: int = 40) -> Dict[str, Any]:
    """获取卷信息的便捷函数"""
    manager = VolumeManager()
    return manager.get_volume_info(novel_id, chapter_number, chapters_per_volume)


def get_volume_guidance(novel_id: str, chapter_number: int,
                       chapters_per_volume: int = 40) -> str:
    """获取卷指导的便捷函数"""
    manager = VolumeManager()
    return manager.get_volume_guidance(novel_id, chapter_number, chapters_per_volume)

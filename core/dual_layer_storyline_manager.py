"""
双层故事线管理器
实现上层（整本小说）和下层（章节）的故事线管理
"""

import json
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import math
from utils.logger import get_logger
logger = get_logger("dual_layer_storyline_manager")


class NovelStoryline:
    """整本小说故事线 - 宏观控制层"""
    
    def __init__(self, novel_id: str, data_manager=None):
        self.novel_id = novel_id
        self.data_manager = data_manager
        self.file_path = f"data/novels/{novel_id}/novel_storyline.json"
        
        # 故事线结构
        self.storyline_data = {
            "novel_id": novel_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "total_chapters": 100,  # 预估总章节数
            "current_chapter": 0,
            
            # 主要故事弧线
            "major_arcs": [
                {
                    "arc_id": "setup",
                    "name": "设定阶段",
                    "start_chapter": 1,
                    "end_chapter": 10,
                    "description": "世界观设定、角色介绍、初始冲突",
                    "key_events": [],
                    "character_introductions": [],
                    "world_building": []
                },
                {
                    "arc_id": "confrontation",
                    "name": "冲突阶段",
                    "start_chapter": 11,
                    "end_chapter": 30,
                    "description": "主要冲突展开、角色发展",
                    "key_events": [],
                    "character_development": [],
                    "conflict_escalation": []
                },
                {
                    "arc_id": "climax",
                    "name": "高潮阶段",
                    "start_chapter": 31,
                    "end_chapter": 50,
                    "description": "冲突达到顶点、关键转折",
                    "key_events": [],
                    "major_revelations": [],
                    "turning_points": []
                },
                {
                    "arc_id": "resolution",
                    "name": "解决阶段",
                    "start_chapter": 51,
                    "end_chapter": 100,
                    "description": "冲突解决、故事收尾",
                    "key_events": [],
                    "character_resolution": [],
                    "conclusion": []
                }
            ],
            
            # 角色发展轨迹
            "character_development_tracks": {},
            
            # 世界观演变
            "world_evolution": {
                "initial_state": {},
                "major_changes": [],
                "current_state": {}
            },
            
            # 主题推进
            "theme_progression": {
                "main_themes": [],
                "theme_development": [],
                "current_focus": ""
            },
            
            # 伏笔管理
            "foreshadowing_timeline": {},
            
            # 里程碑
            "milestones": []
        }
    
    def load_storyline(self) -> bool:
        """加载故事线数据"""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    self.storyline_data = json.load(f)
                return True
            else:
                self.save_storyline()
                return True
        except Exception as e:
            logger.error(f"加载故事线失败: {e}")
            return False
    
    def save_storyline(self) -> bool:
        """保存故事线数据"""
        try:
            self.storyline_data["updated_at"] = datetime.now().isoformat()
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.storyline_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存故事线失败: {e}")
            return False
    
    def get_current_phase(self, chapter: int) -> Dict[str, Any]:
        """获取当前章节所在的故事阶段"""
        for arc in self.storyline_data["major_arcs"]:
            if arc["start_chapter"] <= chapter <= arc["end_chapter"]:
                return {
                    "phase": arc["arc_id"],
                    "phase_name": arc["name"],
                    "phase_description": arc["description"],
                    "phase_progress": (chapter - arc["start_chapter"] + 1) / (arc["end_chapter"] - arc["start_chapter"] + 1),
                    "remaining_chapters": arc["end_chapter"] - chapter
                }
        
        return {
            "phase": "unknown",
            "phase_name": "未知阶段",
            "phase_description": "故事阶段未定义",
            "phase_progress": 0,
            "remaining_chapters": 0
        }
    
    def get_constraints_for_chapter(self, chapter: int) -> Dict[str, Any]:
        """获取章节约束"""
        current_phase = self.get_current_phase(chapter)
        
        # 获取阶段特定的约束
        phase_constraints = self._get_phase_constraints(current_phase["phase"])
        
        # 获取角色发展约束
        character_constraints = self._get_character_constraints(chapter)
        
        # 获取伏笔约束
        foreshadowing_constraints = self._get_foreshadowing_constraints(chapter)
        
        return {
            "phase": current_phase,
            "phase_constraints": phase_constraints,
            "character_constraints": character_constraints,
            "foreshadowing_constraints": foreshadowing_constraints,
            "chapter_number": chapter,
            "story_progress": chapter / self.storyline_data["total_chapters"]
        }
    
    def _get_phase_constraints(self, phase: str) -> Dict[str, Any]:
        """获取阶段约束"""
        constraints_map = {
            "setup": {
                "required_elements": ["世界观介绍", "主要角色登场", "初始冲突设定"],
                "forbidden_elements": ["过早揭示重大秘密", "角色突然死亡"],
                "tone": "建立和探索",
                "pace": "中等"
            },
            "confrontation": {
                "required_elements": ["冲突升级", "角色发展", "障碍增加"],
                "forbidden_elements": ["轻易解决冲突", "角色停滞不前"],
                "tone": "紧张和冲突",
                "pace": "加快"
            },
            "climax": {
                "required_elements": ["关键转折", "重大揭示", "高潮事件"],
                "forbidden_elements": ["反高潮", "逻辑漏洞"],
                "tone": "激烈和紧张",
                "pace": "快速"
            },
            "resolution": {
                "required_elements": ["冲突解决", "角色归宿", "故事收尾"],
                "forbidden_elements": ["突然结束", "遗留伏笔"],
                "tone": "总结和反思",
                "pace": "放缓"
            }
        }
        
        return constraints_map.get(phase, {})
    
    def _get_character_constraints(self, chapter: int) -> Dict[str, Any]:
        """获取角色发展约束"""
        # 这里需要与角色数据管理器集成
        return {
            "main_character_development": "必须推进主角成长",
            "supporting_characters": "保持配角一致性",
            "new_character_introduction": chapter <= 20,  # 前20章可以引入新角色
            "character_deaths": chapter >= 30  # 30章后可以安排角色死亡
        }
    
    def _get_foreshadowing_constraints(self, chapter: int) -> Dict[str, Any]:
        """获取伏笔约束"""
        return {
            "active_foreshadowing": [],  # 活跃的伏笔
            "should_reveal": [],  # 应该揭示的伏笔
            "can_plant": True,  # 是否可以埋设新伏笔
            "reveal_threshold": chapter >= 20  # 20章后可以开始揭示伏笔
        }
    
    def update_progress(self, chapter: int, chapter_content: Dict[str, Any]) -> bool:
        """更新故事线进度"""
        try:
            current_phase = self.get_current_phase(chapter)
            
            # 更新当前章节
            self.storyline_data["current_chapter"] = chapter
            
            # 更新阶段信息
            if chapter <= self.storyline_data["total_chapters"]:
                phase_data = self._extract_phase_data(chapter_content, current_phase["phase"])
                self._update_phase_data(current_phase["phase"], phase_data)
            
            # 更新角色发展轨迹
            character_development = self._extract_character_development(chapter_content)
            self._update_character_tracks(chapter, character_development)
            
            # 更新伏笔时间线
            foreshadowing_data = self._extract_foreshadowing_data(chapter_content)
            self._update_foreshadowing_timeline(chapter, foreshadowing_data)
            
            # 保存更新
            return self.save_storyline()
            
        except Exception as e:
            logger.error(f"更新故事线进度失败: {e}")
            return False
    
    def _extract_phase_data(self, chapter_content: Dict[str, Any], phase: str) -> Dict[str, Any]:
        """从章节内容中提取阶段数据"""
        content = chapter_content.get("content", "")
        
        phase_data = {
            "key_events": [],
            "character_development": [],
            "world_changes": [],
            "foreshadowing": [],
            "conflict_escalation": []
        }
        
        # 简单的关键词提取（实际应该用更复杂的NLP）
        if "发现" in content or "揭示" in content:
            phase_data["key_events"].append("重要发现")
        
        if "成长" in content or "学会" in content:
            phase_data["character_development"].append("角色成长")
        
        if "变化" in content or "改变" in content:
            phase_data["world_changes"].append("世界变化")
        
        return phase_data
    
    def _update_phase_data(self, phase: str, phase_data: Dict[str, Any]):
        """更新阶段数据"""
        for arc in self.storyline_data["major_arcs"]:
            if arc["arc_id"] == phase:
                for key, value in phase_data.items():
                    if key in arc:
                        if isinstance(arc[key], list):
                            arc[key].extend(value)
                        else:
                            arc[key] = value
                break
    
    def _extract_character_development(self, chapter_content: Dict[str, Any]) -> Dict[str, Any]:
        """提取角色发展信息"""
        # 这里需要与角色分析器集成
        return {}
    
    def _update_character_tracks(self, chapter: int, development: Dict[str, Any]):
        """更新角色发展轨迹"""
        # 实现角色发展轨迹更新逻辑
        pass
    
    def _extract_foreshadowing_data(self, chapter_content: Dict[str, Any]) -> Dict[str, Any]:
        """提取伏笔数据"""
        # 实现伏笔数据提取逻辑
        return {}
    
    def _update_foreshadowing_timeline(self, chapter: int, foreshadowing_data: Dict[str, Any]):
        """更新伏笔时间线"""
        # 实现伏笔时间线更新逻辑
        pass


class ChapterStoryline:
    """章节故事线 - 微观执行层"""
    
    def __init__(self, novel_storyline: NovelStoryline, chapter: int):
        self.novel_storyline = novel_storyline
        self.chapter = chapter
        self.max_deviation = 0.3  # 最大偏差30%
        
        # 章节故事线结构
        self.chapter_data = {
            "chapter_number": chapter,
            "created_at": datetime.now().isoformat(),
            "title": "",
            "plot_points": [],
            "character_interactions": [],
            "key_events": [],
            "foreshadowing": [],
            "conflict_elements": [],
            "resolution_elements": [],
            "next_chapter_hints": [],
            "deviation_score": 0.0,
            "consistency_score": 0.0
        }
    
    def generate_with_constraints(self, upper_constraints: Dict[str, Any]) -> Dict[str, Any]:
        """在约束下生成章节故事线"""
        
        # 1. 分析上层约束
        phase_info = upper_constraints["phase"]
        phase_constraints = upper_constraints["phase_constraints"]
        
        # 2. 生成基础故事线
        base_storyline = self._generate_base_storyline(phase_info, phase_constraints)
        
        # 3. 添加创新元素
        innovative_storyline = self._add_innovation(base_storyline, upper_constraints)
        
        # 4. 验证偏差度
        deviation_score = self._calculate_deviation(innovative_storyline, upper_constraints)
        
        # 5. 如果偏差过大，进行调整
        if deviation_score > self.max_deviation:
            final_storyline = self._adjust_to_constraints(innovative_storyline, upper_constraints)
        else:
            final_storyline = innovative_storyline
        
        # 6. 计算一致性分数
        consistency_score = self._calculate_consistency(final_storyline, upper_constraints)
        
        # 7. 更新章节数据
        self.chapter_data.update({
            "title": final_storyline.get("title", f"第{self.chapter}章"),
            "plot_points": final_storyline.get("plot_points", []),
            "character_interactions": final_storyline.get("character_interactions", []),
            "key_events": final_storyline.get("key_events", []),
            "foreshadowing": final_storyline.get("foreshadowing", []),
            "conflict_elements": final_storyline.get("conflict_elements", []),
            "resolution_elements": final_storyline.get("resolution_elements", []),
            "next_chapter_hints": final_storyline.get("next_chapter_hints", []),
            "deviation_score": deviation_score,
            "consistency_score": consistency_score
        })
        
        return self.chapter_data
    
    def _generate_base_storyline(self, phase_info: Dict[str, Any], phase_constraints: Dict[str, Any]) -> Dict[str, Any]:
        """生成基础故事线"""
        
        phase = phase_info["phase"]
        phase_progress = phase_info["phase_progress"]
        
        # 根据阶段生成不同的故事线结构
        if phase == "setup":
            return self._generate_setup_storyline(phase_progress)
        elif phase == "confrontation":
            return self._generate_confrontation_storyline(phase_progress)
        elif phase == "climax":
            return self._generate_climax_storyline(phase_progress)
        elif phase == "resolution":
            return self._generate_resolution_storyline(phase_progress)
        else:
            return self._generate_default_storyline()
    
    def _generate_setup_storyline(self, progress: float) -> Dict[str, Any]:
        """生成设定阶段故事线"""
        return {
            "title": f"第{self.chapter}章：{self._get_setup_title(progress)}",
            "plot_points": [
                "世界观进一步展开",
                "角色关系建立",
                "初始冲突引入"
            ],
            "character_interactions": [
                "主要角色互动",
                "角色性格展现"
            ],
            "key_events": [
                "重要信息揭示"
            ],
            "conflict_elements": [
                "轻微冲突或矛盾"
            ]
        }
    
    def _generate_confrontation_storyline(self, progress: float) -> Dict[str, Any]:
        """生成冲突阶段故事线"""
        return {
            "title": f"第{self.chapter}章：{self._get_confrontation_title(progress)}",
            "plot_points": [
                "冲突升级",
                "角色面临挑战",
                "障碍增加"
            ],
            "character_interactions": [
                "角色间冲突",
                "盟友关系建立"
            ],
            "key_events": [
                "重要转折点"
            ],
            "conflict_elements": [
                "主要冲突展开"
            ]
        }
    
    def _generate_climax_storyline(self, progress: float) -> Dict[str, Any]:
        """生成高潮阶段故事线"""
        return {
            "title": f"第{self.chapter}章：{self._get_climax_title(progress)}",
            "plot_points": [
                "冲突达到顶点",
                "关键转折发生",
                "重大揭示"
            ],
            "character_interactions": [
                "角色最终对决",
                "情感高潮"
            ],
            "key_events": [
                "故事高潮"
            ],
            "conflict_elements": [
                "最终冲突"
            ]
        }
    
    def _generate_resolution_storyline(self, progress: float) -> Dict[str, Any]:
        """生成解决阶段故事线"""
        return {
            "title": f"第{self.chapter}章：{self._get_resolution_title(progress)}",
            "plot_points": [
                "冲突解决",
                "角色归宿",
                "故事收尾"
            ],
            "character_interactions": [
                "角色和解",
                "关系总结"
            ],
            "key_events": [
                "最终结局"
            ],
            "resolution_elements": [
                "故事圆满结束"
            ]
        }
    
    def _generate_default_storyline(self) -> Dict[str, Any]:
        """生成默认故事线"""
        return {
            "title": f"第{self.chapter}章：未知标题",
            "plot_points": ["情节发展"],
            "character_interactions": ["角色互动"],
            "key_events": ["重要事件"],
            "conflict_elements": ["冲突元素"]
        }
    
    def _get_setup_title(self, progress: float) -> str:
        """获取设定阶段标题"""
        titles = [
            "初入世界", "角色登场", "环境探索", "关系建立",
            "初始冲突", "秘密发现", "能力觉醒", "目标确立",
            "团队组建", "征程开始"
        ]
        index = int(progress * len(titles))
        return titles[min(index, len(titles) - 1)]
    
    def _get_confrontation_title(self, progress: float) -> str:
        """获取冲突阶段标题"""
        titles = [
            "冲突初现", "挑战来临", "困难增加", "盟友背叛",
            "危机四伏", "绝境求生", "力量觉醒", "真相揭露",
            "决战前夕", "最终对决"
        ]
        index = int(progress * len(titles))
        return titles[min(index, len(titles) - 1)]
    
    def _get_climax_title(self, progress: float) -> str:
        """获取高潮阶段标题"""
        titles = [
            "风暴前夕", "关键转折", "真相大白", "生死抉择",
            "最终决战", "英雄时刻", "命运转折", "胜利在望",
            "新的开始", "完美结局"
        ]
        index = int(progress * len(titles))
        return titles[min(index, len(titles) - 1)]
    
    def _get_resolution_title(self, progress: float) -> str:
        """获取解决阶段标题"""
        titles = [
            "尘埃落定", "新的征程", "角色归宿", "世界和平",
            "英雄传说", "新的开始", "完美结局", "故事终章",
            "新的冒险", "传奇延续"
        ]
        index = int(progress * len(titles))
        return titles[min(index, len(titles) - 1)]
    
    def _add_innovation(self, base_storyline: Dict[str, Any], constraints: Dict[str, Any]) -> Dict[str, Any]:
        """添加创新元素"""
        # 在基础故事线上添加创新元素，但不超过偏差限制
        innovative_storyline = base_storyline.copy()
        
        # 添加一些创新的情节点
        innovative_plot_points = base_storyline.get("plot_points", []).copy()
        
        # 根据章节数添加不同的创新元素
        if self.chapter % 5 == 0:
            innovative_plot_points.append("重要转折点")
        
        if self.chapter % 10 == 0:
            innovative_plot_points.append("重大揭示")
        
        innovative_storyline["plot_points"] = innovative_plot_points
        
        return innovative_storyline
    
    def _calculate_deviation(self, storyline: Dict[str, Any], constraints: Dict[str, Any]) -> float:
        """计算偏差度"""
        # 简单的偏差计算逻辑
        # 实际应该用更复杂的算法
        
        deviation_score = 0.0
        
        # 检查是否违反了阶段约束
        phase_constraints = constraints.get("phase_constraints", {})
        forbidden_elements = phase_constraints.get("forbidden_elements", [])
        
        storyline_text = str(storyline)
        for forbidden in forbidden_elements:
            if forbidden in storyline_text:
                deviation_score += 0.1
        
        # 检查角色发展约束
        character_constraints = constraints.get("character_constraints", {})
        if not character_constraints.get("main_character_development", True):
            deviation_score += 0.2
        
        return min(deviation_score, 1.0)
    
    def _adjust_to_constraints(self, storyline: Dict[str, Any], constraints: Dict[str, Any]) -> Dict[str, Any]:
        """调整故事线以符合约束"""
        adjusted_storyline = storyline.copy()
        
        # 移除违反约束的元素
        phase_constraints = constraints.get("phase_constraints", {})
        forbidden_elements = phase_constraints.get("forbidden_elements", [])
        
        # 过滤掉被禁止的情节点
        if "plot_points" in adjusted_storyline:
            filtered_points = []
            for point in adjusted_storyline["plot_points"]:
                is_forbidden = False
                for forbidden in forbidden_elements:
                    if forbidden in str(point):
                        is_forbidden = True
                        break
                if not is_forbidden:
                    filtered_points.append(point)
            adjusted_storyline["plot_points"] = filtered_points
        
        return adjusted_storyline
    
    def _calculate_consistency(self, storyline: Dict[str, Any], constraints: Dict[str, Any]) -> float:
        """计算一致性分数"""
        consistency_score = 1.0
        
        # 检查阶段一致性
        phase = constraints.get("phase", {})
        phase_name = phase.get("phase_name", "")
        
        storyline_text = str(storyline)
        
        # 根据阶段检查一致性
        if "设定" in phase_name:
            if "冲突" in storyline_text and "解决" not in storyline_text:
                consistency_score -= 0.1
        
        if "冲突" in phase_name:
            if "设定" in storyline_text and "冲突" not in storyline_text:
                consistency_score -= 0.1
        
        return max(consistency_score, 0.0)


class DualLayerStorylineManager:
    """双层故事线管理器"""
    
    def __init__(self, data_manager=None):
        self.data_manager = data_manager
        self.novel_storylines = {}  # {novel_id: NovelStoryline}
        self.chapter_storylines = {}  # {(novel_id, chapter): ChapterStoryline}
    
    def initialize_novel_storyline(self, novel_id: str) -> bool:
        """初始化小说故事线"""
        try:
            novel_storyline = NovelStoryline(novel_id, self.data_manager)
            novel_storyline.load_storyline()
            self.novel_storylines[novel_id] = novel_storyline
            return True
        except Exception as e:
            logger.error(f"初始化小说故事线失败: {e}")
            return False
    
    def get_novel_storyline(self, novel_id: str) -> Optional[NovelStoryline]:
        """获取小说故事线"""
        if novel_id not in self.novel_storylines:
            self.initialize_novel_storyline(novel_id)
        
        return self.novel_storylines.get(novel_id)
    
    def generate_chapter_storyline(self, novel_id: str, chapter: int) -> Dict[str, Any]:
        """生成章节故事线"""
        try:
            # 获取上层故事线
            novel_storyline = self.get_novel_storyline(novel_id)
            if not novel_storyline:
                return {"error": "无法获取小说故事线"}
            
            # 获取上层约束
            upper_constraints = novel_storyline.get_constraints_for_chapter(chapter)
            
            # 创建章节故事线
            chapter_storyline = ChapterStoryline(novel_storyline, chapter)
            
            # 生成章节故事线
            chapter_data = chapter_storyline.generate_with_constraints(upper_constraints)
            
            # 缓存章节故事线
            self.chapter_storylines[(novel_id, chapter)] = chapter_storyline
            
            return {
                "success": True,
                "chapter_storyline": chapter_data,
                "upper_constraints": upper_constraints,
                "deviation_score": chapter_data.get("deviation_score", 0.0),
                "consistency_score": chapter_data.get("consistency_score", 0.0)
            }
            
        except Exception as e:
            logger.error(f"生成章节故事线失败: {e}")
            return {"error": f"生成章节故事线失败: {str(e)}"}
    
    def update_progress(self, novel_id: str, chapter: int, chapter_content: Dict[str, Any]) -> bool:
        """更新故事线进度"""
        try:
            novel_storyline = self.get_novel_storyline(novel_id)
            if not novel_storyline:
                return False
            
            return novel_storyline.update_progress(chapter, chapter_content)
            
        except Exception as e:
            logger.error(f"更新故事线进度失败: {e}")
            return False
    
    def get_story_progress(self, novel_id: str) -> Dict[str, Any]:
        """获取故事进度"""
        try:
            novel_storyline = self.get_novel_storyline(novel_id)
            if not novel_storyline:
                return {"error": "无法获取小说故事线"}
            
            current_chapter = novel_storyline.storyline_data.get("current_chapter", 0)
            total_chapters = novel_storyline.storyline_data.get("total_chapters", 100)
            
            current_phase = novel_storyline.get_current_phase(current_chapter)
            
            return {
                "current_chapter": current_chapter,
                "total_chapters": total_chapters,
                "progress_percentage": (current_chapter / total_chapters) * 100,
                "current_phase": current_phase,
                "major_arcs": novel_storyline.storyline_data.get("major_arcs", [])
            }
            
        except Exception as e:
            logger.error(f"获取故事进度失败: {e}")
            return {"error": f"获取故事进度失败: {str(e)}"}

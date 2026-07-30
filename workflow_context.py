"""
[DEPRECATED] 工作流程上下文管理器（旧流水线遗留）

⚠ 本模块属于 InkAI 旧版状态机式 workflow（inkai_workflow_optimized.py）的产物，
   已被新流水线完全取代——新流水线通过磁盘文件（metadata/characters/storyline/
   blueprint/volume_chapters/chapters_demo）做状态传递，无需中间状态对象。
   - 新代码请勿 import 本模块；保留它仅为兼容历史 novel_dir 中残留的
     workflow_context.json 文件不被误读。

详见：docs/development/data_files_catalog.md
"""
import warnings as _warnings
_warnings.warn(
    "workflow_context 已废弃；新流水线通过磁盘文件直接做状态传递。"
    "详见 docs/development/data_files_catalog.md",
    DeprecationWarning,
    stacklevel=2,
)

from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from utils.logger import get_logger

logger = get_logger("workflow_context")


class WorkflowContext:
    """工作流程上下文管理器"""
    
    def __init__(self, novel_id: str = None):
        self.novel_id = novel_id
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        
        # 核心数据
        self.user_requirements = ""
        self.title = ""
        self.tags = {}
        self.characters = {}
        self.storyline = {}
        self.knowledge_graph_id = None
        
        # 状态管理
        self.current_step = "not_started"
        self.previous_steps = []
        
        # 缓存数据
        self._cache = {}
        self._quality_assessments = {}
        
        # 续写相关数据
        self.is_continuation = False
        self.continuation_data = {}
    
    def set_basic_info(self, title: str, user_requirements: str):
        """设置基本信息"""
        self.title = title
        self.user_requirements = user_requirements
        self._update_timestamp()
    
    def set_tags(self, tags: Dict[str, List[str]]):
        """设置标签"""
        self.tags = tags
        self._update_timestamp()
    
    def set_characters(self, characters: Dict[str, Any]):
        """设置人物信息"""
        self.characters = characters
        self._update_timestamp()
    
    def set_storyline(self, storyline: Dict[str, Any]):
        """设置故事线"""
        self.storyline = storyline
        self._update_timestamp()
    
    def set_knowledge_graph_id(self, kg_id: str):
        """设置知识图谱ID"""
        self.knowledge_graph_id = kg_id
        self._update_timestamp()
    
    def set_current_step(self, step: str):
        """设置当前步骤"""
        if self.current_step != "not_started":
            self.previous_steps.append(self.current_step)
        self.current_step = step
        self._update_timestamp()
    
    def get_agent_input_data(self, agent_type: str, additional_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """为智能体生成标准化的输入数据"""
        base_data = {
            "user_requirements": self.user_requirements,
            "title": self.title,
            "novel_id": self.novel_id,
            "current_step": self.current_step
        }
        
        # 根据智能体类型添加特定数据
        if agent_type == "tag_selector":
            base_data.update({
                "selected_tags": additional_data.get("selected_tags") if additional_data else None
            })
        
        elif agent_type == "character_creator":
            base_data.update({
                "selected_tags": self.tags,
                "user_requirements": self.user_requirements
            })
        
        elif agent_type == "storyline_generator":
            base_data.update({
                "selected_tags": self.tags,
                "characters": self.characters,
                "user_requirements": self.user_requirements
            })
        
        elif agent_type == "chapter_writer":
            base_data.update({
                "chapter_info": additional_data.get("chapter_info") if additional_data else {},
                "characters": self.characters,
                "storyline": self.storyline,
                "tags": self.tags,
                "user_requirements": self.user_requirements
            })
        
        elif agent_type == "quality_assessor":
            base_data.update({
                "content": additional_data.get("content") if additional_data else {},
                "content_type": additional_data.get("content_type", "story") if additional_data else "story",
                "previous_chapters": additional_data.get("previous_chapters") if additional_data else None,
                "overall_storyline": additional_data.get("overall_storyline") if additional_data else self.storyline,
                "user_requirements": self.user_requirements
            })
        
        # 添加续写相关数据
        if self.is_continuation:
            base_data.update({
                "knowledge_base": self.continuation_data.get("knowledge_base", {}),
                "novel_data": self.continuation_data.get("novel_data", {})
            })
        
        # 合并额外数据
        if additional_data:
            base_data.update(additional_data)
        
        return base_data
    
    def cache_result(self, key: str, result: Dict[str, Any]):
        """缓存智能体结果"""
        self._cache[key] = {
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "step": self.current_step
        }
        self._update_timestamp()
    
    def get_cached_result(self, key: str) -> Optional[Dict[str, Any]]:
        """获取缓存的结果"""
        if key in self._cache:
            return self._cache[key]["result"]
        return None
    
    def cache_quality_assessment(self, content_type: str, assessment: Dict[str, Any]):
        """缓存质量评估结果"""
        self._quality_assessments[content_type] = {
            "assessment": assessment,
            "timestamp": datetime.now().isoformat(),
            "step": self.current_step
        }
        self._update_timestamp()
    
    def get_quality_assessment(self, content_type: str) -> Optional[Dict[str, Any]]:
        """获取质量评估结果"""
        if content_type in self._quality_assessments:
            return self._quality_assessments[content_type]["assessment"]
        return None
    
    def set_continuation_mode(self, novel_data: Dict[str, Any], knowledge_base: Dict[str, Any]):
        """设置续写模式"""
        self.is_continuation = True
        self.continuation_data = {
            "novel_data": novel_data,
            "knowledge_base": knowledge_base
        }
        self._update_timestamp()
    
    def get_continuation_data(self) -> Dict[str, Any]:
        """获取续写数据"""
        return self.continuation_data if self.is_continuation else {}
    
    def get_summary(self) -> Dict[str, Any]:
        """获取上下文摘要"""
        return {
            "novel_id": self.novel_id,
            "title": self.title,
            "current_step": self.current_step,
            "previous_steps": self.previous_steps,
            "has_tags": bool(self.tags),
            "has_characters": bool(self.characters),
            "has_storyline": bool(self.storyline),
            "has_knowledge_graph": bool(self.knowledge_graph_id),
            "is_continuation": self.is_continuation,
            "cache_size": len(self._cache),
            "quality_assessments_count": len(self._quality_assessments),
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    def _update_timestamp(self):
        """更新时间戳"""
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "novel_id": self.novel_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "user_requirements": self.user_requirements,
            "title": self.title,
            "tags": self.tags,
            "characters": self.characters,
            "storyline": self.storyline,
            "knowledge_graph_id": self.knowledge_graph_id,
            "current_step": self.current_step,
            "previous_steps": self.previous_steps,
            "cache": self._cache,
            "quality_assessments": self._quality_assessments,
            "is_continuation": self.is_continuation,
            "continuation_data": self.continuation_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowContext':
        """从字典创建上下文"""
        context = cls(data.get("novel_id"))
        context.created_at = data.get("created_at", datetime.now().isoformat())
        context.updated_at = data.get("updated_at", datetime.now().isoformat())
        context.user_requirements = data.get("user_requirements", "")
        context.title = data.get("title", "")
        context.tags = data.get("tags", {})
        context.characters = data.get("characters", {})
        context.storyline = data.get("storyline", {})
        context.knowledge_graph_id = data.get("knowledge_graph_id")
        context.current_step = data.get("current_step", "not_started")
        context.previous_steps = data.get("previous_steps", [])
        context._cache = data.get("cache", {})
        context._quality_assessments = data.get("quality_assessments", {})
        context.is_continuation = data.get("is_continuation", False)
        context.continuation_data = data.get("continuation_data", {})
        return context
    
    def save_to_file(self, file_path: str) -> bool:
        """保存上下文到文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存上下文失败: {e}")
            return False
    
    @classmethod
    def load_from_file(cls, file_path: str) -> Optional['WorkflowContext']:
        """从文件加载上下文"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception as e:
            logger.error(f"加载上下文失败: {e}")
            return None
    
    def validate_context(self) -> Dict[str, Any]:
        """验证上下文完整性"""
        issues = []
        warnings = []
        
        # 检查必要字段
        if not self.novel_id:
            issues.append("缺少小说ID")
        
        if not self.user_requirements:
            warnings.append("缺少用户需求")
        
        if not self.title:
            warnings.append("缺少小说标题")
        
        # 检查步骤完整性
        if self.current_step == "character_creation" and not self.tags:
            issues.append("角色创建步骤缺少标签数据")
        
        if self.current_step == "storyline_generation" and not self.characters:
            issues.append("故事线生成步骤缺少角色数据")
        
        if self.current_step == "chapter_writing" and not self.storyline:
            issues.append("章节写作步骤缺少故事线数据")
        
        # 检查续写模式
        if self.is_continuation and not self.continuation_data:
            issues.append("续写模式缺少续写数据")
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "context_summary": self.get_summary()
        }
    
    def reset_to_step(self, step: str) -> bool:
        """重置到指定步骤"""
        valid_steps = [
            "not_started", "tag_selection", "character_creation", 
            "storyline_generation", "knowledge_graph_creation", 
            "chapter_writing", "chapter_completed"
        ]
        
        if step not in valid_steps:
            return False
        
        # 根据步骤清理相关数据
        if step == "not_started":
            self.tags = {}
            self.characters = {}
            self.storyline = {}
            self.knowledge_graph_id = None
            self._cache = {}
            self._quality_assessments = {}
        elif step == "tag_selection":
            self.characters = {}
            self.storyline = {}
            self.knowledge_graph_id = None
            self._cache = {}
            self._quality_assessments = {}
        elif step == "character_creation":
            self.storyline = {}
            self.knowledge_graph_id = None
            self._cache = {}
            self._quality_assessments = {}
        elif step == "storyline_generation":
            self.knowledge_graph_id = None
            self._cache = {}
            self._quality_assessments = {}
        
        self.current_step = step
        self._update_timestamp()
        return True
    
    def save_context(self):
        """保存上下文到文件"""
        if not self.novel_id:
            return False
        
        try:
            import os
            import json
            from data_manager import DataManager
            
            # 获取数据管理器
            data_manager = DataManager()
            novel_dir = os.path.join(data_manager.novels_dir, self.novel_id)
            
            # 确保目录存在
            os.makedirs(novel_dir, exist_ok=True)
            
            # 构建上下文数据
            context_data = {
                "novel_id": self.novel_id,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
                "user_requirements": self.user_requirements,
                "title": self.title,
                "tags": self.tags,
                "characters": self.characters,
                "storyline": self.storyline,
                "knowledge_graph_id": self.knowledge_graph_id,
                "current_step": self.current_step,
                "previous_steps": self.previous_steps,
                "is_continuation": self.is_continuation,
                "continuation_data": self.continuation_data,
                "cache": self._cache,
                "quality_assessments": self._quality_assessments
            }
            
            # 保存到文件
            context_file = os.path.join(novel_dir, "workflow_context.json")
            with open(context_file, 'w', encoding='utf-8') as f:
                json.dump(context_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"保存上下文失败: {e}")
            return False
    
    def load_context(self, novel_id: str) -> bool:
        """从文件加载上下文"""
        try:
            import os
            import json
            from data_manager import DataManager
            
            # 获取数据管理器
            data_manager = DataManager()
            novel_dir = os.path.join(data_manager.novels_dir, novel_id)
            context_file = os.path.join(novel_dir, "workflow_context.json")
            
            if not os.path.exists(context_file):
                return False
            
            # 读取文件
            with open(context_file, 'r', encoding='utf-8') as f:
                context_data = json.load(f)
            
            # 恢复上下文数据
            self.novel_id = context_data.get("novel_id", novel_id)
            self.created_at = context_data.get("created_at", "")
            self.updated_at = context_data.get("updated_at", "")
            self.user_requirements = context_data.get("user_requirements", "")
            self.title = context_data.get("title", "")
            self.tags = context_data.get("tags", {})
            self.characters = context_data.get("characters", {})
            self.storyline = context_data.get("storyline", {})
            self.knowledge_graph_id = context_data.get("knowledge_graph_id")
            self.current_step = context_data.get("current_step", "not_started")
            self.previous_steps = context_data.get("previous_steps", [])
            self.is_continuation = context_data.get("is_continuation", False)
            self.continuation_data = context_data.get("continuation_data", {})
            self._cache = context_data.get("cache", {})
            self._quality_assessments = context_data.get("quality_assessments", {})
            
            return True
            
        except Exception as e:
            logger.error(f"加载上下文失败: {e}")
            return False
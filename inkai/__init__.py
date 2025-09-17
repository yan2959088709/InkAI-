"""
InkAI - 智能小说创作系统
=======================

一个基于大语言模型的完整小说创作框架系统，提供从创意构思到最终成品的全流程支持。

主要功能：
- 智能标签推荐
- 人物角色创建  
- 故事线生成
- 章节内容写作
- 质量评估分析
- 数据管理存储
- 工作流程控制
- 高级功能扩展
- 续写分析写作

版本: 2.0.0
作者: InkAI Team
"""

__version__ = "2.0.0"
__author__ = "InkAI Team"

# 导入核心组件
from .core.base_agent import EnhancedBaseAgent
from .agents.tag_selector import EnhancedTagSelectorAgent
from .agents.character_creator import EnhancedCharacterCreatorAgent
from .agents.storyline_generator import EnhancedStorylineGeneratorAgent
from .agents.chapter_writer import EnhancedChapterWriterAgent
from .agents.quality_assessor import EnhancedQualityAssessorAgent
from .agents.continuation_analyzer import ContinuationAnalyzerAgent
from .agents.continuation_writer import ContinuationWriterAgent

from .managers.data_manager import EnhancedDataManager
from .managers.workflow_controller import EnhancedWorkflowController

from .system.main_system import LightweightInkAIWithContinuation
from .utils.config import API_CONFIG, SYSTEM_CONFIG, CREATIVE_CONFIG

__all__ = [
    'EnhancedBaseAgent',
    'EnhancedTagSelectorAgent', 
    'EnhancedCharacterCreatorAgent',
    'EnhancedStorylineGeneratorAgent',
    'EnhancedChapterWriterAgent',
    'EnhancedQualityAssessorAgent',
    'ContinuationAnalyzerAgent',
    'ContinuationWriterAgent',
    'EnhancedDataManager',
    'EnhancedWorkflowController', 
    'LightweightInkAIWithContinuation',
    'API_CONFIG',
    'SYSTEM_CONFIG', 
    'CREATIVE_CONFIG'
]

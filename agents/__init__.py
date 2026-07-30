"""
智能体模块初始化文件
提供统一的导入接口
"""
import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入基础类
from .base_continuation_assessor import BaseContinuationAssessor
from .base_continuation_improver import BaseContinuationImprover

# 导入所有智能体
from .tag_selector import TagSelectorAgent
from .character_creator import CharacterCreatorAgent
from .character_improver import CharacterImprover
from .storyline_generator import StorylineGeneratorAgent
from .quality_assessor import QualityAssessorAgent
from .chapter_writer import ChapterWriterAgent
from .novel_continuation_agent import NovelContinuationAgent
from .continuation_storyline_generator import ContinuationStorylineGenerator
from .continuation_chapter_writer import ContinuationChapterWriter
from .novel_storyline_improver import NovelStorylineImprover
from .continuation_quality_assessor import ContinuationQualityAssessor
from .continuation_chapter_improver import ContinuationChapterImprover
from .continuation_character_consistency_assessor import ContinuationCharacterConsistencyAssessor
from .continuation_plot_logic_assessor import ContinuationPlotLogicAssessor
from .continuation_world_consistency_assessor import ContinuationWorldConsistencyAssessor
from .continuation_style_consistency_assessor import ContinuationStyleConsistencyAssessor
from .continuation_reader_experience_assessor import ContinuationReaderExperienceAssessor
from .continuation_long_term_consistency_assessor import ContinuationLongTermConsistencyAssessor
from .continuation_character_consistency_improver import ContinuationCharacterConsistencyImprover
from .continuation_plot_logic_improver import ContinuationPlotLogicImprover
from .continuation_world_consistency_improver import ContinuationWorldConsistencyImprover
from .continuation_style_consistency_improver import ContinuationStyleConsistencyImprover
from .continuation_reader_experience_improver import ContinuationReaderExperienceImprover
from .continuation_long_term_consistency_improver import ContinuationLongTermConsistencyImprover
from .chapter_summary_generator import ChapterSummaryGenerator
from .enhanced_character_analyzer import EnhancedCharacterAnalyzer

# 向后兼容：StorylineImprover 现在是 NovelStorylineImprover 的别名
StorylineImprover = NovelStorylineImprover

__all__ = [
    # 基础类
    'BaseContinuationAssessor',
    'BaseContinuationImprover',
    # 核心智能体
    'TagSelectorAgent',
    'CharacterCreatorAgent', 
    'CharacterImprover',
    'StorylineGeneratorAgent',
    'QualityAssessorAgent',
    'ChapterWriterAgent',
    'NovelContinuationAgent',
    'ContinuationStorylineGenerator',
    'ContinuationChapterWriter',
    'NovelStorylineImprover',
    'StorylineImprover',  # 向后兼容别名
    'ContinuationQualityAssessor',
    'ContinuationChapterImprover',
    # 评估智能体
    'ContinuationCharacterConsistencyAssessor',
    'ContinuationPlotLogicAssessor',
    'ContinuationWorldConsistencyAssessor',
    'ContinuationStyleConsistencyAssessor',
    'ContinuationReaderExperienceAssessor',
    'ContinuationLongTermConsistencyAssessor',
    # 改进智能体
    'ContinuationCharacterConsistencyImprover',
    'ContinuationPlotLogicImprover',
    'ContinuationWorldConsistencyImprover',
    'ContinuationStyleConsistencyImprover',
    'ContinuationReaderExperienceImprover',
    'ContinuationLongTermConsistencyImprover',
    # 辅助智能体
    'ChapterSummaryGenerator',
    'EnhancedCharacterAnalyzer'
]

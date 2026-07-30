"""
[DEPRECATED] InkAI 旧版主工作流程控制器（已被新流水线取代）

⚠ 本文件是 InkAI 项目早期的"巨型状态机"，包含：
  - 角色/故事线的端到端生成
  - 章节续写与质量评估
  - 各种"知识管理器"的集成
   
  目前已被一组解耦的 CLI 工具取代：
    run_init_novel.py       —— 初始化（含 --also-storyline 一键展开）
    run_outline_demo.py     —— 蓝图 + 章节卡
    run_chapter_demo.py     —— 章节正文
    run_validate_volume.py  —— 整卷质量校验
    run_validate_canon.py   —— 档案一致性校验

  保留本文件仅为历史回溯，请勿在新代码中调用本模块。

详见：docs/development/data_files_catalog.md
"""
import warnings as _warnings
_warnings.warn(
    "inkai_workflow_optimized 已废弃；请使用 run_init_novel/run_outline_demo/run_chapter_demo "
    "等 CLI 工具。详见 docs/development/data_files_catalog.md",
    DeprecationWarning,
    stacklevel=2,
)

import os
import sys
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

# 添加agents目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'agents'))

# 导入日志模块
from utils.logger import get_logger
logger = get_logger("inkai_workflow")

# 导入智能体
# 导入所有智能体
from agents import (
    TagSelectorAgent,
    CharacterCreatorAgent,
    CharacterImprover,
    StorylineGeneratorAgent,
    QualityAssessorAgent,
    ChapterWriterAgent,
    NovelContinuationAgent,
    ContinuationStorylineGenerator,
    ContinuationChapterWriter,
    NovelStorylineImprover,
    StorylineImprover,
    ContinuationQualityAssessor,
    ContinuationChapterImprover,
    ContinuationCharacterConsistencyAssessor,
    ContinuationPlotLogicAssessor,
    ContinuationWorldConsistencyAssessor,
    ContinuationStyleConsistencyAssessor,
    ContinuationReaderExperienceAssessor,
    ContinuationLongTermConsistencyAssessor,
    ContinuationCharacterConsistencyImprover,
    ContinuationPlotLogicImprover,
    ContinuationWorldConsistencyImprover,
    ContinuationStyleConsistencyImprover,
    ContinuationReaderExperienceImprover,
    ContinuationLongTermConsistencyImprover,
    ChapterSummaryGenerator,
    EnhancedCharacterAnalyzer
)

# 导入核心管理模块
from core.core_knowledge_manager import CoreKnowledgeManager
from core.dynamic_knowledge_manager import DynamicKnowledgeManager
from core.intelligent_context_selector import IntelligentContextSelector

# 导入性能优化模块
from performance.parallel_processor import ParallelProcessor
from performance.intelligent_cache_manager import IntelligentCacheManager
from performance.batch_processor import BatchProcessor, LLMRequestBatcher
from performance.performance_monitor import PerformanceMonitor

# 导入长期优化模块
from optimization.runtime_guarantee_system import RuntimeGuaranteeSystem
from optimization.long_term_consistency_system import LongTermConsistencySystem

# 导入其他模块
from data_manager import DataManager
from workflow_context import WorkflowContext
import config


class InkAIWorkflowOptimized:
    """InkAI 优化后的主工作流程控制器"""
    
    def __init__(self):
        # 初始化智能体
        self.tag_selector = TagSelectorAgent()
        self.character_creator = CharacterCreatorAgent()
        self.character_improver = CharacterImprover()
        self.storyline_generator = StorylineGeneratorAgent()
        self.quality_assessor = QualityAssessorAgent()
        self.chapter_writer = ChapterWriterAgent()
        
        # 续写相关智能体
        self.novel_continuation_agent = NovelContinuationAgent()
        self.continuation_storyline_generator = ContinuationStorylineGenerator()
        self.continuation_chapter_writer = ContinuationChapterWriter()
        self.storyline_improver = NovelStorylineImprover()
        self.continuation_storyline_improver = NovelStorylineImprover()
        self.continuation_quality_assessor = ContinuationQualityAssessor()
        self.continuation_chapter_improver = ContinuationChapterImprover()
        
        # 专项评估智能体
        self.continuation_character_consistency_assessor = ContinuationCharacterConsistencyAssessor()
        self.continuation_plot_logic_assessor = ContinuationPlotLogicAssessor()
        self.continuation_world_consistency_assessor = ContinuationWorldConsistencyAssessor()
        self.continuation_style_consistency_assessor = ContinuationStyleConsistencyAssessor()
        self.continuation_reader_experience_assessor = ContinuationReaderExperienceAssessor()
        self.continuation_long_term_consistency_assessor = ContinuationLongTermConsistencyAssessor()
        
        # 专项改进智能体
        self.continuation_character_consistency_improver = ContinuationCharacterConsistencyImprover()
        self.continuation_plot_logic_improver = ContinuationPlotLogicImprover()
        self.continuation_world_consistency_improver = ContinuationWorldConsistencyImprover()
        self.continuation_style_consistency_improver = ContinuationStyleConsistencyImprover()
        self.continuation_reader_experience_improver = ContinuationReaderExperienceImprover()
        self.continuation_long_term_consistency_improver = ContinuationLongTermConsistencyImprover()
        
        # 辅助智能体
        self.chapter_summary_generator = ChapterSummaryGenerator()
        self.enhanced_character_analyzer = EnhancedCharacterAnalyzer()
        
        self.data_manager = DataManager()
        
        # 初始化核心管理模块
        self.core_knowledge_manager = CoreKnowledgeManager(self.data_manager)
        self.dynamic_knowledge_manager = DynamicKnowledgeManager(self.data_manager)
        
        # [NEW] 初始化整合知识系统
        try:
            from core.integrated_knowledge_system import IntegratedKnowledgeSystem
            self.integrated_knowledge = IntegratedKnowledgeSystem(self.data_manager)
            logger.info("[OK] 整合知识系统已初始化")
        except Exception as e:
            logger.error(f"[FAIL] 整合知识系统初始化失败: {e}")
            self.integrated_knowledge = None
        
        # 初始化性能优化模块（需要在智能上下文选择器之前初始化缓存管理器）
        try:
            self.parallel_processor = ParallelProcessor(max_workers=4)
            self.cache_manager = IntelligentCacheManager()
            self.batch_processor = BatchProcessor()
            self.llm_batcher = LLMRequestBatcher(self.batch_processor)
            self.performance_monitor = PerformanceMonitor()
            
            # 初始化长期优化模块
            self.runtime_guarantee_system = RuntimeGuaranteeSystem()
            self.long_term_consistency_system = LongTermConsistencySystem(self.data_manager)
            
            # 延迟启动性能监控，避免启动时的问题
            self._performance_monitoring_enabled = True
            logger.info("性能优化模块初始化成功")
        except Exception as e:
            logger.error(f"性能优化模块初始化失败: {e}")
            # 设置默认值，确保系统仍能运行
            self.parallel_processor = None
            self.cache_manager = None
            self.batch_processor = None
            self.llm_batcher = None
            self.performance_monitor = None
            self.runtime_guarantee_system = None
            self.long_term_consistency_system = None
            self._performance_monitoring_enabled = False
        
        # [NEW] 初始化嵌入服务和向量数据库
        from core.embedding_service import EmbeddingService
        from core.vector_database import VectorDatabase
        from core.phase_planner import PhasePlanner
        from core.quality_validator import QualityValidator
        from openai import OpenAI

        self.embedding_service = EmbeddingService()
        self.vector_database = VectorDatabase(
            self.data_manager,
            self.embedding_service
        )
        client = OpenAI(api_key=config.API_KEY, base_url=config.BASE_URL)
        self.phase_planner = PhasePlanner(client=client)
        self.quality_validator = QualityValidator()

        self.intelligent_context_selector = IntelligentContextSelector(
            self.data_manager, 
            self.dynamic_knowledge_manager,
            self.core_knowledge_manager,  # [NEW] 添加核心知识库管理器
            self.embedding_service,  # [NEW] 添加嵌入服务
            self.vector_database,  # [NEW] 添加向量数据库
            self.cache_manager  # [NEW] 添加缓存管理器
        )
        
        # 使用统一的工作流程上下文
        self.context = None
    
    def start_performance_monitoring(self):
        """启动性能监控"""
        try:
            if self._performance_monitoring_enabled and self.performance_monitor:
                self.performance_monitor.start_monitoring()
                logger.info("性能监控已启动")
                return True
            else:
                logger.info("性能监控未启用或不可用")
                return False
        except Exception as e:
            logger.error(f"启动性能监控失败: {e}")
            return False
    
    def stop_performance_monitoring(self):
        """停止性能监控"""
        try:
            if self.performance_monitor:
                self.performance_monitor.stop_monitoring()
                logger.info("性能监控已停止")
                return True
            return False
        except Exception as e:
            logger.error(f"停止性能监控失败: {e}")
            return False
    
    def start_new_novel(self, user_requirements: str, title: str = "未命名小说", 
                       novel_type: str = "超长篇", estimated_chapters: int = None) -> Dict[str, Any]:
        """
        开始新小说创作流程
        
        Args:
            user_requirements: 用户需求
            title: 小说标题
            novel_type: 篇幅类型（短篇/中篇/长篇/超长篇）
            estimated_chapters: 预估章节数（可选）
        """
        logger.info(f"开始创作新小说: {title}")
        logger.info(f"篇幅类型: {novel_type}")
        logger.info(f"用户需求: {user_requirements}")
        
        # [NEW] 使用小说规划器进行规划
        from core.novel_planner import NovelPlanner
        planner = NovelPlanner()
        
        # 生成小说规划
        novel_plan = planner.plan_novel(novel_type, estimated_chapters)
        dual_storyline_plan = planner.plan_dual_storyline(novel_type, user_requirements)
        
        logger.info(f"小说规划: {novel_plan['estimated_chapters']}章, {novel_plan['expected_volumes']}卷")
        
        # 初始化小说项目
        novel_data = {
            "title": title,
            "user_requirements": user_requirements,
            "novel_type": novel_type,
            "novel_plan": novel_plan,
            "dual_storyline_plan": dual_storyline_plan,
            "tags": {},
            "characters": {},
            "storyline": {}
        }
        
        novel_id = self.data_manager.create_novel_project(novel_data)
        
        # 创建统一的工作流程上下文
        self.context = WorkflowContext(novel_id)
        self.context.set_basic_info(title, user_requirements)
        self.context.set_current_step("tag_selection")
        
        # [NEW] 保存规划信息到上下文
        self.context.cache_result("novel_plan", novel_plan)
        self.context.cache_result("dual_storyline_plan", dual_storyline_plan)
        
        # 保存上下文到文件
        self.context.save_context()
        
        return {
            "novel_id": novel_id,
            "status": "created",
            "novel_type": novel_type,
            "novel_plan": novel_plan,
            "dual_storyline_plan": dual_storyline_plan,
            "next_step": "tag_selection"
        }
    
    def select_tags(self, selected_tags: Optional[Dict[str, List[str]]] = None) -> Dict[str, Any]:
        """选择小说标签"""
        logger.info("开始标签选择流程...")
        
        if not self.context:
            return {"error": "请先创建新小说项目"}
        
        # 使用统一的输入数据生成
        input_data = self.context.get_agent_input_data("tag_selector", {"selected_tags": selected_tags})
        
        result = self.tag_selector.process(input_data)
        
        # 保存结果到上下文
        self.context.set_tags(result["selected_tags"])
        self.context.cache_result("tags", result)
        self.context.set_current_step("character_creation")
        
        # 保存到数据管理器
        self.data_manager.save_novel_data(self.context.novel_id, "tags", result)
        
        # 保存工作流状态
        self.context.save_context()
        
        logger.info(f"标签选择完成: {result['selected_tags']}")
        
        return {
            "status": "success",
            "tags": result,
            "next_step": "character_creation"
        }
    
    def create_characters(self) -> Dict[str, Any]:
        """创建人物形象"""
        logger.info("开始人物形象创建...")
        
        if not self.context:
            return {"error": "请先创建新小说项目"}
        
        # 使用统一的输入数据生成
        input_data = self.context.get_agent_input_data("character_creator")
        
        result = self.character_creator.process(input_data)
        
        # 保存结果到上下文
        self.context.set_characters(result)
        self.context.cache_result("characters", result)
        
        # 质量评估
        quality_input = self.context.get_agent_input_data("quality_assessor", {
            "content": result.get("main_character", {}),
            "content_type": "character"
        })
        
        quality_result = self.quality_assessor.process(quality_input)
        self.context.cache_quality_assessment("character", quality_result)
        
        # 保存到数据管理器
        self.data_manager.save_novel_data(self.context.novel_id, "characters", result)
        self.data_manager.save_novel_data(self.context.novel_id, "character_quality_assessment", quality_result)
        
        # [NEW] 初始化核心知识库（部分初始化，先初始化角色信息）
        try:
            novel_data = {
                "metadata": {
                    "title": self.context.title,
                    "user_requirements": self.context.user_requirements
                },
                "characters": result,
                "tags": self.context.tags,
                "storyline": {},  # 故事线还未生成
                "user_requirements": self.context.user_requirements
            }
            core_knowledge = self.core_knowledge_manager.initialize_core_knowledge(
                self.context.novel_id, 
                novel_data
            )
            if core_knowledge:
                logger.info("[OK] 核心知识库已初始化（角色部分）")
            else:
                logger.error("[WARN] 核心知识库初始化失败，但继续流程")
        except Exception as e:
            logger.warning(f"[WARN] 初始化核心知识库时出错: {e}，但继续流程")
        
        logger.info("人物形象创建完成")
        
        # 根据质量评估结果决定下一步
        if quality_result.get("is_high_quality", False):
            self.context.set_current_step("storyline_generation")
            next_step = "storyline_generation"
        else:
            logger.info(f"人物质量评估: {quality_result['overall_score']}分")
            logger.info(f"改进建议: {quality_result['suggestions']}")
            self.context.set_current_step("character_improvement")
            next_step = "character_improvement"
        
        # 保存工作流状态
        self.context.save_context()
        
        return {
            "status": "success" if quality_result.get("is_high_quality", False) else "needs_improvement",
            "characters": result,
            "quality_assessment": quality_result,
            "next_step": next_step
        }
    
    def improve_character(self, suggestions: List[str]) -> Dict[str, Any]:
        """改进人物形象"""
        logger.info("开始人物形象改进...")
        
        if not self.context:
            return {"error": "请先创建新小说项目"}
        
        # 获取当前人物数据
        current_characters = self.context.characters
        if not current_characters:
            return {"error": "没有找到现有人物数据"}
        
        # 获取质量评估结果（如果没有则使用默认建议）
        quality_assessment = self.context.get_quality_assessment("character")
        if not quality_assessment:
            logger.info("没有找到质量评估结果，使用默认改进建议")
            quality_assessment = {"suggestions": []}
        
        # 构建改进输入数据
        input_data = {
            "current_characters": current_characters,
            "overall_storyline": self.context.storyline,
            "improvement_suggestions": suggestions or quality_assessment.get("suggestions", []),
            "tags": self.context.tags,
            "user_requirements": self.context.user_requirements
        }
        
        # 调用人物改进智能体
        result = self.character_improver.process(input_data)
        
        if "error" in result:
            return result
        
        # 保存改进后的人物数据
        improved_characters = result.get("improved_characters", {})
        self.context.set_characters(improved_characters)
        self.context.cache_result("characters", improved_characters)
        
        # 保存到数据管理器
        self.data_manager.save_novel_data(self.context.novel_id, "characters", improved_characters)
        
        # 重新进行质量评估
        quality_input = self.context.get_agent_input_data("quality_assessor", {
            "content": improved_characters.get("main_character", {}),
            "content_type": "character"
        })
        
        new_quality_result = self.quality_assessor.process(quality_input)
        self.context.cache_quality_assessment("character", new_quality_result)
        
        # 保存质量评估结果到数据管理器
        self.data_manager.save_novel_data(self.context.novel_id, "character_quality_assessment", new_quality_result)
        
        logger.info("人物形象改进完成")
        
        # 根据新的质量评估结果决定下一步
        if new_quality_result.get("is_high_quality", False):
            self.context.set_current_step("storyline_generation")
            next_step = "storyline_generation"
        else:
            logger.info(f"改进后人物质量评估: {new_quality_result['overall_score']}分")
            logger.info(f"改进建议: {new_quality_result['suggestions']}")
            self.context.set_current_step("character_improvement")
            next_step = "character_improvement"
        
        # 保存工作流状态
        self.context.save_context()
        
        return {
            "status": "success" if new_quality_result.get("is_high_quality", False) else "needs_improvement",
            "characters": improved_characters,
            "quality_assessment": new_quality_result,
            "improvement_notes": result.get("improvement_notes", []),
            "next_step": next_step
        }
    
    def generate_storyline(self) -> Dict[str, Any]:
        """生成故事线"""
        logger.info("开始故事线生成...")
        
        if not self.context:
            return {"error": "请先创建新小说项目"}
        
        # 使用统一的输入数据生成
        input_data = self.context.get_agent_input_data("storyline_generator")
        
        result = self.storyline_generator.process(input_data)
        
        # 保存结果到上下文
        self.context.set_storyline(result)
        self.context.cache_result("storyline", result)
        
        # 质量评估
        quality_input = self.context.get_agent_input_data("quality_assessor", {
            "content": result.get("overall_storyline", {}),
            "content_type": "storyline"
        })
        
        quality_result = self.quality_assessor.process(quality_input)
        self.context.cache_quality_assessment("storyline", quality_result)
        
        # 保存到数据管理器
        self.data_manager.save_novel_data(self.context.novel_id, "storyline", result)
        self.data_manager.save_novel_data(self.context.novel_id, "storyline_quality_assessment", quality_result)
        
        # [NEW] 更新核心知识库（完整初始化，包含故事线和世界观）
        try:
            novel_data = {
                "metadata": {
                    "title": self.context.title,
                    "user_requirements": self.context.user_requirements
                },
                "characters": self.context.characters,
                "tags": self.context.tags,
                "storyline": result,
                "user_requirements": self.context.user_requirements
            }
            # 如果核心知识库已存在，更新它；否则初始化
            existing_core_knowledge = self.core_knowledge_manager.get_core_knowledge(self.context.novel_id)
            if existing_core_knowledge:
                # 更新核心知识库
                updates = {
                    "world_setting": self.core_knowledge_manager._extract_world_setting(novel_data),
                    "story_themes": self.core_knowledge_manager._extract_story_themes(novel_data),
                    "basic_rules": self.core_knowledge_manager._extract_basic_rules(novel_data)
                }
                self.core_knowledge_manager.update_core_knowledge(self.context.novel_id, updates)
                logger.info("[OK] 核心知识库已更新（故事线和世界观）")
            else:
                # 完整初始化核心知识库
                core_knowledge = self.core_knowledge_manager.initialize_core_knowledge(
                    self.context.novel_id, 
                    novel_data
                )
                if core_knowledge:
                    logger.info("[OK] 核心知识库已完整初始化")
                else:
                    logger.error("[WARN] 核心知识库初始化失败，但继续流程")
        except Exception as e:
            logger.warning(f"[WARN] 更新核心知识库时出错: {e}，但继续流程")
        
        # [NEW] 初始化动态知识库
        try:
            dynamic_knowledge = self.dynamic_knowledge_manager.initialize_dynamic_knowledge(self.context.novel_id)
            if dynamic_knowledge:
                logger.info("[OK] 动态知识库已初始化")
            else:
                logger.error("[WARN] 动态知识库初始化失败，但继续流程")
        except Exception as e:
            logger.warning(f"[WARN] 初始化动态知识库时出错: {e}，但继续流程")
        
        logger.info("故事线生成完成")
        
        # 根据质量评估结果决定下一步
        if quality_result.get("is_high_quality", False):
            self.context.set_current_step("knowledge_graph_creation")
            next_step = "knowledge_graph_creation"
        else:
            logger.info(f"故事线质量评估: {quality_result['overall_score']}分")
            logger.info(f"改进建议: {quality_result['suggestions']}")
            # 即使质量不高，也继续到下一步，用户可以在故事线生成模块中手动优化
            self.context.set_current_step("knowledge_graph_creation")
            next_step = "knowledge_graph_creation"
        
        # 保存工作流状态
        self.context.save_context()
        
        return {
            "status": "success" if quality_result.get("is_high_quality", False) else "needs_improvement",
            "storyline": result,
            "quality_assessment": quality_result,
            "next_step": next_step
        }
    
    def improve_storyline(self, suggestions: List[str]) -> Dict[str, Any]:
        """改进故事线"""
        logger.info("开始故事线改进...")
        
        if not self.context:
            return {"error": "请先创建新小说项目"}
        
        # 获取当前故事线数据
        current_storyline = self.context.storyline
        if not current_storyline:
            return {"error": "没有找到现有故事线数据"}
        
        # 获取质量评估结果（如果没有则使用默认建议）
        quality_assessment = self.context.get_quality_assessment("storyline")
        if not quality_assessment:
            logger.info("没有找到质量评估结果，使用默认改进建议")
            quality_assessment = {"suggestions": []}
        
        # 构建改进输入数据
        input_data = {
            "current_storyline": current_storyline,
            "overall_storyline": current_storyline.get("overall_storyline", {}),
            "characters": self.context.characters,
            "improvement_suggestions": suggestions or quality_assessment.get("suggestions", []),
            "tags": self.context.tags,
            "user_requirements": self.context.user_requirements
        }
        
        # 调用故事线改进智能体
        result = self.storyline_improver.process(input_data)
        
        if "error" in result:
            return result
        
        # 保存改进后的故事线数据
        improved_storyline = result.get("improved_storyline", {})
        self.context.set_storyline(improved_storyline)
        self.context.cache_result("storyline", improved_storyline)
        
        # 保存到数据管理器
        self.data_manager.save_novel_data(self.context.novel_id, "storyline", improved_storyline)
        
        # 重新进行质量评估
        quality_input = self.context.get_agent_input_data("quality_assessor", {
            "content": improved_storyline.get("overall_storyline", {}),
            "content_type": "storyline"
        })
        
        new_quality_result = self.quality_assessor.process(quality_input)
        self.context.cache_quality_assessment("storyline", new_quality_result)
        
        # 保存质量评估结果到数据管理器
        self.data_manager.save_novel_data(self.context.novel_id, "storyline_quality_assessment", new_quality_result)
        
        logger.info("故事线改进完成")
        
        # 根据新的质量评估结果决定下一步
        if new_quality_result.get("is_high_quality", False):
            self.context.set_current_step("knowledge_graph_creation")
            next_step = "knowledge_graph_creation"
        else:
            logger.info(f"改进后故事线质量评估: {new_quality_result['overall_score']}分")
            logger.info(f"改进建议: {new_quality_result['suggestions']}")
            # 即使改进后质量仍不高，也继续到下一步，用户可以在故事线生成模块中继续优化
            self.context.set_current_step("knowledge_graph_creation")
            next_step = "knowledge_graph_creation"
        
        # 保存工作流状态
        self.context.save_context()
        
        return {
            "status": "success" if new_quality_result.get("is_high_quality", False) else "needs_improvement",
            "storyline": improved_storyline,
            "quality_assessment": new_quality_result,
            "improvement_notes": result.get("improvement_notes", []),
            "next_step": next_step
        }
    
    def create_knowledge_graph(self) -> Dict[str, Any]:
        """创建知识图谱"""
        logger.info("开始创建知识图谱...")
        
        if not self.context:
            return {"error": "请先创建新小说项目"}
        
        # 创建知识图谱
        kg_id = self.data_manager.create_knowledge_graph(
            self.context.novel_id, 
            self.context.characters, 
            self.context.storyline
        )
        
        self.context.set_knowledge_graph_id(kg_id)
        self.context.set_current_step("chapter_writing")
        
        # 保存工作流状态
        self.context.save_context()
        
        logger.info(f"知识图谱创建完成: {kg_id}")
        
        return {
            "status": "success",
            "knowledge_graph_id": kg_id,
            "next_step": "chapter_writing"
        }
    
    def write_first_chapter(self) -> Dict[str, Any]:
        """写作第一章"""
        logger.info("开始写作第一章...")
        
        if not self.context:
            return {"error": "请先创建新小说项目"}
        
        # 智能数据检查和恢复
        if not self.context.storyline:
            logger.info("上下文中storyline为空，尝试重新加载...")
            storyline = self.data_manager.load_novel_data(self.context.novel_id, "storyline")
            if storyline:
                self.context.set_storyline(storyline)
                logger.info("已重新加载storyline数据")
            else:
                return {"error": "未找到故事线数据，请先生成故事线"}
        
        # 获取第一章信息
        first_module = self.context.storyline.get("first_module", {})
        if not first_module:
            # 尝试从文件直接加载storyline数据
            logger.info("上下文中未找到first_module，尝试从文件重新加载...")
            storyline = self.data_manager.load_novel_data(self.context.novel_id, "storyline")
            if storyline:
                self.context.set_storyline(storyline)
                first_module = self.context.storyline.get("first_module", {})
                if first_module:
                    logger.info("已成功重新加载first_module数据")
                else:
                    return {"error": "故事线数据中缺少第一章信息，请重新生成故事线"}
            else:
                return {"error": "未找到第一章信息，请检查故事线数据完整性"}
        
        # [NEW] 使用智能上下文选择器获取上下文（第一章时可能为空，但为后续章节做准备）
        try:
            intelligent_context = self.intelligent_context_selector.select_context(
                self.context.novel_id,
                current_chapter=1,
                user_requirements=self.context.user_requirements
            )
            logger.info("[OK] 已获取智能上下文")
        except Exception as e:
            logger.warning(f"[WARN] 获取智能上下文时出错: {e}，使用默认上下文")
            intelligent_context = {}
        
        # 使用统一的输入数据生成（包含智能上下文）
        input_data = self.context.get_agent_input_data("chapter_writer", {
            "chapter_info": first_module,
            "intelligent_context": intelligent_context  # [NEW] 添加智能上下文
        })
        
        result = self.chapter_writer.process(input_data)
        
        # 质量评估
        quality_input = self.context.get_agent_input_data("quality_assessor", {
            "content": result["chapter_content"],
            "content_type": "story"
        })
        
        quality_result = self.quality_assessor.process(quality_input)
        self.context.cache_quality_assessment("story", quality_result)
        
        # 保存章节
        chapter_saved = self.data_manager.save_chapter(
            self.context.novel_id, 
            1, 
            result["chapter_content"]
        )
        
        if chapter_saved:
            # [NEW] 章节完成后，更新动态知识库和向量数据库
            try:
                logger.info("开始更新动态知识库和向量数据库...")

                # [NEW] 将章节内容添加到向量数据库
                try:
                    chapter_text = result["chapter_content"].get("content", "")
                    if chapter_text:
                        chapter_id = "chapter_1"
                        vector_added = self.vector_database.add_vector(
                            self.context.novel_id,
                            chapter_id,
                            chapter_text,
                            metadata={
                                "chapter_number": 1,
                                "title": result["chapter_content"].get("title", ""),
                                "type": "chapter"
                            }
                        )
                        if vector_added:
                            logger.info("[OK] 已将第一章内容添加到向量数据库")
                        else:
                            logger.warning("[WARN] 第一章向量添加失败（嵌入服务不可用）")
                except Exception as e:
                    logger.error(f"[WARN] 添加章节到向量数据库失败: {e}")
                
                # 1. 生成章节摘要
                chapter_summary_input = {
                    "chapter_content": result["chapter_content"],
                    "chapter_number": 1,
                    "novel_context": intelligent_context.get("narrative_phase", {}),
                    "previous_summaries": []
                }
                summary_result = self.chapter_summary_generator.process(chapter_summary_input)
                
                if summary_result.get("success") and summary_result.get("summary_data"):
                    summary_data = summary_result["summary_data"]
                    
                    # 2. 添加章节摘要到动态知识库
                    self.dynamic_knowledge_manager.add_chapter_summary(
                        self.context.novel_id,
                        1,
                        summary_data
                    )
                    
                    # 3. 分析角色发展
                    character_analysis_input = {
                        "chapter_content": result["chapter_content"],
                        "current_character_states": {},  # 第一章时为空
                        "chapter_number": 1
                    }
                    character_analysis = self.enhanced_character_analyzer.process(character_analysis_input)
                    
                    if character_analysis.get("success") and character_analysis.get("character_changes"):
                        # 4. 更新角色发展轨迹
                        for char_name, changes in character_analysis["character_changes"].items():
                            self.dynamic_knowledge_manager.update_character_evolution(
                                self.context.novel_id,
                                1,
                                char_name,
                                changes
                            )
                    
                    # 5. 更新情节时间线
                    key_events = summary_data.get("key_events", [])
                    if key_events:
                        plot_events = [{"type": "plot", "description": event, "importance": "medium"} 
                                     for event in key_events]
                        self.dynamic_knowledge_manager.update_plot_timeline(
                            self.context.novel_id,
                            1,
                            plot_events
                        )
                    
                    # 6. 更新伏笔追踪
                    new_foreshadowing = summary_data.get("new_foreshadowing", [])
                    if new_foreshadowing:
                        for foreshadowing_content in new_foreshadowing:
                            self.dynamic_knowledge_manager.update_foreshadowing_tracking(
                                self.context.novel_id,
                                1,
                                {
                                    "type": "general",
                                    "content": foreshadowing_content,
                                    "importance": "medium"
                                }
                            )
                    
                    logger.info("[OK] 动态知识库更新完成")
                else:
                    logger.error("[WARN] 章节摘要生成失败，跳过动态知识库更新")
                    
            except Exception as e:
                logger.warning(f"[WARN] 更新动态知识库时出错: {e}，但章节已保存")
            
            self.context.set_current_step("chapter_completed")
            
            # 保存工作流状态
            self.context.save_context()
            
            logger.info("第一章写作完成")
            
            return {
                "status": "success",
                "chapter": result["chapter_content"],
                "quality_assessment": quality_result,
                "next_step": "chapter_completed"
            }
        else:
            return {"error": "章节保存失败"}
    
    def start_novel_continuation(self, novel_id: str, user_requirements: str = "", reset_cache: bool = False) -> Dict[str, Any]:
        """开始小说续写流程"""
        logger.info(f"开始续写小说: {novel_id}, 重置缓存: {reset_cache}")
        
        # 如果用户没有提供需求，从metadata.json中读取原始创作需求
        if not user_requirements:
            logger.info("用户未提供续写需求，从原始创作需求中读取...")
            metadata = self.data_manager._load_novel_metadata(novel_id)
            if metadata and metadata.get("user_requirements"):
                user_requirements = metadata["user_requirements"]
                logger.info(f"成功读取原始创作需求，长度: {len(user_requirements)}")
            else:
                logger.warning("警告：无法读取原始创作需求")
        
        # 根据用户选择决定是否清除缓存
        if reset_cache:
            try:
                logger.info("用户选择重新开始，清除续写缓存数据...")
                clear_result = self.clear_continuation_cache(novel_id)
                if "error" in clear_result:
                    logger.error(f"清除缓存时出现警告: {clear_result['error']}")
            except Exception as e:
                logger.error(f"清除缓存时出现异常: {e}")
        else:
            logger.info("用户选择继续上次进度，保留缓存数据...")
        
        # 尝试加载现有上下文
        context_loaded = self.load_context_by_novel_id(novel_id)
        
        if not context_loaded:
            # 如果没有现有上下文，创建新的
            logger.info("没有找到现有上下文，创建新的续写上下文")
            self.context = WorkflowContext(novel_id)
        else:
            logger.info(f"成功加载现有上下文，当前步骤: {self.context.current_step}")
            
            # 如果已经有续写上下文且用户没有选择重置，检查是否可以继续
            if self.context.is_continuation and not reset_cache:
                # 即使继续上次进度，也要确保user_requirements不为空
                if not self.context.user_requirements and user_requirements:
                    logger.info("更新上下文中的用户需求")
                    self.context.user_requirements = user_requirements
                    self.context.save_context()
                
                logger.info("检测到现有续写进度，继续上次的续写流程")
                return {
                    "success": True,
                    "status": "continued",
                    "message": "继续上次的续写进度",
                    "current_step": self.context.current_step,
                    "next_step": self.context.current_step
                }
        
        # 调用续写智能体查找小说并构建知识库
        try:
            logger.info(f"调用续写智能体处理小说: {novel_id}")
            result = self.novel_continuation_agent.process({
                "novel_id": novel_id,
                "user_requirements": user_requirements
            })
            
            if "error" in result:
                logger.error(f"续写智能体处理失败: {result['error']}")
                return {"success": False, "error": result['error']}
                
        except Exception as e:
            logger.error(f"调用续写智能体时发生异常: {e}")
            return {"success": False, "error": f"调用续写智能体失败: {str(e)}"}
        
        # 设置续写上下文
        if not self.context:
            self.context = WorkflowContext(novel_id)
        
        self.context.set_basic_info(
            result["novel_data"]["novel_info"]["title"], 
            user_requirements
        )
        self.context.set_continuation_mode(
            result["novel_data"], 
            result["knowledge_base"]
        )
        self.context.set_current_step("storyline_generation")
        
        # 保存上下文
        self.save_context()
        
        return {
            "success": True,
            "status": "success",
            "novel_id": novel_id,
            "novel_title": result["novel_data"]["novel_info"]["title"],
            "chapter_count": len(result["novel_data"]["chapters"]),
            "next_step": "storyline_generation"
        }
    
    def generate_continuation_storyline(self, novel_id: str = None, intelligent_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """生成续写故事线"""
        logger.info("开始生成续写故事线...")
        
        # 如果提供了novel_id，确保上下文正确设置
        if novel_id and (not self.context or self.context.novel_id != novel_id):
            # 尝试加载现有上下文
            if not self.load_context_by_novel_id(novel_id):
                return {"error": f"无法加载小说 {novel_id} 的上下文，请先开始续写流程"}
        
        if not self.context or not self.context.is_continuation:
            return {"error": "请先开始续写流程"}
        
        # [NEW] 获取核心知识库（双层知识库的上层）
        core_knowledge = None
        try:
            core_knowledge = self.core_knowledge_manager.get_core_knowledge(self.context.novel_id)
            if core_knowledge:
                logger.info("[OK] 已获取核心知识库（续写故事线生成）")
            else:
                logger.warning("[WARN] 核心知识库不存在，可能还未初始化，继续使用动态知识库")
        except Exception as e:
            logger.warning(f"[WARN] 获取核心知识库时出错: {e}，继续使用动态知识库")
        
        # [NEW] 使用智能上下文选择器（整合核心知识和动态知识）
        if not intelligent_context:
            try:
                # 获取当前章节号（续写章节号）
                current_chapter = len(self.data_manager.get_chapters(self.context.novel_id)) + 1
                intelligent_context = self.intelligent_context_selector.select_context(
                    self.context.novel_id,
                    current_chapter=current_chapter,
                    user_requirements=self.context.user_requirements
                )
                logger.info("[OK] 已获取智能上下文（整合核心知识和动态知识）")
            except Exception as e:
                logger.warning(f"[WARN] 获取智能上下文时出错: {e}，使用原始知识库")
                intelligent_context = None
        
        # [FIX] 构建完整的knowledge_base，包含last_chapter的content_ending
        chapters = self.data_manager.get_chapters(self.context.novel_id)
        last_chapter = chapters[-1] if chapters else {}
        last_chapter_content = last_chapter.get("content", "")
        
        # [NEW] 获取前3章摘要（增加上下文）
        previous_summaries = []
        for i in range(max(0, len(chapters) - 3), len(chapters)):
            if i < len(chapters):
                ch = chapters[i]
                previous_summaries.append({
                    "chapter_number": ch.get("chapter_number", i + 1),
                    "title": ch.get("title", ""),
                    "summary": ch.get("summary", "")
                })
        
        # [NEW] 获取卷摘要（如果有）
        volume_summary = None
        try:
            from core.volume_manager import VolumeManager
            volume_manager = VolumeManager(self.data_manager)
            volume_info = volume_manager.get_volume_info(
                self.context.novel_id, 
                len(chapters) + 1
            )
            # 如果是新卷开始，获取上一卷摘要
            if volume_info["is_volume_start"] and volume_info["volume_number"] > 1:
                volume_summary = volume_manager.load_volume_summary(
                    self.context.novel_id,
                    volume_info["volume_number"] - 1
                )
        except Exception as e:
            logger.warning(f"[WARN] 获取卷摘要失败: {e}")
        
        # 从context获取数据
        characters = self.context.characters or {}
        storyline_data = self.context.storyline or {}
        tags = self.context.tags or {}
        
        # 提取world_setting和story_tone
        overall_storyline = storyline_data.get("overall_storyline", {})
        world_setting = overall_storyline.get("world_setting", "")
        story_tone = overall_storyline.get("tone", "")
        
        # 构建完整的knowledge_base（增强上下文窗口）
        knowledge_base = {
            "novel_info": {
                "title": self.context.title or "未知标题",
                "user_requirements": self.context.user_requirements or ""
            },
            "character_profiles": characters,
            "world_setting": world_setting,
            "story_tone": story_tone,
            "tags": tags,
            "last_chapter_summary": {
                "chapter_number": last_chapter.get("chapter_number", 0),
                "title": last_chapter.get("title", ""),
                "summary": last_chapter.get("summary", ""),
                "key_events": last_chapter.get("key_events", []),
                "foreshadowing": last_chapter.get("foreshadowing", []),
                "next_chapter_hint": last_chapter.get("next_chapter_hint", ""),
                "content_ending": last_chapter_content[-2500:] if last_chapter_content else ""  # [FIX] 从800字增加到2500字
            },
            "previous_summaries": previous_summaries,  # [NEW] 前3章摘要
            "volume_summary": volume_summary,  # [NEW] 卷摘要
            "chapters": chapters,
            "plot_lines": storyline_data
        }
        
        # 调用续写故事线生成智能体
        input_data = {
            "knowledge_base": knowledge_base,  # [FIX] 使用完整的knowledge_base
            "user_requirements": self.context.user_requirements
        }
        
        # [NEW] 添加核心知识库到输入数据
        if core_knowledge:
            input_data["core_knowledge"] = {
                "character_profiles": core_knowledge.get("character_profiles", {}),
                "world_setting": core_knowledge.get("world_setting", {}),
                "story_themes": core_knowledge.get("story_themes", []),
                "basic_rules": core_knowledge.get("basic_rules", {})
            }
            logger.info("[OK] 已将核心知识库添加到输入数据")
        
        # 如果提供了智能上下文，则使用智能上下文替代原始知识库
        if intelligent_context:
            input_data["intelligent_context"] = intelligent_context
            logger.info("[OK] 使用智能上下文进行故事线生成（双层知识库）")
        
        result = self.continuation_storyline_generator.process(input_data)
        
        if "error" in result:
            logger.error(f"续写故事线生成智能体返回错误: {result['error']}")
            return {"success": False, "error": result["error"]}
        
        # 检查返回结果的结构
        if "next_chapter_storyline" not in result:
            logger.info(f"续写故事线生成智能体返回结果缺少next_chapter_storyline字段: {result}")
            return {"success": False, "error": "故事线生成结果格式错误"}
        
        # 检查故事线数据是否有解析错误
        storyline_data = result["next_chapter_storyline"]
        if isinstance(storyline_data, dict) and storyline_data.get("parse_error"):
            logger.error(f"[ERROR] 故事线生成时发生JSON解析错误，原始内容长度: {len(storyline_data.get('content', ''))}")
            return {"success": False, "error": "故事线生成时JSON解析失败，请重试"}
        
        # 验证故事线数据的完整性
        if isinstance(storyline_data, dict):
            required_fields = ["chapter_title", "scene_setting", "plot_points"]
            missing_fields = [field for field in required_fields if field not in storyline_data or not storyline_data[field]]
            if missing_fields:
                logger.error(f"[ERROR] 故事线数据不完整，缺少字段: {missing_fields}")
                return {"success": False, "error": f"故事线数据不完整，缺少: {', '.join(missing_fields)}"}
        
        # 保存故事线到上下文
        self.context.cache_result("next_chapter_storyline", result["next_chapter_storyline"])
        
        # 自动进行质量评估（与正常故事线生成流程保持一致）
        logger.info("开始续写故事线质量评估...")
        quality_result = self.assess_continuation_quality(novel_id, "storyline")
        
        # [NEW] 如果质量不达标，进行一致性改进
        if quality_result.get("success") and quality_result.get("needs_improvement"):
            consistency_assessments = quality_result.get("consistency_assessments", {})
            if consistency_assessments:
                logger.info("开始执行一致性改进...")
                improvement_result = self._perform_consistency_improvements(
                    result["next_chapter_storyline"],
                    consistency_assessments,
                    "storyline",
                    novel_id
                )
                
                if improvement_result.get("improved_content"):
                    # 更新故事线
                    improved_storyline = improvement_result["improved_content"]
                    self.context.cache_result("next_chapter_storyline", improved_storyline)
                    self.data_manager.save_novel_data(self.context.novel_id, "next_chapter_storyline", improved_storyline)
                    result["next_chapter_storyline"] = improved_storyline
                    logger.info("[OK] 故事线已根据一致性评估结果改进")
        
        if quality_result.get("success", False):
            logger.info(f"续写故事线质量评估完成: {quality_result.get('quality_assessment', {}).get('overall_score', '未知')}分")
            # 根据质量评估结果决定下一步（assess_continuation_quality已经设置了current_step）
            next_step = quality_result.get("next_step", "chapter_writing")
        else:
            logger.error(f"续写故事线质量评估失败: {quality_result.get('error', '未知错误')}")
            # 即使质量评估失败，也继续到下一步
            self.context.set_current_step("chapter_writing")
            next_step = "chapter_writing"
        
        # 保存上下文和缓存数据到文件
        self.save_context()
        logger.info(f"已保存上下文，当前步骤: {self.context.current_step}")
        
        return {
            "success": True,
            "status": "success",
            "storyline": result["next_chapter_storyline"],
            "next_step": next_step,
            "quality_assessment": quality_result.get("quality_assessment") if quality_result.get("success") else None
        }
    
    def improve_continuation_storyline(self, novel_id: str = None) -> Dict[str, Any]:
        """改进续写故事线"""
        logger.info("开始改进续写故事线...")
        
        # 如果提供了novel_id，确保上下文正确设置
        if novel_id and (not self.context or self.context.novel_id != novel_id):
            # 尝试加载现有上下文
            if not self.load_context_by_novel_id(novel_id):
                return {"error": f"无法加载小说 {novel_id} 的上下文，请先开始续写流程"}
        
        if not self.context or not self.context.is_continuation:
            return {"error": "请先开始续写流程"}
        
        # 获取当前故事线
        current_storyline = self.context.get_cached_result("next_chapter_storyline")
        if not current_storyline:
            return {"error": "请先生成故事线"}
        
        # 获取质量评估结果（如果没有则使用默认建议）
        quality_assessment = self.context.get_quality_assessment("storyline")
        if not quality_assessment:
            logger.info("没有找到质量评估结果，使用默认改进建议")
            quality_assessment = {"suggestions": ["提升故事线的逻辑性和连贯性", "增强情节的吸引力"]}
        
        # 确保有改进建议
        suggestions = quality_assessment.get("suggestions", [])
        if not suggestions or len(suggestions) == 0:
            logger.info("质量评估结果中没有改进建议，使用默认建议")
            suggestions = ["提升故事线的逻辑性和连贯性", "增强情节的吸引力", "优化人物发展轨迹"]
        
        # 构建改进输入数据
        knowledge_base = self.context.continuation_data["knowledge_base"]
        input_data = {
            "current_storyline": current_storyline,
            "overall_storyline": knowledge_base.get("plot_lines", {}),
            "characters": knowledge_base.get("character_profiles", {}),
            "improvement_suggestions": suggestions,
            "tags": knowledge_base.get("tags", {}),
            "user_requirements": self.context.user_requirements
        }
        
        logger.debug(f"改进输入数据检查:")
        logger.info(f"  - current_storyline: {bool(current_storyline)}")
        logger.info(f"  - improvement_suggestions: {len(suggestions)} 条")
        logger.info(f"  - knowledge_base: {bool(knowledge_base)}")
        logger.info(f"  - user_requirements: {bool(self.context.user_requirements)}")
        
        # 调用续写故事线改进智能体
        result = self.continuation_storyline_improver.process(input_data)
        
        if "error" in result:
            logger.error(f"续写故事线改进智能体返回错误: {result['error']}")
            return {"success": False, "error": result["error"]}
        
        # 检查返回结果的结构
        if "improved_storyline" not in result:
            logger.info(f"续写故事线改进智能体返回结果缺少improved_storyline字段: {result}")
            return {"success": False, "error": "故事线改进结果格式错误"}
        
        # 保存改进后的故事线
        improved_storyline = result.get("improved_storyline", {})
        self.context.cache_result("next_chapter_storyline", improved_storyline)
        
        # 保存到数据管理器（持久化存储）
        self.data_manager.save_novel_data(self.context.novel_id, "next_chapter_storyline", improved_storyline)
        
        # 保存上下文
        self.save_context()
        
        logger.info("续写故事线改进完成")
        
        return {
            "success": True,
            "status": "success",
            "storyline": improved_storyline,
            "improvement_notes": result.get("improvement_notes", []),
            "next_step": "quality_assessment"
        }
    
    def improve_continuation_chapter(self, novel_id: str = None, suggestions: List[str] = None) -> Dict[str, Any]:
        """改进续写章节"""
        logger.info("开始改进续写章节...")
        
        # 如果提供了novel_id，确保上下文正确设置
        if novel_id and (not self.context or self.context.novel_id != novel_id):
            # 尝试加载现有上下文
            if not self.load_context_by_novel_id(novel_id):
                return {"error": f"无法加载小说 {novel_id} 的上下文，请先开始续写流程"}
        
        if not self.context or not self.context.is_continuation:
            return {"error": "请先开始续写流程"}
        
        try:
            # 获取当前续写章节
            continuation_chapter = self.context.get_cached_result("continuation_chapter")
            if not continuation_chapter:
                return {"error": "未找到续写章节数据，请先生成章节"}
            
            # 获取质量评估数据（如果有的话）
            quality_assessment = self.context.get_quality_assessment("chapter")
            if not quality_assessment:
                logger.info("没有找到章节质量评估结果，使用默认改进建议")
                quality_assessment = {"suggestions": suggestions or []}
            
            # 构建改进输入
            knowledge_base = self.context.continuation_data["knowledge_base"]
            improvement_input = {
                "chapter_content": continuation_chapter,
                "quality_assessment": quality_assessment,
                "knowledge_base": {
                    "characters": knowledge_base.get("character_profiles", {}),
                    "storyline": knowledge_base.get("plot_lines", {}),
                    "continuation_storyline": self.context.get_cached_result("next_chapter_storyline"),
                    "tags": knowledge_base.get("tags", {})
                },
                "user_requirements": self.context.user_requirements,
                "suggestions": suggestions or []
            }
            
            # 调用续写章节改进智能体
            improved_result = self.continuation_chapter_improver.process(improvement_input)
            
            if "error" in improved_result:
                return {"error": f"章节改进失败: {improved_result['error']}"}
            
            # 更新上下文中的续写章节
            improved_chapter = improved_result.get("improved_chapter", continuation_chapter)
            self.context.cache_result("continuation_chapter", improved_chapter)
            
            # 保存改进后的章节到数据管理器
            self.data_manager.save_novel_data(
                self.context.novel_id, 
                "continuation_chapter", 
                improved_chapter
            )
            
            logger.info("续写章节改进完成")
            
            return {
                "success": True,
                "status": "success",
                "improved_chapter": improved_chapter,
                "improvement_plan": improved_result.get("improvement_plan", {}),
                "improvement_summary": improved_result.get("improvement_summary", "章节已改进"),
                "next_step": "save_chapter"
            }
            
        except Exception as e:
            logger.info(f"改进续写章节时出错: {e}")
            return {"error": f"改进续写章节失败: {str(e)}"}
    
    def update_continuation_storyline(self, novel_id: str = None, update_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """更新续写故事线"""
        logger.info("开始更新续写故事线...")
        
        # 如果提供了novel_id，确保上下文正确设置
        if novel_id and (not self.context or self.context.novel_id != novel_id):
            # 尝试加载现有上下文
            if not self.load_context_by_novel_id(novel_id):
                return {"error": f"无法加载小说 {novel_id} 的上下文，请先开始续写流程"}
        
        if not self.context or not self.context.is_continuation:
            return {"error": "请先开始续写流程"}
        
        if not update_data:
            return {"error": "没有提供更新数据"}
        
        try:
            # 获取当前的故事线数据
            current_storyline = self.context.get_cached_result("next_chapter_storyline")
            if not current_storyline:
                return {"error": "没有找到续写故事线数据"}
            
            # 更新故事线数据
            updated_storyline = {**current_storyline}
            
            # 处理各种字段的更新
            for field, value in update_data.items():
                if field == "scene_setting" and isinstance(value, dict):
                    # 更新场景设定
                    if not updated_storyline.get("scene_setting"):
                        updated_storyline["scene_setting"] = {}
                    updated_storyline["scene_setting"].update(value)
                elif field in ["plot_points", "key_events", "foreshadowing"] and isinstance(value, str):
                    # 处理列表字段（从字符串转换为列表）
                    lines = [line.strip() for line in value.split('\n') if line.strip()]
                    updated_storyline[field] = lines
                else:
                    # 直接更新其他字段
                    updated_storyline[field] = value
            
            # 保存更新后的故事线到缓存
            self.context.cache_result("next_chapter_storyline", updated_storyline)
            
            # 保存到数据管理器（持久化存储）
            self.data_manager.save_novel_data(self.context.novel_id, "next_chapter_storyline", updated_storyline)
            
            # 保存上下文
            self.save_context()
            
            logger.info("续写故事线更新成功")
            return {
                "status": "success",
                "message": "续写故事线更新成功",
                "storyline": updated_storyline
            }
            
        except Exception as e:
            logger.error(f"更新续写故事线失败: {e}")
            return {"error": f"更新续写故事线失败: {str(e)}"}
    
    def assess_continuation_quality(self, novel_id: str = None, content_type: str = "storyline") -> Dict[str, Any]:
        """评估续写质量"""
        logger.info("开始评估续写质量...")
        
        # 如果提供了novel_id，确保上下文正确设置
        if novel_id and (not self.context or self.context.novel_id != novel_id):
            # 尝试加载现有上下文
            if not self.load_context_by_novel_id(novel_id):
                return {"error": f"无法加载小说 {novel_id} 的上下文，请先开始续写流程"}
        
        if not self.context or not self.context.is_continuation:
            return {"error": "请先开始续写流程"}
        
        # 获取要评估的内容
        if content_type == "storyline":
            content = self.context.get_cached_result("next_chapter_storyline")
        elif content_type == "story":
            content = self.context.get_cached_result("next_chapter_content")
            # 如果缓存中没有内容，尝试从已保存的章节中获取最新的章节
            if not content:
                logger.info("缓存中没有章节内容，尝试从已保存的章节中获取...")
                chapters = self.data_manager.get_chapters(self.context.novel_id)
                if chapters and len(chapters) > 0:
                    # 获取最新的章节（续写章节）
                    latest_chapter = chapters[-1]
                    if latest_chapter.get("chapter_number", 0) > 1:  # 确保是续写章节
                        content = latest_chapter
                        logger.info(f"从已保存的章节中获取到内容: 第{latest_chapter.get('chapter_number')}章")
        else:
            return {"error": "不支持的内容类型"}
        
        if not content:
            return {"error": f"缺少{content_type}内容"}
        
        # [NEW] 构建原始知识库（整合核心知识库和动态知识库）
        original_knowledge_base = self._build_original_knowledge_base(novel_id)
        if not original_knowledge_base:
            # 如果无法构建，使用续写知识库作为备选
            original_knowledge_base = self.context.continuation_data["knowledge_base"]
        
        # 构建续写质量评估输入
        quality_input = {
            "continuation_content": content,
            "original_knowledge_base": original_knowledge_base,  # [NEW] 使用整合后的知识库
            "content_type": content_type,
            "user_requirements": self.context.user_requirements
        }
        
        result = self.continuation_quality_assessor.process(quality_input)
        
        if "error" in result:
            logger.error(f"续写质量评估智能体返回错误: {result['error']}")
            return {"success": False, "error": result["error"]}
        
        self.context.cache_quality_assessment(content_type, result)
        
        # 保存质量评估结果到数据管理器
        # 统一命名：story -> chapter, storyline -> storyline
        if content_type == "story":
            data_key = "continuation_chapter_quality_assessment"
        else:
            data_key = f"continuation_{content_type}_quality_assessment"
        self.data_manager.save_novel_data(self.context.novel_id, data_key, result)
        
        # [NEW] 如果通用质量评估不通过，进行专项一致性评估
        consistency_assessments = {}
        needs_improvement = False
        
        if not result.get("is_high_quality", False) or result.get("overall_score", 100) < 80:
            logger.info("通用质量评估未通过，开始专项一致性评估...")
            consistency_assessments = self._perform_consistency_assessments(
                content, content_type, novel_id
            )
            
            # 检查是否有需要改进的问题
            needs_improvement = self._check_consistency_issues(consistency_assessments)
            
            if needs_improvement:
                logger.info("检测到一致性问题，将进行自动改进")
            else:
                logger.info("专项一致性评估通过，无需改进")
        
        # 根据评估结果决定下一步
        if result.get("is_high_quality", False) and not needs_improvement:
            if content_type == "storyline":
                self.context.set_current_step("chapter_writing")
                next_step = "chapter_writing"
            else:
                self.context.set_current_step("chapter_save")
                next_step = "chapter_save"
        else:
            if content_type == "storyline":
                self.context.set_current_step("storyline_improvement")
                next_step = "storyline_improvement"
            else:
                self.context.set_current_step("content_improvement")
                next_step = "content_improvement"
        
        # 保存上下文，确保步骤变更被持久化
        self.save_context()
        logger.info(f"质量评估完成，已保存上下文，当前步骤: {self.context.current_step}")
        
        return {
            "success": True,
            "status": "success",
            "quality_assessment": result,
            "consistency_assessments": consistency_assessments,  # [NEW] 添加一致性评估结果
            "needs_improvement": needs_improvement,  # [NEW] 添加是否需要改进标志
            "next_step": next_step
        }
    
    def write_continuation_chapter(self, novel_id: str = None) -> Dict[str, Any]:
        """写作续写章节"""
        logger.info("开始写作续写章节...")
        
        # 如果提供了novel_id，确保上下文正确设置
        if novel_id and (not self.context or self.context.novel_id != novel_id):
            # 尝试加载现有上下文
            if not self.load_context_by_novel_id(novel_id):
                return {"error": f"无法加载小说 {novel_id} 的上下文，请先开始续写流程"}
        
        if not self.context or not self.context.is_continuation:
            return {"error": "请先开始续写流程"}
        
        storyline = self.context.get_cached_result("next_chapter_storyline")
        if not storyline:
            return {"error": "请先生成故事线"}
        
        # [OPTIMIZED] 检查是否使用长上下文模式
        use_long_context = getattr(config, 'USE_LONG_CONTEXT_MODE', False)
        
        if use_long_context:
            logger.info("[OPTIMIZED] 使用长上下文模式生成章节")
            return self._write_continuation_chapter_long_context(storyline)
        
        # [LEGACY] 传统模式
        return self._write_continuation_chapter_legacy(storyline)
    
    def _write_continuation_chapter_long_context(self, storyline: Dict[str, Any]) -> Dict[str, Any]:
        """[OPTIMIZED] 长上下文模式写作续写章节"""
        logger.info("使用长上下文模式写作续写章节...")
        
        # 获取当前章节号
        current_chapter = len(self.data_manager.get_chapters(self.context.novel_id)) + 1
        
        # 使用长上下文选择器
        try:
            long_context = self.intelligent_context_selector.select_context_long_context(
                self.context.novel_id,
                current_chapter=current_chapter,
                user_requirements=self.context.user_requirements,
                recent_chapters_count=getattr(config, 'LONG_CONTEXT_RECENT_CHAPTERS', 10)
            )
            logger.info(f"[OK] 已构建长上下文（包含最近{getattr(config, 'LONG_CONTEXT_RECENT_CHAPTERS', 10)}章原文）")
        except Exception as e:
            logger.warning(f"[WARN] 构建长上下文失败: {e}，降级到传统模式")
            return self._write_continuation_chapter_legacy(storyline)
        
        # 调用长上下文模式的续写章节写作智能体
        input_data = {
            "long_context": long_context,
            "storyline": storyline,
            "user_requirements": self.context.user_requirements
        }
        
        result = self.continuation_chapter_writer.process_long_context(input_data)
        
        if "error" in result:
            logger.error(f"续写章节写作智能体返回错误: {result['error']}")
            return {"success": False, "error": result["error"]}
        
        # 检查返回结果的结构
        if "chapter_content" not in result:
            logger.info(f"续写章节写作智能体返回结果缺少chapter_content字段: {result}")
            return {"success": False, "error": "章节写作结果格式错误"}
        
        # 检查章节内容是否为空
        chapter_content = result["chapter_content"]
        if not chapter_content or not chapter_content.get("content"):
            logger.info(f"章节内容为空: {chapter_content}")
            return {"success": False, "error": "章节内容为空"}

        # [NEW] 质量验证
        core_knowledge = None
        try:
            core_knowledge = self.core_knowledge_manager.get_core_knowledge(self.context.novel_id)
        except:
            pass

        protagonist_name = "沈夜"
        if core_knowledge and "main_character" in core_knowledge:
            protagonist_name = core_knowledge["main_character"].get("basic_info", {}).get("name", "沈夜")

        validation_result = self.quality_validator.validate_chapter(
            chapter_content,
            {
                "word_count_range": (3000, 5000),
                "protagonist_name": protagonist_name
            }
        )

        if not validation_result["passed"]:
            logger.warning(f"⚠️ 章节质量验证失败: {validation_result['errors']}")
            # 验证失败，记录但继续保存（不阻塞生成流程）

        logger.info(f"✅ 章节质量验证: passed={validation_result['passed']}")

        # 保存章节内容到上下文
        self.context.cache_result("next_chapter_content", result["chapter_content"])
        
        # 长上下文模式下跳过复杂的一致性评估，直接保存
        self.context.set_current_step("chapter_save")
        
        # 保存上下文和缓存数据到文件
        self.save_context()
        logger.info(f"已保存上下文，当前步骤: {self.context.current_step}")
        
        return {
            "success": True,
            "status": "success",
            "chapter_content": result["chapter_content"],
            "word_count": result["word_count"],
            "writing_quality": result.get("writing_quality", {}),
            "current_step": "chapter_save",
            "next_step": "chapter_save"
        }
    
    def _write_continuation_chapter_legacy(self, storyline: Dict[str, Any]) -> Dict[str, Any]:
        """[LEGACY] 传统模式写作续写章节"""
        
        # [NEW] 获取核心知识库（双层知识库的上层）
        core_knowledge = None
        try:
            core_knowledge = self.core_knowledge_manager.get_core_knowledge(self.context.novel_id)
            if core_knowledge:
                logger.info("[OK] 已获取核心知识库（续写章节写作）")
            else:
                logger.warning("[WARN] 核心知识库不存在，可能还未初始化，继续使用动态知识库")
        except Exception as e:
            logger.warning(f"[WARN] 获取核心知识库时出错: {e}，继续使用动态知识库")
        
        # [NEW] 使用智能上下文选择器（整合核心知识和动态知识）
        try:
            # 获取当前章节号（续写章节号）
            current_chapter = len(self.data_manager.get_chapters(self.context.novel_id)) + 1
            intelligent_context = self.intelligent_context_selector.select_context(
                self.context.novel_id,
                current_chapter=current_chapter,
                user_requirements=self.context.user_requirements
            )
            logger.info("[OK] 已获取智能上下文（整合核心知识和动态知识）")
        except Exception as e:
            logger.warning(f"[WARN] 获取智能上下文时出错: {e}，使用原始知识库")
            intelligent_context = None
        
        # [FIX] 构建完整的knowledge_base，包含所有必要字段
        chapters = self.data_manager.get_chapters(self.context.novel_id)
        last_chapter = chapters[-1] if chapters else {}
        
        # [NEW] 获取前3章摘要（增加上下文）
        previous_summaries = []
        for i in range(max(0, len(chapters) - 3), len(chapters)):
            if i < len(chapters):
                ch = chapters[i]
                previous_summaries.append({
                    "chapter_number": ch.get("chapter_number", i + 1),
                    "title": ch.get("title", ""),
                    "summary": ch.get("summary", "")
                })
        
        # [NEW] 获取卷摘要（如果有）
        volume_summary = None
        try:
            from core.volume_manager import VolumeManager
            volume_manager = VolumeManager(self.data_manager)
            volume_info = volume_manager.get_volume_info(
                self.context.novel_id, 
                len(chapters) + 1
            )
            # 如果是新卷开始，获取上一卷摘要
            if volume_info["is_volume_start"] and volume_info["volume_number"] > 1:
                volume_summary = volume_manager.load_volume_summary(
                    self.context.novel_id,
                    volume_info["volume_number"] - 1
                )
        except Exception as e:
            logger.warning(f"[WARN] 获取卷摘要失败: {e}")
        
        # 从context获取数据
        characters = self.context.characters or {}
        storyline_data = self.context.storyline or {}
        tags = self.context.tags or {}
        
        # 提取world_setting和story_tone
        overall_storyline = storyline_data.get("overall_storyline", {})
        world_setting = overall_storyline.get("world_setting", "")
        story_tone = overall_storyline.get("tone", "")
        
        # 构建上一章结尾（取最后2500字，增加上下文窗口）
        last_chapter_content = last_chapter.get("content", "")
        last_chapter_ending = last_chapter_content[-2500:] if last_chapter_content else ""
        
        # 构建完整的knowledge_base（增强上下文窗口）
        knowledge_base = {
            "novel_info": {
                "title": self.context.title or "未知标题",
                "user_requirements": self.context.user_requirements or ""
            },
            "character_profiles": characters,
            "world_setting": world_setting,
            "story_tone": story_tone,
            "tags": tags,
            "last_chapter_summary": {
                "chapter_number": last_chapter.get("chapter_number", 0),
                "title": last_chapter.get("title", ""),
                "summary": last_chapter.get("summary", ""),
                "key_events": last_chapter.get("key_events", []),
                "foreshadowing": last_chapter.get("foreshadowing", []),
                "next_chapter_hint": last_chapter.get("next_chapter_hint", ""),
                "content_ending": last_chapter_ending  # [FIX] 从800字增加到2500字
            },
            "previous_summaries": previous_summaries,  # [NEW] 前3章摘要
            "volume_summary": volume_summary,  # [NEW] 卷摘要
            "chapters": chapters,
            # 从continuation_data获取其他字段
            "character_profiles": self.context.continuation_data.get("knowledge_base", {}).get("character_profiles", characters),
            "plot_lines": self.context.continuation_data.get("knowledge_base", {}).get("plot_lines", storyline_data)
        }
        
        # 调用续写章节写作智能体
        input_data = {
            "storyline": storyline,
            "knowledge_base": knowledge_base,  # [FIX] 使用完整的knowledge_base
            "user_requirements": self.context.user_requirements
        }
        
        # [NEW] 添加核心知识库到输入数据
        if core_knowledge:
            input_data["core_knowledge"] = {
                "character_profiles": core_knowledge.get("character_profiles", {}),
                "world_setting": core_knowledge.get("world_setting", {}),
                "story_themes": core_knowledge.get("story_themes", []),
                "basic_rules": core_knowledge.get("basic_rules", {})
            }
            logger.info("[OK] 已将核心知识库添加到输入数据")
        
        # [NEW] 添加智能上下文到输入数据
        if intelligent_context:
            input_data["intelligent_context"] = intelligent_context
            logger.info("[OK] 已将智能上下文添加到输入数据（双层知识库）")
        
        result = self.continuation_chapter_writer.process(input_data)
        
        if "error" in result:
            logger.error(f"续写章节写作智能体返回错误: {result['error']}")
            return {"success": False, "error": result["error"]}
        
        # 检查返回结果的结构
        if "chapter_content" not in result:
            logger.info(f"续写章节写作智能体返回结果缺少chapter_content字段: {result}")
            return {"success": False, "error": "章节写作结果格式错误"}
        
        # 检查章节内容是否为空
        chapter_content = result["chapter_content"]
        if not chapter_content or not chapter_content.get("content"):
            logger.info(f"章节内容为空: {chapter_content}")
            return {"success": False, "error": "章节内容为空"}
        
        # 保存章节内容到上下文
        self.context.cache_result("next_chapter_content", result["chapter_content"])
        
        # 自动进行章节质量评估（与续写故事线生成流程保持一致）
        logger.info("开始续写章节质量评估...")
        quality_result = self.assess_continuation_quality(novel_id, "story")
        
        # [NEW] 如果质量不达标，进行一致性改进
        if quality_result.get("success") and quality_result.get("needs_improvement"):
            consistency_assessments = quality_result.get("consistency_assessments", {})
            if consistency_assessments:
                logger.info("开始执行一致性改进...")
                improvement_result = self._perform_consistency_improvements(
                    result["chapter_content"],
                    consistency_assessments,
                    "story",
                    novel_id
                )
                
                if improvement_result.get("improved_content"):
                    # 更新章节内容
                    improved_chapter = improvement_result["improved_content"]
                    self.context.cache_result("next_chapter_content", improved_chapter)
                    result["chapter_content"] = improved_chapter
                    logger.info("[OK] 章节已根据一致性评估结果改进")
        
        if quality_result.get("success", False):
            logger.info(f"续写章节质量评估完成: {quality_result.get('quality_assessment', {}).get('overall_score', '未知')}分")
            # 根据质量评估结果决定下一步（assess_continuation_quality已经设置了current_step）
            next_step = quality_result.get("next_step", "chapter_save")
        else:
            logger.error(f"续写章节质量评估失败: {quality_result.get('error', '未知错误')}")
            # 即使质量评估失败，也继续到下一步
            self.context.set_current_step("chapter_save")
            next_step = "chapter_save"
        
        # 保存上下文和缓存数据到文件
        self.save_context()
        logger.info(f"已保存上下文，当前步骤: {self.context.current_step}")
        
        return {
            "success": True,
            "status": "success",
            "chapter_content": result["chapter_content"],
            "word_count": result["word_count"],
            "writing_quality": result["writing_quality"],
            "next_step": next_step,
            "quality_assessment": quality_result.get("quality_assessment") if quality_result.get("success") else None
        }
    
    def save_continuation_chapter(self, novel_id: str = None) -> Dict[str, Any]:
        """保存续写章节"""
        logger.info("开始保存续写章节...")
        
        # 如果提供了novel_id，确保上下文正确设置
        if novel_id and (not self.context or self.context.novel_id != novel_id):
            # 尝试加载现有上下文
            if not self.load_context_by_novel_id(novel_id):
                return {"error": f"无法加载小说 {novel_id} 的上下文，请先开始续写流程"}
        
        if not self.context or not self.context.is_continuation:
            return {"error": "请先开始续写流程"}
        
        chapter_content = self.context.get_cached_result("next_chapter_content")
        if not chapter_content:
            return {"error": "请先写作章节内容"}
        
        # 获取当前章节号 - 修复：使用文件系统章节数而不是上下文数据
        current_chapter_number = len(self.data_manager.get_novel_chapters(novel_id)) + 1
        
        # 提取纯文本内容
        raw_content = chapter_content.get("content", "")
        clean_content = self._extract_clean_content(raw_content)
        
        # 保存章节（包含所有字段）
        chapter_data = {
            "chapter_number": current_chapter_number,
            "title": chapter_content.get("title", f"第{current_chapter_number}章"),
            "content": clean_content,  # 使用清理后的纯文本内容
            "summary": chapter_content.get("summary", ""),
            "key_events": chapter_content.get("key_events", []),
            "character_development": chapter_content.get("character_development", ""),
            "foreshadowing": chapter_content.get("foreshadowing", []),
            "next_chapter_hint": chapter_content.get("next_chapter_hint", ""),
            "consistency_notes": chapter_content.get("consistency_notes", ""),
            "created_at": datetime.now().isoformat(),
            "word_count": len(clean_content)
        }
        
        # 验证章节字数 [BUG FIX]
        word_count = len(clean_content)
        MIN_WORD_COUNT = 2500
        if word_count < MIN_WORD_COUNT:
            logger.warning(f"⚠️ 第{current_chapter_number}章字数不足 ({word_count} < {MIN_WORD_COUNT})，将跳过保存")
            return {"success": False, "error": f"章节字数不足 ({word_count}/{MIN_WORD_COUNT})"}

        success = self.data_manager.save_chapter(self.context.novel_id, current_chapter_number, chapter_data)

        if success:
            # 验证章节字数（已通过上面的检查）
            pass
            
            # [NEW] 章节保存后，更新动态知识库和向量数据库（双层知识库的下层）
            try:
                logger.info(f"开始更新动态知识库和向量数据库（第{current_chapter_number}章）...")

                # [NEW] 将章节内容添加到向量数据库
                try:
                    chapter_text = chapter_data.get("content", "")
                    if chapter_text:
                        chapter_id = f"chapter_{current_chapter_number}"
                        vector_added = self.vector_database.add_vector(
                            self.context.novel_id,
                            chapter_id,
                            chapter_text,
                            metadata={
                                "chapter_number": current_chapter_number,
                                "title": chapter_data.get("title", ""),
                                "type": "chapter"
                            }
                        )
                        if vector_added:
                            logger.info(f"[OK] 已将第{current_chapter_number}章内容添加到向量数据库")
                        else:
                            logger.warning(f"[WARN] 第{current_chapter_number}章向量添加失败（嵌入服务不可用）")
                except Exception as e:
                    logger.error(f"[WARN] 添加章节到向量数据库失败: {e}")
                
                # 获取智能上下文（用于章节摘要生成）
                try:
                    intelligent_context = self.intelligent_context_selector.select_context(
                        self.context.novel_id,
                        current_chapter=current_chapter_number,
                        user_requirements=self.context.user_requirements
                    )
                except Exception as e:
                    logger.warning(f"[WARN] 获取智能上下文时出错: {e}，使用默认上下文")
                    intelligent_context = {"narrative_phase": {}}
                
                # 1. 生成章节摘要
                chapter_summary_input = {
                    "chapter_content": chapter_data,
                    "chapter_number": current_chapter_number,
                    "novel_context": intelligent_context.get("narrative_phase", {}),
                    "previous_summaries": self.dynamic_knowledge_manager.get_recent_summaries(
                        self.context.novel_id, 3
                    ) if hasattr(self.dynamic_knowledge_manager, 'get_recent_summaries') else []
                }
                summary_result = self.chapter_summary_generator.process(chapter_summary_input)
                
                if summary_result.get("success") and summary_result.get("summary_data"):
                    summary_data = summary_result["summary_data"]
                    
                    # 2. 添加章节摘要到动态知识库
                    self.dynamic_knowledge_manager.add_chapter_summary(
                        self.context.novel_id,
                        current_chapter_number,
                        summary_data
                    )
                    
                    # 3. 分析角色发展
                    # 获取核心知识库中的角色列表
                    core_knowledge = self.core_knowledge_manager.get_core_knowledge(self.context.novel_id)
                    character_names = []
                    if core_knowledge:
                        main_char = core_knowledge.get("character_profiles", {}).get("main_character", {})
                        if main_char.get("name"):
                            character_names.append(main_char["name"])
                        supporting_chars = core_knowledge.get("character_profiles", {}).get("supporting_characters", [])
                        for char in supporting_chars:
                            if char.get("name"):
                                character_names.append(char["name"])
                    
                    # 获取所有角色的当前状态
                    current_character_states = {}
                    if hasattr(self.dynamic_knowledge_manager, 'get_character_current_state'):
                        for char_name in character_names:
                            state = self.dynamic_knowledge_manager.get_character_current_state(
                                self.context.novel_id,
                                char_name,
                                current_chapter_number - 1
                            )
                            if state:
                                current_character_states[char_name] = state
                    
                    character_analysis_input = {
                        "chapter_content": chapter_data,
                        "current_character_states": current_character_states,
                        "chapter_number": current_chapter_number
                    }
                    character_analysis = self.enhanced_character_analyzer.process(character_analysis_input)
                    
                    if character_analysis.get("success") and character_analysis.get("character_changes"):
                        # 4. 更新角色发展轨迹
                        for char_name, changes in character_analysis["character_changes"].items():
                            self.dynamic_knowledge_manager.update_character_evolution(
                                self.context.novel_id,
                                current_chapter_number,
                                char_name,
                                changes
                            )
                    
                    # 5. 更新情节时间线
                    key_events = summary_data.get("key_events", [])
                    if key_events:
                        plot_events = [{"type": "plot", "description": event, "importance": "medium"} 
                                     for event in key_events]
                        self.dynamic_knowledge_manager.update_plot_timeline(
                            self.context.novel_id,
                            current_chapter_number,
                            plot_events
                        )
                    
                    # 6. 更新伏笔追踪
                    new_foreshadowing = summary_data.get("new_foreshadowing", [])
                    if new_foreshadowing:
                        for foreshadowing_content in new_foreshadowing:
                            self.dynamic_knowledge_manager.update_foreshadowing_tracking(
                                self.context.novel_id,
                                current_chapter_number,
                                {
                                    "type": "general",
                                    "content": foreshadowing_content,
                                    "importance": "medium"
                                }
                            )
                    
                    logger.info(f"[OK] 动态知识库更新完成（第{current_chapter_number}章）")
                else:
                    logger.error(f"[WARN] 章节摘要生成失败，跳过动态知识库更新")
                    
            except Exception as e:
                logger.warning(f"[WARN] 更新动态知识库时出错: {e}，但章节已保存")
            
            # [NEW] 使用整合知识系统更新所有知识图谱模块
            if self.integrated_knowledge:
                try:
                    logger.info(f"开始更新整合知识系统（第{current_chapter_number}章）...")
                    update_success = self.integrated_knowledge.update_knowledge_after_chapter(
                        self.context.novel_id,
                        current_chapter_number,
                        chapter_data
                    )
                    if update_success:
                        logger.info(f"[OK] 整合知识系统更新完成（第{current_chapter_number}章）")
                    else:
                        logger.warning(f"[WARN] 整合知识系统部分更新失败")
                except Exception as e:
                    logger.error(f"[WARN] 更新整合知识系统时出错: {e}")
            
            # 清除相关缓存，避免状态检测错误
            if "next_chapter_storyline" in self.context._cache:
                del self.context._cache["next_chapter_storyline"]
            if "next_chapter_content" in self.context._cache:
                del self.context._cache["next_chapter_content"]
            
            # 修复：更新上下文中的章节数据
            if self.context.continuation_data and "novel_data" in self.context.continuation_data:
                # 重新加载最新的章节数据
                latest_chapters = self.data_manager.get_novel_chapters(novel_id)
                self.context.continuation_data["novel_data"]["chapters"] = latest_chapters
                logger.info(f"上下文章节数据已更新，当前章节数: {len(latest_chapters)}")
            
            self.context.set_current_step("chapter_completed")
            self.save_context()  # 保存上下文以清除缓存
            
            # 检查字数并返回相应的状态
            if word_count < MIN_WORD_COUNT:
                logger.warning(f"[WARN] 警告：章节字数({word_count})少于推荐值({MIN_WORD_COUNT})")
                return {
                    "success": True,
                    "status": "warning",
                    "chapter_number": current_chapter_number,
                    "chapter_title": chapter_data["title"],
                    "word_count": word_count,
                    "message": f"章节保存成功，但字数({word_count})偏少，建议重新生成",
                    "warning": f"章节字数({word_count})少于推荐值({MIN_WORD_COUNT})"
                }
            else:
                return {
                    "success": True,
                    "status": "success",
                    "chapter_number": current_chapter_number,
                    "chapter_title": chapter_data["title"],
                    "word_count": word_count,
                    "message": "章节保存成功"
                }
        else:
            return {"error": "章节保存失败"}
    
    def _perform_consistency_assessments(self, content: Dict[str, Any], 
                                       content_type: str, novel_id: str = None) -> Dict[str, Any]:
        """
        执行所有专项一致性评估
        
        Args:
            content: 要评估的内容（章节或故事线）
            content_type: 内容类型（"story" 或 "storyline"）
            novel_id: 小说ID
            
        Returns:
            所有评估结果的字典
        """
        assessments = {}
        
        # 获取原始知识库（整合核心知识库和动态知识库）
        original_knowledge_base = self._build_original_knowledge_base(novel_id)
        
        if not original_knowledge_base:
            logger.warning("[WARN] 无法构建原始知识库，跳过专项一致性评估")
            return assessments
        
        # 准备评估输入数据
        base_input = {
            "continuation_content": content,
            "original_knowledge_base": original_knowledge_base,
            "content_type": content_type
        }
        
        # [NEW] 检查缓存
        cache_key = self.cache_manager.get_cache_key({
            "content": content,
            "knowledge_base": original_knowledge_base,
            "content_type": content_type,
            "type": "consistency_assessments"
        })
        cached_assessments = self.cache_manager.get_assessment_cache(cache_key)
        if cached_assessments:
            logger.info("[OK] 从缓存获取一致性评估结果")
            return cached_assessments
        
        # [NEW] 记录性能监控
        import time
        start_time = time.time()
        
        # 执行6个专项评估
        assessors = [
            ("character", self.continuation_character_consistency_assessor),
            ("plot_logic", self.continuation_plot_logic_assessor),
            ("world", self.continuation_world_consistency_assessor),
            ("style", self.continuation_style_consistency_assessor),
            ("reader_experience", self.continuation_reader_experience_assessor),
            ("long_term", self.continuation_long_term_consistency_assessor)
        ]
        
        logger.info(f"开始执行{len(assessors)}个专项一致性评估（并行处理）...")
        
        # [NEW] 使用并行处理
        try:
            # 创建评估任务
            assessment_tasks = []
            for assessment_type, assessor in assessors:
                task = {
                    "task_id": assessment_type,
                    "assessor": assessor,
                    "assessor_type": assessment_type,
                    "input_data": base_input,
                    "start_time": time.time()
                }
                assessment_tasks.append(task)
            
            # 并行执行评估
            parallel_result = self.parallel_processor.execute_parallel_assessment(assessment_tasks)
            
            if parallel_result.get("status") == "success":
                # 处理并行执行结果
                for task_id, task_result in parallel_result.get("results", {}).items():
                    if "error" in task_result:
                        assessments[task_id] = {
                            "error": task_result.get("error"),
                            "overall_score": 0,
                            "is_high_quality": False
                        }
                        logger.error(f"  [WARN] {task_id}一致性评估失败: {task_result.get('error')}")
                    else:
                        result = task_result.get("result", {})
                        assessments[task_id] = result
                        score = result.get("overall_score", 0)
                        exec_time = task_result.get("execution_time", 0)
                        logger.info(f"  [OK] {task_id}一致性评估完成: {score}分 (耗时: {exec_time:.2f}秒)")
            else:
                # 并行处理失败，回退到串行处理
                logger.error("[WARN] 并行处理失败，回退到串行处理...")
                for assessment_type, assessor in assessors:
                    try:
                        logger.info(f"  评估中: {assessment_type}一致性...")
                        assessment_result = assessor.process(base_input)
                        
                        if "error" not in assessment_result:
                            assessments[assessment_type] = assessment_result
                            score = assessment_result.get("overall_score", 0)
                            logger.info(f"  [OK] {assessment_type}一致性评估完成: {score}分")
                        else:
                            logger.error(f"  [WARN] {assessment_type}一致性评估失败: {assessment_result.get('error')}")
                            assessments[assessment_type] = {
                                "error": assessment_result.get("error"),
                                "overall_score": 0,
                                "is_high_quality": False
                            }
                    except Exception as e:
                        logger.error(f"  [ERROR] {assessment_type}一致性评估异常: {e}")
                        assessments[assessment_type] = {
                            "error": str(e),
                            "overall_score": 0,
                            "is_high_quality": False
                        }
        except Exception as e:
            logger.error(f"[WARN] 并行处理异常: {e}，回退到串行处理...")
            # 回退到串行处理
            for assessment_type, assessor in assessors:
                try:
                    logger.info(f"  评估中: {assessment_type}一致性...")
                    assessment_result = assessor.process(base_input)
                    
                    if "error" not in assessment_result:
                        assessments[assessment_type] = assessment_result
                        score = assessment_result.get("overall_score", 0)
                        logger.info(f"  [OK] {assessment_type}一致性评估完成: {score}分")
                    else:
                        logger.error(f"  [WARN] {assessment_type}一致性评估失败: {assessment_result.get('error')}")
                        assessments[assessment_type] = {
                            "error": assessment_result.get("error"),
                            "overall_score": 0,
                            "is_high_quality": False
                        }
                except Exception as ex:
                    logger.error(f"  [ERROR] {assessment_type}一致性评估异常: {ex}")
                    assessments[assessment_type] = {
                        "error": str(ex),
                        "overall_score": 0,
                        "is_high_quality": False
                    }
        
        # [NEW] 记录性能监控
        execution_time = time.time() - start_time
        if hasattr(self.performance_monitor, 'record_task_execution'):
            self.performance_monitor.record_task_execution("consistency_assessments", execution_time, success=True)
        logger.info(f"专项一致性评估完成，共{len(assessments)}项，总耗时: {execution_time:.2f}秒")
        
        # [NEW] 保存缓存
        if assessments:
            self.cache_manager.set_assessment_cache(cache_key, assessments, ttl=3600)
        
        return assessments
    
    def _check_consistency_issues(self, consistency_assessments: Dict[str, Any]) -> bool:
        """
        检查一致性评估结果，判断是否需要改进
        
        Args:
            consistency_assessments: 一致性评估结果字典
            
        Returns:
            是否需要改进
        """
        if not consistency_assessments:
            return False
        
        # 检查每个评估结果
        for assessment_type, assessment_result in consistency_assessments.items():
            if "error" in assessment_result:
                continue  # 跳过有错误的评估
            
            overall_score = assessment_result.get("overall_score", 100)
            is_high_quality = assessment_result.get("is_high_quality", True)
            
            # 如果总分低于80或标记为低质量，需要改进
            if overall_score < 80 or not is_high_quality:
                logger.warning(f"  [WARN] {assessment_type}一致性需要改进 (分数: {overall_score})")
                return True
        
        return False
    
    def _perform_consistency_improvements(self, content: Dict[str, Any], 
                                         consistency_assessments: Dict[str, Any],
                                         content_type: str, novel_id: str = None) -> Dict[str, Any]:
        """
        执行一致性改进
        
        Args:
            content: 需要改进的内容
            consistency_assessments: 一致性评估结果
            content_type: 内容类型（"story" 或 "storyline"）
            novel_id: 小说ID
            
        Returns:
            改进后的内容和改进摘要
        """
        improved_content = content.copy()
        improvement_summary = {}
        
        # 获取知识库
        knowledge_base = self._build_original_knowledge_base(novel_id)
        
        if not knowledge_base:
            logger.warning("[WARN] 无法构建知识库，跳过一致性改进")
            return {
                "improved_content": improved_content,
                "improvement_summary": improvement_summary
            }
        
        # 准备改进输入数据
        base_input = {
            "continuation_content": improved_content,
            "knowledge_base": knowledge_base,
            "user_requirements": self.context.user_requirements if self.context else ""
        }
        
        # 改进器映射
        improvers = [
            ("character", self.continuation_character_consistency_improver),
            ("plot_logic", self.continuation_plot_logic_improver),
            ("world", self.continuation_world_consistency_improver),
            ("style", self.continuation_style_consistency_improver),
            ("reader_experience", self.continuation_reader_experience_improver),
            ("long_term", self.continuation_long_term_consistency_improver)
        ]
        
        # [NEW] 记录性能监控
        import time
        start_time = time.time()
        
        logger.info(f"开始执行一致性改进（并行处理）...")
        
        # [NEW] 收集需要改进的任务
        improvement_tasks = []
        for improvement_type, improver in improvers:
            # 检查对应的评估结果
            assessment = consistency_assessments.get(improvement_type, {})
            
            if "error" in assessment:
                continue  # 跳过有错误的评估对应的改进
            
            overall_score = assessment.get("overall_score", 100)
            is_high_quality = assessment.get("is_high_quality", True)
            
            # 如果不需要改进，跳过
            if overall_score >= 80 and is_high_quality:
                continue
            
            # 构建改进输入
            improvement_input = {
                **base_input,
                "quality_assessment": assessment
            }
            
            task = {
                "task_id": improvement_type,
                "improver": improver,
                "improver_type": improvement_type,
                "input_data": improvement_input,
                "start_time": time.time(),
                "content_type": content_type
            }
            improvement_tasks.append(task)
        
        if not improvement_tasks:
            logger.info("无需改进，所有一致性评估都通过")
            return {
                "improved_content": improved_content,
                "improvement_summary": improvement_summary
            }
        
        # [NEW] 使用并行处理
        try:
            # 并行执行改进
            parallel_result = self.parallel_processor.execute_parallel_improvement(improvement_tasks)
            
            if parallel_result.get("status") == "success":
                # 处理并行执行结果
                for task_id, task_result in parallel_result.get("results", {}).items():
                    if "error" in task_result:
                        improvement_summary[task_id] = {
                            "improved": False,
                            "error": task_result.get("error")
                        }
                        logger.error(f"  [WARN] {task_id}一致性改进失败: {task_result.get('error')}")
                    else:
                        result = task_result.get("result", {})
                        
                        # 更新改进后的内容
                        if content_type == "story":
                            if "improved_chapter" in result:
                                improved_content = result["improved_chapter"]
                        elif content_type == "storyline":
                            if "improved_storyline" in result:
                                improved_content = result["improved_storyline"]
                        
                        improvement_summary[task_id] = {
                            "improved": True,
                            "summary": result.get("improvement_summary", "")
                        }
                        exec_time = task_result.get("execution_time", 0)
                        logger.info(f"  [OK] {task_id}一致性改进完成 (耗时: {exec_time:.2f}秒)")
            else:
                # 并行处理失败，回退到串行处理
                logger.error("[WARN] 并行处理失败，回退到串行处理...")
                for task in improvement_tasks:
                    improvement_type = task["task_id"]
                    improver = task["improver"]
                    improvement_input = task["input_data"]
                    
                    try:
                        logger.info(f"  改进中: {improvement_type}一致性...")
                        improvement_result = improver.process(improvement_input)
                        
                        if "error" not in improvement_result:
                            # 更新改进后的内容
                            if content_type == "story":
                                if "improved_chapter" in improvement_result:
                                    improved_content = improvement_result["improved_chapter"]
                            elif content_type == "storyline":
                                if "improved_storyline" in improvement_result:
                                    improved_content = improvement_result["improved_storyline"]
                            
                            improvement_summary[improvement_type] = {
                                "improved": True,
                                "summary": improvement_result.get("improvement_summary", "")
                            }
                            logger.info(f"  [OK] {improvement_type}一致性改进完成")
                        else:
                            logger.error(f"  [WARN] {improvement_type}一致性改进失败: {improvement_result.get('error')}")
                            improvement_summary[improvement_type] = {
                                "improved": False,
                                "error": improvement_result.get("error")
                            }
                    except Exception as e:
                        logger.error(f"  [ERROR] {improvement_type}一致性改进异常: {e}")
                        improvement_summary[improvement_type] = {
                            "improved": False,
                            "error": str(e)
                        }
        except Exception as e:
            logger.error(f"[WARN] 并行处理异常: {e}，回退到串行处理...")
            # 回退到串行处理
            for task in improvement_tasks:
                improvement_type = task["task_id"]
                improver = task["improver"]
                improvement_input = task["input_data"]
                
                try:
                    logger.info(f"  改进中: {improvement_type}一致性...")
                    improvement_result = improver.process(improvement_input)
                    
                    if "error" not in improvement_result:
                        # 更新改进后的内容
                        if content_type == "story":
                            if "improved_chapter" in improvement_result:
                                improved_content = improvement_result["improved_chapter"]
                        elif content_type == "storyline":
                            if "improved_storyline" in improvement_result:
                                improved_content = improvement_result["improved_storyline"]
                        
                        improvement_summary[improvement_type] = {
                            "improved": True,
                            "summary": improvement_result.get("improvement_summary", "")
                        }
                        logger.info(f"  [OK] {improvement_type}一致性改进完成")
                    else:
                        logger.error(f"  [WARN] {improvement_type}一致性改进失败: {improvement_result.get('error')}")
                        improvement_summary[improvement_type] = {
                            "improved": False,
                            "error": improvement_result.get("error")
                        }
                except Exception as ex:
                    logger.error(f"  [ERROR] {improvement_type}一致性改进异常: {ex}")
                    improvement_summary[improvement_type] = {
                        "improved": False,
                        "error": str(ex)
                    }
        
        # [NEW] 记录性能监控
        execution_time = time.time() - start_time
        if hasattr(self.performance_monitor, 'record_task_execution'):
            self.performance_monitor.record_task_execution("consistency_improvements", execution_time, success=True)
        logger.info(f"一致性改进完成，总耗时: {execution_time:.2f}秒")
        
        return {
            "improved_content": improved_content,
            "improvement_summary": improvement_summary
        }
    
    def _build_original_knowledge_base(self, novel_id: str = None) -> Dict[str, Any]:
        """
        构建原始知识库（整合核心知识库和动态知识库）
        
        Args:
            novel_id: 小说ID
            
        Returns:
            整合后的知识库
        """
        if not novel_id and self.context:
            novel_id = self.context.novel_id
        
        if not novel_id:
            return {}
        
        knowledge_base = {}
        
        # 1. 获取核心知识库
        try:
            core_knowledge = self.core_knowledge_manager.get_core_knowledge(novel_id)
            if core_knowledge:
                knowledge_base["character_profiles"] = core_knowledge.get("character_profiles", {})
                knowledge_base["world_setting"] = core_knowledge.get("world_setting", {})
                knowledge_base["story_themes"] = core_knowledge.get("story_themes", [])
                knowledge_base["basic_rules"] = core_knowledge.get("basic_rules", {})
        except Exception as e:
            logger.warning(f"[WARN] 获取核心知识库时出错: {e}")
        
        # 2. 获取动态知识库
        try:
            dynamic_knowledge = self.dynamic_knowledge_manager.get_dynamic_knowledge(novel_id)
            if dynamic_knowledge:
                knowledge_base["character_evolution"] = dynamic_knowledge.get("character_evolution", {})
                knowledge_base["plot_timeline"] = dynamic_knowledge.get("plot_timeline", [])
                knowledge_base["foreshadowing_tracking"] = dynamic_knowledge.get("foreshadowing_tracking", {})
                knowledge_base["world_changes"] = dynamic_knowledge.get("world_changes", [])
                knowledge_base["chapter_summaries"] = dynamic_knowledge.get("chapter_summaries", {})
        except Exception as e:
            logger.warning(f"[WARN] 获取动态知识库时出错: {e}")
        
        # 3. 整合续写知识库（如果存在）
        if self.context and self.context.continuation_data:
            continuation_kb = self.context.continuation_data.get("knowledge_base", {})
            if continuation_kb:
                # 合并续写知识库（续写知识库优先）
                knowledge_base["plot_lines"] = continuation_kb.get("plot_lines", {})
                knowledge_base["story_tone"] = continuation_kb.get("story_tone", "")
                knowledge_base["tags"] = continuation_kb.get("tags", {})
                # 如果核心知识库中没有角色信息，使用续写知识库的
                if not knowledge_base.get("character_profiles"):
                    knowledge_base["character_profiles"] = continuation_kb.get("character_profiles", {})
        
        return knowledge_base
    
    def _extract_clean_content(self, raw_content: str) -> str:
        """从可能包含markdown格式的内容中提取纯文本"""
        if not raw_content:
            return ""
        
        # 如果是markdown格式的JSON，直接提取```json到```之间的内容
        if raw_content.startswith("```json"):
            try:
                import json
                # 找到```json和```的位置
                start = raw_content.find("```json") + 7  # 跳过```json
                end = raw_content.find("```", start)
                if end != -1:
                    json_str = raw_content[start:end].strip()
                    parsed = json.loads(json_str)
                    content = parsed.get("content", raw_content)
                    # 确保内容不被截断，特别是包含双引号的内容
                    return content
            except Exception as e:
                logger.error(f"JSON解析失败，使用原始内容: {e}")
                pass
        
        # 如果内容包含转义的换行符，转换为实际换行符
        if "\\n" in raw_content:
            raw_content = raw_content.replace("\\n", "\n")
        
        # 如果内容包含转义的双引号，转换为实际双引号
        if '\\"' in raw_content:
            raw_content = raw_content.replace('\\"', '"')
        
        return raw_content
    
    
    def clear_continuation_cache(self, novel_id: str = None) -> Dict[str, Any]:
        """清除续写缓存数据"""
        logger.info("开始清除续写缓存数据...")
        
        # 如果提供了novel_id，尝试加载现有上下文
        if novel_id:
            # 尝试加载现有上下文，如果失败就返回成功（表示没有缓存需要清除）
            if not self.load_context_by_novel_id(novel_id):
                logger.info(f"没有找到小说 {novel_id} 的上下文，无需清除缓存")
                return {"status": "success", "message": "没有需要清除的缓存数据"}
        
        if not self.context:
            return {"status": "success", "message": "没有需要清除的缓存数据"}
        
        # 清除所有续写相关的缓存数据
        cache_keys_to_clear = [
            "next_chapter_content",
            "next_chapter_storyline", 
            "continuation_storyline_quality_assessment",
            "continuation_story_quality_assessment"
        ]
        
        for key in cache_keys_to_clear:
            if key in self.context._cache:
                del self.context._cache[key]
                logger.info(f"已清除缓存: {key}")
        
        # 如果是续写模式，重置当前步骤到故事线生成
        if self.context.is_continuation:
            self.context.set_current_step("storyline_generation")
            logger.info("已重置续写步骤到故事线生成")
        
        # 保存上下文
        self.save_context()
        
        return {
            "status": "success",
            "message": "续写缓存数据已清除，准备开始新的续写流程"
        }
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """获取工作流程状态"""
        if not self.context:
            return {
                "novel_id": None,
                "current_step": "not_started",
                "workflow_state": {}
            }
        
        return {
            "novel_id": self.context.novel_id,
            "current_step": self.context.current_step,
            "workflow_state": self.context.get_summary()
        }
    
    def get_continuation_status(self, novel_id: str = None) -> Dict[str, Any]:
        """获取续写状态"""
        # 如果提供了novel_id，确保上下文正确设置
        if novel_id and (not self.context or self.context.novel_id != novel_id):
            # 尝试加载现有上下文
            if not self.load_context_by_novel_id(novel_id):
                return {"error": f"无法加载小说 {novel_id} 的上下文，请先开始续写流程"}
        
        if not self.context or not self.context.is_continuation:
            return {
                "novel_id": novel_id,
                "is_continuation": False,
                "current_step": "not_started",
                "continuation_state": {}
            }
        
        novel_data = self.context.continuation_data.get("novel_data", {})
        novel_info = novel_data.get("novel_info", {})
        chapters = novel_data.get("chapters", [])
        
        # 根据实际数据确定当前步骤
        current_step = self.context.current_step
        
        # 检查是否有续写故事线数据
        next_chapter_storyline = self.context.get_cached_result("next_chapter_storyline")
        # 检查是否有续写章节内容
        next_chapter_content = self.context.get_cached_result("next_chapter_content")
        
        # 检查是否有已保存的续写章节
        saved_chapters = self.data_manager.get_novel_chapters(novel_id)
        current_chapter_number = len(chapters) + 1
        
        # 调试信息
        logger.debug(f"状态检测调试信息:")
        logger.info(f"  - novel_data.chapters 数量: {len(chapters)}")
        logger.info(f"  - saved_chapters 数量: {len(saved_chapters)}")
        logger.info(f"  - next_chapter_content 存在: {bool(next_chapter_content)}")
        logger.info(f"  - next_chapter_storyline 存在: {bool(next_chapter_storyline)}")
        
        # 根据实际数据重新确定当前步骤
        # 优先级：上下文当前步骤（如果是续写模式）> 已保存章节 > 缓存内容 > 默认状态
        
        # 如果是续写模式且上下文中有明确的步骤，优先信任上下文
        if self.context.is_continuation and current_step and current_step != "not_started":
            logger.info(f"  - 续写模式：信任上下文中的当前步骤: {current_step}")
            
            # 对于续写模式，尝试从数据文件恢复缓存数据
            if current_step != "storyline_generation":
                # 尝试恢复故事线数据
                if not next_chapter_storyline:
                    saved_storyline = self.data_manager.load_novel_data(self.context.novel_id, "next_chapter_storyline")
                    if saved_storyline:
                        self.context.cache_result("next_chapter_storyline", saved_storyline)
                        next_chapter_storyline = saved_storyline
                        logger.info(f"  - 从文件恢复故事线数据")
                
                # 尝试恢复章节内容数据
                if not next_chapter_content:
                    saved_content = self.data_manager.load_novel_data(self.context.novel_id, "next_chapter_content")
                    if saved_content:
                        self.context.cache_result("next_chapter_content", saved_content)
                        next_chapter_content = saved_content
                        logger.info(f"  - 从文件恢复章节内容数据")
                        
                # 尝试恢复质量评估数据
                storyline_quality = self.data_manager.load_novel_data(self.context.novel_id, "continuation_storyline_quality_assessment")
                if storyline_quality:
                    self.context.cache_quality_assessment("storyline", storyline_quality)
                    logger.info(f"  - 从文件恢复故事线质量评估数据")
                    
                chapter_quality = self.data_manager.load_novel_data(self.context.novel_id, "continuation_chapter_quality_assessment")
                if chapter_quality:
                    self.context.cache_quality_assessment("story", chapter_quality)
                    logger.info(f"  - 从文件恢复章节质量评估数据")
        else:
            # 非续写模式或没有明确步骤时，使用原来的推断逻辑
            logger.info(f"  - 使用数据推断逻辑确定步骤")
            
            # 检查是否有续写章节文件（续写章节会保存为独立的文件）
            continuation_chapter_files = [ch for ch in saved_chapters if ch.get("chapter_number", 0) > 1]
            
            if continuation_chapter_files:
                # 有续写章节文件，说明续写已完成
                current_step = "chapter_completed"
                logger.info(f"  - 检测到续写章节文件 {[ch.get('chapter_number') for ch in continuation_chapter_files]}，设置状态为: {current_step}")
            elif next_chapter_content:
                # 有章节内容，说明章节写作已完成
                current_step = "chapter_completed"
                logger.info(f"  - 检测到 next_chapter_content，设置状态为: {current_step}")
            elif next_chapter_storyline:
                # 有故事线但没有章节内容，说明故事线生成已完成，下一步是章节写作
                current_step = "chapter_writing"
                logger.info(f"  - 检测到 next_chapter_storyline，设置状态为: {current_step}")
            else:
                # 没有故事线数据，说明需要生成故事线
                current_step = "storyline_generation"
                logger.info(f"  - 没有检测到相关数据，设置状态为: {current_step}")
        
        # 更新上下文中的当前步骤（只有在步骤确实改变时才更新）
        if self.context.current_step != current_step:
            logger.info(f"  - 更新步骤: {self.context.current_step} → {current_step}")
            self.context.set_current_step(current_step)
            self.save_context()  # 保存上下文以持久化状态变更
        else:
            logger.info(f"  - 步骤未改变，保持: {current_step}")
        
        # 构建续写状态数据
        continuation_state = {
            "novel_data": novel_data,
            "knowledge_base": self.context.continuation_data.get("knowledge_base", {}),
            "user_requirements": self.context.user_requirements
        }
        
        # 添加续写故事线数据（如果存在）
        if next_chapter_storyline:
            continuation_state["next_chapter_storyline"] = next_chapter_storyline
        
        # 添加续写章节内容数据（如果存在）
        if next_chapter_content:
            continuation_state["next_chapter_content"] = next_chapter_content
        
        return {
            "novel_id": self.context.novel_id,
            "is_continuation": True,
            "current_step": current_step,
            "novel_title": novel_info.get("title", "未知标题"),
            "chapter_count": len(saved_chapters),  # 返回实际保存的章节数量
            "user_requirements": self.context.user_requirements,
            "continuation_state": continuation_state
        }
    
    def continue_workflow(self) -> Dict[str, Any]:
        """继续工作流程"""
        if not self.context:
            return {"error": "没有活跃的工作流程"}
        
        current_step = self.context.current_step
        
        if current_step == "tag_selection":
            return self.select_tags()
        elif current_step == "character_creation":
            return self.create_characters()
        elif current_step == "storyline_generation":
            if self.context.is_continuation:
                return self.generate_continuation_storyline()
            else:
                return self.generate_storyline()
        elif current_step == "knowledge_graph_creation":
            return self.create_knowledge_graph()
        elif current_step == "chapter_writing":
            if self.context.is_continuation:
                return self.write_continuation_chapter()
            else:
                return self.write_first_chapter()
        else:
            return {"error": f"未知的工作流程步骤: {current_step}"}
    
    def save_context(self, file_path: str = None) -> bool:
        """保存工作流程上下文"""
        if not self.context:
            return False
        
        if not file_path:
            # 将workflow_context文件保存到小说目录内
            novel_dir = os.path.join(self.data_manager.novels_dir, self.context.novel_id)
            os.makedirs(novel_dir, exist_ok=True)
            file_path = os.path.join(novel_dir, "workflow_context.json")
        
        return self.context.save_to_file(file_path)
    
    def load_context(self, file_path: str) -> bool:
        """加载工作流程上下文"""
        context = WorkflowContext.load_from_file(file_path)
        if context:
            self.context = context
            return True
        return False
    
    def load_context_by_novel_id(self, novel_id: str) -> bool:
        """根据小说ID加载上下文"""
        # 从小说目录内加载workflow_context文件
        novel_dir = os.path.join(self.data_manager.novels_dir, novel_id)
        file_path = os.path.join(novel_dir, "workflow_context.json")
        return self.load_context(file_path)
    
    def validate_and_repair_context(self) -> Dict[str, Any]:
        """验证并修复上下文"""
        if not self.context:
            return {
                "is_valid": False,
                "issues": ["缺少工作流程上下文"],
                "warnings": [],
                "repair_suggestions": ["重新开始工作流程"]
            }
        
        validation_result = self.context.validate_context()
        
        # 如果上下文无效，尝试修复
        if not validation_result["is_valid"]:
            repair_suggestions = []
            
            for issue in validation_result["issues"]:
                if "缺少小说ID" in issue:
                    repair_suggestions.append("重新创建小说项目")
                elif "缺少标签数据" in issue:
                    repair_suggestions.append("重新执行标签选择步骤")
                elif "缺少角色数据" in issue:
                    repair_suggestions.append("重新执行角色创建步骤")
                elif "缺少故事线数据" in issue:
                    repair_suggestions.append("重新执行故事线生成步骤")
                elif "缺少续写数据" in issue:
                    repair_suggestions.append("重新开始续写流程")
            
            validation_result["repair_suggestions"] = repair_suggestions
        
        return validation_result
    
    def auto_repair_context(self) -> bool:
        """自动修复上下文"""
        validation_result = self.validate_and_repair_context()
        
        if validation_result["is_valid"]:
            return True
        
        # 尝试自动修复
        if "缺少小说ID" in validation_result["issues"]:
            return False  # 无法自动修复
        
        # 重置到合适的步骤
        if "缺少标签数据" in validation_result["issues"]:
            return self.context.reset_to_step("tag_selection")
        elif "缺少角色数据" in validation_result["issues"]:
            return self.context.reset_to_step("character_creation")
        elif "缺少故事线数据" in validation_result["issues"]:
            return self.context.reset_to_step("storyline_generation")
        
        return False
    
    def start_quick_continuation_fixed(self, chapter_count: int = 1, requirements: str = "") -> bool:
        """启动指定章节数的快速续写"""
        logger.info(f"启动快速续写（指定章节数）: {chapter_count}章")
        logger.info(f"续写需求: {requirements}")
        
        try:
            # 更新用户需求（如果有提供）
            if requirements:
                self.context.user_requirements = requirements
                self.context.save_context()
            
            # 启动续写流程
            logger.info(f"开始启动续写流程，小说ID: {self.context.novel_id}")
            result = self.start_novel_continuation(self.context.novel_id, requirements)
            logger.info(f"续写流程启动结果: {result}")
            
            if not result.get("success", False):
                error_msg = result.get('error', '未知错误')
                logger.error(f"启动续写流程失败: {error_msg}")
                return False
            
            # 开始自动执行续写流程
            return self._execute_quick_continuation_loop(chapter_count, mode='fixed')
            
        except Exception as e:
            logger.error(f"快速续写启动失败: {e}")
            return False
    
    def start_quick_continuation_continuous(self, continuous_mode: str = 'auto', requirements: str = "") -> bool:
        """启动持续写作模式的快速续写"""
        logger.info(f"启动快速续写（持续模式）: {continuous_mode}")
        logger.info(f"续写需求: {requirements}")
        
        try:
            # 更新用户需求（如果有提供）
            if requirements:
                self.context.user_requirements = requirements
                self.context.save_context()
            
            # 启动续写流程
            result = self.start_novel_continuation(self.context.novel_id, requirements)
            if not result.get("success", False):
                logger.error(f"启动续写流程失败: {result.get('error', '未知错误')}")
                return False
            
            # 开始自动执行续写流程
            return self._execute_quick_continuation_loop(max_chapters=50, mode='continuous', continuous_mode=continuous_mode)
            
        except Exception as e:
            logger.error(f"快速续写启动失败: {e}")
            return False
    
    def _execute_quick_continuation_loop(self, max_chapters: int = 1, mode: str = 'fixed', continuous_mode: str = 'auto') -> bool:
        """执行快速续写循环"""
        logger.info(f"开始执行快速续写循环: max_chapters={max_chapters}, mode={mode}")
        
        chapters_completed = 0
        
        try:
            while chapters_completed < max_chapters:
                logger.info(f"\n=== 开始续写第 {chapters_completed + 1} 章 ===")
                
                # 步骤1: 生成续写故事线
                logger.info("步骤1: 生成续写故事线...")
                storyline_result = self.generate_continuation_storyline()
                if not storyline_result.get("success", False):
                    logger.error(f"故事线生成失败: {storyline_result.get('error', '未知错误')}")
                    break
                
                # 步骤2: 改进故事线（可选）
                logger.info("步骤2: 改进故事线...")
                improve_result = self.improve_continuation_storyline()
                if not improve_result.get("success", False):
                    logger.error(f"故事线改进失败: {improve_result.get('error', '未知错误')}")
                    # 继续执行，改进失败不是致命错误
                
                # 步骤3: 评估故事线质量
                logger.info("步骤3: 评估故事线质量...")
                quality_result = self.assess_continuation_quality(content_type="storyline")
                if not quality_result.get("success", False):
                    logger.error(f"故事线质量评估失败: {quality_result.get('error', '未知错误')}")
                    # 继续执行，质量评估失败不是致命错误
                
                # 步骤4: 写作章节
                logger.info("步骤4: 写作章节...")
                chapter_result = self.write_continuation_chapter()
                if not chapter_result.get("success", False):
                    logger.error(f"章节写作失败: {chapter_result.get('error', '未知错误')}")
                    break
                
                # 步骤5: 保存章节
                logger.info("步骤5: 保存章节...")
                save_result = self.save_continuation_chapter()
                if not save_result.get("success", False):
                    logger.error(f"章节保存失败: {save_result.get('error', '未知错误')}")
                    break
                
                chapters_completed += 1
                logger.info(f"第 {chapters_completed} 章完成！")
                
                # 如果是持续模式且为手动模式，需要用户确认是否继续
                if mode == 'continuous' and continuous_mode == 'manual':
                    logger.info("手动模式：请在前端界面确认是否继续下一章...")
                    # 这里可以设置一个标志，让前端知道需要用户确认
                    break
                
                # 如果是自动模式，检查是否应该停止
                if mode == 'continuous' and continuous_mode == 'auto':
                    # 检查故事是否达到自然结束点
                    if self._should_stop_continuous_writing():
                        logger.info("检测到故事自然结束点，停止续写")
                        break
            
            logger.info(f"\n快速续写完成！总共完成 {chapters_completed} 章")
            return True
            
        except Exception as e:
            logger.error(f"快速续写循环执行失败: {e}")
            return False
    
    def _should_stop_continuous_writing(self) -> bool:
        """判断是否应该停止持续写作"""
        try:
            # 获取最新的故事线内容
            storyline_data = self.context.continuation_data.get("next_chapter_storyline", {})
            storyline_content = storyline_data.get("content", "")
            
            # 简单的结束点检测逻辑
            end_indicators = [
                "完结", "结束", "大结局", "尾声", "后记",
                "故事结束", "全文完", "全剧终"
            ]
            
            for indicator in end_indicators:
                if indicator in storyline_content:
                    return True
            
            # 检查章节数量是否过多（防止无限循环）
            current_chapters = len(self.context.novel_data.get("chapters", []))
            if current_chapters > 100:  # 最多100章
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"检查是否停止持续写作时出错: {e}")
            return False

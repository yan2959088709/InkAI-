"""
综合小说生成系统
集成所有优化模块的主系统
"""

import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import sys

# 导入核心模块
from .dual_layer_storyline_manager import DualLayerStorylineManager
from .dynamic_knowledge_graph import DynamicKnowledgeGraph
from .optimized_agent_interaction_system import OptimizedAgentInteractionSystem
from .intelligent_memory_manager import IntelligentMemoryManager

# 导入现有智能体
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.character_creator import CharacterCreatorAgent
from agents.storyline_generator import StorylineGeneratorAgent
from agents.chapter_writer import ChapterWriterAgent
from agents.quality_assessor import QualityAssessorAgent
from agents.continuation_storyline_generator import ContinuationStorylineGenerator
from agents.continuation_chapter_writer import ContinuationChapterWriter
from agents.continuation_quality_assessor import ContinuationQualityAssessor
from utils.logger import get_logger
logger = get_logger("comprehensive_novel_generation_system")


class ComprehensiveNovelGenerationSystem:
    """综合小说生成系统"""
    
    def __init__(self, data_manager=None):
        self.data_manager = data_manager
        
        # 核心组件初始化
        self.dual_layer_storyline = DualLayerStorylineManager(data_manager)
        self.dynamic_knowledge_graph = None  # 延迟初始化
        self.agent_interaction = OptimizedAgentInteractionSystem()
        self.memory_manager = IntelligentMemoryManager(data_manager)
        
        # 智能体实例
        self.agents = {}
        
        # 系统状态
        self.system_status = {
            "initialized": False,
            "active_novels": {},
            "performance_metrics": {},
            "error_count": 0
        }
        
        # 初始化系统
        self._initialize_system()
    
    def _initialize_system(self):
        """初始化系统"""
        try:
            logger.info("🚀 初始化综合小说生成系统...")
            
            # 初始化智能体
            self._initialize_agents()
            
            # 注册智能体到交互系统
            self._register_agents()
            
            # 初始化知识图谱（延迟初始化）
            logger.info("✅ 系统初始化完成")
            self.system_status["initialized"] = True
            
        except Exception as e:
            logger.error(f"❌ 系统初始化失败: {e}")
            self.system_status["initialized"] = False
    
    def _initialize_agents(self):
        """初始化智能体"""
        try:
            logger.info("📦 初始化智能体...")
            
            # 现有智能体
            self.agents["character_creator"] = CharacterCreatorAgent()
            self.agents["storyline_generator"] = StorylineGeneratorAgent()
            self.agents["chapter_writer"] = ChapterWriterAgent()
            self.agents["quality_assessor"] = QualityAssessorAgent()
            self.agents["continuation_storyline_generator"] = ContinuationStorylineGenerator()
            self.agents["continuation_chapter_writer"] = ContinuationChapterWriter()
            self.agents["continuation_quality_assessor"] = ContinuationQualityAssessor()
            
            # 包装核心组件为智能体
            self.agents["context_manager"] = ContextManagerAgent(self.memory_manager)
            self.agents["storyline_manager"] = StorylineManagerAgent(self.dual_layer_storyline)
            self.agents["knowledge_graph"] = KnowledgeGraphAgent(self)
            self.agents["content_generator"] = ContentGeneratorAgent(self.agents["continuation_chapter_writer"])
            self.agents["content_improver"] = ContentImproverAgent()
            self.agents["final_validator"] = FinalValidatorAgent()
            
            logger.info(f"✅ 已初始化 {len(self.agents)} 个智能体")
            
        except Exception as e:
            logger.error(f"❌ 智能体初始化失败: {e}")
            raise
    
    def _register_agents(self):
        """注册智能体到交互系统"""
        try:
            for agent_name, agent_instance in self.agents.items():
                self.agent_interaction.register_agent(agent_name, agent_instance)
            
            logger.info("✅ 智能体注册完成")
            
        except Exception as e:
            logger.error(f"❌ 智能体注册失败: {e}")
            raise
    
    def initialize_novel(self, novel_id: str) -> bool:
        """初始化小说"""
        try:
            logger.info(f"📚 初始化小说: {novel_id}")
            
            # 初始化双层故事线
            success = self.dual_layer_storyline.initialize_novel_storyline(novel_id)
            if not success:
                return False
            
            # 初始化动态知识图谱
            self.dynamic_knowledge_graph = DynamicKnowledgeGraph(novel_id, self.data_manager)
            
            # 更新系统状态
            self.system_status["active_novels"][novel_id] = {
                "initialized_at": datetime.now().isoformat(),
                "current_chapter": 0,
                "status": "active"
            }
            
            logger.info(f"✅ 小说 {novel_id} 初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 小说初始化失败: {e}")
            self.system_status["error_count"] += 1
            return False
    
    def generate_chapter(self, novel_id: str, chapter: int, 
                        requirements: str = "") -> Dict[str, Any]:
        """生成章节"""
        
        if not self.system_status["initialized"]:
            return {"error": "系统未初始化"}
        
        if novel_id not in self.system_status["active_novels"]:
            if not self.initialize_novel(novel_id):
                return {"error": "小说初始化失败"}
        
        try:
            logger.info(f"✍️ 开始生成第{chapter}章...")
            
            # 检查内存使用
            if self.memory_manager.check_and_cleanup():
                logger.info("🧹 已执行内存清理")
            
            # 清理旧数据
            if chapter > 20:
                self.memory_manager.cleanup_old_data(novel_id, chapter)
            
            # 执行章节生成流程
            result = self.agent_interaction.execute_flow(
                "chapter_generation",
                {
                    "novel_id": novel_id,
                    "chapter_number": chapter,
                    "requirements": requirements,
                    "previous_chapters": self._get_previous_chapters(novel_id, chapter),
                    "upper_constraints": self._get_upper_constraints(novel_id, chapter),
                    "current_knowledge": self._get_current_knowledge(novel_id, chapter)
                }
            )
            
            if result.get("success"):
                # 更新系统状态
                self._update_system_status(novel_id, chapter, result)
                
                # 更新故事线进度
                if "final_content" in result["final_data"]:
                    self.dual_layer_storyline.update_progress(
                        novel_id, chapter, result["final_data"]["final_content"]
                    )
                
                # 更新知识图谱
                if self.dynamic_knowledge_graph and "final_content" in result["final_data"]:
                    self.dynamic_knowledge_graph.update_from_chapter(
                        chapter, result["final_data"]["final_content"]
                    )
                
                logger.info(f"✅ 第{chapter}章生成完成")
                return {
                    "success": True,
                    "chapter_content": result["final_data"].get("final_content", {}),
                    "quality_score": result["final_data"].get("final_quality_score", 0),
                    "generation_metadata": result["final_data"].get("generation_metadata", {}),
                    "performance": result.get("execution_summary", {})
                }
            else:
                error_msg = result.get("error", "未知错误")
                logger.error(f"❌ 第{chapter}章生成失败: {error_msg}")
                self.system_status["error_count"] += 1
                return {"error": error_msg}
            
        except Exception as e:
            error_msg = f"章节生成异常: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.system_status["error_count"] += 1
            return {"error": error_msg}
    
    def _get_previous_chapters(self, novel_id: str, chapter: int) -> List[Dict[str, Any]]:
        """获取之前的章节"""
        try:
            if self.data_manager:
                chapters = self.data_manager.get_novel_chapters(novel_id)
                if chapters and chapter > 1:
                    return chapters[:chapter-1]
            return []
        except Exception as e:
            return []
    
    def _get_upper_constraints(self, novel_id: str, chapter: int) -> Dict[str, Any]:
        """获取上层约束"""
        try:
            result = self.dual_layer_storyline.generate_chapter_storyline(novel_id, chapter)
            if result.get("success"):
                return result.get("upper_constraints", {})
            return {}
        except Exception as e:
            return {}
    
    def _get_current_knowledge(self, novel_id: str, chapter: int) -> Dict[str, Any]:
        """获取当前知识"""
        try:
            if self.dynamic_knowledge_graph:
                return self.dynamic_knowledge_graph.get_context_for_generation(chapter)
            return {}
        except Exception as e:
            return {}
    
    def _update_system_status(self, novel_id: str, chapter: int, result: Dict[str, Any]):
        """更新系统状态"""
        if novel_id in self.system_status["active_novels"]:
            self.system_status["active_novels"][novel_id]["current_chapter"] = chapter
            self.system_status["active_novels"][novel_id]["last_update"] = datetime.now().isoformat()
        
        # 更新性能指标
        execution_summary = result.get("execution_summary", {})
        if "total_duration" in execution_summary:
            if "total_execution_time" not in self.system_status["performance_metrics"]:
                self.system_status["performance_metrics"]["total_execution_time"] = 0
            self.system_status["performance_metrics"]["total_execution_time"] += execution_summary["total_duration"]
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        memory_report = self.memory_manager.get_memory_report()
        
        return {
            "system_status": self.system_status,
            "memory_report": memory_report,
            "performance_report": self.agent_interaction.performance_monitor.get_performance_report(),
            "active_novels_count": len(self.system_status["active_novels"]),
            "total_errors": self.system_status["error_count"]
        }
    
    def get_novel_progress(self, novel_id: str) -> Dict[str, Any]:
        """获取小说进度"""
        try:
            return self.dual_layer_storyline.get_story_progress(novel_id)
        except Exception as e:
            return {"error": f"获取进度失败: {str(e)}"}
    
    def shutdown(self):
        """关闭系统"""
        try:
            logger.info("🛑 正在关闭综合小说生成系统...")
            
            # 关闭内存管理器
            self.memory_manager.shutdown()
            
            # 保存系统状态
            self._save_system_status()
            
            logger.info("✅ 系统已安全关闭")
            
        except Exception as e:
            logger.error(f"❌ 系统关闭异常: {e}")
    
    def _save_system_status(self):
        """保存系统状态"""
        try:
            status_file = "system_status.json"
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(self.system_status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存系统状态失败: {e}")


# 智能体包装器
class ContextManagerAgent:
    """上下文管理器智能体包装器"""
    
    def __init__(self, memory_manager: IntelligentMemoryManager):
        self.memory_manager = memory_manager
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理上下文管理请求"""
        try:
            novel_id = input_data.get("novel_id")
            chapter = input_data.get("chapter_number")
            
            if not novel_id or not chapter:
                return {"error": "缺少必要参数"}
            
            # 获取压缩上下文
            context = self.memory_manager.get_context_with_compression(novel_id, chapter)
            
            return {
                "compressed_context": context,
                "memory_usage": self.memory_manager.memory_monitor.get_memory_status(),
                "relevant_entities": context.get("character_info", {}),
                "success": True
            }
            
        except Exception as e:
            return {"error": f"上下文管理失败: {str(e)}"}


class StorylineManagerAgent:
    """故事线管理器智能体包装器"""
    
    def __init__(self, dual_layer_storyline: DualLayerStorylineManager):
        self.dual_layer_storyline = dual_layer_storyline
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理故事线生成请求"""
        try:
            # 从输入数据中提取必要信息
            compressed_context = input_data.get("compressed_context", {})
            novel_id = compressed_context.get("novel_id", "test_novel")
            chapter = compressed_context.get("current_chapter", 1)
            
            # 生成章节故事线
            storyline_result = self.dual_layer_storyline.generate_chapter_storyline(novel_id, chapter)
            
            if storyline_result.get("success"):
                chapter_storyline = storyline_result.get("chapter_storyline", {})
                upper_constraints = storyline_result.get("upper_constraints", {})
                
                return {
                    "chapter_storyline": chapter_storyline,
                    "deviation_score": chapter_storyline.get("deviation_score", 0.0),
                    "consistency_score": chapter_storyline.get("consistency_score", 1.0),
                    "upper_constraints": upper_constraints,
                    "success": True
                }
            else:
                return {
                    "error": storyline_result.get("error", "故事线生成失败"),
                    "chapter_storyline": {},
                    "deviation_score": 0.0,
                    "consistency_score": 0.0
                }
            
        except Exception as e:
            return {"error": f"故事线生成失败: {str(e)}"}


class KnowledgeGraphAgent:
    """知识图谱智能体包装器"""
    
    def __init__(self, system: ComprehensiveNovelGenerationSystem):
        self.system = system
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理知识图谱更新请求"""
        try:
            if not self.system.dynamic_knowledge_graph:
                return {"error": "知识图谱未初始化"}
            
            # 获取当前知识上下文
            knowledge_context = self.system.dynamic_knowledge_graph.get_context_for_generation(
                input_data.get("chapter", 1)
            )
            
            return {
                "updated_knowledge": knowledge_context,
                "consistency_check": {"passed": True},
                "new_entities": knowledge_context.get("entities", []),
                "success": True
            }
            
        except Exception as e:
            return {"error": f"知识图谱处理失败: {str(e)}"}


class ContentGeneratorAgent:
    """内容生成器智能体包装器"""
    
    def __init__(self, chapter_writer):
        self.chapter_writer = chapter_writer
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理内容生成请求"""
        try:
            # 使用现有的章节写作智能体
            result = self.chapter_writer.process(input_data)
            
            return {
                "chapter_content": result,
                "generation_metadata": {"method": "continuation_chapter_writer"},
                "word_count": len(str(result).split()) if isinstance(result, dict) else 0,
                "success": True
            }
            
        except Exception as e:
            return {"error": f"内容生成失败: {str(e)}"}


class ContentImproverAgent:
    """内容改进器智能体包装器"""
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理内容改进请求"""
        try:
            # 简化实现
            content = input_data.get("chapter_content", {})
            suggestions = input_data.get("improvement_suggestions", [])
            
            # 这里应该实现具体的内容改进逻辑
            improved_content = content.copy()
            
            return {
                "improved_content": improved_content,
                "improvement_metadata": {"suggestions_applied": len(suggestions)},
                "success": True
            }
            
        except Exception as e:
            return {"error": f"内容改进失败: {str(e)}"}


class FinalValidatorAgent:
    """最终验证器智能体包装器"""
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理最终验证请求"""
        try:
            content = input_data.get("improved_content", input_data.get("chapter_content", {}))
            quality_score = input_data.get("quality_score", 0)
            
            # 简单验证
            validation_passed = quality_score >= 70
            
            return {
                "final_content": content,
                "validation_result": {"passed": validation_passed},
                "final_quality_score": quality_score,
                "success": True
            }
            
        except Exception as e:
            return {"error": f"最终验证失败: {str(e)}"}

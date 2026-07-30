"""
OptimizedNovelWorkflow - 优化后的完整小说生成工作流

整合三个核心组件:
1. NarrativeStateMonitor - 剧情状态监控中心
2. EnhancedContextBuilder - 增强上下文构建器
3. SimplifiedWriterAgent - 简化后的写作Agent

使用方式:
```python
workflow = OptimizedNovelWorkflow(
    novel_id="xxx",
    data_manager=data_manager,
    llm_client=llm_client
)

# 续写100章
results = workflow.continue_writing(start_chapter=1, end_chapter=100)

# 查看状态
print(workflow.get_progress_report())
```
"""

import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from core.narrative_state_monitor import NarrativeStateMonitor
from core.enhanced_context_builder import EnhancedContextBuilder
from agents.simplified_writer_agent import SimplifiedWriterAgent, QualityGates


@dataclass
class WorkflowResult:
    """工作流执行结果"""
    success: bool
    chapters_generated: int
    total_words: int
    avg_health_score: float
    errors: List[str]
    execution_time: float
    chapter_results: List[Dict]


class OptimizedNovelWorkflow:
    """
    优化后的完整小说生成工作流

    核心流程:
    1. 初始化组件
    2. 主循环 (每章):
       a. 获取当前状态
       b. 构建上下文
       c. 生成章节
       d. 质量门控
       e. 更新状态
    3. 定期诊断
    4. 生成报告
    """

    def __init__(self,
                 novel_id: str,
                 data_manager: Any = None,
                 llm_client: Any = None,
                 config: Dict = None):
        """
        初始化工作流

        Args:
            novel_id: 小说ID
            data_manager: 数据管理器
            llm_client: LLM客户端
            config: 配置字典
        """
        self.novel_id = novel_id
        self.data_manager = data_manager
        self.llm_client = llm_client

        # 配置
        self.config = config or self._default_config()

        # 初始化组件
        self._init_components()

        # 状态
        self._is_running = False
        self._start_time = None
        self._chapter_results: List[Dict] = []

    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            "strategy": "max_context",  # 上下文策略
            "retry_limit": 2,           # 最大重试次数
            "pause_on_error": True,     # 错误时暂停
            "save_interval": 5,         # 每N章保存一次
            "diagnostic_interval": 10,   # 每N章诊断一次
            "min_health_score": 50,      # 健康度低于此值时告警
            "gate3_human_review": True,  # 是否启用人类审核
            "human_review_interval": 20  # 每N章人类审核
        }

    def _init_components(self):
        """初始化组件"""
        # 1. NarrativeStateMonitor
        self.narrative_monitor = NarrativeStateMonitor(
            novel_id=self.novel_id,
            data_manager=self.data_manager
        )

        # 2. EnhancedContextBuilder
        self.context_builder = EnhancedContextBuilder(
            data_manager=self.data_manager,
            narrative_monitor=self.narrative_monitor,
            default_strategy=self.config.get("strategy", "max_context")
        )

        # 3. SimplifiedWriterAgent
        self.writer_agent = SimplifiedWriterAgent(
            llm_client=self.llm_client,
            context_builder=self.context_builder,
            narrative_monitor=self.narrative_monitor
        )

        # 4. QualityGates
        self.quality_gates = QualityGates(
            narrative_monitor=self.narrative_monitor
        )

    def continue_writing(self,
                        start_chapter: int = 1,
                        end_chapter: int = 10) -> WorkflowResult:
        """
        续写章节

        Args:
            start_chapter: 起始章节
            end_chapter: 结束章节

        Returns:
            WorkflowResult: 执行结果
        """
        self._is_running = True
        self._start_time = time.time()
        self._chapter_results = []

        errors = []
        total_words = 0
        health_scores = []

        print(f"\n{'='*60}")
        print(f"开始生成: 第{start_chapter}章 - 第{end_chapter}章")
        print(f"策略: {self.config.get('strategy')}")
        print(f"{'='*60}\n")

        try:
            for chapter_num in range(start_chapter, end_chapter + 1):
                chapter_start_time = time.time()

                # === 步骤A: 状态检查 ===
                current_state = self.narrative_monitor.get_current_state(chapter_num)

                # 健康度检查
                if current_state["health_score"] < self.config["min_health_score"]:
                    print(f"⚠️ 第{chapter_num}章: 健康度警告 {current_state['health_score']}")
                    # 可以选择暂停或继续

                # === 步骤B: 生成章节 ===
                retry_count = 0
                chapter_output = None

                while retry_count <= self.config["retry_limit"]:
                    try:
                        chapter_output = self.writer_agent.write(
                            novel_id=self.novel_id,
                            chapter_num=chapter_num,
                            strategy=self.config.get("strategy", "max_context"),
                            retry_count=retry_count
                        )
                        break
                    except Exception as e:
                        retry_count += 1
                        if retry_count > self.config["retry_limit"]:
                            errors.append(f"第{chapter_num}章: 生成失败 - {str(e)}")
                            if self.config["pause_on_error"]:
                                raise
                        print(f"⚠️ 第{chapter_num}章: 重试 {retry_count}/{self.config['retry_limit']}")

                if chapter_output is None:
                    continue

                # === 步骤C: 质量门控 ===
                gate_result = self.quality_gates.check(chapter_output, current_state)

                if not gate_result["gate_1_instant"]:
                    print(f"⚠️ 第{chapter_num}章: Gate1未通过 - {gate_result['issues']}")

                # === 步骤D: 保存章节 ===
                if self.data_manager:
                    try:
                        self.data_manager.save_chapter(
                            self.novel_id,
                            chapter_num,
                            {
                                "content": chapter_output.chapter_content,
                                "word_count": chapter_output.word_count,
                                "writing_decisions": chapter_output.writing_decisions,
                                "metadata": chapter_output.metadata
                            }
                        )
                    except Exception as e:
                        errors.append(f"第{chapter_num}章: 保存失败 - {str(e)}")

                # === 步骤E: 记录结果 ===
                chapter_time = time.time() - chapter_start_time
                self._chapter_results.append({
                    "chapter": chapter_num,
                    "word_count": chapter_output.word_count,
                    "health_score": current_state["health_score"],
                    "gate_result": gate_result,
                    "time": chapter_time,
                    "success": True
                })

                total_words += chapter_output.word_count
                health_scores.append(current_state["health_score"])

                # === 步骤F: 定期诊断 ===
                if chapter_num % self.config["diagnostic_interval"] == 0:
                    diagnostic = self.narrative_monitor.run_full_diagnostic()
                    print(f"\n📊 第{chapter_num}章诊断:")
                    print(f"   健康度: {diagnostic['health_score']}")
                    print(f"   趋势: {diagnostic['trend']}")
                    print(f"   主要问题: {', '.join(diagnostic['major_issues']) if diagnostic['major_issues'] else '无'}")
                    print()

                # 打印进度
                progress = (chapter_num - start_chapter + 1) / (end_chapter - start_chapter + 1)
                print(f"进度: {chapter_num}/{end_chapter} ({progress:.0%}) | " +
                      f"字数: {chapter_output.word_count} | " +
                      f"健康度: {current_state['health_score']} | " +
                      f"用时: {chapter_time:.1f}s")

        except KeyboardInterrupt:
            print("\n⚠️ 用户中断")
            errors.append("用户中断")
        except Exception as e:
            errors.append(f"执行异常: {str(e)}")
            raise
        finally:
            self._is_running = False

        # 计算结果
        execution_time = time.time() - self._start_time
        avg_health = sum(health_scores) / len(health_scores) if health_scores else 0

        result = WorkflowResult(
            success=len(errors) == 0,
            chapters_generated=len(self._chapter_results),
            total_words=total_words,
            avg_health_score=round(avg_health, 1),
            errors=errors,
            execution_time=round(execution_time, 1),
            chapter_results=self._chapter_results
        )

        print(f"\n{'='*60}")
        print(f"生成完成")
        print(f"成功章节: {result.chapters_generated}/{end_chapter - start_chapter + 1}")
        print(f"总字数: {result.total_words}")
        print(f"平均健康度: {result.avg_health_score}")
        print(f"总用时: {result.execution_time}秒")
        if errors:
            print(f"错误数: {len(errors)}")
        print(f"{'='*60}\n")

        return result

    def get_progress_report(self) -> Dict[str, Any]:
        """
        获取进度报告

        Returns:
            进度报告
        """
        if not self._chapter_results:
            return {"status": "未开始", "chapters": 0}

        total_chapters = len(self._chapter_results)
        total_words = sum(r["word_count"] for r in self._chapter_results)
        avg_health = sum(r["health_score"] for r in self._chapter_results) / total_chapters
        total_time = sum(r["time"] for r in self._chapter_results)

        # 最新状态
        latest_state = self.narrative_monitor.get_current_state()

        return {
            "status": "运行中" if self._is_running else "已完成",
            "total_chapters": total_chapters,
            "total_words": total_words,
            "avg_word_count": round(total_words / total_chapters),
            "avg_health_score": round(avg_health, 1),
            "total_time": round(total_time, 1),
            "latest_chapter": self._chapter_results[-1]["chapter"] if self._chapter_results else 0,
            "latest_state": latest_state,
            "recent_results": self._chapter_results[-5:]
        }

    def get_current_state(self) -> Dict[str, Any]:
        """获取当前状态"""
        return self.narrative_monitor.get_current_state()

    def run_diagnostic(self) -> Dict[str, Any]:
        """运行完整诊断"""
        return self.narrative_monitor.run_full_diagnostic()

    def export_state(self, filepath: str):
        """导出状态到文件"""
        self.narrative_monitor.export_state(filepath)

    def import_state(self, filepath: str):
        """从文件导入状态"""
        self.narrative_monitor.import_state(filepath)


class ExperimentRunner:
    """
    对比实验运行器

    用于运行A/B对比实验，验证新架构的效果
    """

    def __init__(self,
                 novel_ids: List[str],
                 config: Dict = None):
        """
        初始化实验运行器

        Args:
            novel_ids: 测试用的小说ID列表
            config: 实验配置
        """
        self.novel_ids = novel_ids
        self.config = config or {}

    def run_comparison_experiment(self,
                                 test_type: str = "new_vs_old") -> Dict[str, Any]:
        """
        运行对比实验

        Args:
            test_type: 实验类型
                - "new_vs_old": 新架构 vs 原架构
                - "context_strategy": 不同上下文策略对比
                - "scale_test": 规模测试

        Returns:
            实验结果
        """
        print(f"\n{'='*60}")
        print(f"开始对比实验: {test_type}")
        print(f"测试项目数: {len(self.novel_ids)}")
        print(f"{'='*60}\n")

        results = {
            "test_type": test_type,
            "novels": {},
            "summary": {}
        }

        for novel_id in self.novel_ids:
            print(f"\n--- 测试项目: {novel_id} ---")
            # 这里会调用实际的生成流程
            # results["novels"][novel_id] = ...

        # 生成汇总
        results["summary"] = self._generate_summary(results["novels"])

        print(f"\n{'='*60}")
        print("实验完成")
        print(f"{'='*60}\n")

        return results

    def run_scale_test(self,
                      chapter_counts: List[int] = [50, 100, 300]) -> Dict[str, Any]:
        """
        运行规模测试

        Args:
            chapter_counts: 要测试的章节数量列表

        Returns:
            测试结果
        """
        print(f"\n{'='*60}")
        print(f"开始规模测试: {chapter_counts}")
        print(f"{'='*60}\n")

        results = {
            "chapter_counts": chapter_counts,
            "scales": {}
        }

        for count in chapter_counts:
            print(f"\n--- 测试规模: {count}章 ---")
            scale_result = {
                "chapters": count,
                "estimated_time": count * 3,  # 假设每章3分钟
                "estimated_cost": count * 0.1,  # 假设每章0.1元
                "feasibility": "high" if count <= 300 else "medium"
            }
            results["scales"][count] = scale_result

        return results

    def _generate_summary(self, novel_results: Dict) -> Dict[str, Any]:
        """生成汇总"""
        if not novel_results:
            return {}

        total_chapters = sum(r.get("chapters_generated", 0) for r in novel_results.values())
        total_words = sum(r.get("total_words", 0) for r in novel_results.values())
        avg_health = sum(r.get("avg_health_score", 0) for r in novel_results.values()) / max(1, len(novel_results))

        return {
            "total_chapters": total_chapters,
            "total_words": total_words,
            "avg_health_score": round(avg_health, 1),
            "conclusion": "新架构优于原架构" if avg_health > 70 else "需要进一步优化"
        }


if __name__ == "__main__":
    print("=== OptimizedNovelWorkflow 测试 ===\n")

    # 创建工作流 (不实际调用LLM)
    workflow = OptimizedNovelWorkflow(
        novel_id="test_novel",
        data_manager=None,
        llm_client=None,
        config={
            "strategy": "max_context",
            "retry_limit": 2,
            "diagnostic_interval": 5
        }
    )

    # 获取初始状态
    print("初始状态:")
    state = workflow.get_current_state()
    print(f"  章节: {state['chapter']}")
    print(f"  健康度: {state['health_score']}")
    print()

    # 获取诊断
    print("系统诊断:")
    diagnostic = workflow.run_diagnostic()
    print(f"  健康度: {diagnostic['health_score']}")
    print(f"  趋势: {diagnostic['trend']}")
    print(f"  建议: {diagnostic['recommendations'][:100]}...")
    print()

    # 模拟生成 (用mock数据测试流程)
    print("\n=== 对比实验设计 ===")
    experiment_runner = ExperimentRunner(
        novel_ids=["novel_1", "novel_2", "novel_3"],
        config={"strategy": "max_context"}
    )

    scale_result = experiment_runner.run_scale_test([50, 100, 300])
    print(f"\n规模测试结果:")
    for count, result in scale_result["scales"].items():
        print(f"  {count}章: 可行性={result['feasibility']}, " +
              f"预估时间={result['estimated_time']}分钟")

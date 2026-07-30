"""
comprehensive_novel_test.py

综合测试：50章小说生成 + 全面质量评估

测试流程:
1. 创建新小说项目
2. 批量生成50章
3. 生成后质量评估
4. 输出评估报告
"""

import sys
import os
import io
import json
import time
from datetime import datetime
from typing import Dict, List, Any

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from inkai_workflow_optimized import InkAIWorkflowOptimized
from data_manager import DataManager
from core.batch_continuation import BatchContinuationManager
import config


NOVEL_REQUIREMENTS = """
我想写一本50章完结的都市悬疑中篇小说。

【核心设定】
1. 主角：沈夜，28岁，刑侦支队副队长，有超强记忆力和心理分析能力
2. 背景：现代都市，发生在春江市
3. 核心案件：连续失踪案，涉及10名年轻女性
4. 暗线：沈夜5年前殉职搭档的死亡真相

【故事线】
明线：沈夜调查连续失踪案，逐步揭露案件背后的城市阴暗面
暗线：沈夜调查搭档死亡真相，发现师父是幕后黑手

【写作要求】
1. 每章2000-3000字
2. 节奏紧凑，3章一个小高潮
3. 人物性格鲜明，对话简洁有力
4. 50章内必须完整解决所有悬念并完美收尾
"""

NOVEL_TITLE = "《暗夜追凶》"


class NovelQualityEvaluator:
    """小说质量评估器"""

    def __init__(self, novel_id: str):
        self.novel_id = novel_id
        self.data_manager = DataManager()

    def evaluate_all(self) -> Dict[str, Any]:
        """执行全面评估"""
        print("\n" + "=" * 60)
        print("开始全面质量评估")
        print("=" * 60)

        chapters = self.data_manager.get_chapters(self.novel_id)

        evaluation = {
            "timestamp": datetime.now().isoformat(),
            "novel_id": self.novel_id,
            "total_chapters": len(chapters),

            # 1. 基本统计
            "basic_statistics": self._evaluate_basic_statistics(chapters),

            # 2. 内容原创性
            "originality": self._evaluate_originality(chapters),

            # 3. 情节连贯性
            "coherence": self._evaluate_coherence(chapters),

            # 4. 人物塑造一致性
            "character": self._evaluate_character_consistency(chapters),

            # 5. 语言表达流畅度
            "language": self._evaluate_language_fluency(chapters),

            # 6. 章节结构合理性
            "structure": self._evaluate_structure(chapters),

            # 7. 系统效率
            "system_efficiency": self._evaluate_system_efficiency(),

            # 综合评分
            "overall_score": 0,
            "recommendations": []
        }

        # 计算综合评分
        evaluation["overall_score"] = self._calculate_overall_score(evaluation)

        # 生成建议
        evaluation["recommendations"] = self._generate_recommendations(evaluation)

        return evaluation

    def _evaluate_basic_statistics(self, chapters: List) -> Dict:
        """评估基本统计"""
        print("\n[1/7] 评估基本统计...")

        if not chapters:
            return {"status": "no_data"}

        word_counts = []
        for ch in chapters:
            content = ch.get("content", "")
            word_counts.append(len(content))

        total_words = sum(word_counts)
        avg_words = total_words / len(word_counts) if word_counts else 0
        min_words = min(word_counts) if word_counts else 0
        max_words = max(word_counts) if word_counts else 0

        # 检查是否符合要求 (2000-3000字)
        compliance_count = sum(1 for wc in word_counts if 1000 <= wc <= 5000)
        compliance_rate = compliance_count / len(word_counts) if word_counts else 0

        return {
            "total_words": total_words,
            "avg_words_per_chapter": avg_words,
            "min_words": min_words,
            "max_words": max_words,
            "compliance_rate": compliance_rate,
            "compliance_status": "优秀" if compliance_rate > 0.8 else "良好" if compliance_rate > 0.5 else "需改进"
        }

    def _evaluate_originality(self, chapters: List) -> Dict:
        """评估内容原创性"""
        print("[2/7] 评估内容原创性...")

        # 检查重复模式
        duplicate_patterns = 0
        for i, ch in enumerate(chapters):
            if i > 0:
                prev_content = chapters[i-1].get("content", "")[:500]
                curr_content = ch.get("content", "")[:500]
                if prev_content == curr_content:
                    duplicate_patterns += 1

        originality_rate = (len(chapters) - duplicate_patterns) / len(chapters) if chapters else 0

        return {
            "originality_rate": originality_rate,
            "duplicate_patterns": duplicate_patterns,
            "status": "优秀" if originality_rate > 0.95 else "良好" if originality_rate > 0.8 else "需改进"
        }

    def _evaluate_coherence(self, chapters: List) -> Dict:
        """评估情节连贯性"""
        print("[3/7] 评估情节连贯性...")

        # 检查章节之间的衔接
        coherence_issues = []

        for i, ch in enumerate(chapters):
            if i > 0:
                prev_ch = chapters[i-1]
                curr_ch = ch

                # 检查是否有衔接标记
                prev_content = prev_ch.get("content", "")
                curr_content = curr_ch.get("content", "")

                # 简单检查：上一章结尾和本章开头是否有承接
                if len(prev_content) > 100 and len(curr_content) > 100:
                    prev_ending = prev_content[-100:]
                    curr_start = curr_content[:100]

                    # 检查是否有时间/地点/人物衔接
                    has_connection = (
                        "，" in curr_start[:50] or
                        "。" in curr_start[:50] or
                        "接着" in curr_start or
                        "随后" in curr_start or
                        "与此同时" in curr_start
                    )

                    if not has_connection:
                        coherence_issues.append(f"第{i}章与第{i+1}章衔接不明显")

        coherence_rate = (len(chapters) - len(coherence_issues)) / len(chapters) if chapters else 0

        return {
            "coherence_rate": coherence_rate,
            "issues_count": len(coherence_issues),
            "issues": coherence_issues[:5],  # 只显示前5个
            "status": "优秀" if coherence_rate > 0.9 else "良好" if coherence_rate > 0.7 else "需改进"
        }

    def _evaluate_character_consistency(self, chapters: List) -> Dict:
        """评估人物一致性"""
        print("[4/7] 评估人物塑造一致性...")

        # 统计人物出场
        character_mentions = {}
        main_characters = ["沈夜", "林可", "师父", "搭档"]

        for ch in chapters:
            content = ch.get("content", "")
            for char in main_characters:
                if char in content:
                    character_mentions[char] = character_mentions.get(char, 0) + 1

        # 检查主角是否贯穿全文
        protagonist_consistency = character_mentions.get("沈夜", 0) / len(chapters) if chapters else 0

        return {
            "character_mentions": character_mentions,
            "protagonist_presence_rate": protagonist_consistency,
            "status": "优秀" if protagonist_consistency > 0.9 else "良好" if protagonist_consistency > 0.7 else "需改进"
        }

    def _evaluate_language_fluency(self, chapters: List) -> Dict:
        """评估语言流畅度"""
        print("[5/7] 评估语言表达流畅度...")

        language_issues = []

        for i, ch in enumerate(chapters):
            content = ch.get("content", "")

            # 检查是否有过短的章节
            if len(content) < 500:
                language_issues.append(f"第{i+1}章内容过短 ({len(content)}字)")

            # 检查是否有明显的重复
            if len(content) > 100:
                first_half = content[:len(content)//2]
                second_half = content[len(content)//2:]
                if first_half == second_half:
                    language_issues.append(f"第{i+1}章存在重复内容")

        fluency_rate = (len(chapters) - len(language_issues)) / len(chapters) if chapters else 0

        return {
            "fluency_rate": fluency_rate,
            "issues_count": len(language_issues),
            "status": "优秀" if fluency_rate > 0.9 else "良好" if fluency_rate > 0.7 else "需改进"
        }

    def _evaluate_structure(self, chapters: List) -> Dict:
        """评估章节结构"""
        print("[6/7] 评估章节结构合理性...")

        # 检查开头和结尾
        structure_issues = []

        if chapters:
            first_chapter = chapters[0].get("content", "")
            last_chapter = chapters[-1].get("content", "")

            # 检查第一章是否有引入
            if len(first_chapter) < 500 or "案件" not in first_chapter:
                structure_issues.append("第一章引入不足")

            # 检查最后一章是否有收尾
            if len(last_chapter) < 500 or ("结局" not in last_chapter and "真相" not in last_chapter):
                structure_issues.append("最后一章收尾不足")

        structure_rate = (len(chapters) - len(structure_issues)) / len(chapters) if chapters else 0

        return {
            "structure_rate": structure_rate,
            "issues": structure_issues,
            "status": "优秀" if structure_rate > 0.9 else "良好" if structure_rate > 0.7 else "需改进"
        }

    def _evaluate_system_efficiency(self) -> Dict:
        """评估系统效率"""
        print("[7/7] 评估系统效率...")

        return {
            "model_used": config.MODEL_NAME,
            "max_context_tokens": config.MAX_CONTEXT_TOKENS,
            "long_context_chapters": config.LONG_CONTEXT_RECENT_CHAPTERS,
            "max_output_tokens": config.MAX_TOKENS,
            "status": "正常"
        }

    def _calculate_overall_score(self, evaluation: Dict) -> float:
        """计算综合评分 (0-100)"""
        scores = []

        # 基本统计 (20分)
        basic = evaluation.get("basic_statistics", {})
        if basic.get("status") == "优秀":
            scores.append(20)
        elif basic.get("status") == "良好":
            scores.append(15)
        else:
            scores.append(10)

        # 原创性 (15分)
        orig = evaluation.get("originality", {})
        if orig.get("status") == "优秀":
            scores.append(15)
        elif orig.get("status") == "良好":
            scores.append(12)
        else:
            scores.append(8)

        # 连贯性 (25分)
        coh = evaluation.get("coherence", {})
        if coh.get("status") == "优秀":
            scores.append(25)
        elif coh.get("status") == "良好":
            scores.append(20)
        else:
            scores.append(15)

        # 人物一致性 (20分)
        char = evaluation.get("character", {})
        if char.get("status") == "优秀":
            scores.append(20)
        elif char.get("status") == "良好":
            scores.append(15)
        else:
            scores.append(10)

        # 语言流畅度 (10分)
        lang = evaluation.get("language", {})
        if lang.get("status") == "优秀":
            scores.append(10)
        elif lang.get("status") == "良好":
            scores.append(8)
        else:
            scores.append(5)

        # 章节结构 (10分)
        struct = evaluation.get("structure", {})
        if struct.get("status") == "优秀":
            scores.append(10)
        elif struct.get("status") == "良好":
            scores.append(8)
        else:
            scores.append(5)

        return sum(scores)

    def _generate_recommendations(self, evaluation: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []

        if evaluation.get("basic_statistics", {}).get("compliance_rate", 0) < 0.8:
            recommendations.append("部分章节字数不符合要求，建议调整章节长度")

        if evaluation.get("originality", {}).get("status") != "优秀":
            recommendations.append("存在重复内容，建议加强内容多样性")

        if evaluation.get("coherence", {}).get("status") != "优秀":
            recommendations.append("章节衔接需要改进，建议增强过渡描写")

        if evaluation.get("language", {}).get("status") != "优秀":
            recommendations.append("部分章节语言表达有问题，建议润色")

        if evaluation.get("structure", {}).get("status") != "优秀":
            recommendations.append("开头或结尾章节结构不完整，需要补充")

        if not recommendations:
            recommendations.append("整体质量良好，可进一步优化细节")

        return recommendations


def run_generation():
    """运行小说生成"""
    print("=" * 60)
    print("综合测试：50章小说生成 + 全面质量评估")
    print("=" * 60)
    print(f"小说: {NOVEL_TITLE}")
    print(f"目标: 50章")
    print(f"模型: {config.MODEL_NAME}")
    print(f"上下文: {config.LONG_CONTEXT_RECENT_CHAPTERS}章")
    print("=" * 60)

    workflow = InkAIWorkflowOptimized()

    # 1. 创建新小说项目
    print("\n[步骤1/4] 创建新小说项目...")
    result = workflow.start_new_novel(
        user_requirements=NOVEL_REQUIREMENTS,
        title=NOVEL_TITLE,
        novel_type="中篇",
        estimated_chapters=50
    )

    if result.get("error"):
        print(f"ERROR: 创建小说失败: {result}")
        return None

    novel_id = result.get("novel_id")
    print(f"✓ 小说创建成功: {novel_id}")

    # 2. 初始化
    print("\n[步骤2/4] 初始化项目...")
    workflow.select_tags()
    print("✓ 标签选择完成")

    workflow.create_characters()
    print("✓ 人物创建完成")

    storyline_result = workflow.generate_storyline()
    if not storyline_result.get("error"):
        print("✓ 故事线生成完成")
    else:
        print(f"WARN: 故事线生成有问题: {storyline_result}")

    # 3. 批量生成
    print("\n[步骤3/4] 批量生成50章...")
    print("=" * 60)

    manager = BatchContinuationManager(
        workflow=workflow,
        data_manager=DataManager(),
        enable_fault_tolerance=False
    )

    start_time = time.time()

    def progress_callback(info):
        elapsed = time.time() - start_time
        progress = info['progress'] * 100
        print(f"  进度: {info['completed']}/{info['total']} ({progress:.1f}%) - {elapsed:.0f}秒", flush=True)

    batch_result = manager.batch_continue(
        novel_id=novel_id,
        num_chapters=50,
        start_chapter=1,
        chapters_per_volume=40,
        progress_callback=progress_callback
    )

    generation_time = time.time() - start_time

    print("\n生成完成!")
    print(f"  完成: {batch_result['completed_chapters']}/50")
    print(f"  失败: {batch_result['failed_chapters']}")
    print(f"  耗时: {generation_time:.0f}秒 ({generation_time/60:.1f}分钟)")

    return novel_id, batch_result


def run_evaluation(novel_id: str):
    """运行质量评估"""
    print("\n[步骤4/4] 质量评估...")

    evaluator = NovelQualityEvaluator(novel_id)
    evaluation = evaluator.evaluate_all()

    return evaluation


def save_full_report(novel_id: str, generation_result: Dict, evaluation: Dict):
    """保存完整报告"""
    report = {
        "test_type": "comprehensive_novel_test",
        "test_time": datetime.now().isoformat(),
        "novel_id": novel_id,
        "novel_title": NOVEL_TITLE,

        "generation_result": {
            "completed_chapters": generation_result.get("completed_chapters", 0),
            "failed_chapters": generation_result.get("failed_chapters", 0),
            "success_rate": generation_result.get("completed_chapters", 0) / 50,
            "total_time_seconds": generation_result.get("elapsed_seconds", 0),
            "avg_time_per_chapter": generation_result.get("average_time_per_chapter", 0)
        },

        "quality_evaluation": evaluation,

        "system_config": {
            "model": config.MODEL_NAME,
            "max_context_tokens": config.MAX_CONTEXT_TOKENS,
            "long_context_chapters": config.LONG_CONTEXT_RECENT_CHAPTERS,
            "max_output_tokens": config.MAX_TOKENS
        }
    }

    report_dir = "data/test_reports"
    os.makedirs(report_dir, exist_ok=True)

    report_path = f"{report_dir}/comprehensive_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n报告已保存: {report_path}")

    return report_path


def print_summary(generation_result: Dict, evaluation: Dict):
    """打印总结"""
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)

    print("\n【生成统计】")
    print(f"  完成章节: {generation_result.get('completed_chapters', 0)}/50")
    print(f"  成功率: {generation_result.get('completed_chapters', 0) / 50 * 100:.1f}%")
    print(f"  总耗时: {generation_result.get('elapsed_seconds', 0):.0f}秒")
    print(f"  平均每章: {generation_result.get('average_time_per_chapter', 0):.0f}秒")

    print("\n【质量评分】")
    print(f"  综合评分: {evaluation.get('overall_score', 0):.1f}/100")

    basic = evaluation.get("basic_statistics", {})
    print(f"  基本统计: {basic.get('status', 'N/A')} (字数{basic.get('compliance_rate', 0)*100:.0f}%合规)")

    orig = evaluation.get("originality", {})
    print(f"  原创性: {orig.get('status', 'N/A')} ({orig.get('originality_rate', 0)*100:.1f}%)")

    coh = evaluation.get("coherence", {})
    print(f"  连贯性: {coh.get('status', 'N/A')} ({coh.get('coherence_rate', 0)*100:.1f}%)")

    char = evaluation.get("character", {})
    print(f"  人物一致性: {char.get('status', 'N/A')} (主角出现率{char.get('protagonist_presence_rate', 0)*100:.1f}%)")

    lang = evaluation.get("language", {})
    print(f"  语言流畅度: {lang.get('status', 'N/A')} ({lang.get('fluency_rate', 0)*100:.1f}%)")

    struct = evaluation.get("structure", {})
    print(f"  章节结构: {struct.get('status', 'N/A')} ({struct.get('structure_rate', 0)*100:.1f}%)")

    print("\n【系统配置】")
    sys_eff = evaluation.get("system_efficiency", {})
    print(f"  模型: {sys_eff.get('model_used', 'N/A')}")
    print(f"  上下文: {sys_eff.get('long_context_chapters', 'N/A')}章")
    print(f"  最大输出: {sys_eff.get('max_output_tokens', 'N/A')} tokens")

    print("\n【改进建议】")
    for rec in evaluation.get("recommendations", []):
        print(f"  - {rec}")

    print("\n" + "=" * 60)


def main():
    """主函数"""
    try:
        # 1. 运行生成
        result = run_generation()
        if not result:
            print("生成失败，测试终止")
            return

        novel_id, generation_result = result

        # 2. 运行评估
        evaluation = run_evaluation(novel_id)

        # 3. 保存报告
        save_full_report(novel_id, generation_result, evaluation)

        # 4. 打印总结
        print_summary(generation_result, evaluation)

        print("\n✅ 测试完成!")

    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

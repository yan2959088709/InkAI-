"""
[DEPRECATED] new_50chapters_novel_auto.py —— 旧版"50 章自动跑通"测试脚本

⚠ 本脚本依赖已废弃的 inkai_workflow_optimized.py + workflow_context.py。
   新流水线请使用：
     python run_chapter_demo.py --start-chapter 1 --end-chapter 50 --target-words 2500

详见：docs/development/data_files_catalog.md
"""
import warnings as _warnings
_warnings.warn(
    "new_50chapters_novel_auto 已废弃；请改用 run_chapter_demo.py 配合 --start-chapter / --end-chapter。",
    DeprecationWarning,
    stacklevel=2,
)

import sys
import os
import io
import json
import time
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from inkai_workflow_optimized import InkAIWorkflowOptimized
from data_manager import DataManager
from workflow_context import WorkflowContext


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


def main():
    print("=" * 60)
    print("InkAI 全新50章小说生成测试 (自动模式)")
    print("=" * 60)
    print(f"小说: {NOVEL_TITLE}")
    print(f"类型: 都市悬疑")
    print(f"目标: 50章完结")
    print("=" * 60)

    workflow = InkAIWorkflowOptimized()
    data_manager = DataManager()

    print("\n[1/5] 创建新小说项目...")
    try:
        result = workflow.start_new_novel(
            user_requirements=NOVEL_REQUIREMENTS,
            title=NOVEL_TITLE,
            novel_type="中篇",
            estimated_chapters=50
        )

        novel_id = result.get("novel_id")
        if not novel_id:
            print("ERROR: 创建小说失败，未获取novel_id")
            return

        print(f"✓ 小说创建成功!")
        print(f"  Novel ID: {novel_id}")
        print(f"  标题: {result.get('title', NOVEL_TITLE)}")

    except Exception as e:
        print(f"ERROR: 创建小说失败: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n[2/5] 初始化续写流程...")
    try:
        workflow.context = WorkflowContext(novel_id)
        workflow.context.load_context(novel_id)

        storyline = data_manager.load_novel_data(novel_id, "storyline")
        characters = data_manager.load_novel_data(novel_id, "characters")
        tags = data_manager.load_novel_data(novel_id, "tags")
        chapters = data_manager.get_chapters(novel_id)

        workflow.context.set_storyline(storyline)
        workflow.context.set_characters(characters)
        workflow.context.set_tags(tags)
        workflow.context.is_continuation = True

        workflow.context.continuation_data = {
            "knowledge_base": {
                "character_profiles": characters or {},
                "plot_lines": storyline or {},
                "chapters": chapters,
                "tags": tags or {}
            },
            "status": "initialized"
        }

        print(f"✓ 续写流程初始化成功")
        print(f"  当前章节: {len(chapters) + 1}")

    except Exception as e:
        print(f"ERROR: 续写流程初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n[3/5] 开始生成章节...")
    print("=" * 60)

    start_time = time.time()
    completed = 0
    failed = []
    chapter_times = []
    chapter_words = []

    for chapter_num in range(1, 51):
        ch_start = time.time()
        print(f"\n--- 第{chapter_num}章 ---", flush=True)

        try:
            if chapter_num > 1:
                storyline_result = workflow.generate_continuation_storyline(novel_id)
                if storyline_result and storyline_result.get("error"):
                    print(f"  ⚠ 故事线生成失败: {storyline_result.get('error')}", flush=True)
                    time.sleep(2)
                    continue

            result = workflow.write_continuation_chapter(novel_id)
            ch_time = time.time() - ch_start

            if result and (result.get("success") or result.get("content")):
                save_result = workflow.save_continuation_chapter(novel_id)
                if save_result and save_result.get("success"):
                    saved_chapters = data_manager.get_chapters(novel_id)
                    word_count = len(saved_chapters[-1].get("content", "")) if saved_chapters else 0

                    completed += 1
                    chapter_times.append(ch_time)
                    chapter_words.append(word_count)

                    print(f"  ✓ 成功 - {word_count}字 - {ch_time:.1f}秒", flush=True)
                else:
                    error_msg = save_result.get("error", "保存失败") if save_result else "保存结果为空"
                    failed.append(chapter_num)
                    print(f"  ✗ 保存失败: {error_msg}", flush=True)
            else:
                error_msg = result.get("error", "未知错误") if result else "结果为空"
                failed.append(chapter_num)
                print(f"  ✗ 失败: {error_msg}", flush=True)

        except Exception as e:
            ch_time = time.time() - ch_start
            failed.append(chapter_num)
            print(f"  ✗ 异常: {e}", flush=True)

            if "quota" in str(e).lower() or "limit" in str(e).lower():
                print("\n⚠️ 检测到API配额限制，暂停生成")
                break

            time.sleep(3)

    total_time = time.time() - start_time

    print("\n[4/5] 生成摘要")
    print("=" * 60)
    print(f"完成章节: {completed}/50")
    print(f"失败章节: {len(failed)}")

    if chapter_times:
        avg_time = sum(chapter_times) / len(chapter_times)
        print(f"平均每章耗时: {avg_time:.1f}秒")

    if chapter_words:
        total_words = sum(chapter_words)
        avg_words = total_words / len(chapter_words)
        print(f"总字数: {total_words:,}")
        print(f"平均每章: {avg_words:,.0f}字")

    print(f"总耗时: {total_time:.1f}秒 ({total_time/60:.1f}分钟)")

    if failed:
        print(f"失败章节列表: {failed}")

    print("\n[5/5] 保存报告")
    report = {
        "test_type": "new_50chapters_novel",
        "novel_id": novel_id,
        "novel_title": NOVEL_TITLE,
        "test_time": datetime.now().isoformat(),
        "metrics": {
            "completed": completed,
            "failed": failed,
            "success_rate": completed / 50,
            "total_time_seconds": total_time,
            "avg_chapter_time": sum(chapter_times) / len(chapter_times) if chapter_times else 0,
            "total_words": sum(chapter_words) if chapter_words else 0,
            "avg_words": sum(chapter_words) / len(chapter_words) if chapter_words else 0,
        }
    }

    report_dir = "data/test_reports"
    os.makedirs(report_dir, exist_ok=True)

    report_path = f"{report_dir}/new_novel_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"✓ 报告已保存: {report_path}")

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()

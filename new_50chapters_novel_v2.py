"""
new_50chapters_novel_v2.py

使用BatchContinuationManager的50章小说生成测试
正确实现批量续写逻辑
"""

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
from core.batch_continuation import BatchContinuationManager


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


def create_new_novel_with_full_init():
    """
    创建新小说并完成所有初始化步骤
    包括：标签选择、人物创建、故事线生成
    """
    print("=" * 60)
    print("创建并初始化新小说项目")
    print("=" * 60)

    workflow = InkAIWorkflowOptimized()

    print("\n[1/5] 创建新小说项目...")
    result = workflow.start_new_novel(
        user_requirements=NOVEL_REQUIREMENTS,
        title=NOVEL_TITLE,
        novel_type="中篇",
        estimated_chapters=50
    )

    if not result or result.get("error"):
        print(f"ERROR: 创建小说失败: {result}")
        return None

    novel_id = result.get("novel_id")
    print(f"✓ 小说创建成功: {novel_id}")

    print("\n[2/5] 选择标签...")
    workflow.select_tags()
    print("✓ 标签选择完成")

    print("\n[3/5] 创建人物...")
    workflow.create_characters()
    print("✓ 人物创建完成")

    print("\n[4/5] 生成故事线...")
    storyline_result = workflow.generate_storyline()
    if storyline_result and not storyline_result.get("error"):
        print("✓ 故事线生成完成")
    else:
        print(f"WARN: 故事线生成有问题: {storyline_result}")

    print("\n[5/5] 验证初始化...")
    dm = DataManager()
    storyline = dm.load_novel_data(novel_id, "storyline")
    characters = dm.load_novel_data(novel_id, "characters")
    tags = dm.load_novel_data(novel_id, "tags")

    if storyline and characters and tags:
        print("✓ 初始化验证通过")
    else:
        print("WARN: 初始化验证未完全通过，但继续...")

    return novel_id


def run_batch_continuation(novel_id: str, num_chapters: int = 50):
    """
    使用BatchContinuationManager进行批量续写
    """
    print("\n" + "=" * 60)
    print(f"开始批量续写 {num_chapters} 章")
    print("=" * 60)

    manager = BatchContinuationManager(
        workflow=None,
        data_manager=None,
        enable_fault_tolerance=False
    )

    start_time = time.time()

    def progress_callback(info):
        chapter_num = info['chapter_number']
        completed = info['completed']
        total = info['total']
        progress = info['progress'] * 100
        elapsed = time.time() - start_time
        print(f"  第{chapter_num}章完成 ({completed}/{total}) [{progress:.1f}%] - {elapsed:.0f}秒", flush=True)

    result = manager.batch_continue(
        novel_id=novel_id,
        num_chapters=num_chapters,
        start_chapter=1,
        chapters_per_volume=40,
        progress_callback=progress_callback
    )

    return result


def verify_chapters(novel_id: str):
    """验证生成的章节"""
    print("\n" + "=" * 60)
    print("验证章节生成")
    print("=" * 60)

    dm = DataManager()
    chapters = dm.get_chapters(novel_id)

    print(f"总章节数: {len(chapters)}")

    if len(chapters) == 0:
        print("ERROR: 没有生成任何章节")
        return False

    total_words = 0
    for ch in chapters:
        content = ch.get("content", "")
        word_count = len(content)
        total_words += word_count

    avg_words = total_words / len(chapters) if chapters else 0

    print(f"总字数: {total_words:,}")
    print(f"平均每章: {avg_words:,.0f}字")

    if avg_words < 500:
        print("WARN: 平均字数过低，可能有问题")

    return True


def main():
    print("=" * 60)
    print("InkAI 50章小说生成测试 v2")
    print("使用 BatchContinuationManager")
    print("=" * 60)
    print(f"小说: {NOVEL_TITLE}")
    print(f"目标: 50章")
    print("=" * 60)

    novel_id = create_new_novel_with_full_init()

    if not novel_id:
        print("\nERROR: 小说创建失败")
        return

    print(f"\n✓ 小说项目创建完成")
    print(f"  Novel ID: {novel_id}")

    input("\n按Enter开始批量续写...")

    batch_result = run_batch_continuation(novel_id, 50)

    print("\n" + "=" * 60)
    print("批量续写完成")
    print("=" * 60)
    print(f"完成章节: {batch_result['completed_chapters']}/50")
    print(f"失败章节: {batch_result['failed_chapters']}")
    print(f"总耗时: {batch_result['elapsed_seconds']:.0f}秒 ({batch_result['elapsed_seconds']/60:.1f}分钟)")
    print(f"平均每章: {batch_result['average_time_per_chapter']:.0f}秒")

    verify_chapters(novel_id)

    report = {
        "test_type": "new_50chapters_v2",
        "novel_id": novel_id,
        "novel_title": NOVEL_TITLE,
        "test_time": datetime.now().isoformat(),
        "batch_result": {
            "completed": batch_result['completed_chapters'],
            "failed": batch_result['failed_chapters'],
            "total_time": batch_result['elapsed_seconds'],
            "avg_time_per_chapter": batch_result['average_time_per_chapter']
        }
    }

    report_dir = "data/test_reports"
    os.makedirs(report_dir, exist_ok=True)
    report_path = f"{report_dir}/test_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n报告已保存: {report_path}")


if __name__ == "__main__":
    main()

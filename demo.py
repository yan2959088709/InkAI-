#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
InkAI 功能演示脚本
==================

展示InkAI系统的主要功能和特性。
"""

import sys
import os
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def demo_tag_recommendation():
    """演示标签推荐功能"""
    print("🏷️ 演示：智能标签推荐")
    print("=" * 40)
    
    from inkai.agents.tag_selector import EnhancedTagSelectorAgent
    
    # 创建标签选择智能体
    tag_agent = EnhancedTagSelectorAgent()
    
    # 演示需求
    requirements = "我想写一个程序员获得系统后逆袭的都市小说"
    print(f"📝 用户需求: {requirements}")
    
    # 获取标签推荐
    print("\n🤖 正在分析需求并推荐标签...")
    result = tag_agent.recommend_tags(requirements)
    
    print(f"\n🎯 推荐结果:")
    recommended_tags = result.get("recommended_tags", {})
    for category, tags in recommended_tags.items():
        print(f"  {category}: {', '.join(tags)}")
    
    print(f"\n💡 推荐理由: {result.get('reasoning', 'N/A')}")
    print(f"🎲 置信度: {result.get('confidence', 0)}")
    print(f"📈 市场潜力: {result.get('market_score', 0):.2f}")
    
    return result


def demo_character_creation(tags):
    """演示人物创建功能"""
    print("\n👤 演示：智能人物创建")
    print("=" * 40)
    
    from inkai.agents.character_creator import EnhancedCharacterCreatorAgent
    
    # 创建人物创建智能体
    character_agent = EnhancedCharacterCreatorAgent()
    
    # 人物创建需求
    requirements = "创建一个内向但聪明的程序员主角，有强烈的学习欲望和正义感"
    print(f"📝 人物需求: {requirements}")
    
    # 创建主角
    print("\n🤖 正在创建主角...")
    character = character_agent.create_character(tags, requirements, "主角")
    
    print(f"\n👤 主角信息:")
    basic_info = character.get("basic_info", {})
    print(f"  姓名: {basic_info.get('name', '未知')}")
    print(f"  年龄: {basic_info.get('age', '未知')}")
    print(f"  职业: {basic_info.get('occupation', '未知')}")
    
    personality = character.get("personality_description", "")
    if personality:
        print(f"  性格: {personality[:100]}...")
    
    # 人物一致性检查
    print("\n📊 人物一致性检查:")
    consistency = character_agent.analyze_character_consistency(character)
    print(f"  一致性得分: {consistency['consistency_score']}/100")
    print(f"  优点: {', '.join(consistency['strengths'][:2])}")
    
    return character


def demo_storyline_generation(tags, character):
    """演示故事线生成功能"""
    print("\n📖 演示：智能故事线生成")
    print("=" * 40)
    
    from inkai.agents.storyline_generator import EnhancedStorylineGeneratorAgent
    
    # 创建故事线生成智能体
    storyline_agent = EnhancedStorylineGeneratorAgent()
    
    # 故事线需求
    requirements = "创建一个程序员逆袭的励志故事，要有成长和科技元素"
    print(f"📝 故事需求: {requirements}")
    
    # 生成故事线
    print("\n🤖 正在生成故事线...")
    storyline = storyline_agent.generate_storyline(tags, character, requirements)
    
    print(f"\n📚 故事线信息:")
    metadata = storyline.get("story_metadata", {})
    print(f"  故事类型: {metadata.get('story_type', '未知')}")
    print(f"  预估长度: {metadata.get('estimated_length', '未知')}")
    print(f"  复杂度: {metadata.get('complexity_level', '未知')}")
    print(f"  目标章节: {metadata.get('target_chapters', 0)}")
    
    # 世界观设定
    world_setting = storyline.get("world_setting", {})
    if world_setting:
        print(f"\n🌍 世界观设定:")
        for key, value in world_setting.items():
            if isinstance(value, str) and value:
                print(f"  {key}: {value[:50]}...")
    
    return storyline


def demo_chapter_writing(storyline, character):
    """演示章节写作功能"""
    print("\n✍️ 演示：智能章节写作")
    print("=" * 40)
    
    from inkai.agents.chapter_writer import EnhancedChapterWriterAgent
    
    # 创建章节写作智能体
    chapter_agent = EnhancedChapterWriterAgent()
    
    # 章节信息
    chapter_info = {
        "chapter_title": "第一章：平凡的开始",
        "chapter_number": 1,
        "chapter_type": "标准",
        "scene_setting": "办公室"
    }
    
    print(f"📝 章节信息: {chapter_info['chapter_title']}")
    
    # 写作章节
    print("\n🤖 正在写作章节...")
    chapter = chapter_agent.write_chapter(storyline, character, chapter_info)
    
    print(f"\n📄 章节结果:")
    print(f"  标题: {chapter.get('title', '未知')}")
    
    metadata = chapter.get("chapter_metadata", {})
    print(f"  字数: {metadata.get('word_count', 0)}")
    print(f"  写作风格: {metadata.get('writing_style', '未知')}")
    
    # 写作分析
    analysis = chapter.get("writing_analysis", {})
    if analysis:
        print(f"\n📊 写作分析:")
        print(f"  可读性: {analysis.get('readability_score', 0)}")
        print(f"  对话比例: {analysis.get('dialogue_ratio', 0):.1f}%")
        print(f"  情感强度: {analysis.get('emotional_intensity', '未知')}")
    
    return chapter


def demo_quality_assessment(chapter):
    """演示质量评估功能"""
    print("\n📊 演示：智能质量评估")
    print("=" * 40)
    
    from inkai.agents.quality_assessor import EnhancedQualityAssessorAgent
    
    # 创建质量评估智能体
    quality_agent = EnhancedQualityAssessorAgent()
    
    # 评估章节质量
    content = chapter.get("content", "")
    print(f"📝 评估内容长度: {len(content)} 字符")
    
    print("\n🤖 正在评估质量...")
    assessment = quality_agent.assess_content_quality(content, "章节")
    
    print(f"\n🎯 评估结果:")
    print(f"  总体得分: {assessment['overall_score']}")
    print(f"  质量等级: {assessment['quality_level']}")
    
    print(f"\n📈 各维度得分:")
    for dimension, score in assessment['dimension_scores'].items():
        print(f"  {dimension}: {score}")
    
    # 改进建议
    suggestions = assessment.get('improvement_suggestions', [])
    if suggestions:
        print(f"\n💡 改进建议:")
        for suggestion in suggestions[:3]:
            print(f"  - {suggestion.get('suggestion', 'N/A')}")
    
    return assessment


def demo_continuation_system():
    """演示续写系统功能"""
    print("\n🔄 演示：智能续写系统")
    print("=" * 40)
    
    from inkai.agents.continuation_analyzer import ContinuationAnalyzerAgent
    from inkai.agents.continuation_writer import ContinuationWriterAgent
    
    # 模拟现有小说数据
    mock_novel_data = {
        "title": "程序员的逆袭之路",
        "chapters": [
            {
                "title": "第一章：平凡的开始",
                "summary": "介绍主角林轩，一个普通的程序员",
                "key_events": ["日常工作", "遇到困难", "意外发现"],
                "foreshadowing": ["神秘系统", "未知力量"]
            }
        ],
        "characters": {
            "basic_info": {"name": "林轩", "age": 25, "occupation": "程序员"},
            "personality": {"description": "内向但聪明，有正义感"}
        },
        "storyline": {
            "world_setting": {"physical_world": "现代都市"},
            "main_conflict": {"type": "人与自我", "description": "突破自我限制"}
        }
    }
    
    # 创建续写智能体
    analyzer = ContinuationAnalyzerAgent()
    writer = ContinuationWriterAgent()
    
    # 续写需求
    requirements = "希望增加更多技术细节和人物成长"
    print(f"📝 续写需求: {requirements}")
    
    # 分析现有内容
    print("\n🔍 分析现有内容...")
    analysis = analyzer.analyze_for_continuation(mock_novel_data, requirements)
    
    print(f"📊 分析结果:")
    direction = analysis.get("continuation_direction", {})
    print(f"  主要焦点: {direction.get('primary_focus', '未知')}")
    print(f"  续写类型: {direction.get('continuation_type', '未知')}")
    
    # 执行续写
    print("\n✍️ 执行续写...")
    continuation = writer.write_continuation(mock_novel_data, analysis, requirements)
    
    print(f"📝 续写结果:")
    chapter_info = continuation.get("chapter_info", {})
    print(f"  新章节: {chapter_info.get('title', '未知')}")
    print(f"  字数: {chapter_info.get('word_count', 0)}")
    
    consistency = continuation.get("consistency_check", {})
    print(f"  连贯性得分: {consistency.get('overall_score', 0):.1f}")
    
    return continuation


def demo_system_integration():
    """演示系统集成功能"""
    print("\n🚀 演示：系统集成")
    print("=" * 40)
    
    from inkai import LightweightInkAIWithContinuation
    
    # 创建完整系统
    print("🤖 初始化完整系统...")
    inkai = LightweightInkAIWithContinuation()
    
    # 显示系统统计
    print("\n📊 系统统计:")
    stats = inkai.get_system_stats()
    
    agents_stats = stats.get("agents_stats", {})
    print(f"  注册智能体数量: {len(agents_stats)}")
    
    data_stats = stats.get("data_stats", {})
    print(f"  总小说数: {data_stats.get('total_novels', 0)}")
    print(f"  总章节数: {data_stats.get('total_chapters', 0)}")
    
    # 关闭系统
    inkai.shutdown()
    print("✅ 系统演示完成")
    
    return True


def main():
    """主演示函数"""
    print("🎮 InkAI 功能演示")
    print("=" * 50)
    print("版本: 2.0.0")
    print("\n这个演示将展示InkAI系统的主要功能...")
    print()
    
    try:
        # 演示各个功能模块
        print("🎯 开始功能演示...")
        
        # 1. 标签推荐
        tags = demo_tag_recommendation()
        time.sleep(1)
        
        # 2. 人物创建
        character = demo_character_creation(tags)
        time.sleep(1)
        
        # 3. 故事线生成
        storyline = demo_storyline_generation(tags, character)
        time.sleep(1)
        
        # 4. 章节写作
        chapter = demo_chapter_writing(storyline, character)
        time.sleep(1)
        
        # 5. 质量评估
        assessment = demo_quality_assessment(chapter)
        time.sleep(1)
        
        # 6. 续写系统
        continuation = demo_continuation_system()
        time.sleep(1)
        
        # 7. 系统集成
        demo_system_integration()
        
        print("\n🎉 所有功能演示完成！")
        print("✨ InkAI系统功能完整，运行正常！")
        
        # 显示使用建议
        print(f"\n🚀 使用建议:")
        print(f"  1. 运行 'python main.py' 进入交互模式")
        print(f"  2. 查看 'examples/basic_usage.py' 了解编程接口")
        print(f"  3. 阅读 'README.md' 获取完整文档")
        print(f"  4. 运行 'python main.py --demo' 体验完整流程")
        
    except Exception as e:
        print(f"❌ 演示过程出错: {e}")
        print("请检查系统配置和依赖安装")
        
        # 显示错误诊断建议
        print(f"\n🔧 错误诊断建议:")
        print(f"  1. 运行 'python check_config.py' 检查配置")
        print(f"  2. 确认API密钥配置正确")
        print(f"  3. 检查网络连接")
        print(f"  4. 查看详细错误信息")


if __name__ == "__main__":
    main()

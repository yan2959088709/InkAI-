#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
InkAI 系统集成测试
==================

测试整个系统的集成和功能完整性。
"""

import sys
import os
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试模块导入"""
    print("🧪 测试模块导入...")
    
    try:
        # 测试核心模块导入
        from inkai.core.base_agent import EnhancedBaseAgent
        print("✅ 核心模块导入成功")
        
        # 测试智能体模块导入
        from inkai.agents.tag_selector import EnhancedTagSelectorAgent
        from inkai.agents.character_creator import EnhancedCharacterCreatorAgent
        from inkai.agents.storyline_generator import EnhancedStorylineGeneratorAgent
        from inkai.agents.chapter_writer import EnhancedChapterWriterAgent
        from inkai.agents.quality_assessor import EnhancedQualityAssessorAgent
        from inkai.agents.continuation_analyzer import ContinuationAnalyzerAgent
        from inkai.agents.continuation_writer import ContinuationWriterAgent
        print("✅ 智能体模块导入成功")
        
        # 测试管理模块导入
        from inkai.managers.data_manager import EnhancedDataManager
        from inkai.managers.workflow_controller import EnhancedWorkflowController
        print("✅ 管理模块导入成功")
        
        # 测试系统模块导入
        from inkai.system.main_system import LightweightInkAIWithContinuation
        from inkai.system.advanced_features import AdvancedFeaturesManager
        print("✅ 系统模块导入成功")
        
        # 测试工具模块导入
        from inkai.utils.config import API_CONFIG, SYSTEM_CONFIG
        from inkai.utils.text_processor import TextProcessor
        from inkai.utils.data_validator import DataValidator
        print("✅ 工具模块导入成功")
        
        return True
        
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 导入过程出错: {e}")
        return False

def test_agent_creation():
    """测试智能体创建"""
    print("\n🤖 测试智能体创建...")
    
    try:
        from inkai.agents.tag_selector import EnhancedTagSelectorAgent
        from inkai.agents.character_creator import EnhancedCharacterCreatorAgent
        
        # 创建智能体实例
        tag_agent = EnhancedTagSelectorAgent()
        print("✅ 标签选择智能体创建成功")
        
        character_agent = EnhancedCharacterCreatorAgent()
        print("✅ 人物创建智能体创建成功")
        
        # 测试基本功能
        stats = tag_agent.get_stats()
        print(f"✅ 智能体统计功能正常: {stats['name']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 智能体创建失败: {e}")
        return False

def test_data_manager():
    """测试数据管理器"""
    print("\n💾 测试数据管理器...")
    
    try:
        from inkai.managers.data_manager import EnhancedDataManager
        
        # 创建数据管理器
        data_manager = EnhancedDataManager("test_data")
        print("✅ 数据管理器创建成功")
        
        # 测试项目创建
        project_data = {
            "title": "测试小说",
            "description": "这是一个测试项目"
        }
        
        project_id = data_manager.create_novel_project(project_data)
        if project_id:
            print(f"✅ 测试项目创建成功: {project_id}")
            
            # 测试数据保存和加载
            test_data = {"test": "data"}
            save_success = data_manager.save_novel_data(project_id, "test", test_data)
            if save_success:
                print("✅ 数据保存功能正常")
                
                loaded_data = data_manager.load_novel_data(project_id, "test")
                if loaded_data:
                    print("✅ 数据加载功能正常")
                else:
                    print("⚠️ 数据加载失败")
            else:
                print("⚠️ 数据保存失败")
        else:
            print("⚠️ 项目创建失败")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据管理器测试失败: {e}")
        return False

def test_main_system():
    """测试主系统"""
    print("\n🚀 测试主系统...")
    
    try:
        from inkai.system.main_system import LightweightInkAIWithContinuation
        
        # 创建主系统实例
        print("⏳ 正在初始化主系统...")
        inkai = LightweightInkAIWithContinuation()
        print("✅ 主系统初始化成功")
        
        # 测试基本功能
        novels = inkai.list_novels()
        print(f"✅ 小说列表功能正常: 找到 {len(novels)} 部小说")
        
        # 测试系统统计
        stats = inkai.get_system_stats()
        if stats:
            print("✅ 系统统计功能正常")
        
        # 关闭系统
        inkai.shutdown()
        print("✅ 系统关闭功能正常")
        
        return True
        
    except Exception as e:
        print(f"❌ 主系统测试失败: {e}")
        return False

def test_configuration():
    """测试配置系统"""
    print("\n⚙️ 测试配置系统...")
    
    try:
        from inkai.utils.config import API_CONFIG, SYSTEM_CONFIG, CREATIVE_CONFIG
        
        # 检查配置结构
        required_api_keys = ["api_key", "base_url", "model", "temperature", "max_tokens"]
        for key in required_api_keys:
            if key in API_CONFIG:
                print(f"✅ API配置包含 {key}")
            else:
                print(f"⚠️ API配置缺少 {key}")
        
        # 检查系统配置
        required_system_keys = ["data_dir", "max_retries", "timeout", "log_level"]
        for key in required_system_keys:
            if key in SYSTEM_CONFIG:
                print(f"✅ 系统配置包含 {key}")
            else:
                print(f"⚠️ 系统配置缺少 {key}")
        
        print("✅ 配置系统测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 配置系统测试失败: {e}")
        return False

def run_integration_test():
    """运行集成测试"""
    print("🧪 InkAI 系统集成测试")
    print("=" * 50)
    
    tests = [
        ("模块导入测试", test_imports),
        ("智能体创建测试", test_agent_creation),
        ("数据管理器测试", test_data_manager),
        ("配置系统测试", test_configuration),
        ("主系统测试", test_main_system)
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed_tests += 1
                print(f"✅ {test_name} 通过")
            else:
                print(f"❌ {test_name} 失败")
        except Exception as e:
            print(f"❌ {test_name} 出错: {e}")
    
    print(f"\n📊 测试结果: {passed_tests}/{total_tests} 通过")
    
    if passed_tests == total_tests:
        print("🎉 所有测试通过！系统集成成功！")
        return True
    else:
        print("⚠️ 部分测试失败，请检查相关模块")
        return False

def cleanup_test_data():
    """清理测试数据"""
    print("\n🧹 清理测试数据...")
    
    import shutil
    test_dirs = ["test_data", "novel_data", "data"]
    
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            try:
                shutil.rmtree(test_dir)
                print(f"✅ 清理目录: {test_dir}")
            except Exception as e:
                print(f"⚠️ 清理目录失败 {test_dir}: {e}")

if __name__ == "__main__":
    print("🎯 InkAI 系统集成测试工具")
    print("版本: 2.0.0")
    print()
    
    try:
        # 运行集成测试
        success = run_integration_test()
        
        if success:
            print("\n🎯 系统准备就绪！您可以开始使用InkAI了！")
            print("运行 'python main.py' 开始创作")
        else:
            print("\n⚠️ 系统存在问题，请检查配置和依赖")
        
        # 询问是否清理测试数据
        if input("\n是否清理测试数据？(y/N): ").lower() == 'y':
            cleanup_test_data()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程出错: {e}")
    
    print("\n👋 测试完成！")

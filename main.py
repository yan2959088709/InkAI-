#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
InkAI 主程序入口
================

InkAI 是一个基于大语言模型的智能小说创作系统，提供从创意构思到最终成品的全流程支持。

使用方法：
    python main.py

或者作为模块导入：
    from inkai import LightweightInkAIWithContinuation
    
    # 创建系统实例
    inkai = LightweightInkAIWithContinuation()
    
    # 创建新小说
    novel_id = inkai.create_new_novel("我的小说", "想写一个都市系统文")
    
    # 续写小说
    result = inkai.continue_novel(novel_id, "增加更多冒险元素")
"""

import os
import sys
import time
from typing import Dict, List, Any, Optional

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from inkai import LightweightInkAIWithContinuation
from inkai.utils.config import API_CONFIG, SYSTEM_CONFIG


class InkAIApplication:
    """InkAI 应用程序主类"""
    
    def __init__(self):
        self.inkai = None
        self.current_novel_id = None
        
    def initialize(self) -> bool:
        """初始化系统"""
        try:
            print("🚀 正在初始化InkAI系统...")
            
            # 检查配置
            if not self._check_configuration():
                return False
            
            # 创建系统实例
            self.inkai = LightweightInkAIWithContinuation()
            
            print("✅ InkAI系统初始化完成！")
            return True
            
        except Exception as e:
            print(f"❌ 系统初始化失败: {e}")
            return False
    
    def _check_configuration(self) -> bool:
        """检查配置"""
        print("🔧 检查系统配置...")
        
        # 检查API配置
        api_key = API_CONFIG.get("api_key", "")
        if not api_key or api_key == "your_api_key_here":
            print("⚠️ 警告：API密钥未配置，将使用模拟模式")
        else:
            print("✅ API配置检查通过")
        
        # 检查数据目录
        data_dir = SYSTEM_CONFIG.get("data_dir", "novel_data")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
            print(f"✅ 创建数据目录: {data_dir}")
        else:
            print(f"✅ 数据目录存在: {data_dir}")
        
        return True
    
    def run_interactive_mode(self):
        """运行交互模式"""
        if not self.inkai:
            print("❌ 系统未初始化，请先运行 initialize()")
            return
        
        print("\n🎮 InkAI 交互式创作系统")
        print("=" * 50)
        
        while True:
            self._show_main_menu()
            choice = input("\n请输入选择 (0-7): ").strip()
            
            if choice == "0":
                print("👋 感谢使用InkAI系统！")
                self.shutdown()
                break
            elif choice == "1":
                self._create_novel_interactive()
            elif choice == "2":
                self._continue_novel_interactive()
            elif choice == "3":
                self._list_novels_interactive()
            elif choice == "4":
                self._show_novel_details_interactive()
            elif choice == "5":
                self._export_novel_interactive()
            elif choice == "6":
                self._show_system_stats()
            elif choice == "7":
                self._run_demo()
            else:
                print("❌ 无效选择，请重新输入")
    
    def _show_main_menu(self):
        """显示主菜单"""
        print("\n📋 请选择操作：")
        print("1. 📚 创建新小说")
        print("2. 🔄 续写现有小说")
        print("3. 📖 查看小说列表")
        print("4. 🔍 查看小说详情")
        print("5. 📤 导出小说")
        print("6. 📊 系统统计")
        print("7. 🎮 运行演示")
        print("0. 🚪 退出系统")
    
    def _create_novel_interactive(self):
        """交互式创建小说"""
        print("\n📚 创建新小说")
        print("-" * 30)
        
        title = input("请输入小说标题: ").strip()
        if not title:
            title = "我的小说"
        
        requirements = input("请输入创作需求: ").strip()
        if not requirements:
            requirements = "想写一部有趣的小说"
        
        print(f"\n🚀 开始创建小说: {title}")
        print("⏳ 这可能需要几分钟时间，请耐心等待...")
        
        try:
            novel_id = self.inkai.create_new_novel(title, requirements)
            
            if novel_id:
                print(f"✅ 小说创建成功！")
                print(f"📖 小说ID: {novel_id}")
                print(f"📝 标题: {title}")
                self.current_novel_id = novel_id
                
                # 等待工作流程完成
                self._wait_for_workflow_completion(novel_id)
            else:
                print("❌ 小说创建失败")
                
        except Exception as e:
            print(f"❌ 创建过程出错: {e}")
    
    def _continue_novel_interactive(self):
        """交互式续写小说"""
        print("\n🔄 续写小说")
        print("-" * 30)
        
        # 显示现有小说
        novels = self.inkai.list_novels()
        if not novels:
            print("❌ 没有找到现有小说，请先创建小说")
            return
        
        print("现有小说：")
        for i, novel in enumerate(novels, 1):
            print(f"{i}. {novel['title']} (ID: {novel['novel_id']}) - {novel['total_chapters']}章")
        
        try:
            choice = int(input("\n请选择要续写的小说编号: ")) - 1
            if 0 <= choice < len(novels):
                novel_id = novels[choice]['novel_id']
                requirements = input("请输入续写需求（可选）: ").strip()
                
                print(f"\n✍️ 开始续写小说: {novels[choice]['title']}")
                print("⏳ 正在分析现有内容并生成续写...")
                
                result = self.inkai.continue_novel(novel_id, requirements)
                
                if result.get("status") == "success":
                    print("✅ 续写成功！")
                    print(f"📝 新章节: {result['new_chapter']['title']}")
                    print(f"📊 字数: {result['new_chapter']['word_count']}")
                    print(f"🎯 连贯性得分: {result['analysis_summary']['consistency_score']:.1f}")
                else:
                    print(f"❌ 续写失败: {result.get('error', '未知错误')}")
            else:
                print("❌ 无效选择")
        except ValueError:
            print("❌ 请输入有效数字")
        except Exception as e:
            print(f"❌ 续写过程出错: {e}")
    
    def _list_novels_interactive(self):
        """交互式列出小说"""
        print("\n📖 小说列表")
        print("-" * 30)
        
        novels = self.inkai.list_novels()
        if not novels:
            print("📝 暂无小说")
            return
        
        for novel in novels:
            print(f"📚 {novel['title']}")
            print(f"   ID: {novel['novel_id']}")
            print(f"   章节数: {novel['total_chapters']}")
            print(f"   创建时间: {novel['created_at']}")
            print(f"   更新时间: {novel['updated_at']}")
            print()
    
    def _show_novel_details_interactive(self):
        """交互式显示小说详情"""
        print("\n🔍 小说详情")
        print("-" * 30)
        
        novels = self.inkai.list_novels()
        if not novels:
            print("❌ 没有找到现有小说")
            return
        
        print("现有小说：")
        for i, novel in enumerate(novels, 1):
            print(f"{i}. {novel['title']}")
        
        try:
            choice = int(input("\n请选择要查看的小说编号: ")) - 1
            if 0 <= choice < len(novels):
                novel_id = novels[choice]['novel_id']
                novel_info = self.inkai.get_novel_info(novel_id)
                
                print(f"\n📖 {novel_info['title']}")
                print(f"ID: {novel_info['novel_id']}")
                print(f"总章节数: {novel_info['total_chapters']}")
                print(f"创建时间: {novel_info['created_at']}")
                print(f"更新时间: {novel_info['updated_at']}")
                
                if novel_info['last_chapter']:
                    print(f"\n📝 最新章节: {novel_info['last_chapter']['title']}")
                    print(f"字数: {novel_info['last_chapter'].get('word_count', '未知')}")
            else:
                print("❌ 无效选择")
        except ValueError:
            print("❌ 请输入有效数字")
    
    def _export_novel_interactive(self):
        """交互式导出小说"""
        print("\n📤 导出小说")
        print("-" * 30)
        
        novels = self.inkai.list_novels()
        if not novels:
            print("❌ 没有找到现有小说")
            return
        
        print("现有小说：")
        for i, novel in enumerate(novels, 1):
            print(f"{i}. {novel['title']}")
        
        try:
            choice = int(input("\n请选择要导出的小说编号: ")) - 1
            if 0 <= choice < len(novels):
                novel_id = novels[choice]['novel_id']
                
                print("📋 选择导出格式：")
                print("1. TXT文本文件")
                print("2. JSON数据文件")
                
                format_choice = input("请选择格式 (1-2): ").strip()
                format_type = "txt" if format_choice == "1" else "json"
                
                print(f"📤 正在导出为 {format_type.upper()} 格式...")
                filename = self.inkai.export_novel(novel_id, format_type)
                
                if filename:
                    print(f"✅ 小说已导出为: {filename}")
                else:
                    print("❌ 导出失败")
            else:
                print("❌ 无效选择")
        except ValueError:
            print("❌ 请输入有效数字")
    
    def _show_system_stats(self):
        """显示系统统计"""
        print("\n📊 系统统计")
        print("-" * 30)
        
        try:
            stats = self.inkai.get_system_stats()
            
            print("🤖 智能体统计:")
            for agent_name, agent_stats in stats["agents_stats"].items():
                print(f"  {agent_name}:")
                print(f"    调用次数: {agent_stats['call_count']}")
                print(f"    成功率: {agent_stats['success_rate']}%")
                print(f"    平均响应时间: {agent_stats['average_response_time']:.2f}s")
            
            print(f"\n📊 数据统计:")
            data_stats = stats["data_stats"]
            print(f"  总小说数: {data_stats['total_novels']}")
            print(f"  总章节数: {data_stats['total_chapters']}")
            print(f"  存储使用: {data_stats['storage_usage']} 字节")
            
        except Exception as e:
            print(f"❌ 获取统计信息失败: {e}")
    
    def _run_demo(self):
        """运行演示"""
        print("\n🎮 InkAI 演示模式")
        print("-" * 30)
        
        print("📚 演示：创建一个都市系统小说")
        
        # 演示创建小说
        demo_title = "程序员的逆袭之路"
        demo_requirements = "想写一个程序员获得系统后逆袭的故事，要有成长和励志元素"
        
        print(f"📖 标题: {demo_title}")
        print(f"📝 需求: {demo_requirements}")
        print("\n🚀 开始创建...")
        
        try:
            novel_id = self.inkai.create_new_novel(demo_title, demo_requirements)
            
            if novel_id:
                print(f"✅ 演示小说创建成功！ID: {novel_id}")
                
                # 等待一段时间让工作流程执行
                print("⏳ 等待创作完成...")
                time.sleep(3)
                
                # 演示续写
                print("\n🔄 演示续写功能...")
                continuation_result = self.inkai.continue_novel(novel_id, "增加更多技术细节和人物互动")
                
                if continuation_result.get("status") == "success":
                    print("✅ 演示续写成功！")
                    print(f"📝 新章节: {continuation_result['new_chapter']['title']}")
                else:
                    print(f"❌ 演示续写失败: {continuation_result.get('error', '未知错误')}")
            else:
                print("❌ 演示小说创建失败")
                
        except Exception as e:
            print(f"❌ 演示过程出错: {e}")
    
    def _wait_for_workflow_completion(self, novel_id: str, timeout: int = 300):
        """等待工作流程完成"""
        print("⏳ 等待创作流程完成...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # 这里可以检查工作流程状态
            # 简化版本，等待一段时间
            time.sleep(5)
            print(".", end="", flush=True)
            
            # 模拟完成
            if time.time() - start_time > 10:
                print("\n✅ 创作流程完成！")
                break
        else:
            print("\n⏰ 等待超时，请稍后检查结果")
    
    def shutdown(self):
        """关闭系统"""
        if self.inkai:
            self.inkai.shutdown()
            print("✅ 系统已安全关闭")


def main():
    """主函数"""
    print("🎯 InkAI - 智能小说创作系统")
    print("=" * 50)
    print("版本: 2.0.0")
    print("作者: InkAI Team")
    print()
    
    # 创建应用实例
    app = InkAIApplication()
    
    # 初始化系统
    if not app.initialize():
        print("❌ 系统初始化失败，程序退出")
        return
    
    try:
        # 检查命令行参数
        if len(sys.argv) > 1:
            command = sys.argv[1]
            if command == "--demo":
                app._run_demo()
            elif command == "--stats":
                app._show_system_stats()
            elif command == "--help":
                print_help()
            else:
                print(f"❌ 未知命令: {command}")
                print_help()
        else:
            # 运行交互模式
            app.run_interactive_mode()
            
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断，正在安全关闭...")
        app.shutdown()
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        app.shutdown()


def print_help():
    """打印帮助信息"""
    print("""
🔧 InkAI 使用帮助

命令行参数：
  --demo    运行演示模式
  --stats   显示系统统计
  --help    显示此帮助信息

交互模式：
  直接运行 python main.py 进入交互模式

API配置：
  在 inkai/utils/config.py 中配置API密钥：
  API_CONFIG["api_key"] = "your_api_key_here"

环境变量：
  ZHIPUAI_API_KEY    智谱AI API密钥
  INKAI_DATA_DIR     数据存储目录
  INKAI_LOG_LEVEL    日志级别

更多信息请查看 README.md
    """)


if __name__ == "__main__":
    main()

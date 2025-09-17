#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
InkAI 安装脚本
==============

自动安装和配置InkAI系统。
"""

import os
import sys
import subprocess
import shutil


def install_dependencies():
    """安装依赖包"""
    print("📦 安装依赖包...")
    
    try:
        # 安装requirements.txt中的依赖
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ 依赖包安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖包安装失败: {e}")
        return False


def create_directories():
    """创建必要目录"""
    print("📁 创建数据目录...")
    
    directories = [
        "novel_data",
        "novel_data/novels", 
        "novel_data/backups",
        "novel_data/temp",
        "logs"
    ]
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"✅ 创建目录: {directory}")
        except Exception as e:
            print(f"❌ 创建目录失败 {directory}: {e}")
            return False
    
    return True


def setup_configuration():
    """设置配置"""
    print("⚙️ 配置系统...")
    
    # 检查是否需要配置API密钥
    config_file = "inkai/utils/config.py"
    
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if "your_api_key_here" in content or "ebb349c2e5d1d84720577c74fb0fbd92" in content:
            print("⚠️ 检测到默认API密钥，建议更新为您自己的密钥")
            
            api_key = input("请输入您的智谱AI API密钥（回车跳过）: ").strip()
            if api_key:
                # 更新配置文件
                content = content.replace(
                    'os.getenv("ZHIPUAI_API_KEY", "ebb349c2e5d1d84720577c74fb0fbd92.ingUVT96KKU7kTx1")',
                    f'os.getenv("ZHIPUAI_API_KEY", "{api_key}")'
                )
                
                with open(config_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print("✅ API密钥已更新")
            else:
                print("⚠️ 跳过API密钥配置，将使用模拟模式")
        else:
            print("✅ API配置已存在")
    
    return True


def run_system_test():
    """运行系统测试"""
    print("🧪 运行系统测试...")
    
    try:
        # 运行配置检查
        result = subprocess.run([sys.executable, "check_config.py"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 系统测试通过")
            return True
        else:
            print("⚠️ 系统测试发现问题:")
            print(result.stdout)
            return False
            
    except Exception as e:
        print(f"❌ 系统测试失败: {e}")
        return False


def main():
    """主安装函数"""
    print("🚀 InkAI 系统安装程序")
    print("=" * 50)
    print("版本: 2.0.0")
    print()
    
    print("这个脚本将帮助您安装和配置InkAI智能小说创作系统")
    print()
    
    # 确认安装
    confirm = input("是否继续安装？(Y/n): ").strip().lower()
    if confirm and confirm != 'y' and confirm != 'yes':
        print("❌ 安装已取消")
        return
    
    steps = [
        ("安装依赖包", install_dependencies),
        ("创建数据目录", create_directories), 
        ("配置系统", setup_configuration),
        ("运行系统测试", run_system_test)
    ]
    
    success_count = 0
    
    for step_name, step_func in steps:
        print(f"\n📋 {step_name}")
        print("-" * 30)
        
        try:
            if step_func():
                success_count += 1
                print(f"✅ {step_name} 完成")
            else:
                print(f"❌ {step_name} 失败")
        except Exception as e:
            print(f"❌ {step_name} 出错: {e}")
    
    print(f"\n📊 安装结果: {success_count}/{len(steps)} 步骤完成")
    
    if success_count == len(steps):
        print("\n🎉 InkAI 安装完成！")
        print("✨ 系统已准备就绪，您可以开始创作了！")
        print("\n🚀 使用方法:")
        print("  python main.py          # 交互模式")
        print("  python main.py --demo   # 演示模式")
        print("  python main.py --help   # 查看帮助")
    else:
        print("\n⚠️ 安装过程中遇到问题，请检查错误信息并手动修复")
        print("\n🔧 手动安装步骤:")
        print("1. pip install -r requirements.txt")
        print("2. 编辑 inkai/utils/config.py 配置API密钥")
        print("3. python check_config.py 验证配置")


if __name__ == "__main__":
    main()

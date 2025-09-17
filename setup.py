#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
InkAI 安装配置文件
==================

用于安装和分发InkAI智能小说创作系统。
"""

from setuptools import setup, find_packages
import os

# 读取README文件
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "InkAI - 智能小说创作系统"

# 读取requirements.txt
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    requirements = []
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # 移除注释
                    if '#' in line:
                        line = line.split('#')[0].strip()
                    requirements.append(line)
    return requirements

setup(
    name="inkai",
    version="2.0.0",
    author="InkAI Team",
    author_email="team@inkai.ai",
    description="基于大语言模型的智能小说创作系统",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/inkai-team/inkai",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: Linguistic",
        "Topic :: Multimedia :: Graphics :: Editors",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Natural Language :: Chinese (Simplified)",
    ],
    python_requires=">=3.8",
    install_requires=[
        "zhipuai>=2.0.0",
        "requests>=2.28.0",
        "python-dateutil>=2.8.0"
    ],
    extras_require={
        "full": read_requirements(),
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0"
        ],
        "analytics": [
            "pandas>=1.5.0",
            "numpy>=1.21.0"
        ],
        "chinese": [
            "jieba>=0.42.1"
        ],
        "web": [
            "flask>=2.3.0",
            "flask-cors>=4.0.0"
        ]
    },
    entry_points={
        "console_scripts": [
            "inkai=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "inkai": [
            "utils/*.py",
            "core/*.py",
            "agents/*.py",
            "managers/*.py",
            "system/*.py"
        ]
    },
    keywords=[
        "ai", "nlp", "novel", "writing", "creative", "llm", 
        "chinese", "storytelling", "automation", "智能写作",
        "小说创作", "人工智能", "自然语言处理"
    ],
    project_urls={
        "Bug Reports": "https://github.com/inkai-team/inkai/issues",
        "Documentation": "https://inkai.readthedocs.io/",
        "Source": "https://github.com/inkai-team/inkai",
    },
)

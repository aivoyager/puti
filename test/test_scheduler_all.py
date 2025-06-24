#!/usr/bin/env python
"""
运行所有调度器相关的测试。
这个文件帮助一次性执行所有scheduler的测试。
"""
import os
import sys
import pytest
from pathlib import Path

# 确保puti可以被导入
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 引入Pathh以确保使用实际配置目录
from puti.constant.base import Pathh

# 确保配置目录存在
config_dir = Path(Pathh.CONFIG_DIR.val)
config_dir.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    """运行所有scheduler相关的测试"""
    
    # 列出所有scheduler相关的测试文件
    test_dir = Path(__file__).parent
    test_files = [
        "test_scheduler_cli.py",
        "test_scheduler_integration.py", 
        "test_scheduler_execution.py"
    ]
    
    test_modules = [str(test_dir / file) for file in test_files if (test_dir / file).exists()]
    
    # 运行所有测试
    print(f"正在运行以下调度器测试文件:\n" + "\n".join(f"- {Path(m).name}" for m in test_modules))
    print(f"使用实际配置目录: {config_dir}")
    
    exit_code = pytest.main(["-v"] + test_modules)
    sys.exit(exit_code) 
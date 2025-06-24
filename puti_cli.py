#!/usr/bin/env python3
"""
主要的CLI入口点，用于启动puti命令
"""
import os
import sys

# 确保可以导入puti包
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

# 设置环境变量
if not os.environ.get('PUTI_DATA_PATH'):
    data_path = os.path.expanduser('~/puti/data')
    os.makedirs(data_path, exist_ok=True)
    os.environ['PUTI_DATA_PATH'] = data_path
    print(f"Set PUTI_DATA_PATH to {data_path}")

# 导入并运行主CLI
from puti.cli import main

if __name__ == '__main__':
    main() 
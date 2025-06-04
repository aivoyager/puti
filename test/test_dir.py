"""
@Author: obstacles
@Time:  2025-06-03 16:58
@Description:  
"""
import sys
import os


def test_dir():
    print("--- DIAGNOSTIC INFO START ---")
    print("Current Python Executable:", sys.executable)
    print("Current Working Directory (os.getcwd()):", os.getcwd())
    print("sys.path:")
    for p in sys.path:
        print(f"  {p}")
    print("--- DIAGNOSTIC INFO END ---")

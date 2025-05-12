"""
@Author: obstacles
@Time:  2025-05-09 16:00
@Description:  
"""
import asyncio
import json

from llm.tools.terminal import Terminal
from llm.roles.alex import Alex


def test_echo():
    alex = Alex()
    resp = asyncio.run(alex.run('1.在终端输出 "hello world"'
                                ' 2. 查看当前目录下文件列表 '
                                '3.并查看当前目录层级 '
                                '4.切换到项目根目录，并查看内容'
                                '5.测试危险命令拦截'
                                ''))


def test_python():
    alex = Alex()
    # resp = asyncio.run(alex.run('请定义一个函数 square(n) 并输出 square(5) 的结果'))
    resp = asyncio.run(alex.run('在当前目录 用python写一个贪吃蛇游戏 并写入文件 snake_game.py'))
    print(resp)
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


def test_file():
    alex = Alex()
    # 1. 测试文件创建
    prompt_create = "请在当前目录创建一个名为 test_file_tool.txt 的文件，内容为 'hello file tool'"
    resp_create = asyncio.run(alex.run(prompt_create))
    assert 'test_file_tool.txt' in resp_create or '创建' in resp_create

    # 2. 测试文件读取
    prompt_read = "请读取 test_file_tool.txt 文件内容"
    resp_read = asyncio.run(alex.run(prompt_read))
    assert 'hello file tool' in resp_read

    # 3. 测试文件写入（覆盖）
    prompt_write = "请将 test_file_tool.txt 文件内容改为 'file tool overwrite'"
    resp_write = asyncio.run(alex.run(prompt_write))
    assert 'file tool overwrite' in asyncio.run(alex.run('请读取 test_file_tool.txt'))

    # 4. 测试文件追加
    prompt_append = "请在 test_file_tool.txt 文件末尾追加一行 'append success'"
    resp_append = asyncio.run(alex.run(prompt_append))
    assert 'append success' in asyncio.run(alex.run('请读取 test_file_tool.txt'))

    # 5. 测试文件重命名
    prompt_rename = "请将 test_file_tool.txt 重命名为 test_file_tool_renamed.txt"
    resp_rename = asyncio.run(alex.run(prompt_rename))
    assert 'test_file_tool_renamed.txt' in resp_rename or '重命名' in resp_rename

    # 6. 测试文件删除
    prompt_delete = "请删除 test_file_tool_renamed.txt 文件"
    resp_delete = asyncio.run(alex.run(prompt_delete))
    assert '删除' in resp_delete or '不存在' in asyncio.run(alex.run('请读取 test_file_tool_renamed.txt'))
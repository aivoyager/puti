"""
@Author: obstacles
@Time:  2025-03-28 11:22
@Description:  
"""
import asyncio
import pytest

from puti.llm.tools.project_analyzer import ProjectAnalyzer
from puti.llm.tools.demo import GetFlightInfo
from puti.llm.tools import toolkit
from puti.llm.tools.common import GetTodayDate
from puti.llm.tools.web_search import WebSearch
from puti.llm.roles.agents import Alex
from puti.llm.nodes import OpenAINode


def test_base_tool_inherit():
    a = toolkit.add_tool(GetFlightInfo)
    b = toolkit.add_tools([GetFlightInfo])
    for name, tool in toolkit.toolkit.items():
        print(tool.param)


def test_get_today_date():
    g = GetTodayDate()
    g.run()
    print('')


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


def test_web_search_tool():
    # g_search = GoogleSearchEngine()
    # resp = g_search.search('罗伯特 唐尼')
    # resp = list(resp)
    # alex = Alex()
    # resp = asyncio.run(alex.run('请搜索 "python" 并输出前5条结果'))

    wb = WebSearch()
    resp = asyncio.run(wb.run(query='罗伯特 唐尼', llm=OpenAINode()))
    print(resp)


def test_split_into_chunks():
    # 普通文本分割测试
    text = '这是一个测试句子。第二个句子！第三个问题？第四个句子。'
    chunks = WebSearch.split_into_chunks(text, max_length=50)
    assert len(chunks) == 4

    # 长文本自动分块测试
    long_text = 'a' * 600
    chunks = WebSearch.split_into_chunks(long_text, max_length=500)
    assert 500 >= len(chunks[0]) >= 400
    assert len(chunks) == 2

    # 标点符号分割测试
    mixed_text = 'Hello.World!你好世界？测试'
    chunks = WebSearch.split_into_chunks(mixed_text)
    assert len(chunks) == 3

    # 空文本处理测试
    assert WebSearch.split_into_chunks('') == []


def test_web_search():
    alex = Alex()
    resp = alex.cp.invoke(alex.run, '帮我看看今天的股票行情概要')
    print(resp)
    print()


@pytest.mark.asyncio
async def test_project_analyzer_run():
    """
    Tests the basic functionality of the ProjectAnalyzer tool.
    """
    # 1. Initialize the tool
    analyzer_tool = ProjectAnalyzer()

    # 2. Run the tool with default parameters (root directory, depth=3)
    response = await analyzer_tool.run()

    # 3. Assert the response is successful and contains expected data
    assert response.is_success(), f"Tool failed with message: {response.msg}"
    assert isinstance(response.data, str)
    assert len(response.data) > 0, "Tool returned an empty string."

    # 4. Check for the presence of key project files/directories in the output
    assert "README.md" in response.data, "README.md not found in project analysis."
    assert "puti/" in response.data, "puti/ directory not found in project analysis."
    assert "setup.py" in response.data, "setup.py not found in project analysis."
    # assert ".git" not in response.data, ".git directory should be ignored."
    assert "__pycache__" not in response.data, "__pycache__ directory should be ignored."

    print("\\n--- Project Analyzer Output (Defaults) ---")
    print(response.data)
    print("------------------------------------------")


@pytest.mark.asyncio
async def test_project_analyzer_with_path_and_depth():
    """
    Tests the ProjectAnalyzer tool with a specific path and depth.
    """
    # 1. Initialize the tool
    analyzer_tool = ProjectAnalyzer()

    # 2. Run the tool with a specific path and a shallow depth
    response = await analyzer_tool.run(path='puti', max_depth=1)

    # 3. Assert the response is successful
    assert response.is_success(), f"Tool failed with message: {response.msg}"
    assert isinstance(response.data, str)

    # 4. Check that the output reflects the specified path and depth
    assert "Project structure analysis from 'puti'" in response.data
    # Check for a file directly under 'puti'
    assert "cli.py" in response.data
    # Check for a directory under 'puti'
    assert "llm/" in response.data
    # A file deeper than max_depth=1 should not be present
    assert "agents.py" not in response.data, "Analysis went deeper than max_depth."

    print("\\n--- Project Analyzer Output (path='puti', max_depth=1) ---")
    print(response.data)
    print("---------------------------------------------------------")


@pytest.mark.asyncio
async def test_alex_runs_project_analyzer():
    """
    Integration test to ensure the Alex agent can use the ProjectAnalyzer tool.
    """
    # 1. Initialize the Alex agent
    alex = Alex()

    # 2. Create a prompt that should trigger the project analyzer tool
    prompt = "Analyze the structure of this project and show me the file tree."

    # 3. Run the agent
    # The response here will be the final reply from the LLM, which should contain the tool's output.
    response_message = await alex.run(prompt)

    # 4. Assert that the response is valid and contains expected output
    assert response_message is not None, "Agent did not return a message."

    # The final output is a string from the agent
    final_answer = str(response_message)
    assert "README.md" in final_answer, "Agent response did not contain 'README.md'."
    assert "puti/" in final_answer, "Agent response did not contain 'puti/'."

    print("\\n--- Alex Agent Response with Project Analysis ---")
    print(final_answer)
    print("--------------------------------------------------")

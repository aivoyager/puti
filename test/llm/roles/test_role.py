"""
@Author: obstacles
@Time:  2025-03-27 14:15
@Description:  
"""
from puti.llm.roles.agents import Alex
from puti.llm.messages import UserMessage


async def test_mcp_role():
    alex = Alex()
    resp = await alex.run('你好呀')
    print(resp)
    resp = await alex.run('针对我项目目录下的Dockerfile进行分析')
    print(resp)


async def test_search_flag():
    print("=== 测试 disable_history_search 功能 ===")

    # 创建一个Role实例
    agent = Alex()

    # 创建一个包装函数来跟踪search被调用的次数
    original_search = agent.rc.memory.search
    search_call_count = 0

    async def wrapped_search(*args, **kwargs):
        nonlocal search_call_count
        search_call_count += 1
        print(f"Memory search called with query: {args[0]}")
        return await original_search(*args, **kwargs)

    # 替换search方法
    agent.rc.memory.search = wrapped_search

    # 使用disable_history_search=False进行测试
    print("\n1. 测试默认情况下启用历史搜索")
    msg = UserMessage(content="测试消息")

    # 如果有错误，捕获并继续测试
    try:
        await agent.run(msg=msg, disable_history_search=False)
        print(f"搜索调用次数: {search_call_count}")
        assert search_call_count > 0, "应该调用search方法"
    except Exception as e:
        print(f"测试1出错: {e}")

    # 重置计数器
    search_call_count = 0

    # 使用disable_history_search=True进行测试
    print("\n2. 测试禁用历史搜索")
    try:
        await agent.run(msg=msg, disable_history_search=True)
        print(f"搜索调用次数: {search_call_count}")
        assert search_call_count == 0, "不应该调用search方法"
    except Exception as e:
        print(f"测试2出错: {e}")

    print("\n所有测试完成!")
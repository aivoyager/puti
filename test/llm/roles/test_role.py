"""
@Author: obstacles
@Time:  2025-03-27 14:15
@Description:  
"""
from puti.llm.roles.agents import Alex


async def test_mcp_role():
    alex = Alex()
    resp = await alex.run('你好呀')
    print(resp)
    resp = await alex.run('针对我项目目录下的Dockerfile进行分析')
    print(resp)

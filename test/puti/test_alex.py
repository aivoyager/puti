"""
@Author: obstacles
@Time:  2025-06-04 11:27
@Description:  
"""
from puti.llm.roles.agents import Alex


async def test_alex():
    alex = Alex()
    resp = await alex.run('你好')
    print(resp)

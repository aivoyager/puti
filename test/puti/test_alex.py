"""
@Author: obstacles
@Time:  2025-06-04 11:27
@Description:  
"""
from puti.llm.roles.agents import Alex


async def test_alex():
    alex = Alex()
    # resp = await alex.run('介绍一下根目录下的logs.py')
    # resp = await alex.run('优化一下x_bot.py中的内容并进行修改')
    resp = await alex.run('25年4月份有什么重大新闻')
    print(resp)

    resp = alex.cp.invoke(alex.run, '详细介绍一下第二条')
    print(resp)

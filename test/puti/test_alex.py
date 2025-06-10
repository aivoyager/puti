"""
@Author: obstacles
@Time:  2025-06-04 11:27
@Description:  
"""
from puti.llm.roles.agents import Alex


async def test_alex():
    alex = Alex(name='Alex')
    # resp = await alex.run('生化危机9有什么最新的爆料')
    # print(resp)
    # resp = await alex.run('为什么叫安魂曲')
    # print(resp)
    resp = await alex.run('介绍一下Dockerfile')
    print(resp)
    resp = await alex.run('解释一下我的Dockerfile')
    print(resp)
    resp = await alex.run('你在瞎编吗')
    print(resp)
    resp = await alex.run('针对我项目目录下的Dockerfile进行分析')
    print(resp)



    resp = alex.cp.invoke(alex.run, '详细介绍一下第二条')
    print(resp)

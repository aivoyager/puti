"""
@Author: obstacles
@Time:  2025-03-07 15:38
@Description:  
"""
import asyncio

from llm.envs import Env
from llm.roles.talker import Talker
from llm.messages import Message
from llm.roles.debater import Debater


def test_chat():
    msg = 'hello, what is u name'
    talker = Talker()
    msg = asyncio.run(talker.run(msg))
    print(msg.content)


def test_env():
    env = Env()
    talker = Talker()
    env.add_roles([talker])
    env.publish_message(Message.from_any('hi hi'))
    asyncio.run(env.run())
    print('')


def test_debate():
    env = Env(name='game', desc='play games with other')
    debater1 = Debater(name='bot1')
    debater2 = Debater(name='bot2')
    env.add_roles([debater1, debater2])
    env.publish_message(Message.from_any(
        f'现在你们正在进行一场辩论赛，主题为：科技发展是有益的，还是有弊的？{debater1}为正方 {debater2}为反方',
        receiver=debater1.address
    ))
    env.cp.invoke(env.run)
    # asyncio.run(env.run())


def test_state_choose():
    with open('../data/test.txt', 'r') as f:
        resp = f.read()
    import json
    from llm.nodes import OpenAINode
    prompt = json.loads(resp)
    node = OpenAINode()
    resp = asyncio.run(node.achat(prompt))
    print()


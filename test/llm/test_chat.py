"""
@Author: obstacles
@Time:  2025-03-07 15:38
@Description:  
"""
import asyncio

from llm.envs import Env
from llm.roles.talker import Talker
from llm.messages import Message


def test_chat():
    msg = 'hello, what is u name'
    talker = Talker()
    msg = asyncio.run(talker.run(msg))
    print(msg.content)


def test_env():
    env = Env(name='family', desc='family environment')
    talker = Talker()
    env.add_roles([talker])
    env.publish_message(Message.from_any('hi hi'))
    asyncio.run(env.run())
    print('')

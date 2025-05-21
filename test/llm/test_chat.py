"""
@Author: obstacles
@Time:  2025-03-07 15:38
@Description:  
"""
import asyncio
import sys

from llm.envs import Env
from llm.roles.talker import PuTi, PuTiMCP
from llm.messages import Message
from llm.roles.debater import Debater
from llm.nodes import OllamaNode
from conf.llm_config import LlamaConfig, OpenaiConfig
from llm.roles.cz import CZ
from llm.nodes import OpenAINode
from llm.roles.x_bot import TwitWhiz

# sys.stdout.reconfigure(line_buffering=True)


def test_chat():
    # TODO: llama fc
    msg = 'hi hi'
    talker = PuTi(agent_node=ollama_node)
    msg = talker.cp.invoke(talker.run, msg)
    print(f'answer:{msg.data}')


def test_env():
    env = Env()
    talker = PuTi(agent_node=openai_node)
    env.add_roles([talker])
    env.publish_message(Message.from_any('hi hi'))
    asyncio.run(env.run())
    print('')


def test_mcp_env():
    env = Env()
    talker = PuTiMCP(agent_node=openai_node)
    env.add_roles([talker])
    # msg = 'hi hi'
    msg = 'How long is the flight from New York(NYC) to Los Angeles(LAX)'
    env.publish_message(Message.from_any(msg))
    # asyncio.run(env.run())
    env.cp.invoke(env.run)
    print('ok')


def test_debate():
    env = Env(name='game', desc='play games with other')
    debater1 = Debater(name='alex', goal='make a positive point every round of debate. Your opponent is rock')
    debater2 = Debater(name='rock', goal='make a negative point every round of debate. Your opponent is alex')
    env.add_roles([debater1, debater2])
    message = Message.from_any(
        f'现在你们正在进行一场辩论赛，主题为：科技发展是有益的，还是有弊的？',
        # message,
        receiver=debater1.address,
        sender='user'
    )
    debater2.rc.memory.add_one(message)
    env.publish_message(message)
    env.cp.invoke(env.run)
    print(env.history)


def test_state_choose():
    with open('../data/test.txt', 'r') as f:
        resp = f.read()
    import json
    from llm.nodes import OpenAINode
    prompt = json.loads(resp)
    node = OpenAINode()
    resp = asyncio.run(node.chat(prompt))
    print()


def test_cz():
    cz = CZ()
    resp = cz.cp.invoke(cz.run, 'give me a tweet')
    print(resp)

def test_x_bot():
    x_bot = TwitWhiz()
    resp = x_bot.cp.invoke(x_bot.run, 'hihi')
    print(resp)


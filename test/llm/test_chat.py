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
from llm.nodes import OllamaNode, ollama_node, openai_node
from conf.llm_config import LlamaConfig

# sys.stdout.reconfigure(line_buffering=True)


def test_chat():
    msg = 'hi hi'
    talker = PuTi()
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
    # debater1 = Debater(name='alex', agent_node=ollama_node)
    # debater2 = Debater(name='rock', agent_node=ollama_node)
    debater1 = Debater(name='alex')
    debater2 = Debater(name='rock')
    env.add_roles([debater1, debater2])
    # message = (f'Now you are having a debate on the topic: '
    #            f'Is the development of science and technology beneficial or harmful? {debater1} is the positive side and {debater2} is the negative side')
    message = Message.from_any(
        f'现在你们正在进行一场辩论赛，主题为：科技发展是有益的，还是有弊的？{debater1}为正方 {debater2}为反方, 每个人字数限制在50以内',
        # message,
        receiver=debater1.address,
        sender='user'
    )
    debater2.rc.memory.add_one(message)
    env.publish_message(message)
    env.cp.invoke(env.run)


def test_state_choose():
    with open('../data/test.txt', 'r') as f:
        resp = f.read()
    import json
    from llm.nodes import OpenAINode
    prompt = json.loads(resp)
    node = OpenAINode()
    resp = asyncio.run(node.chat(prompt))
    print()



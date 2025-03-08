"""
@Author: obstacles
@Time:  2025-03-04 15:50
@Description:  
"""
import asyncio

from llm.node import LLMNode
from conf import OpenaiConfig
from llm.node import OpenAINode

def test_llm_create():
    llm_conf = OpenaiConfig()
    # llm = LLM(llm_name='openai')
    llm2 = LLMNode(llm_name='openai')
    print('')


def test_action_node():
    messages = [
        {"role": "system", "content": "You are an AI assistant."},
        {"role": "user", "content": "What is the capital of France?"}
    ]
    # messages = Message.from_messages(messages)

    llm_conf = OpenaiConfig()
    openai_node = OpenAINode(llm_name='openai', conf=llm_conf)
    resp = asyncio.run(openai_node.achat(messages))
    print('')


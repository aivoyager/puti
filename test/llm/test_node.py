"""
@Author: obstacles
@Time:  2025-03-04 15:50
@Description:  
"""
import asyncio

from llm.nodes import LLMNode
from conf.llm_config import OpenaiConfig
from llm.nodes import OpenAINode
from llm.nodes import OllamaNode
from conf.llm_config import LlamaConfig


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


def test_ollama():
    t = 'hello, world'
    node = OllamaNode(llm_name='llama', conf=LlamaConfig())
    res = asyncio.run(node.achat(t))
    print(res)


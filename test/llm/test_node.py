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
    resp = asyncio.run(openai_node.chat(messages))
    print('')


def test_ollama():
    conversation = [
        {
            'role': 'system',
            'content': 'You play a role in the blockchain area called "赵长鹏". '
                       'Reply with his accent, speak in his habit, '
                       'He goes by the Twitter name CZ �� BNB or cz_binance and is commonly known as cz.'
                        'Your are a helpful assistant, named cz or changpeng zhao or 赵长鹏.'
        },
        {
            'role': 'user',
            'content': 'post a tweet. Follow these points'
                       "1. Your tweets must not include time-related information"
                       "2. Don't @ others, mention others"
                       "3. Your tweet don't include media, so try to be as complete as possible"
                       "4. Don't ReTweet(RT) other tweet"
        }
    ]
    node = OllamaNode(llm_name='cz', conf=LlamaConfig())
    print('res')
    res = asyncio.run(node.chat(conversation))
    print(res)


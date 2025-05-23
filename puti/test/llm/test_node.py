"""
@Author: obstacles
@Time:  2025-03-04 15:50
@Description:  
"""
import re
import asyncio
from datetime import date
import openai
import time

import pytest

from logs import logger_factory
from llm.nodes import LLMNode
from conf.llm_config import OpenaiConfig, LlamaConfig
from llm.nodes import OpenAINode
from llm.nodes import OllamaNode
from conf.llm_config import LlamaConfig
from utils.path import root_dir

lgr = logger_factory.default


def test_file_upload():
    llm_conf = OpenaiConfig()
    openai.api_key = llm_conf.API_KEY
    openai.base_url = 'https://api.evo4ai.com/v1/'

    file = openai.files.create(
        file=open(str(root_dir() / 'data' / 'cz_combined.json'), "rb"),
        purpose="assistants",
    )
    file_id = file.id
    print("Uploaded file ID:", file_id)

    assistant = openai.beta.assistants.create(
        name="File QA Bot",
        model="gpt-4o",
        tools=[{"type": "retrieval"}],  # 启用文档检索功能
        instructions="你是一个擅长阅读并回答文档问题的助手。"
    )
    thread = openai.beta.threads.create()
    openai.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="作为一个某个人物推文发布的训练数据，这个数据有什么不合理的地方吗。",
        file_ids=[file_id]
    )
    run = openai.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )
    # 等 run 执行完成
    while True:
        run_status = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run_status.status in ["completed", "failed"]:
            break
        time.sleep(1)
    messages = openai.beta.threads.messages.list(thread_id=thread.id)
    for msg in messages.data:
        print(msg.role, ":", msg.content[0].text.value)


def test_llm_create():
    # llm_conf = OpenaiConfig()
    # llm = LLM(llm_name='openai')
    llm2 = OpenAINode(llm_name='openai')
    resp = asyncio.run(llm2.chat([{'role': "user", 'content': 'hello'}]))
    print('')


def test_message_token_cost():
    from utils.llm_cost import count_gpt_message_tokens
    llm2 = OpenAINode(llm_name='openai')
    lgr.debug('test_message_token_cost')
    resp = asyncio.run(llm2.chat([{'role': "user", 'content': 'hello'}]))
    prompt_token = count_gpt_message_tokens([{'role': "user", 'content': 'hello'}], model=llm2.conf.MODEL)

    print('')


def test_action_node():
    messages = [
        {"role": "system", "content": 'You play a role in the blockchain area called "赵长鹏" （cz or changpeng zhao）.'
                                      ' Reply with his accent（learn from recent tweeting styles by search result).'},
        {"role": "user",
         "content": "Come up a tweet related to topic:'所有平台都在做 Meme Launchpad', which tweet characters must between 100 and 250. Just give the tweet, nothing extra.Easier to understand(English).Express some of my own opinions on this topic.Make sure you fully understand the relevant concepts of this topic and ensure the logic and rationality of the tweets you post about this topic. Be more diverse and don't always use fixed catchphrases.Your cognition is limited. For some unfamiliar fields, reply to tweets like a normal person. Sometimes casually, sometimes seriously. Don't act too much like an expert.Analyze cz's recent 30 tweet style (Retweets are not counted)."}
        # {"role": "user", "content": "给我cz的最近3条推文"}
    ]
    # messages = Message.from_messages(messages)

    # llm_conf = OpenaiConfig()
    llm_conf = LlamaConfig()
    # openai_node = OpenAINode(llm_name='openai', conf=llm_conf)
    openai_node = OllamaNode(llm_name='ollama', conf=llm_conf)
    resp = asyncio.run(openai_node.chat(messages))
    print('')


def test_ollama():
    resp = []
    for i in range(10):
        conversation = [
            # {
            #     'role': 'system',
            #     'content': 'You play a role in the blockchain area called "赵长鹏" （cz or changpeng zhao）. '
            #                'Reply with his accent, speak in his habit.'
            #                'He goes by the Twitter name CZ �� BNB or cz_binance and is commonly known as cz.'
            # },
            {
                'role': 'user',
                'content': 'You play a role in the blockchain area called "赵长鹏" （cz or changpeng zhao）. '
                           'Reply with his accent, speak in his habit.'
                           'He goes by the Twitter name CZ �� BNB or cz_binance and is commonly known as cz.'
                           'Now post a tweet. Follow these points'
                           "1. Don't @ others, mention others. Don't ReTweet(RT) other tweet."
                           "2. Your tweet don't include media, so try to be as complete as possible."
                           f"3. If tweet published has any time factor, today is {str(date.today())}, check the language for legitimacy and logic."
            }
        ]
        node = OllamaNode(llm_name='cz', conf=LlamaConfig())
        print('res')
        res = asyncio.run(node.chat(conversation))
        cleaned = re.sub(r'<think>.*?</think>', '', res, flags=re.DOTALL).lstrip().rstrip()
        resp.append(cleaned)
    with open('./text1.txt', 'w', encoding='utf-8') as f:
        for i in range(len(resp)):
            f.write(f'{i + 1} ---> {resp[i]}\n')
    print(res)


def test_generate_cot():
    import json
    with open(str(root_dir() / 'data' / 'cz_filtered.json'), 'r') as f:
        json_data = json.load(f)
    for i in json_data:
        c = [{'role': 'user',
              'content': """
    Here are a tweet, based on tweet, give me a CoT, and a question(The main purpose is to tweet, for example, to post a tweet about "my donation")
    ### Tweet
    {t}
              """.format(c='', q='', t=i['text'])
              }]
        node = OllamaNode(llm_name='cz', conf=LlamaConfig())
        res = asyncio.run(node.chat(c))
        print('')


def test_openai_node_cost():
    """测试OpenAINode的cost计算功能，覆盖常用模型和典型输入输出场景"""
    llm2 = OpenAINode(llm_name='openai')
    messages = [
        {'role': "user", 'content': '生成一个香港的地址'},
    ]
    resp = asyncio.run(llm2.chat(messages))
    cost = getattr(llm2, 'cost', None)
    # print(f"cost: {cost}")
    assert cost is not None and cost.total_cost > 0, "cost计算应大于0"
    # 可根据需要添加不同模型、不同输入的测试


async def test_async_singleton_behavior():
    node1 = OpenAINode()
    node2 = await asyncio.get_event_loop().run_in_executor(None, OpenAINode)
    assert id(node1) == id(node2)


def test_ollama_singleton():
    ollama1 = OllamaNode()
    ollama2 = OllamaNode()
    assert id(ollama1) == id(ollama2)


async def test_concurrent_instances():
    async def create_instance():
        return OpenAINode()

    results = await asyncio.gather(*[create_instance() for _ in range(5)])
    assert all(r is results[0] for r in results)

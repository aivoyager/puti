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

from llm.nodes import LLMNode
from conf.llm_config import OpenaiConfig
from llm.nodes import OpenAINode
from llm.nodes import OllamaNode
from conf.llm_config import LlamaConfig
from utils.path import root_dir


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
            f.write(f'{i+1} ---> {resp[i]}\n')
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






"""
@Author: obstacle
@Time: 21/01/25 15:32
@Description:  
"""
import openai
import langchain

from langchain.agents import (create_structured_chat_agent, load_tools,
                              initialize_agent, AgentType)
from langchain.memory import ConversationBufferMemory
from langchain_openai.llms import OpenAI
from langchain.chains import LLMChain
from langchain_openai.chat_models import ChatOpenAI
from httpx import Client
from langchain.prompts import ChatPromptTemplate
from langchain.prompts.chat import ChatMessagePromptTemplate
from puti.conf.config import conf
from puti.llm.prompts import prompt_setting
from langchain import hub


langchain.debug = True


def get_chat_openai() -> ChatOpenAI:
    local_wrap_params = {
        'openai_api_base': 'http://127.0.0.1:7861/v1',
        'openai_api_key': 'EMPTY'
    }
    params = {
        'model_name': 'gpt-4o-mini',
        'temperature': 0.7,
        'max_tokens': None,  # default max len for specific model
        'verbose': True,
        'streaming': True,
        'openai_api_base': conf.cc.module['llm'][0]['openai']['BASE_URL'],
        'openai_api_key': conf.cc.module['llm'][0]['openai']['API_KEY'],
        'openai_proxy': ''
    }
    model = ChatOpenAI(**params)
    return model


def get_openai_cli() -> OpenAI:
    params = {
        'base_url': conf.cc.module['llm']['BASE_URL'],
        'api_key': conf.cc.module['llm']['API_KEY'],
        'http_client': Client(**{
            'timeout': 300,  # time-out period
            'proxies': {
                "all://127.0.0.1": None,
                "all://localhost": None,
                "http://": None,
                "https://": None,
                "all://": None
            },
            'base_url': conf.cc.module['llm']['BASE_URL']
        })
    }
    cli = openai.Client(**params)
    return cli


def load_my_tools(llm: ChatOpenAI):
    tools = load_tools(['llm-math', 'wikipedia'], llm)
    return tools


def create_agents():
    llm = get_chat_openai()
    my_tools = load_my_tools(llm)
    memory = ConversationBufferMemory(llm=llm, conversation_id='chat1', message_limit=-1)

    # plan A
    agent = initialize_agent(
        my_tools,
        llm,
        agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        memory=memory,
        handler_parsing_errors=True,
        verbose=True,
        prompt='haha'
    )

    # plan B
    prompt = hub.pull('hwchase17/structured-chat-agent')
    agent = create_structured_chat_agent(llm=llm, tools=my_tools, prompt=prompt)
    # agent = AgentExecutor(agent=agent, verbose=True, callbacks=None)
    return agent


def create_model_chain(
        model=None,
        prompt=None,
        history=None,
        tools=None,
        callback=None
):
    llm = get_chat_openai()
    model_name = conf.cc.module['llm'][0]['openai']['MODEL']
    history = [
        # SystemMessagePromptTemplate.from_template('You are a helpful assistant.'),
        {'system': 'You are a helpful assistant.'},
        {'role': 'human', 'content': 'Hi, What is your name?'},
        {'role': 'ai', 'content': 'I am Stitch, thank you! How about you?'}
    ]
    role_maps = {"ai": "assistant", "human": "user"}
    input_text = prompt_setting.llm_model[model_name]
    input_text = ChatMessagePromptTemplate.from_template(
        template=input_text,
        role=role_maps['human'],
        template_format='jinja2'
    )
    chat_prompt = ChatPromptTemplate.from_messages([input_text])
    # prompt = chat_prompt.format_messages(input=input_text)  # format for interface

    # add history in memory
    memory = ConversationBufferMemory(llm=llm, conversation_id='chat1', message_limit=-1)
    for msg in history:
        if msg['role'] == 'human':
            memory.chat_memory.add_user_message(msg['content'])
        else:
            memory.chat_memory.add_ai_message(msg['content'])

    chain = LLMChain(prompt=chat_prompt, llm=llm, memory=memory)
    # full_chain = {"input": lambda x: x["input"]} | chain
    return chain






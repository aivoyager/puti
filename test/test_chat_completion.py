"""
@Author: obstacle
@Time: 21/01/25 15:01
@Description:  
"""
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

from puti.utils.llm import get_chat_openai, create_model_chain, create_agents


def test_chat_completion():
    # cli = get_openai_cli()
    model = get_chat_openai()
    # assert cli
    print('')


def test_create_model_chain():
    chain = create_model_chain()
    resp = chain.run('what is u name ?')
    print(resp)


def test_create_agents():
    agents = create_agents()
    res = agents.run('what is 1 + 1')
    res2 = agents.run('who is chris')
    print(f'res ---> {res}')
    print(f'res2 ---> {res2}')

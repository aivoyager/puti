"""
@Author: obstacles
@Time:  2025-03-07 15:38
@Description:  
"""
import asyncio

from llm.roles.talker import Talker


def test_chat():
    msg = 'hello, what is u name'
    talker = Talker()
    while msg:
        msg = asyncio.run(talker.run(msg))
        print('')
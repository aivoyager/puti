"""
@Author: obstacles
@Time:  2025-04-09 16:35
@Description:  
"""
from abc import ABC

from llm.tools import BaseTool
from pydantic import ConfigDict
from llm.nodes import OllamaNode
from conf.llm_config import LlamaConfig


class GenerateCzTweet(BaseTool, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = 'generate_cz_tweet'
    desc: str = 'Use this tool to generate a cz tweet can be posted on twitter.'

    async def run(self, *args, **kwargs):
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
        resp = await node.chat(conversation)
        return {'generated_tweet': resp}

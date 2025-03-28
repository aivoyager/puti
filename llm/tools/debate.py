"""
@Author: obstacles
@Time:  2025-03-13 11:06
@Description:  
"""
from llm.tools import BaseTool
from pydantic import ConfigDict
from llm.nodes import LLMNode, OpenAINode
from llm.messages import Message


class Debate(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = 'Debate'
    desc: str = 'Use this action in debating.'

    async def run(self, messages, llm: LLMNode = None, *args, **kwargs):
        reply = await llm.achat(messages)
        return reply

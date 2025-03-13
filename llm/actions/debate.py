"""
@Author: obstacles
@Time:  2025-03-13 11:06
@Description:  
"""
from llm.actions import Action
from pydantic import ConfigDict
from llm.nodes import LLMNode, OpenAINode
from llm.messages import Message


class Debate(Action):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = 'Debate'
    desc: str = 'Use this action to convince others and prove your point'

    async def run(self, messages, llm: LLMNode = None, *args, **kwargs):
        reply = await llm.achat(messages)
        return reply

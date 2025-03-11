"""
@Author: obstacles
@Time:  2025-03-07 14:41
@Description:  
"""
from llm.actions import Action
from pydantic import ConfigDict
from llm.nodes import LLMNode, OpenAINode
from llm.messages import Message


class Reply(Action):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = 'Reply'
    desc: str = 'Use this action to reply user message.'

    async def run(self, messages, llm: LLMNode = None, *args, **kwargs):
        reply = await llm.achat(messages)
        return reply

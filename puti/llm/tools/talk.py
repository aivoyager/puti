"""
@Author: obstacles
@Time:  2025-03-07 14:41
@Description:  
"""
from puti.llm.tools import BaseTool, ToolArgs
from pydantic import ConfigDict, Field
from puti.llm.nodes import LLMNode, OpenAINode
from puti.llm.messages import Message


class TalkArgs(ToolArgs):
    text: str = Field(description='content of reply')


class Reply(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = 'reply'
    desc: str = 'Use this tool to reply others.'
    args: TalkArgs = None

    async def run(self, text, *args, **kwargs):
        return text

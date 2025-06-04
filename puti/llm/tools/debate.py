"""
@Author: obstacles
@Time:  2025-03-13 11:06
@Description:  
"""
from puti.llm.tools import BaseTool
from pydantic import ConfigDict, Field
from puti.llm.tools import ToolArgs
from typing import Dict, List, Annotated


class DebateArgs(ToolArgs):
    opinion: str = Field(description="Content of speech")
    # history_memory: List[
    #     Annotated[
    #         Dict[
    #             Annotated[str, 'user name'],
    #             Annotated[str, 'actual content']
    #         ],
    #         ("Dialog, A dictionary contains only a pair of key and value that represent a user's speech."
    #          " key is the user name, and value is the content of the speech")
    #     ]
    # ] = Field(
    #     description='Chat logs of actual conversations based on your memory in json format'
    # )


class Debate(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = 'debate'
    desc: str = 'Use this tool to make your point in an argument.'
    args: DebateArgs = None

    async def run(self, opinion, *args, **kwargs):
        return opinion



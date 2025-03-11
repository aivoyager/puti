"""
@Author: obstacle
@Time: 21/01/25 11:16
@Description:  
"""
from typing import Annotated

from pydantic import BaseModel, Field, ConfigDict
from llm.nodes import LLMNode, OpenAINode
from abc import ABC, abstractmethod


class Action(BaseModel, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = Field(default='', description='Action name')
    desc: str = Field(default='', description='Description of action')

    @abstractmethod
    async def run(self, messages, llm: LLMNode = None, *args, **kwargs) -> Annotated[str, 'action result']:
        """ run action """

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        return self.__str__()


class UserRequirement(Action):
    """From user demands"""

    def run(self, messages, llm=None, **kwargs):
        """ nothing """

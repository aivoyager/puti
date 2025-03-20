"""
@Author: obstacle
@Time: 21/01/25 11:16
@Description:  
"""
from typing import Annotated

from pydantic import BaseModel, Field, ConfigDict
from llm.nodes import LLMNode, OpenAINode
from abc import ABC, abstractmethod


class ActionArgs(BaseModel, ABC):
    """ Action arguments """


class Action(BaseModel, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = Field(default='', description='Action name')
    desc: str = Field(default='', description='Description of action')
    intermediate: bool = Field(
        default=False,
        description='Intermediate action, When called over will publish message to myself rather than broadcast')
    args: ActionArgs = None

    __hash__ = object.__hash__

    @abstractmethod
    async def run(self, *args, **kwargs) -> Annotated[str, 'action result']:
        """ run action """

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        return self.__str__()


class IntermediateAction(Action):
    """ For message field `cause by` """

    role_name: str = Field(default='', description='bind to a role for intermediate action')

    def run(self, *args, **kwargs) -> Annotated[str, 'action result']:
        pass


class UserRequirement(Action):
    """From user demands"""

    name: str = 'user requirement'

    def run(self, messages, llm=None, **kwargs):
        """ nothing """

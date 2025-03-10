"""
@Author: obstacle
@Time: 21/01/25 11:16
@Description:  
"""
from pydantic import BaseModel, Field, ConfigDict
from llm.nodes import LLMNode, OpenAINode


class Action(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = Field(default='', description='Action name')
    node: LLMNode = Field(default=None, exclude=True)
    desc: str = Field(default='', description='Description of action')

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        return self.__str__()


class UserRequirement(Action):
    """From user demands"""

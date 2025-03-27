"""
@Author: obstacle
@Time: 21/01/25 11:16
@Description:  
"""
from typing import Annotated, Dict, TypedDict, Any, Required, NotRequired

from pydantic import BaseModel, Field, ConfigDict
from llm.nodes import LLMNode, OpenAINode
from abc import ABC, abstractmethod
from constant.llm import ParamMap


# class ParamRespFunction(TypedDict):
#     name: Required[str]
#     description: Required[str]
#     parameters: NotRequired[Dict[str, Any]]


class ParamResp(TypedDict):
    type: Required[str]
    function: Required[Dict]


class ActionArgs(BaseModel, ABC):
    """ Action arguments """


class Action(BaseModel, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = Field(..., description='Action name')
    desc: str = Field(default='', description='Description of action')
    intermediate: bool = Field(
        default=False,
        description='Intermediate action, When called over will publish message to myself rather than broadcast')
    args: ActionArgs = None

    __hash__ = object.__hash__

    @property
    def param(self) -> ParamResp:
        action = {
            'type': 'function',
            'function': {
                'name': self.name,
                'description': self.desc
            }
        }

        args: ActionArgs = self.__class__.__annotations__.get('args')
        if args:

            required_fields = []
            properties_obj = {}
            for arg_name, arg_info in args.model_fields.items():
                field_type = args.__annotations__[arg_name].__name__
                field_type = ParamMap.elem_from_str(field_type).dsp
                is_required = arg_info.is_required()
                description = arg_info.description

                if is_required:
                    required_fields.append(arg_name)

                properties_obj.update({arg_name: {'type': field_type, 'description': description}})

            parameter = {
                    'type': 'object',
                    'properties': properties_obj,
                    'required': required_fields
                }
            action['function']['parameters'] = parameter
        return ParamResp(**action)

    @abstractmethod
    async def run(self, *args, **kwargs) -> Annotated[str, 'action result']:
        """ run action """

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        return self.__str__()


class IntermediateAction(Action):
    """ For message field `cause by` """

    name: str = 'intermediate action'
    role_name: str = Field(default='', description='bind to a role for intermediate action')

    def run(self, *args, **kwargs) -> Annotated[str, 'action result']:
        pass


class UserRequirement(Action):
    """From user demands"""

    name: str = 'user requirement'

    def run(self, messages, llm=None, **kwargs):
        """ nothing """

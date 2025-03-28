"""
@Author: obstacle
@Time: 21/01/25 11:16
@Description:  
"""
import os
import sys
import asyncio
import importlib
import pkgutil
import inspect

from typing import Annotated, Dict, TypedDict, Any, Required, NotRequired, List, Type, Set, cast
from pydantic import BaseModel, Field, ConfigDict
from llm.nodes import LLMNode, OpenAINode
from abc import ABC, abstractmethod
from constant.llm import ParamMap
from logs import logger_factory
from pydantic.fields import FieldInfo


lgr = logger_factory.llm


class ModelFields(TypedDict):
    """ using in fc data structure """
    name: Required[FieldInfo]
    desc: Required[FieldInfo]
    intermediate: Required[FieldInfo]
    args: NotRequired['ToolArgs']


class ParamResp(TypedDict):
    type: Required[str]
    function: Required[Dict]


class ToolArgs(BaseModel, ABC):
    """ Action arguments """


class BaseTool(BaseModel, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    name: str = Field(..., description='Tool name')
    desc: str = Field(default='', description='Description of tool')
    args: ToolArgs = None

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

        args: ToolArgs = self.__class__.__annotations__.get('args')
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
    async def run(self, *args, **kwargs) -> Annotated[str, 'tool result']:
        """ run action """

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        return self.__str__()


class Toolkit(BaseModel, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    tools: Dict[str, 'BaseTool'] = Field(default={}, description='List of tools')

    def add_tool(self, tool: Type[BaseTool]) -> Dict[str, 'BaseTool']:
        t = tool()
        if t.name in self.tools:
            lgr.warning(f'Tool {t.name} has been added in toolkit')
            return {}
        self.tools.update({t.name: t})
        return {t.name: t}

    def add_tools(self, tools: List[Type[BaseTool]]) -> List[Dict[str, 'BaseTool']]:
        resp = []
        for t in tools:
            r = self.add_tool(t)
            resp.append(r)
        return resp

    @property
    def param_list(self):
        resp = []
        for tool_name, tool in self.tools.items():
            resp.append(tool.param)
        return resp


toolkit = Toolkit()

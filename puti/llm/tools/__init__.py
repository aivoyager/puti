"""
@Author: obstacle
@Time: 21/01/25 11:16
@Description:  
"""
import inspect

from puti.utils.common import tool_args_to_fc_schema
from typing import Annotated, Dict, TypedDict, Any, Required, NotRequired, List, Type, Set, cast, Optional
from pydantic import BaseModel, Field, ConfigDict
from abc import ABC, abstractmethod
from puti.logs import logger_factory
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

    name: str = Field(..., description='Tool name，The names need to be hump nomenclature')
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

        args: Type[ToolArgs] = self.__class__.__annotations__.get('args')
        if args:
            fc_json = tool_args_to_fc_schema(args)
            action['function']['parameters'] = fc_json
        return ParamResp(**action)

    @abstractmethod
    async def run(self, *args, **kwargs) -> Annotated[str, 'tool result']:
        """ run action """

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        return self.__str__()

    def __init_subclass__(cls):
        """ subclass `run` method must contain *args and **kwargs """
        super().__init_subclass__()
        run_method = cls.__dict__.get('run', None)
        if run_method is None:
            return
        sig = inspect.signature(run_method)
        has_args = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())
        has_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
        if not (has_args and has_kwargs):
            raise TypeError(f"{cls.__name__}.run must accept *args and **kwargs")


class Toolkit(BaseModel, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    tools: Dict[str, 'BaseTool'] = Field(default={}, description='List of tools')

    def intersection_with(self, other: Set[str], inplace: bool = False):
        toolkit_tools = set(self.tools.keys())
        intersection = other.intersection(toolkit_tools)
        remove_tools = toolkit_tools.difference(intersection)
        if inplace:
            for tool_name in list(remove_tools):
                self.remove_tool(tool_name)
        else:
            return Toolkit(tools={tool_name: self.tools.get(tool_name) for tool_name in list(intersection)})

    def remove_tool(self, tool_name: str):
        if tool_name in self.tools:
            self.tools.pop(tool_name)
            # lgr.debug(f'{tool_name} has been removed from toolkit')
        else:
            lgr.warning('Removal did not take effect, {} not found in toolkit'.format(tool_name))

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

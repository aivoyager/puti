"""
@Author: obstacles
@Time:  2025-03-26 14:35
@Description:  
"""
import os
import sys
import argparse
import json
import logging

logging.basicConfig(level=logging.ERROR)

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from puti.llm.tools.project_analyzer import ProjectAnalyzer
from puti.llm.tools.generate_tweet import GenerateCzTweet
from puti.llm.tools.terminal import Terminal
from puti.llm.tools.python import Python
from puti.llm.tools.file import File
from puti.llm.tools.web_search import WebSearch
from inspect import Parameter, Signature
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, List, Type, Any
from puti.llm.tools import BaseTool
from mcp.server.fastmcp import FastMCP
from puti.logs import logger_factory
from puti.constant.client import McpTransportMethod


lgr = logger_factory.client


class MCPServer(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    transport: McpTransportMethod = Field(default=McpTransportMethod.STDIO, validate_default=True, description='communication method')
    server: FastMCP = Field(default_factory=lambda: FastMCP('puti'), validate_default=True)

    @staticmethod
    def _build_docstring(tool: BaseTool) -> str:
        parameter = tool.param
        docstring = tool.desc
        args = parameter['function'].get('parameters', {})
        required_params = parameter['function'].get('parameters', {}).get('required', [])
        if args:
            docstring += "\n\nParameters:\n"
            for k, v in args.get('properties').items():
                required_desc = '(required)' if k in required_params else '(optional)'
                param_type = v.get('type', 'any')
                param_desc = v.get('description', '')
                docstring += f'{k} ({param_type}) {required_desc}: {param_desc}\n'
        return docstring

    @staticmethod
    def _build_signature(tool: BaseTool) -> Signature:
        parameter = tool.param
        args = parameter['function'].get('parameters', {})
        required_params = parameter['function'].get('parameters', {}).get('required', [])
        parameters = []
        for k, v in args.get('properties', {}).items():
            param_type = v.get('type', '')
            default = Parameter.empty if k in required_params else None
            annotation = Any
            if param_type == "string":
                annotation = str
            elif param_type == "integer":
                annotation = int
            elif param_type == "number":
                annotation = float
            elif param_type == "boolean":
                annotation = bool
            elif param_type == "object":
                annotation = dict
            elif param_type == "array":
                annotation = list
            param = Parameter(
                name=k,
                kind=Parameter.KEYWORD_ONLY,
                default=default,
                annotation=annotation
            )
            parameters.append(param)
        return Signature(parameters=parameters)

    def add_tools(self, tools: List[Type[BaseTool]]):
        for tool in tools:
            obj = tool()

            async def tool_dynamic(**kwargs):
                lgr.debug(f'perform action: {tool.name}')
                resp = await tool.run(**kwargs)
                lgr.debug(f'action response: {resp}')
                return json.dumps(resp, ensure_ascii=False)

            tool_dynamic.__name__ = obj.name
            tool_dynamic.__doc__ = self._build_docstring(obj)
            tool_dynamic.__signature__ = self._build_signature(obj)
            tool_dynamic.__parameter_schema__ = {
                k: {
                    'description': v.get('description', ''),
                    'type': v.get('type', 'any'),
                    'required': k in obj.param['function'].get('parameters', {}).get('required', [])
                }
                for k, v in obj.param['function'].get('parameters', {}).get('properties', {}).items()
            }

            self.server.tool()(tool_dynamic)
            # lgr.info(f'add tool `{obj.name}` to mpc')

    def run(self):
        # lgr.info('mcp server started...')
        self.server.run(transport=self.transport.val)


if __name__ == '__main__':
    mcp = MCPServer()
    mcp.add_tools([Terminal, Python, File, WebSearch, ProjectAnalyzer])
    mcp.run()

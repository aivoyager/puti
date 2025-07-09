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

# sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# Delay these imports to avoid issues during testing
# from puti.llm.tools.project_analyzer import ProjectAnalyzer
# from puti.llm.tools.generate_tweet import GenerateCzTweet
# from puti.llm.tools.terminal import Terminal
# from puti.llm.tools.python import Python
# from puti.llm.tools.file import File
# from puti.llm.tools.web_search import WebSearch
from contextlib import asynccontextmanager
from inspect import Parameter, Signature
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr
from typing import Literal, List, Type, Any, Dict, Optional
from puti.llm.tools import BaseTool
from mcp.server.fastmcp import FastMCP
from mcp.shared.message import SessionMessage
from mcp.server.transport_security import TransportSecurityMiddleware, TransportSecuritySettings
from puti.logs import logger_factory
from puti.constant.client import McpTransportMethod
from puti.core.schema import SessionMessage
from uuid import UUID, uuid4
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Mount, Route
from starlette.requests import Request
from starlette.types import Receive, Scope, Send
from puti.mcpp.schema import SeverMessageMetadata
from puti.constant.api import RequestMethod
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream


lgr = logger_factory.client


class MCPServer(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    # sse
    endpoint: PrivateAttr(str) = Field(..., description='Endpoint for the MCP server')
    read_stream_writers: Dict[UUID, MemoryObjectSendStream[]]

    transport: McpTransportMethod = Field(default=McpTransportMethod.STDIO, validate_default=True, description='communication method')
    server: FastMCP = Field(default_factory=lambda: FastMCP('puti'), validate_default=True)
    tools_registry: Dict[str, BaseTool] = Field(default_factory=dict)
    port: Optional[int] = Field(default=3000, description='Port for SSE server')
    host: Optional[str] = Field(default="localhost", description='Host for SSE server')

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
            self.tools_registry[obj.name] = obj

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
            
        # Register the 'see' method as a tool
        async def see_tool_dynamic(**kwargs):
            lgr.debug('perform action: see')
            tools_info = self.see()
            lgr.debug(f'action response: {tools_info}')
            return json.dumps(tools_info, ensure_ascii=False)
            
        see_tool_dynamic.__name__ = "see"
        see_tool_dynamic.__doc__ = "Return information about all available tools registered in the server"
        see_tool_dynamic.__signature__ = Signature(parameters=[])
        see_tool_dynamic.__parameter_schema__ = {}
        
        self.server.tool()(see_tool_dynamic)
        lgr.info(f'added built-in `see` tool to mcp')



    @asynccontextmanager
    def connect_see(self, scope: Scope, receive: Receive, send: Send) -> Dict[str, Dict]:
        """Return information about all available tools registered in the server"""
        if scope['type'] != 'http':
            lgr.error('connect_see only supports HTTP connections')
            raise ValueError('connect_see only supports HTTP connections')

        request = Request(scope, receive)
        content_type = request.headers.get('content-type')
        host = request.headers.get('host')


        if request.method == RequestMethod.POST.val:
            if not content_type:
                lgr.error('Content-Type header is missing')
                raise ValueError('Content-Type header is missing')
            # TODO: DNS rebinding protection
            if not content_type.lower().startswith('application/json'):
                lgr.error('')
                raise ValueError('')



        tools_info = {}
        for name, tool in self.tools_registry.items():
            tools_info[name] = {
                "description": tool.desc,
                "parameters": tool.param['function'].get('parameters', {})
            }
        return tools_info

    def run(self):
        """Run the MCP server with the configured transport method"""
        if self.transport == McpTransportMethod.SSE:
            transport_info = f"using SSE transport on {self.host}:{self.port}"
            
            # 在运行之前设置环境变量，FastMCP会读取这些环境变量
            os.environ["PORT"] = str(self.port)
            os.environ["HOST"] = self.host
            
            # 只传递transport参数
            self.server.run(transport=self.transport.val)
            
            lgr.info(f"MCP server started {transport_info}")
        else:
            transport_info = "using STDIO transport"
            # STDIO模式不需要传递port和host参数
            self.server.run(transport=self.transport.val)
            
            lgr.info(f"MCP server started {transport_info}")


def get_default_tools():
    """Get default tools with lazy importing to avoid issues during testing"""
    from puti.llm.tools.terminal import Terminal
    from puti.llm.tools.python import Python
    from puti.llm.tools.file import File
    from puti.llm.tools.web_search import WebSearch
    from puti.llm.tools.project_analyzer import ProjectAnalyzer
    return [Terminal, Python, File, WebSearch, ProjectAnalyzer]


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="MCP Server")
    parser.add_argument("--transport", "-t", type=str, choices=["stdio", "sse"], default="stdio",
                        help="Transport method: stdio or sse (experimental)")
    parser.add_argument("--port", "-p", type=int, default=3002, help="Port for SSE server (experimental)")
    parser.add_argument("--host", "-H", type=str, default="localhost", help="Host for SSE server (experimental)")
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    
    # 根据命令行参数设置传输方式
    transport_method = McpTransportMethod.STDIO
    if args.transport == "sse":
        transport_method = McpTransportMethod.SSE
        print("警告: SSE传输方式目前为实验性功能，可能不稳定")
        print(f"尝试在 {args.host}:{args.port} 启动SSE服务器")
        
    # 创建并配置服务器
    mcp = MCPServer(
        transport=transport_method,
        port=args.port,
        host=args.host
    )
    
    # 添加工具并运行服务器
    mcp.add_tools(get_default_tools())
    mcp.run()

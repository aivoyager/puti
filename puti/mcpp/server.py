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
import uvicorn
import anyio

logging.basicConfig(level=logging.ERROR)

from contextlib import asynccontextmanager
from inspect import Parameter, Signature
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr, SkipValidation
from typing import List, Type, Any, Dict, Optional, Union, Annotated
from puti.llm.tools import BaseTool
from mcp.server import Server
from mcp.server.stdio import stdio_server
from puti.constant.client import McpTransportMethod
from puti.core.schema import SessionMessage
from uuid import UUID, uuid4
from urllib.parse import quote
from starlette.applications import Starlette
from starlette.responses import Response, JSONResponse
from starlette.routing import Route
from starlette.requests import Request
from starlette.types import Receive, Scope, Send
from sse_starlette import EventSourceResponse
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from puti.llm.tools import BaseToolCls
from puti.logs import logger_factory
from puti.constant.api import RequestMethod


lgr = logger_factory.client


class MCPServer(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    transport: McpTransportMethod = Field(McpTransportMethod.SSE, validate_default=True, description='communication method')
    server: Optional[Server] = Field(default=None, description="MCP Server instance, initialized in post_init")
    port: Optional[int] = Field(default=3000, description='Port for SSE server')
    host: Optional[str] = Field(default="127.0.0.1", description='Host for SSE server')

    # sse
    _endpoint: str = PrivateAttr(default='/mcp/')
    read_stream_writers: Annotated[Dict[UUID, MemoryObjectSendStream[Union[SessionMessage, Exception]]], SkipValidation] = {}

    tools_registry: Dict[str, Any] = Field(default_factory=dict, validate_default=True)

    @staticmethod
    def _build_docstring(tool: BaseTool) -> str:
        parameter = tool.param
        docstring = str(tool.desc)
        args = parameter['function'].get('parameters', {})
        required_params = parameter['function'].get('parameters', {}).get('required', [])
        if args and args.get('properties'):
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

    def add_tools(self, tools: List[BaseToolCls]):
        for tool in tools:
            obj = tool()

            async def tool_dynamic(**kwargs):
                lgr.debug(f'perform action: {obj.name}')
                resp = await obj.run(**kwargs)
                lgr.debug(f'action response: {resp}')
                return json.dumps(resp, ensure_ascii=False)

            tool_name = str(obj.name)
            tool_dynamic.__name__ = tool_name
            tool_dynamic.__doc__ = self._build_docstring(obj)
            tool_dynamic.__signature__ = self._build_signature(obj)
            tool_dynamic.__parameter_schema__ = obj.param['function'].get('parameters', {})

            self.tools_registry[tool_name] = tool_dynamic
            lgr.info(f'add tool `{tool_name}` to mcp')

    async def get_tools_sse(self, request: Request):
        """
        Streams the list of available tools over an SSE connection.
        The connection is automatically closed after all tools are sent.
        If the transport is not SSE, it returns an error response.
        """
        if self.transport != McpTransportMethod.SSE:
            lgr.warning("Attempted to access /tools SSE endpoint when transport is not SSE.")
            return JSONResponse(
                status_code=405,
                content={"error": "This endpoint is only available for SSE transport method."}
            )

        async def tool_event_generator():
            lgr.debug("Starting to stream tools.")
            for name, handler in self.tools_registry.items():
                tool_info = {
                    'name': name,
                    'description': handler.__doc__,
                    'inputSchema': getattr(handler, '__parameter_schema__', {})
                }
                yield {
                    "event": "tool_info",
                    "data": json.dumps(tool_info)
                }
            
            # After sending all tools, the client should close the connection.
            # We can optionally send a 'done' event.
            lgr.debug("Finished streaming tools, sending done event.")
            # yield {
            #     "event": "done",
            #     "data": json.dumps({"status": "complete"})
            # }

        return EventSourceResponse(tool_event_generator())

    def get_tools_stdio(self):
        """Prepares the server for STDIO transport by ensuring tools are registered."""
        # The actual tool registration happens in model_post_init.
        # This method is for conceptual clarity and to fulfill the dynamic call request.
        lgr.info(f"STDIO mode selected. MCP Server is ready with {len(self.tools_registry)} tools.")
        # No further action needed here as self.server is already correctly initialized.

    @staticmethod
    def validate_request(request: Request):
        content_type = request.headers.get('content-type')
        host = request.headers.get('host')
        origin = request.headers.get('origin')

        if request.method == RequestMethod.POST.val:
            if not content_type:
                lgr.error('Content-Type header is missing')
                raise ValueError('Content-Type header is missing')
            if not content_type.lower().startswith('application/json'):
                lgr.error('Invalid Content-Type')
                raise ValueError('Invalid Content-Type')
            if not host:
                lgr.error('Missing Host header')
                raise ValueError('Missing Host header')
            if not origin:
                lgr.error('Missing Origin header')
                raise ValueError('Missing Origin header')

    @asynccontextmanager
    async def connect_see(self, scope: Scope, receive: Receive, send: Send):
        if scope['type'] != 'http':
            lgr.error('connect_see only supports HTTP connections')
            raise ValueError('connect_see only supports HTTP connections')

        request = Request(scope, receive)

        read_stream: MemoryObjectReceiveStream[Union[SessionMessage, Exception]]
        read_stream_writer: MemoryObjectSendStream[Union[SessionMessage, Exception]]
        write_stream: MemoryObjectSendStream[SessionMessage]
        write_stream_reader: MemoryObjectReceiveStream[SessionMessage]

        read_stream_writer, read_stream = anyio.create_memory_object_stream(0)
        write_stream, write_stream_reader = anyio.create_memory_object_stream(0)

        session_id = uuid4()
        self.read_stream_writers[session_id] = read_stream_writer
        root_path = scope.get('root_path', '')
        full_message_path_for_client = root_path.rstrip('/') + self._endpoint
        client_post_url_data = f'{quote(full_message_path_for_client)}?session_id={session_id.hex}'

        sse_stream_writer, see_stream_reader = anyio.create_memory_object_stream[dict[str, Any]](0)

        async def sse_writer():
            async with sse_stream_writer, write_stream_reader:
                await sse_stream_writer.send({'event': 'endpoint', 'data': client_post_url_data})

                async for session_message in write_stream_reader:
                    lgr.debug(f'sending message via see: {session_message}')
                    await sse_stream_writer.send(
                        {'event': 'message', 'data': session_message.message.model_dump_json(by_alias=True, exclude_none=True)}
                    )

        async with anyio.create_task_group() as tg:

            async def response_wrapper(scope: Scope, receive: Receive, send: Send):
                await EventSourceResponse(content=see_stream_reader, data_sender_callable=sse_writer)(scope, receive, send)
                await read_stream_writer.aclose()
                await write_stream_reader.aclose()
                lgr.debug('connection closed')

            tg.start_soon(response_wrapper, scope, receive, send)
            yield read_stream, write_stream

    def run(self):
        """Run the MCP server with the configured transport method"""
        if self.transport == McpTransportMethod.SSE:
            async def handle_sse(request):
                async with self.connect_see(
                        scope=request.scope,
                        receive=request.receive,
                        send=request._send
                ) as (read_stream, write_stream):
                    await self.server.run(read_stream, write_stream, self.server.create_initialization_options())
                return Response()
                      
            starlette_app = Starlette(
                debug=True,
                routes=[
                    Route('/sse', endpoint=handle_sse, methods=["GET"]),
                    Route('/tools', endpoint=self.get_tools_sse, methods=['GET'])
                ]
            )
            lgr.info(f"Starting SSE server on http://{self.host}:{self.port}")
            lgr.info(f"Tool list available as an SSE stream at http://{self.host}:{self.port}/tools")
            for route in starlette_app.routes:
                lgr.debug(f"{route.methods} {route.path}")
            uvicorn.run(starlette_app, host=self.host, port=self.port, log_level='debug')
        else:
            self.get_tools_stdio()
            async def arun():
                async with stdio_server() as (read_stream, write_stream):
                    await self.server.run(read_stream, write_stream, self.server.create_initialization_options())
            anyio.run(arun)

    @staticmethod
    def get_default_tools() -> List[BaseToolCls]:
        """Get default tools with lazy importing to avoid issues during testing"""
        from puti.llm.tools.terminal import Terminal
        from puti.llm.tools.python import Python
        from puti.llm.tools.file import File
        from puti.llm.tools.web_search import WebSearch
        from puti.llm.tools.project_analyzer import ProjectAnalyzer
        return [Terminal, Python, File, WebSearch, ProjectAnalyzer]

    def model_post_init(self, __context: Any) -> None:
        """Initialize the server instance after the model is created."""
        if not self.tools_registry:
            self.add_tools(self.get_default_tools())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run MCP Server")
    parser.add_argument('--transport', type=str, default='sse', choices=['sse', 'stdio'], help='Transport method to use')
    args = parser.parse_args()

    transport_method = McpTransportMethod.SSE if args.transport == 'sse' else McpTransportMethod.STDIO
    
    mcp = MCPServer(transport=transport_method)
    mcp.run()

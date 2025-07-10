"""
@Author: obstacles
@Time:  2025-03-26 11:46
@Description:  
"""
import asyncio
import os
import urllib.parse
import json

from typing import Optional, Dict, Any, Tuple, Literal
from contextlib import AsyncExitStack
from puti.utils.path import root_dir
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from puti.llm.nodes import OpenAINode
from anthropic import Anthropic
from dotenv import load_dotenv
from puti.constant.client import McpTransportMethod


class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
        self.connection_type: Optional[McpTransportMethod] = None

    async def connect_to_server(self, server_path: str, transport_method: McpTransportMethod = McpTransportMethod.STDIO):
        """Connect to an MCP server

        Args:
            server_path: Path to the server script (.py or .js) or URL for SSE connection
            transport_method: Connection method (STDIO or SSE)
        """
        self.connection_type = transport_method
        
        if transport_method == McpTransportMethod.STDIO:
            await self._connect_stdio(server_path)
        elif transport_method == McpTransportMethod.SSE:
            print("警告: SSE传输方式目前为实验性功能，可能不稳定")
            await self._connect_sse(server_path)
        else:
            raise ValueError(f"Unsupported transport method: {transport_method}")
        
        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print(f"\nConnected to server with {transport_method.val} transport. Available tools:", [tool.name for tool in tools])

    async def _connect_stdio(self, server_script_path: str):
        """Connect to a server using STDIO transport"""
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()

    async def _connect_sse(self, server_url: str):
        """Connect to a server using SSE transport"""
        if not (server_url.startswith('http://') or server_url.startswith('https://')):
            raise ValueError("SSE connection requires a valid HTTP or HTTPS URL")
        
        # 去除URL末尾的斜杠
        base_url = server_url.rstrip('/')
        
        # 尝试的路径列表 - FastMCP可能在其中一个路径上提供SSE服务
        paths_to_try = [
            "",             # 直接使用基础URL
            "/api",         # 常见API路径
            "/v1",          # 版本化API常见路径
            "/mcp",         # MCP相关路径
            "/sse",         # SSE特定路径
            "/events",      # 事件流相关路径
            "/mcp/api",     # 组合路径
            "/mcp/v1"       # 组合路径
        ]
        
        # 存储原始错误以便在所有尝试失败时报告
        last_error = None
        
        # 尝试每个路径
        for path in paths_to_try:
            try:
                full_url = f"{base_url}{path}"
                print(f"尝试连接到: {full_url}")
                
                sse_transport = await self.exit_stack.enter_async_context(sse_client(full_url))
                self.session = await self.exit_stack.enter_async_context(ClientSession(sse_transport))
                await self.session.initialize()
                
                # 如果成功，记录使用的URL并返回
                print(f"成功连接到: {full_url}")
                return
            except Exception as e:
                print(f"连接到 {full_url} 失败: {str(e)}")
                last_error = e
        
        # 如果所有尝试都失败，则抛出最后一个错误
        if last_error:
            raise RuntimeError(f"无法连接到SSE服务器，所有路径尝试失败: {str(last_error)}")
        else:
            raise RuntimeError("无法连接到SSE服务器，未知错误")

    async def see(self) -> Dict[str, Any]:
        """Fetch information about all available tools from the server"""
        if not self.session:
            raise RuntimeError("Not connected to a server. Call connect_to_server() first.")
        
        try:
            # Call the server's see method
            result = await self.session.call_tool("see", {})
            
            # 处理服务器返回的数据
            if result and hasattr(result, 'content'):
                # 如果返回的是列表，可能是TextContent对象列表
                if isinstance(result.content, list) and len(result.content) > 0:
                    # 尝试从第一个TextContent对象中提取JSON字符串
                    if hasattr(result.content[0], 'text'):
                        try:
                            return json.loads(result.content[0].text)
                        except json.JSONDecodeError:
                            print("Warning: Failed to parse JSON from server response")
                            return {}
                # 如果是字典，直接返回
                elif isinstance(result.content, dict):
                    return result.content
            
            # 返回空字典作为默认值
            return {}
        except Exception as e:
            print(f"Error fetching tools: {str(e)}")
            return {}

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        response = await self.session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

        # Initial Claude API call
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=messages,
            tools=available_tools
        )

        # resp = await openai_node.achat(messages, tools=available_tools)
        # Process response and handle tool calls
        final_text = []

        assistant_message_content = []
        for content in response.content:
            if content.type == 'text':
                final_text.append(content.text)
                assistant_message_content.append(content)
            elif content.type == 'tool_use':
                tool_name = content.name
                tool_args = content.input

                # Execute tool call
                result = await self.session.call_tool(tool_name, tool_args)
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

                assistant_message_content.append(content)
                messages.append({
                    "role": "assistant",
                    "content": assistant_message_content
                })
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": content.id,
                            "content": result.content
                        }
                    ]
                })

                # Get next response from Claude
                response = self.anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=messages,
                    tools=available_tools
                )

                final_text.append(response.content[0].text)

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries, 'see' to list available tools, or 'quit' to exit.")
        print(f"Connection type: {self.connection_type.val}")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == 'quit':
                    break

                if query.lower() == 'see':
                    tools_info = await self.see()
                    print("\nAvailable tools:")
                    for name, info in tools_info.items():
                        print(f"- {name}: {info['description']}")
                    continue

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    client = MCPClient()
    try:
        # 默认使用STDIO连接本地服务器
        server_path = str(root_dir() / 'mcpp' / 'test_server.py')
        
        # 可以通过环境变量设置连接方式和服务器地址
        transport = os.environ.get('MCP_TRANSPORT', 'stdio')
        if transport.lower() == 'sse':
            server_url = os.environ.get('MCP_SERVER_URL', 'http://localhost:3000')
            await client.connect_to_server(server_url, McpTransportMethod.SSE)
        else:
            await client.connect_to_server(server_path, McpTransportMethod.STDIO)
            
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == '__main__':
    openai_node = OpenAINode()
    load_dotenv()
    asyncio.run(main())

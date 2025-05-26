"""
@Author: obstacles
@Time:  2025-03-26 14:47
@Description:  
"""
import asyncio

from puti.mcpp.server import MCPServer
from puti.llm.tools.talk import Reply
from puti.llm.tools.demo import GetFlightInfo


def test_mcp_server():
    mcp = MCPServer()
    mcp.add_tools([GetFlightInfo])
    mcp.run()

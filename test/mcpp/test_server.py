"""
@Author: obstacles
@Time:  2025-03-26 14:47
@Description:  
"""
import asyncio

from mcpp.server import MCPServer
from llm.actions.talk import Reply
from llm.actions.get_flight_time import GetFlightInfo


def test_mcp_server():
    mcp = MCPServer()
    mcp.add_actions([GetFlightInfo])
    mcp.run()

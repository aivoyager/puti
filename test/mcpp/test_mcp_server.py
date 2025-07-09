"""
@Author: obstacles
@Time:  2025-03-26 14:47
@Description:  
"""
import asyncio
import json

from puti.mcpp.server import MCPServer
from puti.constant.client import McpTransportMethod
from puti.llm.tools.talk import Reply
from puti.llm.tools.demo import GetFlightInfo


def test_mcp_server():
    mcp = MCPServer()
    mcp.add_tools([GetFlightInfo])
    mcp.run()


def test_mcp_server_see():
    # Create server instance and add tools
    mcp = MCPServer(transport=McpTransportMethod.SSE)
    mcp.add_tools([GetFlightInfo, Reply])
    
    # Get the tools information using see method
    tools_info = mcp.see()
    
    # Verify the tools were registered correctly
    assert len(tools_info) == 2
    assert "GetFlightInfo" in tools_info
    assert "Reply" in tools_info
    
    # Verify tool info contains description and parameters
    for name, info in tools_info.items():
        assert "description" in info
        assert "parameters" in info
        
    print(f"Tools information: {json.dumps(tools_info, indent=2)}")
    return tools_info


if __name__ == "__main__":
    tools_info = test_mcp_server_see()
    print("Test passed successfully!")

"""
@Author: obstacles
@Time:  2023-07-22 10:00
@Description: 测试SSE模式的MCP服务器
"""
import sys
import os
import asyncio

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from puti.mcpp.server import MCPServer
from puti.llm.tools.demo import GetFlightInfo
from puti.constant.client import McpTransportMethod


def test_sse_server():
    """测试SSE模式的MCP服务器"""
    # 设置端口和主机
    port = 3002
    host = "localhost"
    
    print(f"启动SSE服务器在 {host}:{port}...")
    
    # 设置一些环境变量进行调试，尝试各种可能的环境变量名
    env_vars = {
        "PORT": str(port),
        "HOST": host,
        "MCP_PORT": str(port),
        "MCP_HOST": host,
        "FASTMCP_PORT": str(port),
        "FASTMCP_HOST": host
    }
    
    for k, v in env_vars.items():
        os.environ[k] = v
        print(f"设置环境变量: {k}={v}")
    
    # 创建服务器实例
    server = MCPServer(
        transport=McpTransportMethod.SSE,
        port=port,
        host=host
    )
    
    # 添加测试工具
    server.add_tools([GetFlightInfo])
    
    # 在启动服务器前打印工具信息
    tools_info = server.see()
    print(f"服务器注册的工具: {list(tools_info.keys())}")
    
    # 启动服务器
    print("服务器启动中...")
    
    # 设置调试标志以获取更多信息
    os.environ["DEBUG"] = "1"
    
    server.run()
    

if __name__ == "__main__":
    test_sse_server() 
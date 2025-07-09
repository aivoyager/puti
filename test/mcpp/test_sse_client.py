"""
@Author: obstacles
@Time:  2023-07-22 10:30
@Description: 测试SSE模式的MCP客户端
"""
import sys
import os
import json
import asyncio

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from puti.mcpp.client import MCPClient
from puti.constant.client import McpTransportMethod


async def test_sse_client():
    """测试SSE模式的MCP客户端"""
    # 设置服务器URL
    server_url = "http://localhost:3002"
    
    print(f"连接到SSE服务器: {server_url}...")
    
    # 创建客户端
    client = MCPClient()
    
    try:
        # 连接到SSE服务器
        await client.connect_to_server(server_url, McpTransportMethod.SSE)
        
        print("连接成功！正在获取工具信息...")
        
        # 使用see方法获取工具信息
        tools_info = await client.see()
        
        # 打印工具信息
        print(f"\n服务器工具信息:\n{json.dumps(tools_info, indent=2)}")
        print(f"可用工具: {list(tools_info.keys())}")
        
        # 简单的交互式测试
        print("\n开始交互式测试。输入 'quit' 退出")
        
        while True:
            cmd = input("\n输入命令 (see/quit): ").strip()
            
            if cmd.lower() == 'quit':
                break
                
            if cmd.lower() == 'see':
                tools_info = await client.see()
                print(f"\n更新的工具信息:\n{json.dumps(tools_info, indent=2)}")
            else:
                print(f"未知命令: {cmd}")
        
    finally:
        # 清理资源
        await client.cleanup()
        print("客户端已关闭")


if __name__ == "__main__":
    asyncio.run(test_sse_client()) 
"""
@Author: obstacles
@Time:  2025-03-17 14:00
@Description:
E         ollama._types.ResponseError: registry.ollama.ai/library/llama3_1:latest does not support tools (status code: 400)

"""
import asyncio

from ollama import Client
from llm.nodes import LlamaNode
from conf.llm_config import LlamaConfig

tools = [
    {
        "name": "get_weather",
        "description": "获取指定城市的天气信息",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "需要查询天气的城市名称"
                }
            },
            "required": ["city"]
        }
    }
]


def get_weather(city):
    """模拟获取天气信息的函数"""
    return f"The weather in {city} is sunny, 25°C."


def test_function_calling():
    node = LlamaNode(llm_name='llama', conf=LlamaConfig())
    msg = [{"role": "user", "content": "What's the weather like in Beijing?"}]
    resp = asyncio.run(node.achat(msg, tools=tools))
    print('')

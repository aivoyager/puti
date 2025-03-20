"""
@Author: obstacles
@Time:  2025-03-17 14:00
@Description:

"""
import asyncio
import json
import asyncio
import sys


from ollama import Client
from llm.nodes import LlamaNode
from conf.llm_config import LlamaConfig
from llm.envs import Env
from llm.roles.talker import Talker
from llm.messages import Message
from llm.roles.debater import Debater
from llm.nodes import LlamaNode, llama_node
from conf.llm_config import LlamaConfig

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定某个城市的实时天气信息",
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
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_flight_times',
            'description': 'Get the flight times between two cities',
            'parameters': {
                'type': 'object',
                'properties': {
                    'departure': {
                        'type': 'string',
                        'description': 'The departure city (airport code)',
                    },
                    'arrival': {
                        'type': 'string',
                        'description': 'The arrival city (airport code)',
                    },
                },
                'required': ['departure', 'arrival'],
            },
        },
    },
]


def get_flight_times(departure: str, arrival: str) -> str:
    flights = {
        'NYC-LAX': {'departure': '08:00 AM', 'arrival': '11:30 AM', 'duration': '5h 30m'},
        'LAX-NYC': {'departure': '02:00 PM', 'arrival': '10:30 PM', 'duration': '5h 30m'},
        'LHR-JFK': {'departure': '10:00 AM', 'arrival': '01:00 PM', 'duration': '8h 00m'},
        'JFK-LHR': {'departure': '09:00 PM', 'arrival': '09:00 AM', 'duration': '7h 00m'},
        'CDG-DXB': {'departure': '11:00 AM', 'arrival': '08:00 PM', 'duration': '6h 00m'},
        'DXB-CDG': {'departure': '03:00 AM', 'arrival': '07:30 AM', 'duration': '7h 30m'},
    }
    # 将出发地和目的地组合成键，并查找航班信息
    key = f'{departure}-{arrival}'.upper()
    return json.dumps(flights.get(key, {'error': 'Flight not found'}))


def get_weather(city):
    """模拟获取天气信息的函数"""
    return f"The weather in {city} is sunny, 25°C."


def test_function_calling():
    node = LlamaNode(llm_name='llama', conf=LlamaConfig())
    msg = [{"role": "user", "content": "What's the weather like in Beijing?"}]
    resp = asyncio.run(node.achat(msg, tools=tools))
    print('')


def test_function_calling_llama():
    tool_map = {
        "get_weather": get_weather,
        'get_flight_times': get_flight_times,
    }
    question = "从纽约(NYC)到洛杉矶(LAX)的航班飞多长时间"
    # question = "从纽约(NYC)到洛杉矶(LAX)的航班什么时候起飞"  # non logical
    msg = [{"role": "user", "content": question}]
    # msg = [{"role": "user", "content": "What's the weather like in Beijing now?"}]
    conf = LlamaConfig()
    ollama = Client(host=conf.BASE_URL)
    resp = ollama.chat(conf.MODEL, msg, tools=tools)
    msg.append(resp.message)
    if hasattr(resp.message, 'tool_calls') and resp.message.tool_calls:
        for call_tool in resp.message.tool_calls:
            func = tool_map.get(call_tool.function.name)
            func_args = call_tool.function.arguments
            func_resp = func(**func_args)
            msg.append({
                'role': 'tool',
                'content': str(func_resp)
            })
    final = ollama.chat(conf.MODEL, msg)
    print(final.message.content)
    reply = final.message.content
    print('')


def test_function_calling_llama_with_params():
    # msg = 'hello, what is u name'
    msg = '从纽约（NYC）到洛杉矶（LAX）的航班要飞多长时间'
    # talker = Talker()
    talker = Talker(agent_node=llama_node)
    msg = talker.cp.invoke(talker.run, msg)
    print(msg.data)












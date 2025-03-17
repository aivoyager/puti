"""
@Author: obstacle
@Time: 05/02/25 17:27
@Description:
Llama 3.1 已经在 Function calling 方面进行了微调。
它支持通过单一、嵌套和并行的方式调用函数，同时支持多轮调用函数。借助 Llama 3.1 您的 AI 应用可以处理涉及多个并行步骤的复杂任务。

ollama
together

"""
import ollama
from pymilvus import model, MilvusClient
import json


# 获取默认的嵌入函数
embedding_fn = model.DefaultEmbeddingFunction()

milvus_client = MilvusClient('./milvus_local.db')


# 模拟获取航班时间的API调用
# 在实际应用中，这会从实时数据库或API获取数据
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


# 在向量数据库中搜索与人工智能相关的数据
def search_data_in_vector_db(query: str) -> str:
    # 将查询转换为向量
    query_vectors = embedding_fn.encode_queries([query])

    # 执行向量数据库搜索
    res = milvus_client.search(
        collection_name="demo_collection",
        data=query_vectors,
        limit=2,  # 限制返回结果数量
        output_fields=["text", "subject"],  # 指定返回的字段
    )

    print(res)  # 打印搜索结果
    return json.dumps(res)


def run(model: str, question: str):
    client = ollama.Client(host='192.168.1.226:11434')
    # Initialize conversation with a user query
    messages = [{'role': 'user', 'content': question}]
    # First API call: Send the query and function description to the model
    response = client.chat(
        model=model,
        messages=messages,
        tools=[
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
            {
                'type': 'function',
                'function': {
                    'name': 'search_data_in_vector_db',
                    'description': 'Search about Artificial Intelligence data in a vector database',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'query': {
                                'type': 'string',
                                'description': 'The search query',
                            },
                        },
                        'required': ['query'],
                    },
                },
            },
        ],
    )
    messages.append(response['message'])
    # Check if the model decided to use the provided function
    if not response['message'].get('tool_calls'):
        print("The model didn't use the function. Its response was:")
        print(response['message']['content'])
        return
    # Process function calls made by the model
    if response['message'].get('tool_calls'):
        available_functions = {
            'get_flight_times': get_flight_times,
            'search_data_in_vector_db': search_data_in_vector_db,
        }
        for tool in response['message']['tool_calls']:
            function_to_call = available_functions[tool['function']['name']]
            function_args = tool['function']['arguments']
            function_response = function_to_call(**function_args)
            # Add function response to the conversation
            messages.append(
                {
                    'role': 'tool',
                    'content': function_response,
                }
            )
    # Second API call: Get final response from the model
    final_response = client.chat(model=model, messages=messages)
    print(final_response['message']['content'])


if __name__ == '__main__':
    # 1 函数调用
    question = "What is the flight time from New York (NYC) to Los Angeles (LAX)?"
    run('llama3.1:latest', question)

    # 2 向量检索
    # question = "What is Artificial Intelligence?"
    # run('llama3.1:latest', question)

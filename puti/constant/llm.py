"""
@Author: obstacles
@Time:  2025-03-04 14:13
@Description:  
"""

from puti.constant.base import Base


class LLM(Base):
    OPENAI = ("openai", "")
    ZHIPUAI = ("zhipuai", "")
    LLAMA = ("llama", "")


class RoleType(Base):
    USER = ('user', 'message from user type')
    SYSTEM = ('system', 'message from system type')
    ASSISTANT = ('assistant', 'message from assistant type')
    TOOL = ('tool', 'tool message type')


class MessageTag(Base):
    ALL = ('<all>', 'message to all people')
    REFLECTION = ('<self-reflection>', 'reflection message tag')
    THINK = ('THINK', 'think tag')


class MessageType(Base):
    FINAL_ANSWER = ('FINAL_ANSWER', 'final answer tag')
    PROCESS_ANSWER = ('PROCESS_ANSWER', 'process answer tag')


TOKEN_COSTS = {
    "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
    "gpt-3.5-turbo-0301": {"prompt": 0.0015, "completion": 0.002},
    "gpt-3.5-turbo-0613": {"prompt": 0.0015, "completion": 0.002},
    "gpt-3.5-turbo-16k": {"prompt": 0.003, "completion": 0.004},
    "gpt-3.5-turbo-16k-0613": {"prompt": 0.003, "completion": 0.004},
    "gpt-35-turbo": {"prompt": 0.0015, "completion": 0.002},
    "gpt-35-turbo-16k": {"prompt": 0.003, "completion": 0.004},
    "gpt-3.5-turbo-1106": {"prompt": 0.001, "completion": 0.002},
    "gpt-3.5-turbo-0125": {"prompt": 0.001, "completion": 0.002},
    "gpt-4-0314": {"prompt": 0.03, "completion": 0.06},
    "gpt-4": {"prompt": 0.03, "completion": 0.06},
    "gpt-4-32k": {"prompt": 0.06, "completion": 0.12},
    "gpt-4-32k-0314": {"prompt": 0.06, "completion": 0.12},
    "gpt-4-0613": {"prompt": 0.06, "completion": 0.12},
    "gpt-4-turbo-preview": {"prompt": 0.01, "completion": 0.03},
    "gpt-4-1106-preview": {"prompt": 0.01, "completion": 0.03},
    "gpt-4-0125-preview": {"prompt": 0.01, "completion": 0.03},
    "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
    "gpt-4-turbo-2024-04-09": {"prompt": 0.01, "completion": 0.03},
    "gpt-4-vision-preview": {"prompt": 0.01, "completion": 0.03},  # TODO add extra image price calculator
    "gpt-4-1106-vision-preview": {"prompt": 0.01, "completion": 0.03},
    "gpt-4o": {"prompt": 0.005, "completion": 0.015},
    "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
    "gpt-4o-mini-2024-07-18": {"prompt": 0.00015, "completion": 0.0006},
    "gpt-4o-2024-05-13": {"prompt": 0.005, "completion": 0.015},
    "gpt-4o-2024-08-06": {"prompt": 0.0025, "completion": 0.01},
    "gpt-4.1-mini": {"prompt": 0.0004, "completion": 0.0016},
    "gpt-4.1": {"prompt": 0.002, "completion": 0.008},
    "o1-preview": {"prompt": 0.015, "completion": 0.06},
    "o1-preview-2024-09-12": {"prompt": 0.015, "completion": 0.06},
    "o1-mini": {"prompt": 0.003, "completion": 0.012},
    "o1-mini-2024-09-12": {"prompt": 0.003, "completion": 0.012},
    "text-embedding-ada-002": {"prompt": 0.0004, "completion": 0.0},
    "glm-3-turbo": {"prompt": 0.0007, "completion": 0.0007},  # 128k version, prompt + completion tokens=0.005￥/k-tokens
    "glm-4": {"prompt": 0.014, "completion": 0.014},  # 128k version, prompt + completion tokens=0.1￥/k-tokens
    "glm-4-flash": {"prompt": 0, "completion": 0},
    "glm-4-plus": {"prompt": 0.007, "completion": 0.007},
    "gemini-1.5-flash": {"prompt": 0.000075, "completion": 0.0003},
    "gemini-1.5-pro": {"prompt": 0.0035, "completion": 0.0105},
    "gemini-1.0-pro": {"prompt": 0.0005, "completion": 0.0015},
    'gemini-2.5-pro-preview-03-25': {'prompt': 0.00125, "completion": 0.010},
    "moonshot-v1-8k": {"prompt": 0.012, "completion": 0.012},  # prompt + completion tokens=0.012￥/k-tokens
    "moonshot-v1-32k": {"prompt": 0.024, "completion": 0.024},
    "moonshot-v1-128k": {"prompt": 0.06, "completion": 0.06},
    "open-mistral-7b": {"prompt": 0.00025, "completion": 0.00025},
    "open-mixtral-8x7b": {"prompt": 0.0007, "completion": 0.0007},
    "mistral-small-latest": {"prompt": 0.002, "completion": 0.006},
    "mistral-medium-latest": {"prompt": 0.0027, "completion": 0.0081},
    "mistral-large-latest": {"prompt": 0.008, "completion": 0.024},
    "claude-instant-1.2": {"prompt": 0.0008, "completion": 0.0024},
    "claude-2.0": {"prompt": 0.008, "completion": 0.024},
    "claude-2.1": {"prompt": 0.008, "completion": 0.024},
    "claude-3-sonnet-20240229": {"prompt": 0.003, "completion": 0.015},
    "claude-3-5-sonnet": {"prompt": 0.003, "completion": 0.015},
    "claude-3-5-sonnet-v2": {"prompt": 0.003, "completion": 0.015},  # alias of newer 3.5 sonnet
    "claude-3-5-sonnet-20240620": {"prompt": 0.003, "completion": 0.015},
    "claude-3-opus-20240229": {"prompt": 0.015, "completion": 0.075},
    "claude-3-haiku-20240307": {"prompt": 0.00025, "completion": 0.00125},
    "yi-34b-chat-0205": {"prompt": 0.0003, "completion": 0.0003},
    "yi-34b-chat-200k": {"prompt": 0.0017, "completion": 0.0017},
    "yi-large": {"prompt": 0.0028, "completion": 0.0028},
    "microsoft/wizardlm-2-8x22b": {"prompt": 0.00108, "completion": 0.00108},  # for openrouter, start
    "meta-llama/llama-3-70b-instruct": {"prompt": 0.008, "completion": 0.008},
    "llama3-70b-8192": {"prompt": 0.0059, "completion": 0.0079},
    "openai/gpt-3.5-turbo-0125": {"prompt": 0.0005, "completion": 0.0015},
    "openai/gpt-4-turbo-preview": {"prompt": 0.01, "completion": 0.03},
    "openai/o1-preview": {"prompt": 0.015, "completion": 0.06},
    "openai/o1-mini": {"prompt": 0.003, "completion": 0.012},
    "anthropic/claude-3-opus": {"prompt": 0.015, "completion": 0.075},
    "anthropic/claude-3.5-sonnet": {"prompt": 0.003, "completion": 0.015},
    "google/gemini-pro-1.5": {"prompt": 0.0025, "completion": 0.0075},  # for openrouter, end
    "deepseek-chat": {"prompt": 0.00014, "completion": 0.00028},
    "deepseek-coder": {"prompt": 0.00014, "completion": 0.00028},
    # For ark model https://www.volcengine.com/docs/82379/1099320
    "doubao-lite-4k-240515": {"prompt": 0.000043, "completion": 0.000086},
    "doubao-lite-32k-240515": {"prompt": 0.000043, "completion": 0.000086},
    "doubao-lite-128k-240515": {"prompt": 0.00011, "completion": 0.00014},
    "doubao-pro-4k-240515": {"prompt": 0.00011, "completion": 0.00029},
    "doubao-pro-32k-240515": {"prompt": 0.00011, "completion": 0.00029},
    "doubao-pro-128k-240515": {"prompt": 0.0007, "completion": 0.0013},
    "llama3-70b-llama3-70b-instruct": {"prompt": 0.0, "completion": 0.0},
    "llama3-8b-llama3-8b-instruct": {"prompt": 0.0, "completion": 0.0},
}

"""
@Author: obstacles
@Time:  2025-03-10 17:08
@Description:  
"""
import ollama

from ollama._types import Message
from ollama import Client
from pydantic import BaseModel, Field, ConfigDict, create_model, model_validator, PrivateAttr, SerializeAsAny, field_validator
from typing import Optional, List, Iterable, Literal, Annotated, Dict, TypedDict, Any, Required, NotRequired, ClassVar, cast
from constant.llm import RoleType
from typing import Dict, Tuple, Type, Any, Union
from conf.llm_config import LLMConfig, OpenaiConfig
from openai import AsyncOpenAI, OpenAI
from abc import ABC, abstractmethod
from llm.cost import Cost
from logs import logger_factory
from openai import AsyncStream
from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion import ChatCompletion
from openai.types import CompletionUsage
from conf.llm_config import LlamaConfig
from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall
from openai.types.chat.chat_completion_message import ChatCompletionMessage


lgr = logger_factory.llm


class LLMNode(BaseModel, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    llm_name: str = Field(default='openai', description='Random llm name.')
    conf: LLMConfig = Field(default_factory=OpenaiConfig, validate_default=True)
    system_prompt: List[dict] = [{'role': RoleType.SYSTEM.val, 'content': 'You are a helpful assistant.'}]
    acli: Optional[Union[AsyncOpenAI, Client]] = Field(None, description='Cli connect with llm.', exclude=True)
    cli: Optional[Union[OpenAI]] = Field(None, description='Cli connect with llm.', exclude=True)
    cost: Optional[Cost] = None

    def model_post_init(self, __context):
        if self.llm_name == 'openai':
            if not self.conf.API_KEY:
                raise AttributeError('API_KEY is missing')
            if not self.acli:
                self.acli = AsyncOpenAI(base_url=self.conf.BASE_URL, api_key=self.conf.API_KEY)
            if not self.cli:
                self.cli = OpenAI(base_url=self.conf.BASE_URL, api_key=self.conf.API_KEY)

    def create_model_class(cls, class_name: str, mapping: Dict[str, Tuple[Type, Any]]):
        """基于pydantic v2的模型动态生成，用来检验结果类型正确性"""

        def check_fields(cls, values):
            all_fields = set(mapping.keys())
            required_fields = set()
            for k, v in mapping.items():
                type_v, field_info = v
                if LLMNode.is_optional_type(type_v):
                    continue
                required_fields.add(k)

            missing_fields = required_fields - set(values.keys())
            if missing_fields:
                raise ValueError(f"Missing fields: {missing_fields}")

            unrecognized_fields = set(values.keys()) - all_fields
            if unrecognized_fields:
                lgr.warning(f"Unrecognized fields: {unrecognized_fields}")
            return values

        validators = {"check_missing_fields_validator": model_validator(mode="before")(check_fields)}

        new_fields = {}
        for field_name, field_value in mapping.items():
            if isinstance(field_value, dict):
                # 对于嵌套结构，递归创建模型类
                nested_class_name = f"{class_name}_{field_name}"
                nested_class = cls.create_model_class(nested_class_name, field_value)
                new_fields[field_name] = (nested_class, ...)
            else:
                new_fields[field_name] = field_value

        new_class = create_model(class_name, __validators__=validators, **new_fields)
        return new_class

    @abstractmethod
    async def chat(self, msg: List[Dict], *args, **kwargs) -> str:
        """ Async chat """


class OpenAINode(LLMNode):

    async def chat(self, msg: List[Dict], **kwargs) -> Union[str, ChatCompletionMessage]:
        stream = self.conf.STREAM
        if kwargs.get('tools'):
            stream = False

        if stream:
            resp: AsyncStream[ChatCompletionChunk] = await self.acli.chat.completions.create(
                messages=msg,
                timeout=self.conf.LLM_API_TIMEOUT,
                stream=stream,
                max_tokens=self.conf.MAX_TOKEN,
                temperature=self.conf.TEMPERATURE,
                model=self.conf.MODEL,
                **kwargs
            )
            collected_messages = []
            async for chunk in resp:
                # TODO: Tool call in async seem have some issue, like lack params given
                # if chunk.choices[0].delta.tool_calls:
                #     return chunk.choices[0].delta.tool_calls
                chunk_message = chunk.choices[0].delta.content or '' if chunk.choices else ''
                finish_reason = (chunk.choices[0].finish_reason if chunk.choices and hasattr(chunk.choices[0], 'finish_reason') else None)
                chunk_has_usage = hasattr(chunk, 'usage') and chunk.usage
                # TODO: get chunk usage
                if finish_reason:
                    if chunk_has_usage:
                        usage = chunk.usage
                    elif hasattr(chunk.choices[0], 'usage'):
                        usage = CompletionUsage(**chunk.choices[0].usage)
                    print('\n')
                print(chunk_message, end='')
                collected_messages.append(chunk_message)
            full_reply = ''.join(collected_messages)
            return full_reply
        else:
            resp: ChatCompletion = self.cli.chat.completions.create(
                messages=msg,
                timeout=self.conf.LLM_API_TIMEOUT,
                stream=stream,
                max_tokens=self.conf.MAX_TOKEN,
                temperature=self.conf.TEMPERATURE,
                model=self.conf.MODEL,
                **kwargs
            )
            if resp.choices[0].message.tool_calls:
                return resp.choices[0].message
            else:
                full_reply = resp.choices[0].message
            return full_reply


class OllamaNode(LLMNode):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ollama = Client(host=self.conf.BASE_URL)
        lgr.debug(f'Ollama node init from {self.conf.BASE_URL} ---> model: {self.conf.MODEL}')

    async def chat(self, msg: Union[List[Dict], str], *args, **kwargs) -> Union[str, List[Message]]:
        # same as gpt, although there are no errors in streaming chat while fc. default non-stream fc
        stream = self.conf.STREAM
        if kwargs.get('tools'):
            stream = False
        response = self.ollama.chat(
            model=self.conf.MODEL,
            messages=msg,
            stream=stream,
            **kwargs
        )
        if stream:
            collected_messages = []
            for chunk in response:
                collected_messages.append(chunk.message.content)
            full_reply = ''.join(collected_messages)
        else:
            if response.message.tool_calls:
                return response.message
            full_reply = response.message.content
        return full_reply


ollama_node = OllamaNode(llm_name='llama', conf=LlamaConfig())
openai_node = OpenAINode(llm_name='openai', conf=OpenaiConfig())

"""
@Author: obstacles
@Time:  2025-03-10 17:08
@Description:  
"""
from pydantic import BaseModel, Field, ConfigDict, create_model, model_validator, PrivateAttr, SerializeAsAny, field_validator
from typing import Optional, List, Iterable, Literal
from constant.llm import RoleType
from typing import Dict, Tuple, Type, Any, Union
from conf.llm_config import LLMConfig, OpenaiConfig
from openai import AsyncOpenAI
from abc import ABC, abstractmethod
from llm.cost import Cost
from logs import logger_factory
from openai import AsyncStream
from openai.types.chat import ChatCompletionChunk
from openai.types import CompletionUsage


lgr = logger_factory.llm


class LLMNode(BaseModel, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    llm_name: str = Field(default='openai', description='Random llm name.')
    conf: LLMConfig = Field(default_factory=OpenaiConfig, validate_default=True)
    system_prompt: List[dict] = [{'role': RoleType.SYSTEM.val, 'content': 'You are a helpful assistant.'}]
    acli: Optional[Union[AsyncOpenAI]] = Field(None, description='Cli connect with llm.', exclude=True)
    cost: Optional[Cost] = None

    def model_post_init(self, __context):
        if not self.acli:
            self.acli = AsyncOpenAI(base_url=self.conf.BASE_URL, api_key=self.conf.API_KEY)

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
    async def achat(self, msg: List[Dict]) -> str:
        """ Async chat """


class OpenAINode(LLMNode):

    async def achat(self, msg: List[Dict]) -> str:
        resp: AsyncStream[ChatCompletionChunk] = await self.acli.chat.completions.create(
            messages=msg,
            timeout=self.conf.LLM_API_TIMEOUT,
            stream=self.conf.STREAM,
            max_tokens=self.conf.MAX_TOKEN,
            temperature=self.conf.TEMPERATURE,
            model=self.conf.MODEL
        )
        collected_messages = []
        async for chunk in resp:
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

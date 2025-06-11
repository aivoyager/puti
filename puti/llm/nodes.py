"""
@Author: obstacles
@Time:  2025-03-10 17:08
@Description:  
"""
from ollama._types import Message
from ollama import Client
from pydantic import BaseModel, Field, ConfigDict, create_model, model_validator
from typing import Optional, List
from puti.constant.llm import RoleType
from typing import Dict, Tuple, Type, Any, Union
from puti.conf.llm_config import LLMConfig, OpenaiConfig
from openai import AsyncOpenAI, OpenAI
from abc import ABC, abstractmethod
from puti.llm.cost import CostManager
from puti.logs import logger_factory
from openai import AsyncStream
from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_message import ChatCompletionMessage


lgr = logger_factory.llm


class LLMNode(BaseModel, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    llm_name: str = Field(default='openai', description='Random llm name.')
    conf: LLMConfig = Field(default_factory=OpenaiConfig, validate_default=True)
    system_prompt: List[dict] = [{'role': RoleType.SYSTEM.val, 'content': 'You are a helpful assistant.'}]
    acli: Optional[Union[AsyncOpenAI, Client]] = Field(None, description='Cli connect with llm.', exclude=True)
    cli: Optional[Union[OpenAI, Client]] = Field(None, description='Cli connect with llm.', exclude=True)
    cost: Optional[CostManager] = None

    def model_post_init(self, __context):
        if self.llm_name == 'openai':
            if not self.conf.API_KEY:
                raise AttributeError('API_KEY is missing')
            if not self.acli:
                self.acli = AsyncOpenAI(base_url=self.conf.BASE_URL, api_key=self.conf.API_KEY)
            if not self.cli:
                self.cli = OpenAI(base_url=self.conf.BASE_URL, api_key=self.conf.API_KEY)
        if not self.cost:
            self.cost = CostManager()

    @abstractmethod
    async def chat(self, msg: List[Dict], *args, **kwargs) -> str:
        """ Async chat """

    @abstractmethod
    async def stream_chat(self, message, **kwargs) -> AsyncStream[ChatCompletionChunk]:
        pass

    @abstractmethod
    async def embedding(self, text: str, **kwargs) -> List[float]:
        pass

    @abstractmethod
    async def get_embedding_dim(self) -> int:
        pass

    async def chat_text(self, text: str, *args, **kwargs):
        messages = [{"role": "user", "content": text}]
        resp = await self.chat(messages, *args, **kwargs)
        return resp


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
                # max_tokens=self.conf.MAX_TOKEN,
                temperature=self.conf.TEMPERATURE,
                model=self.conf.MODEL,
                **kwargs
            )
            collected_messages = []
            async for chunk in resp:
                chunk_message = chunk.choices[0].delta.content or '' if chunk.choices else ''
                # print(chunk_message, end='')
                collected_messages.append(chunk_message)
            full_reply = ''.join(collected_messages)
            self.cost.handle_chat_cost(msg, full_reply, self.conf.MODEL)
            # lgr.info(f"cost: {self.cost.total_cost}")
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
                completion_text = resp.choices[0].message.content if hasattr(resp.choices[0].message, 'content') else ''
                self.cost.handle_chat_cost(msg, completion_text, self.conf.MODEL)
                # lgr.info(f"cost: {self.cost.total_cost}")
                return resp.choices[0].message
            else:
                full_reply = resp.choices[0].message.content if hasattr(resp.choices[0].message, 'content') else ''
                self.cost.handle_chat_cost(msg, full_reply, self.conf.MODEL)
                # lgr.info(f"cost: {self.cost.total_cost}")
            return full_reply

    async def stream_chat(self, message, **kwargs) -> AsyncStream[ChatCompletionChunk]:
        return await self.acli.chat.completions.create(
            model=self.conf.MODEL_NAME,
            messages=message,
            stream=True,
            **kwargs
        )

    async def embedding(self, text: str, **kwargs) -> List[float]:
        """Get the embedding for a text."""
        response = await self.acli.embeddings.create(
            model=self.conf.EMBEDDING_MODEL,
            input=[text],
            **kwargs
        )
        return response.data[0].embedding

    async def get_embedding_dim(self) -> int:
        """Get the embedding dimension for the model."""
        if self.conf.EMBEDDING_DIM:
            return self.conf.EMBEDDING_DIM
        response = await self.acli.embeddings.create(
            model=self.conf.EMBEDDING_MODEL,
            input=["dim"]
        )
        return len(response.data[0].embedding)


class OllamaNode(LLMNode):

    def model_post_init(self, __context):
        self.cli = Client(host=self.conf.BASE_URL)
        lgr.info(f"ollama node init from {self.conf.BASE_URL} model: {self.conf.MODEL}")

    async def chat(self, msg: Union[List[Dict], str], *args, **kwargs) -> Union[str, List[Message]]:
        stream = self.conf.STREAM
        if kwargs.get('tools'):
            stream = False
        response = self.cli.chat(
            model=self.conf.MODEL,
            messages=msg,
            stream=stream,
            **kwargs
        )
        if stream:
            collected_messages = []
            for chunk in response:
                collected_messages.append(chunk.message.content)
                print(chunk.message.content, end='')
            full_reply = ''.join(collected_messages)
            lgr.debug('ollama has not cost yet')
        else:
            if response.message.tool_calls:
                return response.message
            full_reply = response.message.content
            print(full_reply)
            lgr.debug('ollama has not cost yet')
        return full_reply

    async def stream_chat(self, message, **kwargs):
        return await self.acli.chat(model=self.conf.MODEL_NAME, messages=message, stream=True, **kwargs)

    async def embedding(self, text: str, **kwargs) -> List[float]:
        """Get the embedding for a text from Ollama."""
        response = await self.acli.embeddings(
            model=self.conf.EMBEDDING_MODEL,
            prompt=text,
            **kwargs
        )
        return response["embedding"]

    async def get_embedding_dim(self) -> int:
        """Get the embedding dimension for the Ollama model."""
        response = await self.acli.embeddings(
            model=self.conf.EMBEDDING_MODEL,
            prompt="dim"
        )
        return len(response["embedding"])


class ClaudeNode(LLMNode):
    pass

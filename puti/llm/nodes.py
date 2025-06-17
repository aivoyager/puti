"""
@Author: obstacles
@Time:  2025-03-10 17:08
@Description:  
"""
import json

from ollama._types import Message as OMessage
from ollama import Client
from pydantic import BaseModel, Field, ConfigDict, create_model, model_validator
from typing import Optional, List
from typing import Dict, Tuple, Type, Any, Union, Annotated
from abc import ABC, abstractmethod
from openai import AsyncOpenAI, OpenAI
from openai import AsyncStream
from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from puti.utils.files import encode_image
from puti.llm.messages import Message, ToolMessage
from puti.llm.tools import Toolkit
from puti.llm.prompts import promptt
from puti.constant.llm import RoleType
from puti.llm.cost import CostManager
from puti.logs import logger_factory
from puti.conf.llm_config import LLMConfig, OpenaiConfig
from puti.utils.common import any_to_str, is_valid_json
from puti.constant.llm import MessageRouter, MessageType, ChatState, ReflectionType
from puti.core.resp import ChatResponse
from puti.constant.base import Resp


lgr = logger_factory.llm


class LLMNode(BaseModel, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    llm_name: str = Field(default='openai', description='Random llm name.')
    conf: LLMConfig = Field(default_factory=OpenaiConfig, validate_default=True)
    system_prompt: List[dict] = [{'role': RoleType.SYSTEM.val, 'content': 'You are a helpful assistant.'}]
    acli: Optional[Union[AsyncOpenAI, Client]] = Field(None, description='Cli connect with llm.', exclude=True)
    cli: Optional[Union[OpenAI, Client]] = Field(None, description='Cli connect with llm.', exclude=True)
    cost: Optional[CostManager] = None

    def __str__(self):
        return self.llm_name

    def __repr__(self):
        return self.llm_name

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

    @abstractmethod
    async def parse_chat_result(self, *args, **kwargs) -> ChatResponse:
        pass

    async def chat_text(self, text: str, *args, **kwargs):
        messages = [{"role": "user", "content": text}]
        resp = await self.chat(messages, *args, **kwargs)
        return resp

    @staticmethod
    async def parse_answer(think: str) -> Tuple[ChatState, str]:
        if is_valid_json(think):
            think = json.loads(think)

            if think.get(ChatState.FINAL_ANSWER.val):
                final_answer = think.get('FINAL_ANSWER')
                return ChatState.FINAL_ANSWER, final_answer
            elif think.get(ChatState.IN_PROCESS_ANSWER.val):
                in_process_answer = think.get('IN_PROCESS_ANSWER')
                return ChatState.IN_PROCESS_ANSWER, in_process_answer
            else:
                return ChatState.SELF_REFLECTION, ''
        else:
            return ChatState.SELF_REFLECTION, ''


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
            # TODO: add cost for image message
            if not Message.is_image(msg[-1]):
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
                if not Message.is_image(msg[-1]):
                    self.cost.handle_chat_cost(msg, completion_text, self.conf.MODEL)
                # lgr.info(f"cost: {self.cost.total_cost}")
                return resp.choices[0].message
            else:
                full_reply = resp.choices[0].message.content if hasattr(resp.choices[0].message, 'content') else ''
                if not Message.is_image(msg[-1]):
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

    async def parse_chat_result(
            self,
            resp: Union[str, ChatCompletionMessage],   # chat resp
            toolkit: Toolkit,  # get fc call schema
            *args,
            **kwargs
    ) -> ChatResponse:
        if isinstance(resp, ChatCompletionMessage) and resp.tool_calls:
            resp.tool_calls = resp.tool_calls[:1]  # forbidden multiple tool call parallel
            todos = []
            for call_tool in resp.tool_calls:
                todo = toolkit.tools.get(call_tool.function.name)
                todo_args = call_tool.function.arguments if call_tool.function.arguments else {}
                todo_args = json.loads(todo_args) if isinstance(todo_args, str) else todo_args
                tool_call_id = call_tool.id
                todos.append((todo, todo_args, tool_call_id))

            todos = todos[0]  # multiple tool call
            return ChatResponse(
                chat_state=ChatState.FC_CALL,
                tool_to_call=todos[0],
                tool_args=todos[1],
                tool_call_id=todos[2]
            )

        # final answer, not tool call
        elif isinstance(resp, str):
            chat_state, text = await self.parse_answer(resp)

            if chat_state == ChatState.SELF_REFLECTION:
                fix_msg = promptt.self_reflection_for_invalid_json.render(
                    INVALID_DATA=resp,
                    KEYWORDS=MessageType.keys()
                )

                return ChatResponse(
                    chat_state=ChatState.SELF_REFLECTION,
                    reflection_type=ReflectionType.INVALID_JSON,
                    msg=fix_msg
                )
            elif chat_state == ChatState.FINAL_ANSWER:
                return ChatResponse(
                    chat_state=ChatState.FINAL_ANSWER,
                    msg=text
                )
            elif chat_state == ChatState.IN_PROCESS_ANSWER:
                return ChatResponse(
                    chat_state=ChatState.IN_PROCESS_ANSWER,
                    msg=text
                )
            elif chat_state == chat_state.FC_CALL:
                return ChatResponse(
                    chat_state=ChatState.FC_CALL,

                )
            else:
                return ChatResponse(code=Resp.CHAT_RESPONSE_FAIL.val, msg=Resp.CHAT_RESPONSE_FAIL.dsp)

        # self.answer = AssistantMessage(
        #     content=final_answer,
        #     sender=self.name,
        #     receiver={MessageRouter.ALL.val},
        #     # extend conversation rounds like tool call
        #     tool_calls_one_round=self.tool_calls_one_round,
        # )
        # # TODO: multiple tools call for openai support
        # call_message = ToolMessage(non_standard=resp)
        #
        # await self.rc.memory.add_one(call_message)
        # self.rc.todos = todos
        # return ThinkResponse.success(data=(True, ''))


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

    async def parse_chat_result(self, *args, **kwargs) -> ChatResponse:
        # # ollama fc
        # elif isinstance(think, OMessage) and think.tool_calls and all(isinstance(i, OMessage.ToolCall) for i in think.tool_calls):
        #     tool_calls: List[OMessage.ToolCall] = think.tool_calls[:1]
        #     todos = []
        #     for fc in tool_calls:
        #         todo = self.toolkit.tools.get(fc.function.name)
        #         todo_args = fc.function.arguments if fc.function.arguments else {}
        #         todos.append((todo, todo_args, -1))
        #
        #     call_message = Message(non_standard=think)
        #     await self.rc.memory.add_one(call_message)
        #     self.rc.todos = todos
        #     return True, ''
        #
        # # from openai、ollama, different data structure.
        # # llm reply directly
        # elif (isinstance(think, ChatCompletionMessage) and think.content) or isinstance(think, str):  # think resp
        #     try:
        #         if isinstance(think, str):
        #             content = json.loads(think)
        #         else:
        #             content = json.loads(think.content)
        #         final_answer = content.get('FINAL_ANSWER')
        #         in_process_answer = content.get('IN_PROCESS')
        #     except json.JSONDecodeError:
        #         # send to self, no publish, no action
        #         fix_msg = promptt.self_reflection_for_invalid_json.render(INVALID_DATA=think)
        #         return self._correction(fix_msg)
        #
        #     if final_answer:
        #         json_match = re.search(r'({.*})', message[-1]['content'], re.DOTALL)
        #         think_process = ''
        #         if json_match:
        #             match_group = json_match.group()
        #             if is_valid_json(match_group):
        #                 think_process = json.loads(match_group).get('think_process', '')
        #         self.answer = AssistantMessage(content=final_answer, sender=self.name)
        #         await self.rc.memory.add_one(self.answer)
        #         return False, json.dumps({'final_answer': final_answer, 'think_process': think_process}, ensure_ascii=False)
        #     elif in_process_answer:
        #         self.answer = AssistantMessage(content=in_process_answer, sender=self.name)
        #         # will publish message in multi-agent env, so there are no need add message to memory
        #         return False, in_process_answer
        #     else:
        #         fix_msg = f'Your returned json data does not have a "FINAL ANSWER" key. Please check you answer:\n{final_answer}'
        #         return self._correction(fix_msg)

        # # unexpected think format
        # else:
        #     err = f'Unexpected chat response: {type(think)}'
        #     lgr.error(err)
        #     raise RuntimeError(err)
        pass


class ClaudeNode(LLMNode):
    pass

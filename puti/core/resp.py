"""
@Author: obstacle
@Time: 16/01/25 14:00
@Description:  
"""
from pydantic import BaseModel, Field, SerializeAsAny, ConfigDict
from typing import Any, Dict, Union, Iterable, Tuple, Optional, Callable

from pydantic._internal._namespace_utils import MappingNamespace

from puti.constant.base import Resp
from puti.constant.llm import MessageRouter, MessageType, ChatState, ReflectionType


class Response(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    msg: str = Field(default=Resp.OK.dsp, validate_default=True, description='brief description')
    code: int = Field(default=Resp.OK.val, validate_default=True, description='status code from `Resp`')
    data: SerializeAsAny[Any] = Field(default=None, validate_default=True, description='data payload')

    @classmethod
    def default(cls, code: int = 200, msg: str = Resp.OK.dsp, data: Union[Dict, Iterable] = None) -> 'Response':
        if isinstance(data, Response):
            return data
        return Response(**{
            'code': code,
            'msg': msg,
            'data': data,
        })

    @property
    def info(self):
        return f'Error: {self.msg}' if not str(self.code).startswith('2') else f'{self.data}'

    def __str__(self):
        return self.info

    def __repr__(self):
        return self.info

    def is_success(self) -> bool:
        return 200 <= self.code < 300


class ToolResponse(Response):
    """ Tool Response """
    data: Union[str, dict, list] = Field(default='', validate_default=True,
                                         description='tool execution successfully result')
    msg: str = Field(default=Resp.TOOL_OK.dsp, validate_default=True, description='tool execution failed result')
    code: int = Field(default=Resp.TOOL_OK.val, validate_default=True, description='tool execution result code')

    @classmethod
    def fail(cls, msg: str = Resp.TOOL_FAIL.dsp) -> 'ToolResponse':
        return ToolResponse(code=Resp.TOOL_FAIL.val, msg=msg)

    @classmethod
    def success(cls, data: Union[str, dict, list] = None) -> 'ToolResponse':
        return ToolResponse(code=Resp.TOOL_OK.val, msg=Resp.TOOL_OK.dsp, data=data)


class ChatResponse(Response):
    chat_state: ChatState = Field(default=ChatState.FINAL_ANSWER, description='chat state')

    msg: str = Field(default='', description='chat response, if final answer or in process answer then `msg` has value.')

    tool_to_call: 'BaseTool' = Field(default=None, description='actions to do')
    tool_args: dict = Field(default=None, description='tool arguments')
    tool_call_id: str = Field(default=None, description='tool call id')

    reflection_type: ReflectionType = Field(default=None, description='reflection type')

    code: int = Field(default=Resp.CHAT_RESPONSE_OK.val, description='status code')

    def __str__(self):
        return f"code: {self.code}, state: {self.chat_state.val}, msg: {self.msg}"

    def __repr__(self):
        return self.__str__()

    @classmethod
    def model_rebuild(
        cls,
        *,
        force: bool = False,
        raise_errors: bool = True,
        _parent_namespace_depth: int = 2,
        _types_namespace: Optional[MappingNamespace] = None,
    ) -> Optional[bool]:
        from puti.llm.tools import BaseTool  # noqa: F401

        return super(ChatResponse, cls).model_rebuild(
            force=force,
            raise_errors=raise_errors,
            _parent_namespace_depth=_parent_namespace_depth,
            _types_namespace=_types_namespace,
        )


ChatResponse.model_rebuild()


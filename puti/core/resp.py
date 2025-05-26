"""
@Author: obstacle
@Time: 16/01/25 14:00
@Description:  
"""
from pydantic import BaseModel, Field, SerializeAsAny, ConfigDict
from typing import Any, Dict, Union, Iterable
from puti.constant.base import Resp


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
    data: Union[str, dict, list] = Field(default='', validate_default=True, description='tool execution successfully result')
    msg: str = Field(default=Resp.TOOL_OK.dsp, validate_default=True, description='tool execution failed result')
    code: int = Field(default=Resp.TOOL_OK.val, validate_default=True, description='tool execution result code')

    @classmethod
    def fail(cls, msg: str = Resp.TOOL_FAIL.dsp) -> 'ToolResponse':
        return ToolResponse(code=Resp.TOOL_FAIL.val, msg=msg)

    @classmethod
    def success(cls, data: Union[str, dict, list] = None) -> 'ToolResponse':
        return ToolResponse(code=Resp.TOOL_OK.val, msg=Resp.TOOL_OK.dsp, data=data)

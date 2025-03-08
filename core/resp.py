"""
@Author: obstacle
@Time: 16/01/25 14:00
@Description:  
"""
from pydantic import BaseModel, Field, SerializeAsAny, ConfigDict
from typing import Any, Dict, Union, Iterable
from constant.base import Resp


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
        info = str({
            "code": self.code,
            "msg": self.msg,
            "data": self.data,
        })
        return f'{self.__class__} {info}'

    def __str__(self):
        return self.info

    def __repr__(self):
        return self.info

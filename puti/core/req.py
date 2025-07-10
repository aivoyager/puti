"""
@Author: obstacles
@Time:  2025-04-08 14:07
@Description:  
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, TypeVar, Dict, Union, Any, Generic, Literal
from puti.constant.api import RequestMethod

RequestParamsT = TypeVar('RequestParamsT', bound=Union['RequestParams', Dict[str, Any], None])


class RequestParams(BaseModel):
    class Meta(BaseModel):
        model_config = ConfigDict(extra='allow')

    meta: Optional[Meta] = Field(alias='_meta', default=None)


class Request(BaseModel, Generic[RequestParamsT]):
    model_config = ConfigDict(extra='allow')

    params: RequestParamsT
    method: RequestMethod


class JSONRPCRequest(Request[Optional[dict[str, Any]]]):

    jsonrpc: Literal['2.0']
    id: Union[int, str] = Field(..., union_mode='left_to_right')











"""
@Author: obstacles
@Time:  2025-07-09 15:09
@Description:  
"""
from pydantic import RootModel, BaseModel
from puti.core.req import JSONRPCRequest
from typing import Union


class JSONRPCMessage(RootModel[Union[JSONRPCRequest, str]]):
    pass


class SessionMessage(BaseModel):
    message: JSONRPCMessage

"""
@Author: obstacles
@Time:  2025-05-13 14:38
@Description:  
"""
from puti.constant.base import Resp


class BaseError(Exception):
    def __init__(
        self,
        code: int = Resp.INTERNAL_SERVE_ERR.val,
        message: str = Resp.INTERNAL_SERVE_ERR.dsp,
        *args, **kwargs
    ):
        self.code = code
        self.message = message

    def __str__(self):
        return f"Error code: {self.code}, Message: {self.message}"


class ToolError(BaseError):
    def __init__(self, message, code: int = Resp.TOOL_FAIL.val, *args, **kwargs):
        super(ToolError, self).__init__(message=message, code=code, *args, **kwargs)

"""
@Author: obstacles
@Time:  2025-07-09 11:53
@Description:  
"""
from pydantic import BaseModel, Field
from typing import Annotated, Union, Optional, Generic
from puti.core.req import RequestParams, Request


class SeverMessageMetadata(BaseModel):

    related_request_id: Optional[Union[int, str]] = Field(
        default=None,
        union_mode='left_to_right'
    )
    request_context: Optional[object] = Field(
        default=None,
        description='Request-specific context (e.g. headers, auth info)'
    )


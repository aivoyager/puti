"""
@Author: obstacle
@Time: 16/01/25 17:39
@Description:  
"""

from pydantic import BaseModel
from typing import Optional


class Model(BaseModel):
    __table_name__ = ''
    id: Optional[int] = None

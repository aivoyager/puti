"""
@Author: obstacle
@Time: 16/01/25 17:39
@Description:  
"""
import datetime

from puti.db.model import Model
from pydantic import Field
from typing import Optional


class UserModel(Model):
    __table_name__ = 'users'

    name: str
    age: int
    email: Optional[str] = None


class Mentions(Model):
    __table_name__ = 'twitter_mentions'

    id: Optional[int] = Field(None, description='pk for table')
    text: str
    author_id: str
    mention_id: str = Field(None, description='Unique identifier for mentions', unique=True)
    parent_id: Optional[str] = None
    data_time: datetime.datetime = None
    created_at: datetime.datetime = Field(None, description='data time', dft_time='now')
    replied: bool = False
    is_del: bool = False


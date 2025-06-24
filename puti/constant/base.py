"""
@Author: obstacle
@Time: 10/01/25 11:52
@Description:  
"""
from pathlib import Path
from enum import Enum
from puti.utils.path import root_dir
from typing import Type, TypeVar

T = TypeVar("T", bound='Base')


class Base(Enum):

    @property
    def val(self):
        return self.value[0]

    @property
    def dsp(self):
        return self.value[1]

    @classmethod
    def elem_from_str(cls: Type[T], s: str) -> 'Base':
        for item in cls:
            if item.val == s:
                return item
        raise ValueError(f'{s} is not a valid {cls.__name__}')

    @classmethod
    def keys(cls: Type[T]) -> set:
        return {item.val for item in cls}


class Pathh(Base):
    PROJ_NAME = ('PuTi', '')
    ROOT_DIR = (root_dir(), 'PuTi')

    POOL_SIZE = (3, 'db connection pool size')

    CONFIG_DIR = (str(Path.home() / 'puti'), 'PuTi config dir')
    CONFIG_FILE = (str(Path.home() / 'puti' / '.env'), 'PuTi config file')

    INDEX_FILE = (str(Path.home() / 'puti' / 'index.faiss'), 'PuTi index file')
    INDEX_TEXT = (str(Path.home() / 'puti' / 'index.txt'), 'PuTi index text file')

    SQLITE_FILE = (str(Path.home() / 'puti' / 'puti.sqlite'), 'PuTi sqlite file')


class Modules(Base):
    CLIENT = ('client', 'client module')
    API = ('api', 'api module')
    LLM = ('llm', 'llm module')
    UTILITIES = ('utilities', 'utilities module')


class Resp(Base):
    OK = (200, 'ok')
    TOOL_OK = (201, 'tool ok')
    CHAT_RESPONSE_OK = (202, 'react ok')

    UNAUTHORIZED_ERR = (401, 'unauthorized error from tweet')

    INTERNAL_SERVE_ERR = (500, 'internal server error')
    CP_ERR = (501, 'capturing error from `Capture`')
    POST_TWEET_ERR = (502, 'post tweet error')
    REQUEST_TIMEOUT = (503, 'request timeout')

    TOOL_FAIL = (504, 'tool fail')
    TOOL_TIMEOUT = (505, 'tool timeout')
    CHAT_RESPONSE_FAIL = (506, 'chat response fail')


class TaskType(Base):
    POST = ('post', '发推任务')
    REPLY = ('reply', '回复任务')
    RETWEET = ('retweet', '转发任务')
    LIKE = ('like', '点赞任务')
    FOLLOW = ('follow', '关注任务')
    NOTIFICATION = ('notification', '通知任务')
    ANALYTICS = ('analytics', '数据分析任务')
    CONTENT_CURATION = ('content_curation', '内容策划任务')
    SCHEDULED_THREAD = ('scheduled_thread', '计划线程任务')
    OTHER = ('other', '其他任务')


class TaskPostType(Base):
    IMAGE = ('image', 'image task')
    ACTIVITY = ('activity', 'activity task')
    TEXT = ('text', 'text task')


class TaskActivityType(Base):
    JOKE = ('joke', 'joke task')
    SEND_TOKEN = ('send token', 'send token')

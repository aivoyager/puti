"""
@Author: obstacle
@Time: 10/01/25 11:52
@Description:  
"""
import os
from pathlib import Path
from enum import Enum
from puti.utils.path import root_dir
from typing import Type, TypeVar, Union, Any

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


class PathAutoCreate:
    """工具类，用于自动创建路径"""
    
    @staticmethod
    def ensure_path(path_str: str) -> str:
        """确保路径存在
        
        Args:
            path_str: 路径字符串
            
        Returns:
            原始路径字符串
        """
        if not path_str:
            return path_str
            
        path = Path(path_str)
        
        # 判断是文件还是目录（根据是否包含文件扩展名）
        if path.suffix:  # 有扩展名，视为文件
            # 确保父目录存在
            parent_dir = path.parent
            if not parent_dir.exists():
                os.makedirs(parent_dir, exist_ok=True)
        else:  # 没有扩展名，视为目录
            if not path.exists():
                os.makedirs(path, exist_ok=True)
                
        return path_str


# 首先定义基本路径，不依赖于其他路径
home_dir = str(Path.home())
config_dir = str(Path(home_dir) / 'puti')


class Pathh(Base):
    PROJ_NAME = ('PuTi', '')
    ROOT_DIR = (root_dir(), 'PuTi')

    POOL_SIZE = (3, 'db connection pool size')

    # 使用预定义的变量，避免递归初始化
    CONFIG_DIR = (config_dir, 'PuTi config dir')

    CONFIG_FILE = (str(Path(config_dir) / '.env'), 'PuTi config file')

    INDEX_FILE = (str(Path(config_dir) / 'index.faiss'), 'PuTi index file')
    INDEX_TEXT = (str(Path(config_dir) / 'index.txt'), 'PuTi index text file')  # long-term memory retrieval

    SQLITE_FILE = (str(Path(config_dir) / 'puti.sqlite'), 'PuTi sqlite file')

    # celery beat
    BEAT_PID = (str(Path(config_dir) / 'celery' / 'beat.pid'), 'celery beat pid file')
    BEAT_LOG = (str(Path(config_dir) / 'celery' / 'beat.log'), 'celery beat log file')
    BEAT_DB = (str(Path(config_dir) / 'celery' / 'celerybeat-schedule.db'), 'celery beat db file')
    
    @property
    def val(self) -> str:
        """获取路径值并自动检查/创建路径"""
        path_str = super().val
        return PathAutoCreate.ensure_path(path_str)
    
    def __call__(self) -> str:
        """调用枚举实例时自动检查/创建路径"""
        return self.val


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

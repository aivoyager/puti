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
    """Utility class for automatically creating paths."""
    
    @staticmethod
    def ensure_path(path_str: str) -> str:
        """Ensure the path exists.
        
        Args:
            path_str: The path string.
            
        Returns:
            The original path string.
        """
        if not path_str:
            return path_str
            
        path = Path(path_str)
        
        # Determine if it is a file or a directory (based on whether it contains a file extension)
        if path.suffix:  # Has an extension, treated as a file
            # Ensure the parent directory exists
            parent_dir = path.parent
            if not parent_dir.exists():
                os.makedirs(parent_dir, exist_ok=True)
        else:  # No extension, treated as a directory
            if not path.exists():
                os.makedirs(path, exist_ok=True)
                
        return path_str


# First, define the base paths without dependency on other paths.
home_dir = str(Path.home())
config_dir = str(Path(home_dir) / 'puti')


class Pathh(Base):
    PROJ_NAME = ('PuTi', '')
    ROOT_DIR = (root_dir(), 'PuTi')

    POOL_SIZE = (3, 'db connection pool size')

    # Use predefined variables to avoid recursive initialization
    CONFIG_DIR = (config_dir, 'PuTi config dir')

    CONFIG_FILE = (str(Path(config_dir) / '.env'), 'PuTi config file')

    INDEX_FILE = (str(Path(config_dir) / 'index.faiss'), 'PuTi index file')
    INDEX_TEXT = (str(Path(config_dir) / 'index.txt'), 'PuTi index text file')  # long-term memory retrieval

    SQLITE_FILE = (str(Path(config_dir) / 'puti.sqlite'), 'PuTi sqlite file')

    # celery beat - use the same path as the current running process
    BEAT_PID = (str(Path(config_dir) / 'run' / 'beat.pid'), 'celery beat pid file')
    BEAT_LOG = (str(Path(config_dir) / 'logs' / 'beat.log'), 'celery beat log file')
    BEAT_DB = (str(Path(config_dir) / 'celery' / 'celerybeat-schedule.db'), 'celery beat db file')

    # celery worker
    WORKER_PID = (str(Path(config_dir) / 'celery' / 'worker.pid'), 'celery worker pid file')
    WORKER_LOG = (str(Path(config_dir) / 'celery' / 'worker.log'), 'celery worker log file')
    
    @property
    def val(self) -> str:
        """Get the path value and automatically check/create the path."""
        path_str = super().val
        return PathAutoCreate.ensure_path(path_str)
    
    def __call__(self) -> str:
        """Automatically check/create the path when calling the enum instance."""
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
    POST = ('post', 'Post Task')
    REPLY = ('reply', 'Reply Task')
    RETWEET = ('retweet', 'Retweet Task')
    LIKE = ('like', 'Like Task')
    FOLLOW = ('follow', 'Follow Task')
    NOTIFICATION = ('notification', 'Notification Task')
    ANALYTICS = ('analytics', 'Analytics Task')
    CONTENT_CURATION = ('content_curation', 'Content Curation Task')
    SCHEDULED_THREAD = ('scheduled_thread', 'Scheduled Thread Task')
    OTHER = ('other', 'Other Task')

    UNIMPLEMENTED = ('unimplemented', 'Unimplemented Task')


class TaskPostType(Base):
    IMAGE = ('image', 'image task')
    ACTIVITY = ('activity', 'activity task')
    TEXT = ('text', 'text task')


class TaskActivityType(Base):
    JOKE = ('joke', 'joke task')
    SEND_TOKEN = ('send token', 'send token')

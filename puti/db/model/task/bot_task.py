"""
@Author: obstacle
@Time: 21/01/25 10:36
@Description:  
"""
import datetime

from puti.db.model import Model
from puti.constant.base import TaskType, TaskActivityType, TaskPostType
from typing import Optional, Any, List
from pydantic import Field


class BotTask(Model):
    __table_name__ = 'bot_tasks'

    task_type: TaskType
    replay_tweet: List[Any] = None
    post_type: Optional[TaskPostType] = None
    activity_type: Optional[TaskActivityType] = None
    task_create_time: datetime.datetime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    task_start_time: Optional[float] = None
    task_done_time: Optional[float] = None
    created_at: datetime.datetime = Field(None, description='data time', dft_time='now')
    is_del: bool = False

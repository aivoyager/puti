"""
@Author: obstacle
@Time: 21/01/25 10:36
@Description:  
"""
import datetime

from puti.db.model import Model
from puti.constant.base import TaskType, TaskActivityType, TaskPostType
from typing import Optional, Any, List, Dict
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
    
    
class TweetSchedule(Model):
    __table_name__ = 'tweet_schedules'
    
    name: str = Field(..., max_length=255, json_schema_extra={'unique': True})
    cron_schedule: str = Field(..., max_length=255)
    enabled: bool = True
    params: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.now, json_schema_extra={'dft_time': 'now'})
    updated_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.now, json_schema_extra={'dft_time': 'now'})
    task_id: Optional[str] = Field(None, max_length=255, description="Celery task ID associated with this schedule")
    task_type: str = Field(TaskType.POST.val, description="任务类型，如发推、回复等")
    is_del: bool = False
    
    @property
    def task_type_display(self) -> str:
        """获取任务类型的显示名称"""
        try:
            return TaskType.elem_from_str(self.task_type).dsp
        except ValueError:
            return "未知类型"

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
    
    
class TweetSchedule(Model):
    __table_name__ = 'tweet_schedules'
    
    name: str = Field(..., max_length=255, json_schema_extra={'unique': True})
    cron_schedule: str = Field(..., max_length=255)
    enabled: bool = True
    params: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.now, json_schema_extra={'dft_time': 'now'})
    updated_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.now, json_schema_extra={'dft_time': 'now'})
    task_id: Optional[str] = Field(None, max_length=255, description="Celery task ID associated with this schedule")
    task_type: str = Field(TaskType.POST.val, description="The type of task, e.g., post, reply, etc.")
    is_del: bool = False
    last_run: Optional[datetime.datetime] = Field(None, description="Last time the task was executed")
    next_run: Optional[datetime.datetime] = Field(None, description="Next scheduled execution time")
    is_running: bool = Field(False, description="Whether the task is currently running")
    pid: Optional[int] = Field(None, description="Process ID of the running task, if active")
    
    @property
    def task_type_display(self) -> str:
        """Get the display name of the task type."""
        try:
            return TaskType.elem_from_str(self.task_type).dsp
        except ValueError:
            return "Unknown Type"

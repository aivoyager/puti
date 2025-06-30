"""
@Author: obstacle
@Time: 29/07/24 14:00
@Description: Manager for scheduler tasks with individual PIDs
"""
import os
import datetime
import subprocess
from pathlib import Path

from typing import List, Optional, Dict, Any, Union
from croniter import croniter
from puti.db.base_manager import BaseManager
from puti.db.model.task.bot_task import TweetSchedule
from puti.constant.base import TaskType
from puti.logs import logger_factory

lgr = logger_factory.default


class ScheduleManager(BaseManager[TweetSchedule]):
    """Manages tweet schedules in the database with individual PID tracking."""
    
    def __init__(self, **kwargs):
        """Initialize with TweetSchedule as the model type."""
        super().__init__(model_type=TweetSchedule, **kwargs)
    
    def create_schedule(self, name: str, cron_schedule: str, enabled: bool = True, 
                       params: Optional[Dict[str, Any]] = None, task_type: str = TaskType.POST.val) -> TweetSchedule:
        """
        Create a new schedule in the database.
        
        Args:
            name: The name of the schedule
            cron_schedule: Cron expression for schedule timing
            enabled: Whether the schedule should be enabled
            params: Parameters for the task (like topic, tags, etc.)
            task_type: 任务类型，默认为发推(post)，可以是reply(回复)、retweet(转发)等
            
        Returns:
            The created schedule object
        """

        # 验证任务类型是否有效
        try:
            TaskType.elem_from_str(task_type)
        except ValueError:
            lgr.warning(f"无效的任务类型: {task_type}，使用默认类型: {TaskType.POST.val}")
            task_type = TaskType.POST.val
        
        # Calculate next run time
        now = datetime.datetime.now()
        try:
            next_run = croniter(cron_schedule, now).get_next(datetime.datetime)
        except ValueError as e:
            lgr.error(f"Invalid cron expression: {cron_schedule} - {str(e)}")
            raise ValueError(f"Invalid cron expression: {cron_schedule}")
            
        # Create new schedule
        schedule = TweetSchedule(
            name=name,
            cron_schedule=cron_schedule,
            next_run=next_run,
            enabled=enabled,
            params=params or {},
            pid=None,
            is_running=False,
            last_run=None,
            task_type=task_type
        )
        
        # Save to database
        schedule_id = self.save(schedule)
        schedule.id = schedule_id
        return schedule
    
    def update_schedule(self, schedule_id: int, **updates) -> bool:
        """
        Update a schedule in the database.
        
        Args:
            schedule_id: ID of the schedule to update
            **updates: Fields to update
            
        Returns:
            True if successful, False otherwise
        """
        # 如果更新任务类型，验证它是否有效
        if 'task_type' in updates:
            try:
                TaskType.elem_from_str(updates['task_type'])
            except ValueError:
                lgr.error(f"无效的任务类型: {updates['task_type']}")
                return False
                
        # If updating cron schedule, recalculate next run time
        if 'cron_schedule' in updates:
            from croniter import croniter
            now = datetime.datetime.now()
            try:
                updates['next_run'] = croniter(updates['cron_schedule'], now).get_next(datetime.datetime)
            except ValueError as e:
                lgr.error(f"Invalid cron expression: {updates['cron_schedule']} - {str(e)}")
                return False
                
        return self.update(schedule_id, updates)
    
    def get_by_name(self, name: str) -> Optional[TweetSchedule]:
        """Get a schedule by name."""
        schedules = self.get_all(where_clause="name = ?", params=(name,))
        return schedules[0] if schedules else None
    
    def get_active_schedules(self) -> List[TweetSchedule]:
        """Get all active (enabled) schedules."""
        return self.get_all(where_clause="enabled = 1 AND is_del = 0")

    def update(self, schedule_id: int, updates_or_dict: Union[Dict[str, Any], Any], **kwargs) -> bool:
        """
        更新计划任务，支持字典参数或关键字参数。
        
        Args:
            schedule_id: 计划任务ID
            updates_or_dict: 更新字段的字典，或者第一个字段的值
            **kwargs: 如果updates_or_dict不是字典，则这里包含剩余的字段更新
            
        Returns:
            更新是否成功
        """
        if isinstance(updates_or_dict, dict):
            # 如果传入的是字典，直接使用
            updates = updates_or_dict
        else:
            # 否则，假设第一个参数是字段名，值是第一个参数的值
            field_names = list(self.model_type.__annotations__.keys())
            if field_names and field_names[0] not in kwargs:
                # 将第一个参数作为第一个字段的值
                updates = {field_names[0]: updates_or_dict}
                updates.update(kwargs)
            else:
                # 否则只使用kwargs
                updates = kwargs
                
        # 为了兼容，调用父类的update方法
        return super().update(schedule_id, updates)
        
    def reset_stuck_tasks(self, max_minutes: int = 30) -> int:
        """
        重置卡住的任务（标记为运行中但已超过规定时间）
        
        Args:
            max_minutes: 最大运行时间（分钟），超过此时间的任务将被重置
            
        Returns:
            重置的任务数量
        """
        now = datetime.datetime.now()
        stuck_timeout = datetime.timedelta(minutes=max_minutes)
        reset_count = 0
        
        # 查找所有标记为运行中的任务
        running_tasks = self.get_all(where_clause="is_running = 1 AND is_del = 0")
        
        for task in running_tasks:
            # 如果任务有上次更新时间，并且超过了最大运行时间
            if task.updated_at and (now - task.updated_at > stuck_timeout):
                lgr.warning(f'Task "{task.name}" (ID: {task.id}) appears to be stuck. '
                           f'Last update was at {task.updated_at}. Resetting status.')
                self.update(task.id, {"is_running": False, "pid": None})
                reset_count += 1
                
        return reset_count

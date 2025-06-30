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
            task_type: The type of task, defaults to 'post', can be 'reply', 'retweet', etc.
            
        Returns:
            The created schedule object
        """

        # Validate the task type
        try:
            TaskType.elem_from_str(task_type)
        except ValueError:
            lgr.warning(f"Invalid task type: {task_type}, using default: {TaskType.POST.val}")
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
        # If updating task type, validate it
        if 'task_type' in updates:
            try:
                TaskType.elem_from_str(updates['task_type'])
            except ValueError:
                lgr.error(f"Invalid task type: {updates['task_type']}")
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
        Update a scheduled task, supporting dictionary or keyword arguments.
        
        Args:
            schedule_id: The ID of the scheduled task
            updates_or_dict: A dictionary of fields to update, or the value of the first field
            **kwargs: If updates_or_dict is not a dictionary, this contains the remaining field updates
            
        Returns:
            Whether the update was successful
        """
        if isinstance(updates_or_dict, dict):
            # If a dictionary is passed, use it directly
            updates = updates_or_dict
        else:
            # Otherwise, assume the first argument is the field name, and its value is the first argument's value
            field_names = list(self.model_type.__annotations__.keys())
            if field_names and field_names[0] not in kwargs:
                # Treat the first argument as the value for the first field
                updates = {field_names[0]: updates_or_dict}
                updates.update(kwargs)
            else:
                # Otherwise, just use kwargs
                updates = kwargs
                
        # For compatibility, call the parent class's update method
        return super().update(schedule_id, updates)
        
    def reset_stuck_tasks(self, max_minutes: int = 30) -> int:
        """
        Resets stuck tasks (marked as running but have exceeded the specified time).
        
        Args:
            max_minutes: Maximum running time in minutes; tasks exceeding this will be reset.
            
        Returns:
            The number of reset tasks.
        """
        now = datetime.datetime.now()
        stuck_timeout = datetime.timedelta(minutes=max_minutes)
        reset_count = 0
        
        # Find all tasks marked as running
        running_tasks = self.get_all(where_clause="is_running = 1 AND is_del = 0")
        
        for task in running_tasks:
            # If the task has a last update time and has exceeded the max running time
            if task.updated_at and (now - task.updated_at > stuck_timeout):
                lgr.warning(f'Task "{task.name}" (ID: {task.id}) appears to be stuck. '
                           f'Last update was at {task.updated_at}. Resetting status.')
                self.update(task.id, {"is_running": False, "pid": None})
                reset_count += 1
                
        return reset_count

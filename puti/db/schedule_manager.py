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

from puti.db.base_manager import BaseManager
from puti.db.model.task.bot_task import TweetSchedule
from puti.constant.base import TaskType
from puti.logs import logger_factory

lgr = logger_factory.default


class ScheduleManager(BaseManager):
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
        from croniter import croniter
        
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
    
    def get_running_schedules(self) -> List[TweetSchedule]:
        """Get all schedules that are currently running."""
        return self.get_all(where_clause="is_running = 1 AND is_del = 0")
    
    def get_schedules_by_type(self, task_type: str) -> List[TweetSchedule]:
        """获取指定类型的所有计划任务"""
        return self.get_all(where_clause="task_type = ? AND is_del = 0", params=(task_type,))
    
    def get_active_schedules_by_type(self, task_type: str) -> List[TweetSchedule]:
        """获取指定类型的所有启用的计划任务"""
        return self.get_all(where_clause="task_type = ? AND enabled = 1 AND is_del = 0", params=(task_type,))
    
    def start_task(self, schedule_id: int) -> bool:
        """
        Start the task for a specific schedule.
        
        Args:
            schedule_id: ID of the schedule to start
            
        Returns:
            True if successful, False otherwise
        """
        schedule = self.get_by_id(schedule_id)
        if not schedule:
            lgr.error(f"Schedule with ID {schedule_id} not found")
            return False
            
        if schedule.is_running:
            lgr.warning(f"Schedule '{schedule.name}' is already running with PID {schedule.pid}")
            return True
            
        # Start the Celery task
        try:
            from celery_queue.simplified_tasks import generate_tweet_task
            
            # Get parameters from schedule
            params = schedule.params or {}
            topic = params.get('topic')
            
            # 根据任务类型选择不同的任务处理方式
            if schedule.task_type == TaskType.POST.val:
                # 发推任务 - 使用Graph的Workflow功能
                result = generate_tweet_task.delay(topic=topic, use_graph_workflow=True)
                lgr.info(f"Started Graph Workflow tweet task for '{schedule.name}' with topic: {topic}")
            elif schedule.task_type == TaskType.REPLY.val:
                # 回复任务 - 目前仅记录，但尚未实现
                lgr.info(f"Reply task '{schedule.name}' triggered but not implemented yet")
                result = generate_tweet_task.delay(topic=topic)  # 暂时仍使用发推任务
            else:
                # 其他类型的任务 - 默认使用发推任务
                lgr.warning(f"Task type {schedule.task_type} not fully implemented, using post task")
                result = generate_tweet_task.delay(topic=topic)
            
            # Update the schedule with task info
            self.update(schedule_id, {
                "is_running": True,
                "pid": None,  # We don't have direct access to worker PID
                "last_run": datetime.datetime.now(),
                "task_id": result.id
            })
            
            lgr.info(f"Started task for schedule '{schedule.name}' (ID: {schedule_id}, Type: {schedule.task_type_display})")
            return True
        except Exception as e:
            lgr.error(f"Error starting task for schedule '{schedule.name}': {str(e)}")
            return False
    
    def stop_task(self, schedule_id: int) -> bool:
        """
        Stop a running task.
        
        Args:
            schedule_id: ID of the schedule to stop
            
        Returns:
            True if successful, False otherwise
        """
        schedule = self.get_by_id(schedule_id)
        if not schedule:
            lgr.error(f"Schedule with ID {schedule_id} not found")
            return False
            
        if not schedule.is_running:
            lgr.warning(f"Schedule '{schedule.name}' is not running")
            return True
            
        # In a Celery environment, we can't easily stop a running task
        # But we can mark it as not running in our database
        self.update(schedule_id, {
            "is_running": False,
            "pid": None
        })
        
        lgr.info(f"Marked task for schedule '{schedule.name}' (ID: {schedule_id}) as stopped")
        return True
    
    def check_is_running(self, schedule_id: int) -> bool:
        """
        Check if a task for a specific schedule is running.
        
        Args:
            schedule_id: ID of the schedule to check
            
        Returns:
            True if running, False otherwise
        """
        schedule = self.get_by_id(schedule_id)
        if not schedule:
            return False
            
        return schedule.is_running 
"""
@Author: obstacle
@Time: 30/08/24
@Description: Task state guard class to ensure the correct synchronization of status fields during task execution.
"""

import os
import time
import datetime
from contextlib import contextmanager
from typing import Optional, Dict, Any, Union

from puti.db.schedule_manager import ScheduleManager
from puti.db.model.task.bot_task import TweetSchedule
from puti.logs import logger_factory
from croniter import croniter

lgr = logger_factory.default


class TaskStateGuard:
    """
    Task state guard class to ensure correct field synchronization throughout the task lifecycle.
    
    Uses a context manager pattern to ensure that the state is updated correctly, regardless of whether the task succeeds or not:
    
    with TaskStateGuard(task_id="123") as guard:
        # Task execution starts...
        result = do_something()
        # Intermediate states can be recorded during task execution
        guard.update_state(progress=50)
        # Continue execution...
        
    # When exiting the context, the task state will be updated, regardless of whether an exception occurred.
    """
    
    def __init__(self, task_id: Optional[str] = None, schedule_id: Optional[int] = None):
        """
        Initializes the task state guard instance.
        
        Args:
            task_id: Celery task ID
            schedule_id: The ID of the scheduled task in the database
        """
        if not task_id and not schedule_id:
            raise ValueError("Either task_id or schedule_id must be provided")
            
        self.task_id = task_id
        self.schedule_id = schedule_id
        self.manager = ScheduleManager()
        self.schedule = None
        self.start_time = datetime.datetime.now()
        self.state_updates = {}
        self.success = False
        
    def __enter__(self):
        """When entering the context manager, mark the task as running."""
        try:
            # Get the scheduled task record
            if self.schedule_id:
                self.schedule = self.manager.get_by_id(self.schedule_id)
            elif self.task_id:
                schedules = self.manager.get_all(where_clause="task_id = ?", params=(self.task_id,))
                if schedules:
                    self.schedule = schedules[0]
                    self.schedule_id = self.schedule.id
            
            if not self.schedule:
                lgr.warning(f"TaskStateGuard: No schedule found for task_id={self.task_id}, schedule_id={self.schedule_id}")
                return self
                
            # Record PID and running state
            pid = os.getpid()
            updates = {
                "is_running": True,
                "pid": pid
            }
            
            lgr.info(f"[TaskStateGuard] Task {self.schedule.name} (ID: {self.schedule_id}) starting with PID {pid}")
            self.manager.update(self.schedule_id, updates)
            
        except Exception as e:
            lgr.error(f"[TaskStateGuard] Error marking task as running: {str(e)}")
            
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """When exiting the context manager, mark the task as finished."""
        if not self.schedule_id:
            return
            
        try:
            # Generate the basic update dictionary
            updates = {
                "is_running": False,
                "pid": None
            }
            
            # Calculate the next run time
            try:
                if self.schedule:
                    now = datetime.datetime.now()
                    # Force recalculation of next_run
                    next_run = croniter(self.schedule.cron_schedule, now).get_next(datetime.datetime)
                    updates["next_run"] = next_run
                    
                    # If the task completed successfully, update the last_run time
                    if not exc_type:
                        self.success = True
                        updates["last_run"] = self.start_time
                        
            except Exception as e:
                lgr.error(f"[TaskStateGuard] Error calculating next run time: {str(e)}")
                
            # Merge any intermediate state updates
            updates.update(self.state_updates)
                
            # Record the task completion status
            status = "completed successfully" if self.success else f"failed with {exc_type.__name__}: {exc_val}" if exc_type else "completed with unknown state"
            lgr.info(f"[TaskStateGuard] Task {self.schedule_id} {status}")
            
            # Update the database
            self.manager.update(self.schedule_id, updates)
            
            # Record the execution time
            end_time = datetime.datetime.now()
            execution_time = (end_time - self.start_time).total_seconds()
            lgr.info(f"[TaskStateGuard] Task {self.schedule_id} execution time: {execution_time:.2f} seconds")
            
        except Exception as e:
            lgr.error(f"[TaskStateGuard] Error during task cleanup: {str(e)}")
            # Final safety measure: ensure the task is no longer marked as running, no matter what.
            try:
                self.manager.update(self.schedule_id, {"is_running": False, "pid": None})
            except:
                pass
            
        # Do not suppress the exception, let it propagate
        return False
        
    def update_state(self, **kwargs):
        """
        Update the task's state.
        
        Args:
            **kwargs: A dictionary of fields and values.
        """
        if not self.schedule_id:
            lgr.warning("[TaskStateGuard] Cannot update state: no schedule_id")
            return
            
        try:
            # 检查并过滤掉不存在的字段（特别是status字段）
            valid_updates = {}
            
            # 如果TweetSchedule的模型类里有这个字段的定义，才尝试更新它
            if self.schedule:
                model_fields = self.schedule.__annotations__.keys()
                for key, value in kwargs.items():
                    if key in model_fields:
                        valid_updates[key] = value
                    else:
                        lgr.debug(f"[TaskStateGuard] Ignoring field '{key}' that doesn't exist in {self.schedule.__class__.__name__}")
            else:
                valid_updates = kwargs
                
            # 保存有效的状态更新
            self.state_updates.update(valid_updates)
            
            # 如果有有效的字段需要更新，则立即更新数据库
            if valid_updates:
                self.manager.update(self.schedule_id, valid_updates)
                lgr.debug(f"[TaskStateGuard] Updated task {self.schedule_id} state: {valid_updates}")
            
        except Exception as e:
            lgr.error(f"[TaskStateGuard] Error updating task state: {str(e)}")
            
    @classmethod
    @contextmanager
    def for_task(cls, task_id: str = None, schedule_id: int = None):
        """
        Create a context manager for a task.
        
        Args:
            task_id: Celery task ID
            schedule_id: The ID of the scheduled task in the database
            
        Usage:
            with TaskStateGuard.for_task(task_id="123") as guard:
                # Task execution...
                guard.update_state(progress=50)
        """
        guard = cls(task_id=task_id, schedule_id=schedule_id)
        try:
            yield guard
            guard.success = True
        except Exception as e:
            guard.success = False
            raise
        finally:
            # Ensure the state is updated
            if guard.schedule_id:
                try:
                    guard.manager.update(guard.schedule_id, {
                        "is_running": False, 
                        "pid": None,
                        "last_run": guard.start_time if guard.success else None
                    })
                except Exception as e:
                    lgr.error(f"[TaskStateGuard] Error in final state update: {str(e)}") 
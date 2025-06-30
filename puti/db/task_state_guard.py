"""
@Author: obstacle
@Time: 30/08/24
@Description: 任务状态守护类，确保任务执行过程中状态字段的同步正确性
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
    任务状态守护类，确保任务生命周期中字段同步正确。
    
    使用上下文管理器模式来确保无论任务是否成功，状态都能正确更新：
    
    with TaskStateGuard(task_id="123") as guard:
        # 任务开始执行...
        result = do_something()
        # 可以在任务执行过程中记录中间状态
        guard.update_state(progress=50)
        # 继续执行...
        
    # 退出上下文时，无论是否发生异常，任务状态都会更新
    """
    
    def __init__(self, task_id: Optional[str] = None, schedule_id: Optional[int] = None):
        """
        初始化任务状态守护实例。
        
        Args:
            task_id: Celery 任务 ID
            schedule_id: 数据库中的调度任务 ID
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
        """上下文管理器进入时，标记任务开始运行"""
        try:
            # 获取调度任务记录
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
                
            # 记录PID和运行状态
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
        """上下文管理器退出时，标记任务结束"""
        if not self.schedule_id:
            return
            
        try:
            # 生成基本的更新字典
            updates = {
                "is_running": False,
                "pid": None
            }
            
            # 计算下次运行时间
            try:
                if self.schedule:
                    now = datetime.datetime.now()
                    # 强制重新计算next_run
                    next_run = croniter(self.schedule.cron_schedule, now).get_next(datetime.datetime)
                    updates["next_run"] = next_run
                    
                    # 如果任务成功完成，更新last_run时间
                    if not exc_type:
                        self.success = True
                        updates["last_run"] = self.start_time
                        
            except Exception as e:
                lgr.error(f"[TaskStateGuard] Error calculating next run time: {str(e)}")
                
            # 合并中间可能记录的状态
            updates.update(self.state_updates)
                
            # 记录任务完成状态
            status = "completed successfully" if self.success else f"failed with {exc_type.__name__}: {exc_val}" if exc_type else "completed with unknown state"
            lgr.info(f"[TaskStateGuard] Task {self.schedule_id} {status}")
            
            # 更新数据库
            self.manager.update(self.schedule_id, updates)
            
            # 记录执行时间
            end_time = datetime.datetime.now()
            execution_time = (end_time - self.start_time).total_seconds()
            lgr.info(f"[TaskStateGuard] Task {self.schedule_id} execution time: {execution_time:.2f} seconds")
            
        except Exception as e:
            lgr.error(f"[TaskStateGuard] Error during task cleanup: {str(e)}")
            # 最后的安全措施：无论如何都要确保任务不再标记为运行中
            try:
                self.manager.update(self.schedule_id, {"is_running": False, "pid": None})
            except:
                pass
            
        # 不捕获异常，让它向上传播
        return False
        
    def update_state(self, **kwargs):
        """
        更新任务状态。
        
        Args:
            **kwargs: 字段和值的字典
        """
        if not self.schedule_id:
            lgr.warning("[TaskStateGuard] Cannot update state: no schedule_id")
            return
            
        try:
            # 保存状态以便退出时更新
            self.state_updates.update(kwargs)
            
            # 立即更新数据库
            self.manager.update(self.schedule_id, kwargs)
            lgr.debug(f"[TaskStateGuard] Updated task {self.schedule_id} state: {kwargs}")
            
        except Exception as e:
            lgr.error(f"[TaskStateGuard] Error updating task state: {str(e)}")
            
    @classmethod
    @contextmanager
    def for_task(cls, task_id: str = None, schedule_id: int = None):
        """
        为任务创建上下文管理器。
        
        Args:
            task_id: Celery 任务 ID
            schedule_id: 数据库中的调度任务 ID
            
        用法:
            with TaskStateGuard.for_task(task_id="123") as guard:
                # 任务执行...
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
            # 确保状态更新
            if guard.schedule_id:
                try:
                    guard.manager.update(guard.schedule_id, {
                        "is_running": False, 
                        "pid": None,
                        "last_run": guard.start_time if guard.success else None
                    })
                except Exception as e:
                    lgr.error(f"[TaskStateGuard] Error in final state update: {str(e)}") 
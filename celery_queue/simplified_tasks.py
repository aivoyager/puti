"""
@Author: obstacle
@Time: 25/07/24 15:16
@Description: Simplified Celery tasks for scheduler demos
"""
import os
import asyncio
import json
import traceback
from datetime import datetime

from celery import shared_task
from croniter import croniter
from puti.logs import logger_factory
from puti.constant.base import TaskType
from puti.llm.actions.x_bot import GenerateTweetAction, PublishTweetAction
from puti.llm.roles.agents import Ethan, EthanG
from puti.llm.workflow import Workflow
from puti.llm.graph import Graph, Vertex
from puti.db.schedule_manager import ScheduleManager


lgr = logger_factory.default


TASK_MAP = {
    TaskType.POST.val: 'celery_queue.simplified_tasks.generate_tweet_task',
    TaskType.REPLY.val: 'celery_queue.simplified_tasks.unimplemented_task',
    TaskType.RETWEET.val: 'celery_queue.simplified_tasks.unimplemented_task',
}


@shared_task()
def check_dynamic_schedules():
    """
    Checks for dynamic schedules in the database and triggers tasks as needed.
    This task is the heartbeat of the dynamic scheduler system and should be
    scheduled to run frequently (e.g., every minute).
    """
    now = datetime.now()
    lgr.info(f'Checking dynamic schedules at {now}')

    try:
        # Use the schedule manager for better database interaction
        manager = ScheduleManager()
        
        # 1. 自动重置卡住的任务 (stuck tasks)
        running_schedules = manager.get_all(where_clause="is_running = 1 AND is_del = 0")
        stuck_timeout = datetime.timedelta(minutes=10)  # 10分钟超时
        
        for schedule in running_schedules:
            # updated_at 是自动更新的，我们检查它
            if schedule.updated_at and (now - schedule.updated_at > stuck_timeout):
                lgr.warning(f'Task "{schedule.name}" (ID: {schedule.id}) appears to be stuck. '
                            f'Last update was at {schedule.updated_at}. Resetting status.')
                manager.update(schedule.id, {"is_running": False, "pid": None})

        # 2. 获取所有活跃的计划任务 (只处理启用的且未删除的任务)
        schedules = manager.get_all(where_clause="enabled = 1 AND is_del = 0")
        lgr.info(f'Found {len(schedules)} active schedules to evaluate')
        
        # 3. 检查并更新下次执行时间（实时计算）
        for schedule in schedules:
            try:
                # 如果任务正在运行，跳过更新下次执行时间
                if schedule.is_running:
                    continue
                    
                # 检查下次执行时间是否已过期
                if schedule.next_run and schedule.next_run < now:
                    from croniter import croniter
                    # 计算从当前时间开始的下一次执行时间
                    new_next_run = croniter(schedule.cron_schedule, now).get_next(datetime)
                    # 更新数据库
                    manager.update(schedule.id, {"next_run": new_next_run})
                    lgr.info(f'Updated next_run for schedule "{schedule.name}" (ID: {schedule.id}) to {new_next_run}')
            except Exception as e:
                lgr.error(f'Error updating next_run for schedule {schedule.id}: {str(e)}')
        
        # 4. 获取所有状态为"运行中"但已经完成的任务
        running_schedules = manager.get_all(where_clause="is_running = 1 AND is_del = 0")
        for schedule in running_schedules:
            # 检查任务是否仍在运行
            if schedule.pid:
                import os
                try:
                    # 尝试向进程发送信号0来检查它是否存在
                    os.kill(schedule.pid, 0)
                    # 如果没有抛出异常，进程仍在运行
                    continue
                except OSError:
                    # 进程不存在，将任务标记为未运行
                    lgr.info(f'Process for schedule "{schedule.name}" (PID: {schedule.pid}) is no longer running, marking as not running')
                    manager.update(schedule.id, {"is_running": False, "pid": None})
        
        # 5. 检查并触发到期的任务
        for schedule in schedules:
            # Skip schedules that are already running
            if schedule.is_running:
                lgr.debug(f'Schedule "{schedule.name}" is already running, skipping.')
                continue
                
            # A robust way to check if a task should have run.
            # We iterate from the last known run time up to the current time.
            # This ensures we don't miss runs if the service was down.
            last_run = schedule.last_run or datetime.fromtimestamp(0)
            cron = croniter(schedule.cron_schedule, last_run)
            
            # Get the next scheduled run time based on the last execution
            next_run_time = cron.get_next(datetime)

            if next_run_time <= now:
                lgr.info(f'[Scheduler] Triggering task for schedule "{schedule.name}" (ID: {schedule.id})')

                # Extract parameters from the schedule
                params = schedule.params or {}

                # Get the correct task function from the task map
                task_name = TASK_MAP.get(schedule.task_type)
                if not task_name:
                    lgr.error(f"No task found for type '{schedule.task_type}' on schedule {schedule.id}. Skipping.")
                    continue

                # Mark the task as running in the database
                manager.update(schedule.id, {"is_running": True})

                # Dynamically trigger the task by name
                from celery import current_app
                task = current_app.send_task(task_name, kwargs=params)
                
                # Update the schedule's timestamps and task info in the database
                new_next_run = croniter(schedule.cron_schedule, now).get_next(datetime)
                schedule_updates = {
                    "last_run": now,
                    "next_run": new_next_run,
                    "task_id": task.id
                }
                manager.update(schedule.id, **schedule_updates)
                
                lgr.info(f'[Scheduler] Schedule "{schedule.name}" executed. Next run at {new_next_run}.')

    except Exception as e:
        lgr.error(f'[Scheduler] Error checking dynamic schedules: {str(e)}. {traceback.format_exc()}')

    return 'ok'


@shared_task(bind=True)
def unimplemented_task(self, **kwargs):
    """A placeholder for task types that are not yet implemented."""
    lgr.warning(f"Task '{self.name}' with type is not implemented yet. Params: {kwargs}")
    return f"Task type not implemented."


@shared_task(bind=True)
def generate_tweet_task(self, topic: str = None):
    """
    Graph Workflow生成和发布推文。

    Args:
        topic: 推文生成的主题
    """
    from puti.db.schedule_manager import ScheduleManager

    start_time = datetime.now()
    task_id = self.request.id
    
    try:
        # Find the schedule associated with this task
        manager = ScheduleManager()
        
        # Try to update running status 
        try:
            pid = os.getpid()
            
            # Try to find the schedule by task_id if we have one
            schedules = manager.get_all(where_clause="task_id = ?", params=(task_id,))
            if schedules:
                schedule = schedules[0]
                manager.update(schedule.id, {"pid": pid})
                lgr.info(f'[Task {task_id}] Updated schedule {schedule.name} with PID {pid}')
        except Exception as e:
            lgr.warning(f'Could not update PID for task {task_id}: {str(e)}')
        
        lgr.info(f'[Task {task_id}] generate_tweet_task started, topic: {topic}')

        generate_tweet_action = GenerateTweetAction(topic=topic)
        post_tweet_action = PublishTweetAction()
        ethan = EthanG()

        generate_tweet_vertex = Vertex(id='generate_tweet', action=generate_tweet_action)
        post_tweet_vertex = Vertex(id='post_tweet', action=post_tweet_action, role=ethan)

        graph = Graph()
        graph.add_vertices(generate_tweet_vertex, post_tweet_vertex)
        graph.add_edge(generate_tweet_vertex.id, post_tweet_vertex.id)
        graph.set_start_vertex(generate_tweet_vertex.id)

        workflow = Workflow(graph=graph)
        resp = asyncio.run(workflow.run_until_vertex(post_tweet_vertex.id))
        
        # Task completed successfully
        try:
            schedules = manager.get_all(where_clause="task_id = ?", params=(task_id,))
            if schedules:
                schedule = schedules[0]
                manager.update(schedule.id, {"is_running": False, "pid": None})
                lgr.info(f'[Task {task_id}] Completed schedule {schedule.name} successfully')
        except Exception as e:
            lgr.warning(f'Could not update status for task {task_id}: {str(e)}')
        
        execution_time = (datetime.now() - start_time).total_seconds()
        lgr.info(f'[Task {task_id}] Completed in {execution_time:.2f} seconds')
        return resp
        
    except Exception as e:
        # Task failed
        try:
            from puti.db.schedule_manager import ScheduleManager
            manager = ScheduleManager()
            schedules = manager.get_all(where_clause="task_id = ?", params=(task_id,))
            if schedules:
                schedule = schedules[0]
                manager.update(schedule.id, {"is_running": False, "pid": None})
                lgr.error(f'[Task {task_id}] Failed schedule {schedule.name}: {str(e)}')
        except Exception as inner_e:
            lgr.warning(f'Could not update status for task {task_id}: {str(inner_e)}')
            
        lgr.error(f'[Task {task_id}] Failed: {str(e)}. {traceback.format_exc()}')
        return {"status": "error", "message": str(e)}
        
    finally:
        lgr.info(f'[Task {task_id}] Execution finished')


@shared_task()
def auto_manage_scheduler():
    """
    自动管理调度器的状态。
    - 如果有活跃任务但调度器未运行，则启动调度器
    - 如果没有活跃任务且调度器正在运行，可以选择停止调度器（取决于配置）
    """
    try:
        from puti.db.schedule_manager import ScheduleManager
        from puti.scheduler import BeatDaemon
        
        manager = ScheduleManager()
        daemon = BeatDaemon()
        
        # 获取所有已启用且未删除的任务
        active_schedules = manager.get_all(where_clause="enabled = 1 AND is_del = 0")
        # 获取所有正在运行的任务
        running_schedules = manager.get_all(where_clause="is_running = 1 AND is_del = 0")
        
        # 检查调度器是否需要启动
        if active_schedules and not daemon.is_running():
            lgr.info(f'Found {len(active_schedules)} active schedules but scheduler is not running. Starting scheduler...')
            daemon.start()
            lgr.info('Scheduler auto-started')
            return 'Scheduler auto-started'
        
        # 检查调度器是否需要停止 - 默认不自动停止，仅记录日志
        if not active_schedules and not running_schedules and daemon.is_running():
            lgr.info('No active or running schedules found and scheduler is running')
            # 可选：取消下面的注释以启用自动停止
            # lgr.info('Auto-stopping scheduler')
            # daemon.stop()
            # return 'Scheduler auto-stopped'
            return 'No active schedules, but scheduler kept running'
        
        return 'No scheduler management needed'
    except Exception as e:
        lgr.error(f'Error in auto_manage_scheduler: {str(e)}. {traceback.format_exc()}')
        return f'Error: {str(e)}' 
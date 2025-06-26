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
    Checks for enabled schedules in the database and triggers them if they are due.
    This is the core scheduler logic.
    """
    now = datetime.now()
    lgr.info(f'Core scheduler check running at {now}')

    try:
        manager = ScheduleManager()
        schedules = manager.get_all(where_clause="enabled = 1 AND is_del = 0")
        lgr.info(f'Found {len(schedules)} active schedules to evaluate.')

        for schedule in schedules:
            # Skip if the task is already marked as running
            if getattr(schedule, 'is_running', False):
                lgr.debug(f'Schedule "{schedule.name}" is already running, skipping.')
                continue

            try:
                from croniter import croniter
                
                # Determine the base time for the next run calculation
                last_run = getattr(schedule, 'last_run', None) or datetime.fromtimestamp(0)
                
                # Check if the task is due
                cron = croniter(schedule.cron_schedule, last_run)
                next_run_time = cron.get_next(datetime)

                if next_run_time <= now:
                    lgr.info(f'Triggering task for schedule "{schedule.name}" (ID: {schedule.id})')
                    
                    # Get task type and parameters
                    task_type = schedule.task_type
                    params = schedule.params or {}
                    
                    # Find the corresponding Celery task from the mapping
                    task_name = TASK_MAP.get(task_type)
                    if not task_name:
                        lgr.error(f"No task found for type '{task_type}' on schedule {schedule.id}. Skipping.")
                        continue

                    # Mark as running BEFORE dispatching
                    manager.update(schedule.id, {"is_running": True})

                    # Dispatch the task to Celery
                    from celery import current_app
                    task = current_app.send_task(task_name, kwargs=params)
                    
                    # Update schedule with new run times and task ID
                    new_next_run = croniter(schedule.cron_schedule, now).get_next(datetime)
                    schedule_updates = {
                        "last_run": now,
                        "next_run": new_next_run,
                        "task_id": task.id
                    }
                    manager.update(schedule.id, schedule_updates)
                    
                    lgr.info(f'Schedule "{schedule.name}" executed. Next run at {new_next_run}. Task ID: {task.id}')

            except Exception as e:
                lgr.error(f'Error processing schedule {schedule.id} ("{schedule.name}"): {str(e)}')
                # Optional: Attempt to reset the task so it can run again later
                manager.update(schedule.id, {"is_running": False})

    except Exception as e:
        lgr.error(f'Fatal error in check_dynamic_schedules: {str(e)}. {traceback.format_exc()}')

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
        manager = ScheduleManager()
        
        try:
            pid = os.getpid()
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
            schedules = manager.get_all(where_clause="task_id = ?", params=(task_id,))
            if schedules:
                schedule = schedules[0]
                manager.update(schedule.id, {"is_running": False, "pid": None})
                lgr.error(f'[Task {task_id}] Failed schedule {schedule.name}: {str(e)}')
        except Exception as inner_e:
            lgr.warning(f'Could not update status for task {task_id}: {str(inner_e)}')
            
        lgr.error(f'[Task {task_id}] Failed: {str(e)}. {traceback.format_exc()}')
        return str(e)
        
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
        return f'Error: {str(e)}' 
"""
@Author: obstacle
@Time: 25/07/24 15:16
@Description: Simplified Celery tasks for scheduler demos
"""
import os
import asyncio
import json
import traceback
import threading
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
from puti.db.task_state_guard import TaskStateGuard


lgr = logger_factory.default


def run_async(coro):
    """
    Runs and manages an asyncio event loop for a coroutine from a synchronous context.
    This creates a new event loop for each call to ensure isolation,
    preventing "Event loop is closed" errors in long-running applications like Celery.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# 在模块级别实例化Ethan角色，确保只创建一次实例
_ethan_instance = None
# 添加线程锁来保护_ethan_instance在多线程环境下的安全
_ethan_lock = threading.RLock()


# 安全获取Ethan实例的函数
def get_ethan_instance():
    """
    以线程安全的方式获取EthanG实例
    
    实现了懒加载和错误恢复功能：
    1. 仅在首次访问时创建实例
    2. 如果实例出现问题，尝试重新创建
    
    Returns:
        EthanG实例
    """
    global _ethan_instance
    
    with _ethan_lock:
        # 懒加载：如果实例不存在，创建它
        if _ethan_instance is None:
            lgr.info("Creating new EthanG instance")
            _ethan_instance = EthanG()
            
        # 健康检查：确保实例是有效的EthanG对象
        try:
            if not isinstance(_ethan_instance, EthanG):
                lgr.warning("Invalid EthanG instance detected, recreating...")
                _ethan_instance = EthanG()
        except Exception as e:
            # 错误恢复：如果检查过程中发生任何错误，重新创建实例
            lgr.error(f"Error accessing EthanG instance: {str(e)}. Recreating...")
            _ethan_instance = EthanG()
            
        return _ethan_instance


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
        
        # 首先重置任何卡住的任务
        reset_count = manager.reset_stuck_tasks(max_minutes=30)
        if reset_count > 0:
            lgr.info(f'Reset {reset_count} stuck tasks')
            
        # 获取所有启用的任务
        schedules = manager.get_all(where_clause="enabled = 1 AND is_del = 0")
        lgr.info(f'Found {len(schedules)} active schedules to evaluate.')

        for schedule in schedules:
            # 跳过正在运行的任务
            if schedule.is_running:
                lgr.debug(f'Schedule "{schedule.name}" is already running, skipping.')
                continue

            try:
                # 确定下次运行时间计算的基准时间
                last_run = schedule.last_run or datetime.fromtimestamp(0)
                
                # 检查任务是否应该运行
                cron = croniter(schedule.cron_schedule, last_run)
                next_run_time = cron.get_next(datetime)

                if next_run_time <= now:
                    lgr.info(f'Triggering task for schedule "{schedule.name}" (ID: {schedule.id})')
                    
                    # 获取任务类型和参数
                    task_type = schedule.task_type
                    params = schedule.params or {}
                    
                    # 在任务映射中找到对应的Celery任务
                    task_name = TASK_MAP.get(task_type)
                    if not task_name:
                        lgr.error(f"No task found for type '{task_type}' on schedule {schedule.id}. Skipping.")
                        continue

                    # 在派发任务前标记为正在运行
                    manager.update(schedule.id, {"is_running": True})

                    # 派发任务到Celery
                    from celery import current_app
                    task = current_app.send_task(task_name, kwargs=params)
                    
                    # 更新计划的运行时间和任务ID
                    new_next_run = croniter(schedule.cron_schedule, now).get_next(datetime)
                    
                    # 注意：last_run会在任务成功完成后由TaskStateGuard设置，
                    # 这里只更新task_id和next_run
                    schedule_updates = {
                        "next_run": new_next_run,
                        "task_id": task.id
                    }
                    manager.update(schedule.id, schedule_updates)
                    
                    lgr.info(f'Schedule "{schedule.name}" executed. Next run at {new_next_run}. Task ID: {task.id}')

            except Exception as e:
                lgr.error(f'Error processing schedule {schedule.id} ("{schedule.name}"): {str(e)}')
                # 在发生错误时重置任务状态
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
    from puti.db.task_state_guard import TaskStateGuard

    task_id = self.request.id
    
    # 使用TaskStateGuard确保任务状态始终正确更新
    with TaskStateGuard.for_task(task_id=task_id) as guard:
        lgr.info(f'[Task {task_id}] generate_tweet_task started, topic: {topic}')
        
        # 可以在这里更新额外状态（如果需要）
        guard.update_state(status="generating_tweet")

        # 创建动作实例
        generate_tweet_action = GenerateTweetAction(topic=topic)
        post_tweet_action = PublishTweetAction()
        
        # 使用模块级别的Ethan实例，避免重复创建
        ethan = get_ethan_instance()

        # 创建工作图节点
        generate_tweet_vertex = Vertex(id='generate_tweet', action=generate_tweet_action)
        post_tweet_vertex = Vertex(id='post_tweet', action=post_tweet_action, role=ethan)

        # 构建工作流图
        graph = Graph()
        graph.add_vertices(generate_tweet_vertex, post_tweet_vertex)
        graph.add_edge(generate_tweet_vertex.id, post_tweet_vertex.id)
        graph.set_start_vertex(generate_tweet_vertex.id)

        # 更新任务状态
        guard.update_state(status="running_workflow")

        # 执行工作流
        workflow = Workflow(graph=graph)
        resp = run_async(workflow.run_until_vertex(post_tweet_vertex.id))
        
        # 在这里不需要手动更新任务状态，TaskStateGuard会自动处理
        # 成功完成时自动设置 is_running=False, pid=None, last_run=开始时间
        
        # 记录完成信息
        lgr.info(f'[Task {task_id}] Completed successfully')
        return resp


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
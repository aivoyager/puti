"""
@Author: obstacle
@Time: 25/07/24 15:16
@Description: Simplified Celery tasks for scheduler demos
"""
import asyncio
import json
import traceback
from datetime import datetime

from celery import shared_task
from croniter import croniter
from puti.logs import logger_factory
from puti.constant.base import TaskType

lgr = logger_factory.default


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
        from puti.db.schedule_manager import ScheduleManager
        manager = ScheduleManager()
        
        # 获取所有活跃的计划任务
        schedules = manager.get_active_schedules()
        lgr.info(f'Found {len(schedules)} active schedules')
        
        # 检查并更新所有任务的下次执行时间（实时计算）
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
                    manager.update_schedule(schedule.id, next_run=new_next_run)
                    lgr.info(f'Updated next_run for schedule "{schedule.name}" (ID: {schedule.id}) to {new_next_run}')
            except Exception as e:
                lgr.error(f'Error updating next_run for schedule {schedule.id}: {str(e)}')
        
        # 获取所有状态为"运行中"但已经完成的任务
        running_schedules = manager.get_running_schedules()
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
                    manager.update_schedule(schedule.id, is_running=False, pid=None)
        
        # 检查每个活跃的计划任务
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
                topic = params.get('topic')

                # Mark the task as running in the database
                manager.update_schedule(schedule.id, is_running=True)
                
                # 根据任务类型决定如何启动任务
                if hasattr(schedule, 'task_type') and schedule.task_type == TaskType.POST.val:
                    # 发推任务使用Graph Workflow
                    task = generate_tweet_task.delay(topic=topic, use_graph_workflow=True)
                    lgr.info(f'[Scheduler] Started task for "{schedule.name}" with Graph Workflow')
                else:
                    # 其他类型的任务使用基本模式
                    task = generate_tweet_task.delay(topic=topic)
                    lgr.info(f'[Scheduler] Started basic task for "{schedule.name}"')
                
                # Update the schedule's timestamps and task info in the database
                new_next_run = croniter(schedule.cron_schedule, now).get_next(datetime)
                schedule_updates = {
                    "last_run": now,
                    "next_run": new_next_run,
                    "task_id": task.id
                }
                manager.update_schedule(schedule.id, **schedule_updates)
                
                lgr.info(f'[Scheduler] Schedule "{schedule.name}" executed. Next run at {new_next_run}.')

    except Exception as e:
        lgr.error(f'[Scheduler] Error checking dynamic schedules: {str(e)}. {traceback.format_exc()}')

    return 'ok'


@shared_task(bind=True)
def generate_tweet_task(self, topic: str = None, use_graph_workflow: bool = False):
    """
    任务用于生成和发布推文。
    支持两种模式：简单模拟和使用Graph Workflow。
    
    Args:
        topic: 推文生成的主题
        use_graph_workflow: 是否使用Graph Workflow生成和发送推文
    """
    start_time = datetime.now()
    task_id = self.request.id
    
    try:
        # Find the schedule associated with this task
        from puti.db.schedule_manager import ScheduleManager
        manager = ScheduleManager()
        
        # Try to update running status 
        try:
            import os
            pid = os.getpid()
            
            # Try to find the schedule by task_id if we have one
            schedules = manager.get_all(where_clause="task_id = ?", params=(task_id,))
            if schedules:
                schedule = schedules[0]
                manager.update_schedule(schedule.id, pid=pid)
                lgr.info(f'[Task {task_id}] Updated schedule {schedule.name} with PID {pid}')
        except Exception as e:
            lgr.warning(f'Could not update PID for task {task_id}: {str(e)}')
        
        lgr.info(f'[Task {task_id}] generate_tweet_task started, topic: {topic}, use_graph_workflow: {use_graph_workflow}')
        
        # 根据模式选择不同的推文生成方式
        if use_graph_workflow:
            try:
                # 使用Graph Workflow生成推文
                import asyncio
                from puti.llm.roles.agents import Ethan
                from puti.llm.graph.ethan_graph import run_ethan_workflow
                
                # 直接在任务中运行Workflow
                async def run_workflow():
                    # 创建Ethan实例
                    ethan = Ethan()
                    # 将主题作为参数传递给Workflow
                    workflow_params = {}
                    if topic:
                        workflow_params["topic"] = topic
                    
                    # 运行Workflow
                    results = await run_ethan_workflow(ethan)
                    return results
                
                # 执行异步Workflow
                lgr.info(f'[Task {task_id}] Running Graph Workflow for tweet generation')
                results = asyncio.run(run_workflow())
                
                # 从Workflow结果中提取推文内容
                tweet_text = None
                if isinstance(results, dict):
                    if 'publish_tweet' in results:
                        publish_data = results['publish_tweet']
                        if isinstance(publish_data, dict) and 'content' in publish_data:
                            tweet_text = publish_data['content']
                    elif 'generate_and_review' in results:
                        gen_data = results['generate_and_review']
                        if isinstance(gen_data, dict) and 'content' in gen_data:
                            tweet_text = gen_data['content']
                
                # 如果无法从结果中提取内容，使用默认内容
                if not tweet_text:
                    tweet_text = f"Tweet about {topic or 'interesting topics'} generated via workflow"
                
                lgr.info(f'[Task {task_id}] Successfully generated tweet via Graph Workflow: {tweet_text}')
                
            except Exception as e:
                lgr.error(f'[Task {task_id}] Error using Graph Workflow: {str(e)}\n{traceback.format_exc()}')
                # 回退到简单模拟
                tweet_text = f"This is a simulated tweet about {topic if topic else 'something interesting'}! #simulation #demo"
                lgr.info(f'[Task {task_id}] Fallback to simulated tweet: {tweet_text}')
        else:
            # 简单模拟推文生成
            tweet_text = f"This is a simulated tweet about {topic if topic else 'something interesting'}! #simulation #demo"
            lgr.info(f'[Task {task_id}] Generated simulated tweet: {tweet_text}')
        
        # 模拟发布延迟
        import time
        time.sleep(2)
        
        lgr.info(f'[Task {task_id}] Simulated posting tweet to platform: "{tweet_text}"')
        
        # 任务完成，更新状态
        try:
            schedules = manager.get_all(where_clause="task_id = ?", params=(task_id,))
            if schedules:
                schedule = schedules[0]
                manager.update_schedule(schedule.id, is_running=False, pid=None)
                lgr.info(f'[Task {task_id}] Completed schedule {schedule.name} successfully')
        except Exception as e:
            lgr.warning(f'Could not update status for task {task_id}: {str(e)}')
        
        execution_time = (datetime.now() - start_time).total_seconds()
        lgr.info(f'[Task {task_id}] Completed in {execution_time:.2f} seconds')
        return {"status": "success", "tweet": tweet_text}
    except Exception as e:
        # 任务失败处理
        try:
            from puti.db.schedule_manager import ScheduleManager
            manager = ScheduleManager()
            schedules = manager.get_all(where_clause="task_id = ?", params=(task_id,))
            if schedules:
                schedule = schedules[0]
                manager.update_schedule(schedule.id, is_running=False, pid=None)
                lgr.error(f'[Task {task_id}] Failed schedule {schedule.name}: {str(e)}')
        except Exception as inner_e:
            lgr.warning(f'Could not update status for task {task_id}: {str(inner_e)}')
            
        lgr.error(f'[Task {task_id}] Failed: {str(e)}. {traceback.format_exc()}')
    finally:
        lgr.info(f'[Task {task_id}] Execution finished')
    return {"status": "error", "message": str(e) if 'e' in locals() else "Unknown error"}


@shared_task()
def auto_manage_scheduler():
    """
    自动管理调度器的状态。
    - 如果有活跃任务但调度器未运行，则启动调度器
    - 如果没有活跃任务且调度器正在运行，可以选择停止调度器（取决于配置）
    """
    try:
        from puti.db.schedule_manager import ScheduleManager
        from puti.scheduler import SchedulerDaemon
        
        manager = ScheduleManager()
        daemon = SchedulerDaemon()
        
        active_schedules = manager.get_active_schedules()
        running_schedules = manager.get_running_schedules()
        
        # 检查调度器是否需要启动
        if active_schedules and not daemon.is_running():
            lgr.info(f'Found {len(active_schedules)} active schedules but scheduler is not running. Starting scheduler...')
            daemon.start(activate_tasks=False)
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
"""
@Author: obstacle
@Time: 20/01/25 15:16
@Description:  
"""
import asyncio
import json
import traceback
import requests

from urllib.parse import quote
from datetime import datetime
from puti.logs import logger_factory
from celery import shared_task
from tenacity import retry, stop_after_attempt, wait_fixed, RetryCallState

from puti.conf.client_config import TwitterConfig
from puti.llm.roles.agents import CZ
from puti.llm.roles.x_bot import TwitWhiz
from puti.db.sqlite_operator import SQLiteOperator
from puti.db.model.task.bot_task import TweetSchedule
from puti.llm.actions.x_bot import GenerateTweetAction, PublishTweetAction
from puti.llm.roles.agents import Ethan
from puti.llm.workflow import Workflow
from puti.llm.graph import Graph, Vertex
from croniter import croniter

lgr = logger_factory.default
cz = CZ()
x_conf = TwitterConfig()
twit_whiz = TwitWhiz()
ethan = Ethan()


# @celery_app.task(task_always_eager=True)
def add(x, y):
    lgr.info('[任务] add 开始执行')
    try:
        result = x + y
        lgr.info(f'[任务] add 执行成功，结果: {result}')
        return result
    except Exception as e:
        lgr.error(f'[任务] add 执行失败: {e}')
        raise
    finally:
        lgr.info('[任务] add 执行结束')


# @celery_app.task(task_always_eager=False)
@shared_task()
def periodic_post_tweet():
    start_time = datetime.now()
    try:
        loop = asyncio.get_event_loop()
        tweet = loop.run_until_complete(cz.run('give me a tweet'))
        tweet = json.loads(tweet)['final_answer']
        lgr.debug(f'[定时任务] 准备发送推文内容: {tweet}')

        @retry(stop=stop_after_attempt(3), wait=wait_fixed(1), reraise=True)
        def safe_post_tweet():
            url = f"https://api.game.com/ai/xx-bot/twikit/post_tweet?text={quote(tweet)}"
            response = requests.post(url, timeout=10)
            response.raise_for_status()
            return response.text

        result = safe_post_tweet()
        lgr.debug('[定时任务] 耗时: {:.2f}s'.format((datetime.now() - start_time).total_seconds()))
        lgr.debug(f"[定时任务] 定时任务执行成功: {result}")
    except Exception as e:
        lgr.debug(f'[定时任务] 任务执行失败: {e.__class__.__name__} {str(e)}. {traceback.format_exc()}')
    finally:
        lgr.debug(f'============== [定时任务] periodic_post_tweet 执行结束 ==============')
    return 'ok'


@shared_task()
def periodic_get_mentions():
    start_time = datetime.now()
    try:
        url = f"https://api.game.com/ai/xx-bot/twikit/get_mentions?query_name={x_conf.USER_NAME}"
        lgr.debug(f'[定时任务] 请求接口: {url}')

        @retry(stop=stop_after_attempt(3), wait=wait_fixed(1), reraise=True)
        def safe_get_mentions():
            response = requests.post(url, timeout=10)
            response.raise_for_status()
            return response.text

        result = safe_get_mentions()
        lgr.debug('[定时任务] 耗时: {:.2f}s'.format((datetime.now() - start_time).total_seconds()))
        lgr.debug(f"[定时任务] get_mentions 执行成功: {result}")
    except Exception as e:
        lgr.debug(f'[定时任务] get_mentions 任务执行失败: {e.__class__.__name__} {str(e)}. {traceback.format_exc()}')
    finally:
        lgr.debug(f'============== [定时任务] periodic_get_mentions 执行结束 ==============')
    return 'ok'


@shared_task()
def periodic_reply_to_tweet():
    start_time = datetime.now()
    try:
        db = SQLiteOperator()
        sql = "SELECT text, author_id, mention_id FROM twitter_mentions WHERE replied=0 AND is_del=0"
        rows = db.fetchall(sql)
        lgr.debug(f'[定时任务] 查询待回复mentions数量: {len(rows)}')
        for row in rows:
            text, author_id, mention_id = row
            try:
                loop = asyncio.get_event_loop()
                reply = loop.run_until_complete(twit_whiz.run(text))
                reply_text = json.loads(reply).get('final_answer', '')
                if not reply_text:
                    lgr.debug(f'[定时任务] LLM未生成回复: {text}')
                    continue
                url = f"https://api.game.com/ai/xx-bot/twikit/reply_to_tweet?text={quote(reply_text)}&tweet_id={mention_id}&author_id={author_id}"
                lgr.debug(f'[定时任务] 请求接口: {url}')

                @retry(stop=stop_after_attempt(3), wait=wait_fixed(1), reraise=True)
                def safe_reply_to_tweet():
                    response = requests.post(url, timeout=10)
                    response.raise_for_status()
                    return response.text

                result = safe_reply_to_tweet()
                lgr.debug(f"[定时任务] reply_to_tweet 执行成功: {result}")

            except Exception as e:
                lgr.debug(f'[定时任务] 单条回复失败: {e.__class__.__name__} {str(e)}. {traceback.format_exc()}')
    except Exception as e:
        lgr.debug(f'[定时任务] reply_to_tweet 任务执行失败: {e.__class__.__name__} {str(e)}. {traceback.format_exc()}')
    finally:
        lgr.debug(f'============== [定时任务] periodic_reply_to_tweet 执行结束 ==============')
    return 'ok'


@shared_task()
def check_dynamic_schedules():
    """
    Checks for dynamic schedules in the database and triggers tasks as needed.
    This task is the heartbeat of the dynamic scheduler system and should be
    scheduled to run frequently (e.g., every minute).
    """
    now = datetime.now()
    lgr.debug(f'Checking dynamic schedules at {now}')

    try:
        # Use the schedule manager for better database interaction
        from puti.db.schedule_manager import ScheduleManager
        manager = ScheduleManager()
        
        # 1. 自动重置卡住的任务 (stuck tasks)
        running_schedules = manager.get_all(where_clause="is_running = 1 AND is_del = 0")
        stuck_timeout = datetime.timedelta(minutes=10)  # 10分钟超时
        
        for schedule in running_schedules:
            # updated_at 是自动更新的，我们检查它
            if schedule.updated_at and (now - schedule.updated_at > stuck_timeout):
                lgr.warning(f'Task "{schedule.name}" (ID: {schedule.id}) appears to be stuck. '
                            f'Last update was at {schedule.updated_at}. Resetting status.')
                # 即使模型中没有这些字段，我们仍可以通过字典更新数据库
                manager.update(schedule.id, {"is_running": False, "pid": None})
        
        # 2. 获取所有活跃的计划任务
        schedules = manager.get_all(where_clause="enabled = 1 AND is_del = 0")
        lgr.debug(f'Found {len(schedules)} active schedules to evaluate')
        
        # 3. 检查并触发到期的任务
        for schedule in schedules:
            # Skip schedules that are already running
            if getattr(schedule, 'is_running', False):
                lgr.debug(f'Schedule "{schedule.name}" is already running, skipping.')
                continue
                
            # A robust way to check if a task should have run.
            # We iterate from the last known run time up to the current time.
            # This ensures we don't miss runs if the service was down.
            last_run = getattr(schedule, 'last_run', None) or datetime.fromtimestamp(0)
            try:
                cron = croniter(schedule.cron_schedule, last_run)
                
                # Get the next scheduled run time based on the last execution
                next_run_time = cron.get_next(datetime)

                if next_run_time <= now:
                    lgr.info(f'[Scheduler] Triggering task for schedule "{schedule.name}" (ID: {schedule.id})')

                    # Extract parameters from the schedule
                    params = getattr(schedule, 'params', {}) or {}
                    topic = params.get('topic')

                    # Mark the task as running in the database
                    manager.update(schedule.id, {"is_running": True})
                    
                    # Asynchronously trigger the target task via Celery worker
                    task = generate_tweet_task.delay(topic=topic)
                    
                    # Update the schedule's timestamps and task info in the database
                    new_next_run = croniter(schedule.cron_schedule, now).get_next(datetime)
                    schedule_updates = {
                        "last_run": now,
                        "next_run": new_next_run,
                        "task_id": task.id
                    }
                    manager.update(schedule.id, schedule_updates)
                    
                    lgr.info(f'[Scheduler] Schedule "{schedule.name}" executed. Next run at {new_next_run}.')
            except Exception as e:
                lgr.error(f'Error processing schedule {schedule.id} ({schedule.name}): {str(e)}')
                # 尝试设置下一次运行时间
                try:
                    from croniter import croniter
                    new_next_run = croniter(schedule.cron_schedule, now).get_next(datetime)
                    manager.update(schedule.id, {"next_run": new_next_run, "is_running": False})
                    lgr.info(f'Reset next_run for schedule "{schedule.name}" to {new_next_run} after error')
                except Exception as inner_e:
                    lgr.error(f'Could not reset next_run for schedule {schedule.id}: {str(inner_e)}')

    except Exception as e:
        lgr.error(f'[Scheduler] Error checking dynamic schedules: {str(e)}. {traceback.format_exc()}')

    return 'ok'


@shared_task(bind=True)
def generate_tweet_task(self, topic: str = None):
    """
    Task that uses the test_generate_tweet_graph function to generate and post tweets.
    Accepts an optional topic to guide tweet generation.
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
                # 即使模型中没有pid字段，我们仍可以通过字典更新数据库
                manager.update(schedule.id, {"pid": pid})
                lgr.info(f'[Task {task_id}] Updated schedule {schedule.name} with PID {pid}')
        except Exception as e:
            lgr.warning(f'Could not update PID for task {task_id}: {str(e)}')
        
        lgr.info(f'[Task {task_id}] generate_tweet_task started, topic: {topic}')
        
        generate_tweet_action = GenerateTweetAction()
        post_tweet_action = PublishTweetAction()

        # Pass the topic to the action
        generate_tweet_vertex = Vertex(id='generate_tweet', action=generate_tweet_action, topic=topic)
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
                # 即使模型中没有is_running和pid字段，我们仍可以通过字典更新数据库
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
                # 即使模型中没有is_running和pid字段，我们仍可以通过字典更新数据库
                manager.update(schedule.id, {"is_running": False, "pid": None})
                lgr.error(f'[Task {task_id}] Failed schedule {schedule.name}: {str(e)}')
        except Exception as inner_e:
            lgr.warning(f'Could not update status for task {task_id}: {str(inner_e)}')
            
        lgr.error(f'[Task {task_id}] Failed: {str(e)}. {traceback.format_exc()}')
    finally:
        lgr.info(f'[Task {task_id}] Execution finished')
    return 'ok'

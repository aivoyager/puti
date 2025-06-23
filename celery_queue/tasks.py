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
from puti.llm.roles.agents import EthanG
from puti.llm.workflow import Workflow
from puti.llm.graph import Graph, Vertex
from croniter import croniter

lgr = logger_factory.default
cz = CZ()
x_conf = TwitterConfig()
twit_whiz = TwitWhiz()
ethan = EthanG()


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
async def generate_tweet_task(topic: str = None):
    """
    Task that uses the test_generate_tweet_graph function to generate and post tweets.
    Accepts an optional topic to guide tweet generation.
    """
    start_time = datetime.now()
    try:
        lgr.info(f'[定时任务] generate_tweet_task 开始执行')
        
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
        resp = await workflow.run_until_vertex(post_tweet_vertex.id)
        
        lgr.info(f'[定时任务] 生成推文任务执行完成，耗时: {(datetime.now() - start_time).total_seconds():.2f}秒')
        lgr.info(f'[定时任务] 生成推文结果: {resp}')
        return resp
    except Exception as e:
        lgr.error(f'[定时任务] 生成推文任务执行失败: {e.__class__.__name__} {str(e)}. {traceback.format_exc()}')
    finally:
        lgr.info(f'============== [定时任务] generate_tweet_task 执行结束 ==============')
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
        db = SQLiteOperator()
        # Use the model manager for a cleaner DB interaction
        from puti.db.schedule_manager import ScheduleManager
        manager = ScheduleManager(model_type=TweetSchedule, db_operator=db)
        
        schedules = manager.get_all(where_clause="enabled = 1 AND is_del = 0")

        for schedule in schedules:
            # A robust way to check if a task should have run.
            # We iterate from the last known run time up to the current time.
            # This ensures we don't miss runs if the service was down.
            cron = croniter(schedule.cron_schedule, schedule.last_run or datetime.fromtimestamp(0))
            
            # Get the next scheduled run time based on the last execution
            next_run_time = cron.get_next(datetime)

            if next_run_time <= now:
                lgr.info(f'[Scheduler] Triggering task for schedule "{schedule.name}" (ID: {schedule.id})')

                # Asynchronously trigger the target task via Celery worker
                generate_tweet_task.delay(topic=schedule.task_parameters.get('topic'))

                # Update the schedule's timestamps in the database
                new_next_run = croniter(schedule.cron_schedule, now).get_next(datetime)
                schedule_updates = {
                    "last_run": now,
                    "next_run": new_next_run
                }
                manager.update(schedule.id, schedule_updates)
                
                lgr.info(f'[Scheduler] Schedule "{schedule.name}" executed. Next run at {new_next_run}.')

    except Exception as e:
        lgr.error(f'[Scheduler] Error checking dynamic schedules: {str(e)}. {traceback.format_exc()}')

    return 'ok'

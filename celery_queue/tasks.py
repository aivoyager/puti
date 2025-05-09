"""
@Author: obstacle
@Time: 20/01/25 15:16
@Description:  
"""
import asyncio
import time
import json
import traceback

from datetime import datetime
from celery_queue.celery_app import celery_app
from db.model.task.bot_task import BotTask
from logs import logger_factory
from constant.base import TaskPostType
from client.twitter.x_api import TwitterAPI
from conf.client_config import TwitterConfig
from celery.schedules import crontab
from celery import shared_task
from llm.roles.cz import CZ
from tenacity import retry, stop_after_attempt, wait_fixed, RetryCallState


lgr = logger_factory.default
cz = CZ()


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

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1), reraise=True)
    def post_tweet(retry_state: RetryCallState = None):
        attempt_number = retry_state.attempt_number if retry_state else 1

        lgr.debug(f'============== [定时任务] periodic_post_tweet 开始执行第{attempt_number}次 ==============')
        try:
            loop = asyncio.get_event_loop()
            tweet = loop.run_until_complete(cz.run('give me a tweet'))
            tweet = json.loads(tweet)['final_answer']

            lgr.debug(f'[定时任务] 准备发送推文内容: {tweet}')
            result = loop.run_until_complete(api.post_tweet(tweet))
            lgr.debug('[定时任务] 耗时: {:.2f}s'.format(
                (datetime.now() - start_time).total_seconds()
            ))
            lgr.debug(f"[定时任务] 定时任务第{attempt_number}次执行成功: {result}")
        except Exception as e:
            lgr.debug(f'[定时任务] 任务第{attempt_number}次执行失败: {e.__class__.__name__} {str(e)}. {traceback.format_exc()}')
        finally:
            lgr.debug(f'============== [定时任务] periodic_post_tweet 第{attempt_number}次执行结束 ==============')

    api = TwitterAPI()
    start_time = datetime.now()
    post_tweet()
    return 'ok'

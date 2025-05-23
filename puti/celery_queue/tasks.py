"""
@Author: obstacle
@Time: 20/01/25 15:16
@Description:  
"""
import asyncio
import time
import json
import traceback
import requests

from urllib.parse import quote
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
from llm.roles.x_bot import TwitWhiz
from tenacity import retry, stop_after_attempt, wait_fixed, RetryCallState

lgr = logger_factory.default
cz = CZ()
x_conf = TwitterConfig()
twit_whiz = TwitWhiz()


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
    from db.operator import MysqlOperator
    try:
        db = MysqlOperator()
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

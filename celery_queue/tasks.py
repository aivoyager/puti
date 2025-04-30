"""
@Author: obstacle
@Time: 20/01/25 15:16
@Description:  
"""
import asyncio
import time

from datetime import datetime
from celery_queue.celery_app import celery_app
from db.model.task.bot_task import BotTask
from logs import logger_factory
from constant.base import TaskPostType
from client.twitter.x_api import TwitterAPI
from conf.client_config import TwitterConfig
from celery.schedules import crontab

lgr = logger_factory.default


@celery_app.task(task_always_eager=True)
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


@celery_app.task(task_always_eager=True)
def periodic_post_tweet():
    config = TwitterConfig()
    api = TwitterAPI(config)
    lgr.info('[定时任务] periodic_post_tweet 开始执行')
    try:
        content = "定时自动推文：Hello, Twitter!"
        lgr.debug(f'[定时任务] 准备发送推文内容: {content}')
        lgr.debug('[定时任务] 请求开始时间戳: {}'.format(datetime.now().isoformat()))
        start_time = datetime.now()
        result = api.post_tweet(content)
        lgr.debug('[定时任务] 请求结束时间戳: {} 耗时: {:.2f}s'.format(
            datetime.now().isoformat(), 
            (datetime.now() - start_time).total_seconds()
        ))
        lgr.debug(f'[定时任务] TwitterAPI返回原始结果: {result}')
        lgr.info(f"[定时任务] 定时发推成功: {result}")
    except Exception as e:
        lgr.error(f"[定时任务] 定时发推失败: {e}")
        lgr.debug(f'[定时任务] 异常详细信息: {e.__class__.__name__} {str(e)}')
    finally:
        lgr.info('[定时任务] periodic_post_tweet 执行结束')

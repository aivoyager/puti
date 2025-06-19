"""
@Author: obstacle
@Time: 20/01/25 15:16
@Description:  
"""
import asyncio
import json
import traceback
import requests
import sys
import os
from celery import shared_task, Task
from typing import List, Dict, Any
from puti.constant.base import Pathh
from puti.utils.path import root_dir
from puti.llm.roles.agents import Ethan
from puti.llm.graph.ethan_graph import run_ethan_workflow
from celery.utils.log import get_task_logger

from urllib.parse import quote
from datetime import datetime
from puti.logs import logger_factory
from tenacity import retry, stop_after_attempt, wait_fixed, RetryCallState

from puti.conf.client_config import TwitterConfig
from puti.llm.roles.agents import CZ
from puti.llm.roles.x_bot import TwitWhiz
# from puti.db.mysql_operator import MysqlOperator

lgr = logger_factory.default
cz = CZ()
x_conf = TwitterConfig()
twit_whiz = TwitWhiz()

# Set up logging
logger = get_task_logger(__name__)

# Add project root to Python path to ensure imports work correctly
if str(Pathh.ROOT_DIR.val) not in sys.path:
    sys.path.append(str(Pathh.ROOT_DIR.val))


class AsyncTask(Task):
    """Base class for tasks that run async code"""
    
    def run_async(self, *args, **kwargs):
        """Override this method to implement the task's async logic"""
        raise NotImplementedError("Subclasses must implement run_async")
    
    def __call__(self, *args, **kwargs):
        """Run the async task using asyncio"""
        return asyncio.run(self.run_async(*args, **kwargs))


@shared_task(bind=True, base=AsyncTask)
class RunEthanTweetingTask(AsyncTask):
    """Task to run Ethan's daily tweeting workflow"""
    
    name = 'run_ethan_tweeting'
    
    async def run_async(self, save_results: bool = True) -> Dict[str, Any]:
        """
        Executes Ethan's workflow to generate and post a tweet.
        
        Args:
            save_results: If True, save workflow results to a JSON file
            
        Returns:
            Dict containing workflow results
        """
        try:
            logger.info("Starting Ethan's daily tweet workflow")
            
            # Create Ethan instance
            ethan = Ethan()
            
            # Run workflow
            save_path = os.path.join(str(Pathh.ROOT_DIR.val), "data", "ethan_tweets",
                                    f"tweet_{asyncio.get_event_loop().time()}.json") if save_results else None
            
            results = await run_ethan_workflow(ethan, save_path)
            
            logger.info(f"Ethan's tweet workflow completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Error in Ethan's tweet workflow: {str(e)}")
            logger.error(traceback.format_exc())
            raise


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

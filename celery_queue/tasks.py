"""
@Author: obstacle
@Time: 20/01/25 15:16
@Description:  
"""
from celery_queue.celery_app import celery_app
from db.model.task.bot_task import BotTask
from logs import logger_factory
from constant.base import TaskPostType
from llm.comfy_ui_client import comfyui_client

lgr = logger_factory.default


@celery_app.task
def add(x, y):
    return x + y


@celery_app.task()
def consumer_post_tweet(task: BotTask):
    lgr.info("consumer post task")

    prompt = ""
    image_paths = []
    if task.post_type == TaskPostType.TEXT:
        prompt = "Generate a tweet"
    if task.post_type == TaskPostType.IMAGE:
        prompt = "Generate a tweet"
        image_path = comfyui_client.generate_sheldon()
        image_paths.append(image_path)
    try:
        response = send_chat_request(prompt, chat_type=1, bot_name=twitter_client.my_name, history_len=10, stream=False,
                                     max_tokens=160)
        content, media, error = parse_result(response)
        if error:
            xlog.e(error)
            return
        result = await twitter_client.post_tweet(content, image_path=image_paths)
        if result.status != 200:
            xlog.i(result.message)
        else:
            xlog.e(result.message)
        xlog.i("*" * 100)
    except Exception as e:
        xlog.e(e)
    await asyncio.sleep(60 * random.randint(20, 30))


async def consumer_reply_tweet(task: BotTask):
    xlog.i("process reply tweet")
    try:
        xlog.i("*" * 100)
        tweets = task.replay_tweet
        for index, tweet in enumerate(tweets):
            xlog.i(f"{index} of {len(tweets)} reply")
            if tweet.text == "":
                tweet_tracker.replied_tweet(tweet.id)
                xlog.i("No need reply tweet is empty")
                continue
            xlog.i(f"tweet text {tweet.text}")
            history = tweet_tracker.get_history(tweet.id, twitter_client.my_id)
            if history is None:
                xlog.e("No history")
                continue
            if len(history) == 1:
                # tweet_tracker.replied_tweet(tweet.id)
                # xlog.i(f"process reply tweet history is 1 flag to reply | link = https://twitter.com/i/web/status/{tweet.id} ")
                # continue
                response = send_agent_request(history[-1]['content'], bot_name=twitter_client.my_name, history_len=10,
                                              stream=False, max_tokens=160, use_tools=["flux"])
            else:
                response = send_agent_request(history[-1]['content'], bot_name=twitter_client.my_name, history_len=10,
                                              stream=False, max_tokens=160, history=history[:-1], use_tools=["flux"])
            content, media, error = parse_result(response)
            if error:
                xlog.e(error)
                continue
            await asyncio.sleep(random.randint(15, 20))
            # twitter_api_client.reply_to_tweet(reply_text, tweet.id, tweet.author_id)
            result = await twitter_client.reply_to_tweet(content, media, tweet.id, tweet.author_id)
            if result.status != 200:
                xlog.e(result.message)
            else:
                xlog.i(result.message)
                tweet_tracker.replied_tweet(tweet.id)
            xlog.i("=" * 100)
        xlog.i("*" * 100)
    except Exception as e:
        xlog.e(f'Exception when process reply {e}')
        traceback.print_exc()
    # 如果下一个是post的任务，需要等待
    await asyncio.sleep(random.randint(30, 60))

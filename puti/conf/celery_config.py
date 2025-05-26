"""
@Author: obstacle
@Time: 20/01/25 15:45
@Description:  
"""
import platform

from celery.schedules import crontab
from puti.conf.celery_private_conf import CeleryPrivateConfig

c = CeleryPrivateConfig()

# broker_url = 'redis://127.0.0.1:6379/0'
# if platform.system().lower() == 'linux':
broker_url = c.BROKER_URL
# else:
#     broker_url = 'amqp://guest:guest@localhost//'
result_backend = c.RESULT_BACKEND_URL
# result_backend = 'redis://127.0.0.1:6379/0'
# result_backend = 'amqp://guest:guest@localhost//'
result_expires = 3600
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'Asia/Shanghai'
task_always_eager = True
task_eager_propagates = True
enable_utc = False
max_retries = 0
retry_delay = 3

# 设置日志级别
worker_log_level = 'INFO'
beat_log_level = 'INFO'

beat_schedule = {
    'periodic-post-tweet': {
        'task': 'celery_queue.tasks.periodic_post_tweet',
        'schedule': crontab(hour=8, minute=0),
        'args': ()
    },
    'periodic-get-mentions': {
        'task': 'celery_queue.tasks.periodic_get_mentions',
        'schedule': crontab(minute='*/5'),
        'args': ()
    },
    'periodic-reply-to-tweet': {
        'task': 'celery_queue.tasks.periodic_reply_to_tweet',
        'schedule': crontab(minute='*/5'),
        'args': ()
    }
}
broker_transport_options = {
    'visibility_timeout': 600,
    'max_retries': 3,
    'interval_start': 0,
    'interval_step': 0.2
}

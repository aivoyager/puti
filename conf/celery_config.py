"""
@Author: obstacle
@Time: 20/01/25 15:45
@Description:  
"""
from celery.schedules import crontab


# broker_url = 'redis://127.0.0.1:6379/0'
broker_url = 'amqp://guest:guest@localhost//'
result_backend = 'redis://127.0.0.1:6379/0'
# result_backend = 'amqp://guest:guest@localhost//'
result_expires = 3600
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'Asia/Shanghai'
task_eager_propagates = True
enable_utc = False
max_retries = 3
retry_delay = 3

# 设置日志级别
worker_log_level = 'INFO'
beat_log_level = 'INFO'

beat_schedule = {
    'periodic-post-tweet-every-5min': {
        'task': 'celery_queue.tasks.periodic_post_tweet',
        'schedule': crontab(minute='*/1'),
        'args': ()
    }
}
broker_transport_options = {
    'visibility_timeout': 600,
    'max_retries': 3,
    'interval_start': 0,
    'interval_step': 0.2
}
